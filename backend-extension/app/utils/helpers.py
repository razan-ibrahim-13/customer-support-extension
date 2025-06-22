"""
Utility functions for the Customer Support Agent backend.

This module contains helper functions used across different services
for URL handling, text processing, content validation, and other common tasks.
"""

import re
import hashlib
import urllib.parse
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup, Comment
import tldextract
import logging

logger = logging.getLogger(__name__)


# URL and Domain Utilities
def normalize_url(url: str, base_domain: str = None) -> str:
    """
    Normalize URL by adding protocol, removing fragments, and standardizing format.
    
    Args:
        url: URL to normalize
        base_domain: Base domain for relative URLs
    
    Returns:
        Normalized URL string
    """
    url = url.strip()
    
    # Handle relative URLs
    if url.startswith('/') and base_domain:
        url = f"https://{base_domain.rstrip('/')}{url}"
    elif not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    # Parse and rebuild URL
    parsed = urllib.parse.urlparse(url)
    
    # Remove fragment and normalize
    normalized = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip('/') if parsed.path != '/' else '/',
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    return normalized


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        extracted = tldextract.extract(url)
        return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        return urllib.parse.urlparse(url).netloc


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs belong to the same domain."""
    return extract_domain(url1) == extract_domain(url2)


def generate_url_patterns(domain: str) -> List[str]:
    """
    Generate common support documentation URL patterns for a domain.
    
    Args:
        domain: Base domain
    
    Returns:
        List of potential support URLs
    """
    base_url = f"https://{domain}"
    patterns = [
        f"{base_url}/help",
        f"{base_url}/support",
        f"{base_url}/faq",
        f"{base_url}/docs",
        f"{base_url}/documentation",
        f"{base_url}/knowledge-base",
        f"{base_url}/kb",
        f"{base_url}/customer-service",
        f"{base_url}/terms",
        f"{base_url}/privacy",
        f"{base_url}/refund",
        f"{base_url}/cancellation",
        f"{base_url}/billing",
        f"{base_url}/contact",
        f"{base_url}/about/support",
        f"{base_url}/help-center",
        f"{base_url}/support-center",
    ]
    return patterns


# Text Processing Utilities
def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common HTML entities
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&apos;': "'",
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    return text


def extract_text_from_html(html: str) -> str:
    """
    Extract clean text from HTML content.
    
    Args:
        html: HTML content
    
    Returns:
        Cleaned text content
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
        
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Get text and clean it
        text = soup.get_text()
        return clean_text(text)
    
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        return ""


def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for processing.
    
    Args:
        text: Text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + max_chunk_size // 2:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = max(end - overlap, start + 1)
    
    return chunks


# Content Classification Utilities
def classify_support_content(text: str, url: str = "") -> Dict[str, float]:
    """
    Classify content by support category with confidence scores.
    
    Args:
        text: Content to classify
        url: URL context for additional hints
    
    Returns:
        Dictionary of categories with confidence scores
    """
    text_lower = text.lower()
    url_lower = url.lower()
    
    categories = {
        'cancellation': 0.0,
        'refund': 0.0,
        'billing': 0.0,
        'shipping': 0.0,
        'account': 0.0,
        'technical': 0.0,
        'general': 0.0
    }
    
    # Keyword patterns for each category
    patterns = {
        'cancellation': [
            'cancel', 'subscription', 'terminate', 'end service',
            'stop billing', 'discontinue', 'unsubscribe'
        ],
        'refund': [
            'refund', 'money back', 'return', 'reimbursement',
            'chargeback', 'credit', 'partial refund'
        ],
        'billing': [
            'billing', 'payment', 'invoice', 'charge', 'fee',
            'credit card', 'subscription', 'auto-renew'
        ],
        'shipping': [
            'shipping', 'delivery', 'tracking', 'package',
            'shipment', 'carrier', 'address'
        ],
        'account': [
            'account', 'profile', 'login', 'password', 'username',
            'settings', 'personal information'
        ],
        'technical': [
            'error', 'bug', 'not working', 'technical', 'support',
            'troubleshoot', 'issue', 'problem'
        ]
    }
    
    # Score based on keyword matches
    for category, keywords in patterns.items():
        score = 0
        for keyword in keywords:
            score += text_lower.count(keyword)
            score += url_lower.count(keyword) * 0.5  # URL context bonus
        
        categories[category] = min(score / len(text_lower) * 100, 1.0)
    
    # Default to general if no strong category match
    if max(categories.values()) < 0.1:
        categories['general'] = 1.0
    
    return categories


# Content Validation Utilities
def is_valid_support_content(text: str, min_length: int = 50) -> bool:
    """
    Validate if content is meaningful support documentation.
    
    Args:
        text: Content to validate
        min_length: Minimum text length
    
    Returns:
        True if content appears to be valid support content
    """
    if not text or len(text.strip()) < min_length:
        return False
    
    # Check for navigation/menu content
    nav_indicators = [
        'home', 'about', 'contact', 'menu', 'navigation',
        'copyright', '©', 'all rights reserved', 'privacy policy'
    ]
    
    text_lower = text.lower()
    nav_count = sum(1 for indicator in nav_indicators if indicator in text_lower)
    
    # If mostly navigation content, reject
    if nav_count > len(text.split()) * 0.1:
        return False
    
    # Check for meaningful support keywords
    support_keywords = [
        'help', 'support', 'how to', 'faq', 'question', 'answer',
        'policy', 'terms', 'service', 'customer', 'guide', 'tutorial'
    ]
    
    keyword_count = sum(1 for keyword in support_keywords if keyword in text_lower)
    
    return keyword_count > 0


