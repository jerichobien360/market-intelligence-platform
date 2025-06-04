import requests
from typing import List

# services/scrapers/ecommerce_scraper.py
class EcommerceScraper:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.session = requests.Session()
    
    async def scrape_product_prices(self, products: List[Product]):
        results = []
        for product in products:
            price_data = await self._scrape_single_product(product)
            await self._cache_result(product.id, price_data)
            results.append(price_data)
        return results
