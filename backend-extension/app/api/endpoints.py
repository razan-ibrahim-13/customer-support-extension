
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict
import redis
import json
from datetime import datetime

from app.models.schemas import CrawlRequest, QueryRequest, QueryResponse, CrawlStatus
from app.services.crawler import SupportDocumentCrawler
from app.services.processor import KnowledgeProcessor
from app.services.agent import CustomerSupportAgent
from app.config import settings

router = APIRouter()

# Redis client for background task tracking
redis_client = redis.from_url(settings.redis_url)

# Service instances
crawler = SupportDocumentCrawler()
processor = KnowledgeProcessor()
agent = CustomerSupportAgent()

async def background_crawl_task(domain: str):
    """Background task to crawl and process documents"""
    try:
        # Update status to crawling
        status = CrawlStatus(
            domain=domain,
            status="crawling",
            pages_found=0,
            last_updated=datetime.now()
        )
        redis_client.set(f"crawl_status:{domain}", status.model_dump_json(), ex=3600)
        
        # Crawl documents
        chunks = await crawler.crawl_domain(domain)
        
        # Process and store documents
        await processor.process_documents(domain, chunks)
        
        # Update status to completed
        status.status = "completed"
        status.pages_found = len(chunks)
        status.last_updated = datetime.now()
        redis_client.set(f"crawl_status:{domain}", status.model_dump_json(), ex=3600)
        
    except Exception as e:
        # Update status to error
        status = CrawlStatus(
            domain=domain,
            status="error",
            pages_found=0,
            last_updated=datetime.now()
        )
        redis_client.set(f"crawl_status:{domain}", status.model_dump_json(), ex=3600)
        print(f"Crawl task error for {domain}: {e}")

@router.post("/crawl", response_model=Dict[str, str])
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """Start crawling a domain's support documentation"""
    
    # Check if already crawling
    existing_status = redis_client.get(f"crawl_status:{request.domain}")
    if existing_status:
        status_data = json.loads(existing_status)
        if status_data['status'] == 'crawling':
            raise HTTPException(status_code=409, detail="Crawl already in progress for this domain")
    
    # Start background crawl task
    background_tasks.add_task(background_crawl_task, request.domain)
    
    return {"message": f"Started crawling {request.domain}", "domain": request.domain}

@router.get("/crawl-status/{domain}", response_model=CrawlStatus)
async def get_crawl_status(domain: str):
    """Get crawling status for a domain"""
    
    status_data = redis_client.get(f"crawl_status:{domain}")
    if not status_data:
        raise HTTPException(status_code=404, detail="No crawl status found for this domain")
    
    return CrawlStatus(**json.loads(status_data))

@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a user query and return AI-generated response"""
    
    # Check if domain has been crawled
    status_data = redis_client.get(f"crawl_status:{request.domain}")
    if not status_data:
        raise HTTPException(
            status_code=404, 
            detail="Domain not found. Please crawl the domain first."
        )
    
    status = json.loads(status_data)
    if status['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Domain crawl status: {status['status']}. Please wait for crawling to complete."
        )
    
    # Process query
    response = await agent.process_query(
        query=request.question,
        domain=request.domain,
        context=request.context
    )
    
    return response

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

@router.get("/domains")
async def list_crawled_domains():
    """List all crawled domains"""
    keys = [key.decode() for key in redis_client.keys("crawl_status:*")]
    domains = []
    
    for key in keys:
        domain = key.replace("crawl_status:", "")
        status_data = redis_client.get(key)
        if status_data:
            status = json.loads(status_data)
            domains.append({
                "domain": domain,
                "status": status['status'],
                "pages_found": status['pages_found'],
                "last_updated": status['last_updated']
            })
    
    return {"domains": domains}