def extract_contact_info(text: str) -> Dict[str, List[str]]:
    """
    Extract contact information from text.
    
    Args:
        text: Text to search for contact info
    
    Returns:
        Dictionary with emails, phones, and addresses
    """
    contact_info = {
        'emails': [],
        'phones': [],
        'addresses': []
    }
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    contact_info['emails'] = list(set(re.findall(email_pattern, text)))
    
    # Phone pattern (various formats)
    phone_patterns = [
        r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
        r'\b\(\d{3}\)\s*\d{3}-\d{4}\b',  # (123) 456-7890
        r'\b\d{3}\.\d{3}\.\d{4}\b',  # 123.456.7890
        r'\b\+\d{1,3}\s*\d{3,4}\s*\d{3,4}\s*\d{4}\b'  # International
    ]
    
    phones = []
    for pattern in phone_patterns:
        phones.extend(re.findall(pattern, text))
    contact_info['phones'] = list(set(phones))
    
    return contact_info


# Caching and Hashing Utilities
def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash for content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def is_content_fresh(last_updated: datetime, max_age_hours: int = 24) -> bool:
    """Check if content is within freshness threshold."""
    if not last_updated:
        return False
    
    age = datetime.now() - last_updated
    return age < timedelta(hours=max_age_hours)


# Rate Limiting Utilities
class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def can_request(self, key: str) -> bool:
        """Check if request is allowed for given key."""
        now = datetime.now()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > cutoff
        ]
        
        return len(self.requests[key]) < self.max_requests
    
    def record_request(self, key: str):
        """Record a request for the given key."""
        if key not in self.requests:
            self.requests[key] = []
        
        self.requests[key].append(datetime.now())


# Robots.txt Utilities
def can_crawl_url(url: str, user_agent: str = "*") -> bool:
    """
    Check if URL can be crawled according to robots.txt.
    
    Args:
        url: URL to check
        user_agent: User agent string
    
    Returns:
        True if crawling is allowed
    """
    try:
        from urllib.robotparser import RobotFileParser
        
        parsed_url = urllib.parse.urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        
        return rp.can_fetch(user_agent, url)
    
    except Exception as e:
        logger.warning(f"Could not check robots.txt for {url}: {e}")
        return True  # Default to allowing if robots.txt unavailable


# Error Handling Utilities
def safe_request(url: str, timeout: int = 10, **kwargs) -> Optional[requests.Response]:
    """
    Make a safe HTTP request with error handling.
    
    Args:
        url: URL to request
        timeout: Request timeout in seconds
        **kwargs: Additional requests parameters
    
    Returns:
        Response object or None if failed
    """
    try:
        headers = kwargs.get('headers', {})
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'Support-Agent-Crawler/1.0'
            kwargs['headers'] = headers
        
        response = requests.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return None


# Data Processing Utilities
def merge_duplicate_content(contents: List[Dict]) -> List[Dict]:
    """
    Remove duplicate content based on text similarity.
    
    Args:
        contents: List of content dictionaries with 'text' key
    
    Returns:
        List with duplicates removed
    """
    if not contents:
        return []
    
    unique_contents = []
    seen_hashes = set()
    
    for content in contents:
        content_hash = generate_content_hash(content.get('text', ''))
        
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_contents.append(content)
    
    return unique_contents


def prioritize_content(contents: List[Dict], domain: str) -> List[Dict]:
    """
    Prioritize content based on relevance and quality indicators.
    
    Args:
        contents: List of content dictionaries
        domain: Domain context for prioritization
    
    Returns:
        Sorted list of content by priority
    """
    def calculate_priority(content: Dict) -> float:
        score = 0.0
        
        url = content.get('url', '')
        text = content.get('text', '')
        title = content.get('title', '')
        
        # URL-based scoring
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in ['help', 'support', 'faq']):
            score += 3.0
        if any(keyword in url_lower for keyword in ['cancel', 'refund', 'billing']):
            score += 2.0
        
        # Title-based scoring
        title_lower = title.lower()
        if any(keyword in title_lower for keyword in ['help', 'support', 'faq']):
            score += 2.0
        
        # Content length scoring (moderate length preferred)
        text_len = len(text)
        if 100 <= text_len <= 2000:
            score += 1.0
        elif text_len > 2000:
            score += 0.5
        
        # Support keyword density
        support_keywords = ['help', 'support', 'how to', 'cancel', 'refund', 'billing']
        keyword_count = sum(1 for keyword in support_keywords if keyword in text.lower())
        score += keyword_count * 0.5
        
        return score
    
    # Sort by priority score (descending)
    return sorted(contents, key=calculate_priority, reverse=True)