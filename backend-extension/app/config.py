from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    google_api_key: str
    redis_url: str = "redis://localhost:6379"
    max_crawl_pages: int = 50
    crawl_delay: float = 1.0
    vector_db_path: str = "./chroma_db"
    
    class Config:
        env_file = ".env"

settings = Settings()