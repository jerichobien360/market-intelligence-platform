from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Market Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    DEBUG: bool = False
    
    # Scraping settings
    SCRAPING_DELAY: int = 2
    MAX_CONCURRENT_SCRAPERS: int = 5
    USER_AGENT: str = "MarketIntel-Bot/1.0"
    
    class Config:
        env_file = ".env"

settings = Settings()
