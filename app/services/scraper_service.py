from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.scrapers.base_scraper import BaseScraper
from app.scrapers.ecommerce_scraper import EcommerceScraper
from app.scrapers.social_scraper import SocialScraper
from app.scrapers.news_scraper import NewsScraper
from datetime import datetime, timedelta
import logging
import asyncio
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self, db: Session):
        self.db = db
        self.scrapers = {
            'ecommerce': EcommerceScraper(),
            'social': SocialScraper(),
            'news': NewsScraper()
        }

    def scrape_product_data(self, product_id: int) -> Dict[str, Any]:
        """Scrape data for a specific product"""
        product = self.db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == True
        ).first()
        
        if not product:
            return {"error": "Product not found or inactive"}
        
        if not product.url:
            return {"error": "Product URL not configured"}

        # Determine scraper type based on URL or tracking config
        scraper_type = self._determine_scraper_type(product)
        scraper = self.scrapers.get(scraper_type)
        
        if not scraper:
            return {"error": f"No scraper available for type: {scraper_type}"}

        try:
            # Scrape the data
            scraped_data = scraper.scrape(product.url, product.tracking_config or {})
            
            if not scraped_data:
                return {"error": "No data scraped"}

            # Save scraped data to database
            saved_points = self._save_scraped_data(product, scraped_data, scraper_type)
            
            return {
                "success": True,
                "product_id": product_id,
                "data_points_saved": len(saved_points),
                "scraper_type": scraper_type,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scraping product {product_id}: {str(e)}")
            return {"error": f"Scraping failed: {str(e)}"}

    def scrape_all_active_products(self) -> Dict[str, Any]:
        """Scrape data for all active products"""
        active_products = self.db.query(Product).filter(
            Product.is_active == True,
            Product.url.isnot(None)
        ).all()
        
        results = []
        for product in active_products:
            result = self.scrape_product_data(product.id)
            results.append({
                "product_id": product.id,
                "product_name": product.name,
                "result": result
            })
        
        successful = len([r for r in results if r["result"].get("success")])
        
        return {
            "total_products": len(active_products),
            "successful_scrapes": successful,
            "failed_scrapes": len(active_products) - successful,
            "results": results
        }

    def _determine_scraper_type(self, product: Product) -> str:
        """Determine which scraper to use based on product URL or config"""
        if product.tracking_config and product.tracking_config.get('scraper_type'):
            return product.tracking_config['scraper_type']
        
        if not product.url:
            return 'ecommerce'  # default
        
        domain = urlparse(product.url).netloc.lower()
        
        # E-commerce platforms
        ecommerce_domains = [
            'amazon.com', 'ebay.com', 'shopify.com', 'walmart.com',
            'target.com', 'bestbuy.com', 'alibaba.com'
        ]
        
        # Social platforms
        social_domains = [
            'twitter.com', 'facebook.com', 'instagram.com', 'linkedin.com',
            'tiktok.com', 'youtube.com'
        ]
        
        # News platforms
        news_domains = [
            'cnn.com', 'bbc.com', 'reuters.com', 'bloomberg.com',
            'techcrunch.com', 'news.google.com'
        ]
        
        for ecom_domain in ecommerce_domains:
            if ecom_domain in domain:
                return 'ecommerce'
        
        for social_domain in social_domains:
            if social_domain in domain:
                return 'social'
                
        for news_domain in news_domains:
            if news_domain in domain:
                return 'news'
        
        return 'ecommerce'  # default fallback

    def _save_scraped_data(self, product: Product, scraped_data: Dict[str, Any], source: str) -> List[DataPoint]:
        """Save scraped data to database"""
        data_points = []
        current_time = datetime.now()
        
        for metric_type, data in scraped_data.items():
            if isinstance(data, dict):
                # Handle complex data structures
                data_point = DataPoint(
                    product_id=product.id,
                    metric_type=metric_type,
                    value=data.get('value'),
                    text_value=data.get('text_value'),
                    source=source,
                    metadata=data.get('metadata', {}),
                    collected_at=current_time
                )
            else:
                # Handle simple values
                data_point = DataPoint(
                    product_id=product.id,
                    metric_type=metric_type,
                    value=data if isinstance(data, (int, float)) else None,
                    text_value=str(data) if not isinstance(data, (int, float)) else None,
                    source=source,
                    metadata={},
                    collected_at=current_time
                )
            
            data_points.append(data_point)
            self.db.add(data_point)
        
        self.db.commit()
        return data_points

    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        total_products = self.db.query(Product).filter(Product.is_active == True).count()
        
        # Recent data points (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_points = self.db.query(DataPoint).filter(
            DataPoint.collected_at >= yesterday
        ).count()
        
        # Data points by source
        source_stats = self.db.query(DataPoint.source, self.db.func.count(DataPoint.id)).group_by(DataPoint.source).all()
        
        return {
            "active_products": total_products,
            "data_points_last_24h": recent_points,
            "data_points_by_source": dict(source_stats),
            "available_scrapers": list(self.scrapers.keys())
        }
