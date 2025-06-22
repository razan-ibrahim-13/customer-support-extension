from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
from datetime import datetime

class CrawlRequest(BaseModel):
    domain: str
    start_urls: Optional[List[str]] = None
    categories: List[str] = ["cancellation", "refund", "billing", "support"]

class DocumentChunk(BaseModel):
    content: str
    title: str
    url: str
    category: str
    metadata: Dict = {}

class QueryRequest(BaseModel):
    question: str
    domain: str
    context: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, str]]
    confidence: float
    suggested_actions: List[str] = []

class CrawlStatus(BaseModel):
    domain: str
    status: str  # "crawling", "completed", "error" 
    pages_found: int
    last_updated: datetime