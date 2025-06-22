# app/services/agent.py
import google.generativeai as genai
from typing import List, Dict
import json
from app.config import settings
from app.models.schemas import QueryResponse
from app.services.processor import KnowledgeProcessor

# Configure Google AI
genai.configure(api_key=settings.google_api_key)

class CustomerSupportAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-pro')
        self.processor = KnowledgeProcessor()
        
    def _build_system_prompt(self) -> str:
        return """You are a helpful customer support agent. Your role is to:

1. Answer customer questions about cancellations, refunds, billing, and general support
2. Always base your answers on the provided documentation
3. Provide clear, step-by-step instructions when available
4. Include relevant contact information when appropriate
5. Be concise but comprehensive
6. If you cannot answer based on the provided docs, say so clearly

Format your response as:
- Direct answer to the question
- Step-by-step instructions if applicable
- Important notes or warnings
- Relevant contact information
- Source references

Always be helpful, accurate, and professional."""

    async def process_query(self, query: str, domain: str, context: str = None) -> QueryResponse:
        """Process user query and generate response"""
        
        # Search knowledge base
        relevant_docs = self.processor.search_knowledge(domain, query, n_results=3)
        
        if not relevant_docs:
            return QueryResponse(
                answer="I couldn't find specific information about your question in this site's documentation. Please contact their support team directly.",
                sources=[],
                confidence=0.1,
                suggested_actions=["Contact customer support directly"]
            )
        
        # Build context from relevant documents
        doc_context = "\n\n---\n\n".join([
            f"Document: {doc['metadata'].get('title', 'Untitled')}\n"
            f"URL: {doc['metadata'].get('url', 'N/A')}\n"
            f"Content: {doc['content']}"
            for doc in relevant_docs
        ])
        
        # Build prompt
        prompt = f"""
{self._build_system_prompt()}

QUESTION: {query}

RELEVANT DOCUMENTATION:
{doc_context}

ADDITIONAL CONTEXT: {context or 'None'}

Please provide a helpful response based on the documentation above.
"""

        try:
            response = self.model.generate_content(prompt)
            answer = response.text
            
            # Extract sources
            sources = [
                {
                    "title": doc['metadata'].get('title', 'Untitled'),
                    "url": doc['metadata'].get('url', ''),
                    "category": doc['metadata'].get('category', 'general')
                }
                for doc in relevant_docs
            ]
            
            # Generate suggested actions
            suggested_actions = self._generate_actions(query, answer)
            
            # Calculate confidence based on document relevance
            confidence = min(0.9, max(0.3, 1.0 - min(doc['distance'] for doc in relevant_docs)))
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                confidence=confidence,
                suggested_actions=suggested_actions
            )
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return QueryResponse(
                answer="I encountered an error processing your question. Please try again or contact support directly.",
                sources=[],
                confidence=0.1,
                suggested_actions=["Try rephrasing your question", "Contact support directly"]
            )
    
    def _generate_actions(self, query: str, answer: str) -> List[str]:
        """Generate suggested actions based on query and response"""
        actions = []
        
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        if 'cancel' in query_lower:
            actions.append("Go to Account Settings")
            if 'contact' in answer_lower:
                actions.append("Contact Support")
        
        if 'refund' in query_lower:
            actions.append("Check refund eligibility")
            actions.append("Prepare order details")
        
        if 'billing' in query_lower or 'payment' in query_lower:
            actions.append("Review billing information")
            actions.append("Check payment methods")
        
        # Default actions
        if not actions:
            actions = ["Contact customer support", "Check account settings"]
        
        return actions[:3]  # Limit to 3 actions