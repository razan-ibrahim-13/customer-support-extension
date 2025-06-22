
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Set, Dict
from urllib.parse import urljoin, urlparse
import re
from app.config import settings
from app.models.schemas import DocumentChunk

class SupportDocumentCrawler:
    def __init__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        self.crawled_urls: Set[str] = set()
        
    async def discover_support_urls(self, domain: str) -> List[str]:
        """Discover support documentation URLs"""
        base_url = f"https://{domain}"
        support_patterns = [
            "/help", "/support", "/faq", "/docs", "/documentation",
            "/customer-service", "/billing", "/cancellation", "/refund"
        ]
        
        discovered_urls = []
        
        # Try common support URL patterns
        for pattern in support_patterns:
            url = urljoin(base_url, pattern)
            try:
                response = await self.session.get(url)
                if response.status_code == 200:
                    discovered_urls.append(url)
            except:
                continue
                
        # Try to find sitemap
        try:
            sitemap_url = urljoin(base_url, "/sitemap.xml")
            response = await self.session.get(sitemap_url)
            if response.status_code == 200:
                urls = self._parse_sitemap(response.text)
                discovered_urls.extend([u for u in urls if any(p in u.lower() for p in support_patterns)])
        except:
            pass
            
        return discovered_urls[:settings.max_crawl_pages]
    
    def _parse_sitemap(self, sitemap_content: str) -> List[str]:
        """Extract URLs from sitemap"""
        soup = BeautifulSoup(sitemap_content, 'xml')
        return [loc.text for loc in soup.find_all('loc')]
    
    async def crawl_page(self, url: str) -> DocumentChunk:
        """Crawl a single support page"""
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script, style, nav elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            title = soup.find('title')
            title = title.text.strip() if title else ""
            
            # Extract main content
            content_selectors = ['main', 'article', '.content', '#content', '.support-content']
            content = ""
            
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator='\n', strip=True)
                    break
            
            if not content:
                content = soup.get_text(separator='\n', strip=True)
            
            # Categorize content
            category = self._categorize_content(title + " " + content)
            
            return DocumentChunk(
                content=content[:2000],  # Limit content size
                title=title,
                url=url,
                category=category,
                metadata={"scraped_at": str(asyncio.get_event_loop().time())}
            )
            
        except Exception as e:
            print(f"Error crawling {url}: {e}")
            return None
    
    def _categorize_content(self, text: str) -> str:
        """Categorize support content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['cancel', 'cancellation', 'unsubscribe']):
            return 'cancellation'
        elif any(word in text_lower for word in ['refund', 'money back', 'return']):
            return 'refund' 
        elif any(word in text_lower for word in ['billing', 'payment', 'charge', 'invoice']):
            return 'billing'
        elif any(word in text_lower for word in ['shipping', 'delivery', 'tracking']):
            return 'shipping'
        else:
            return 'general'
    
    async def crawl_domain(self, domain: str) -> List[DocumentChunk]:
        """Crawl all support documents for a domain"""
        urls = await self.discover_support_urls(domain)
        chunks = []
        
        for url in urls:
            if url not in self.crawled_urls:
                chunk = await self.crawl_page(url)
                if chunk:
                    chunks.append(chunk)
                self.crawled_urls.add(url)
                await asyncio.sleep(settings.crawl_delay)  # Rate limiting
        
        return chunks
    
    async def close(self):
        await self.session.aclose()