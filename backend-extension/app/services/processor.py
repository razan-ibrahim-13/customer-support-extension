
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import json
from app.models.schemas import DocumentChunk
from app.config import settings

class KnowledgeProcessor:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.vector_db_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
    def get_or_create_collection(self, domain: str):
        """Get or create collection for domain"""
        collection_name = f"support_docs_{domain.replace('.', '_')}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"domain": domain}
        )
    
    async def process_documents(self, domain: str, chunks: List[DocumentChunk]):
        """Process and store document chunks"""
        if not chunks:
            return
            
        collection = self.get_or_create_collection(domain)
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk.content)
            metadatas.append({
                "title": chunk.title,
                "url": chunk.url,
                "category": chunk.category,
                **chunk.metadata
            })
            ids.append(f"{domain}_{i}")
        
        # Generate embeddings
        embeddings = self.embedder.encode(documents).tolist()
        
        # Store in ChromaDB
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
    
    def search_knowledge(self, domain: str, query: str, n_results: int = 5) -> List[Dict]:
        """Search knowledge base for relevant documents"""
        try:
            collection = self.get_or_create_collection(domain)
            
            # Generate query embedding
            query_embedding = self.embedder.encode([query]).tolist()[0]
            
            # Search ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else 0
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return []
    
    def extract_key_info(self, content: str) -> Dict:
        """Extract key information from support content"""
        info = {
            'contact_methods': [],
            'deadlines': [],
            'requirements': [],
            'steps': []
        }
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Extract contact info
            if any(contact in line.lower() for contact in ['email', 'phone', 'contact']):
                info['contact_methods'].append(line)
            
            # Extract deadlines/timeframes
            if any(time in line.lower() for time in ['day', 'days', 'hour', 'week', 'month']):
                if any(action in line.lower() for action in ['within', 'before', 'after']):
                    info['deadlines'].append(line)
            
            # Extract numbered steps
            if line.startswith(('1.', '2.', '3.', '•', '-')):
                info['steps'].append(line)
        
        return info