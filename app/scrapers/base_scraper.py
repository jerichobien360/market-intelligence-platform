from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import time
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import redis
import json
import logging
from app.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    Provides common functionality like rate limiting, caching, and error handling.
    """
    
    def __init__(self, use_selenium: bool = False):
        self.use_selenium = use_selenium
        self.session = requests.Session()
        self.redis_client = redis.from_url(settings.REDIS_URL)
        
        # Configure requests session
        self.session.headers.update({
            'User-Agent': settings.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Selenium driver (initialized on demand)
        self.driver = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
        
        if self.session:
            self.session.close()
    
    def _get_selenium_driver(self) -> webdriver.Chrome:
        """Initialize and return Selenium Chrome driver"""
        if not self.driver:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={settings.USER_AGENT}')
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                raise
                
        return self.driver
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        delay = settings.SCRAPING_DELAY + random.uniform(0, 1)
        time.sleep(delay)
    
    def _get_cache_key(self, url: str, params: Dict = None) -> str:
        """Generate cache key for URL and parameters"""
        key_parts = [url]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        return f"scraper:cache:{hash(''.join(key_parts))}"
    
    def _get_cached_content(self, cache_key: str) -> Optional[str]:
        """Get cached content if available and not expired"""
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                # Check if cache is still valid (1 hour default)
                cached_time = datetime.fromisoformat(data['timestamp'])
                if (datetime.now() - cached_time).seconds < 3600:
                    return data['content']
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        return None
    
    def _cache_content(self, cache_key: str, content: str, ttl: int = 3600):
        """Cache content with timestamp"""
        try:
            cache_data = {
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")
    
    def fetch_page(self, url: str, use_cache: bool = True, **kwargs) -> Optional[str]:
        """
        Fetch page content using requests or Selenium
        
        Args:
            url: URL to fetch
            use_cache: Whether to use cached content
            **kwargs: Additional parameters for requests
            
        Returns:
            HTML content or None if failed
        """
        # Check cache first
        cache_key = self._get_cache_key(url, kwargs)
        if use_cache:
            cached_content = self._get_cached_content(cache_key)
            if cached_content:
                logger.info(f"Using cached content for {url}")
                return cached_content
        
        # Rate limiting
        self._rate_limit()
        
        try:
            if self.use_selenium:
                content = self._fetch_with_selenium(url, **kwargs)
            else:
                content = self._fetch_with_requests(url, **kwargs)
            
            # Cache the content
            if content and use_cache:
                self._cache_content(cache_key, content)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def _fetch_with_requests(self, url: str, **kwargs) -> Optional[str]:
        """Fetch using requests library"""
        try:
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Requests error for {url}: {e}")
            return None
    
    def _fetch_with_selenium(self, url: str, wait_for: str = None, **kwargs) -> Optional[str]:
        """Fetch using Selenium WebDriver"""
        try:
            driver = self._get_selenium_driver()
            driver.get(url)
            
            # Wait for specific element if specified
            if wait_for:
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for)))
            
            return driver.page_source
            
        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Selenium error for {url}: {e}")
            return None
    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
    
    def extract_text(self, element, strip: bool = True) -> str:
        """Safely extract text from BeautifulSoup element"""
        if element:
            text = element.get_text()
            return text.strip() if strip else text
        return ""
    
    def extract_number(self, text: str) -> Optional[float]:
        """Extract numerical value from text"""
        import re
        # Remove common currency symbols and commas
        cleaned = re.sub(r'[^\d.-]', '', text.replace(',', ''))
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    @abstractmethod
    def scrape_product(self, product_url: str, product_config: Dict) -> Dict[str, Any]:
        """
        Scrape product data from given URL
        
        Args:
            product_url: URL of the product to scrape
            product_config: Configuration dict with scraping parameters
            
        Returns:
            Dict containing scraped data
        """
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is supported by this scraper
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is supported, False otherwise
        """
        pass
    
    def get_scraper_info(self) -> Dict[str, Any]:
        """Return information about this scraper"""
        return {
            'name': self.__class__.__name__,
            'supports_selenium': self.use_selenium,
            'version': '1.0.0'
        }
