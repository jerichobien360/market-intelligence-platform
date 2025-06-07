from celery import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.services.scraper_service import ScraperService
from app.services.notification_service import NotificationService
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

# Database setup for workers
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@current_app.task(bind=True, max_retries=3)
def scrape_product(self, product_id: int):
    """Scrape data for a single product"""
    db = SessionLocal()
    try:
        # Get product
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.is_active:
            return {"status": "skipped", "reason": "Product not found or inactive"}
        
        # Initialize scraper service
        scraper_service = ScraperService(db)
        
        # Scrape product data
        results = await scraper_service.scrape_product(product)
        
        # Check for alerts
        notification_service = NotificationService()
        for result in results:
            if await notification_service.check_alert_conditions(result):
                # Trigger appropriate alert
                pass
        
        logger.info(f"Scraped product {product.name}: {len(results)} data points")
        return {"status": "success", "data_points": len(results)}
        
    except Exception as e:
        logger.error(f"Error scraping product {product_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()

@current_app.task
def scrape_all_products():
    """Scrape all active products"""
    db = SessionLocal()
    try:
        # Get all active products
        products = db.query(Product).filter(Product.is_active == True).all()
        
        total_products = len(products)
        successful_scrapes = 0
        
        for product in products:
            try:
                # Queue individual scraping tasks
                scrape_product.delay(product.id)
                successful_scrapes += 1
            except Exception as e:
                logger.error(f"Failed to queue scraping for product {product.id}: {e}")
        
        logger.info(f"Queued scraping for {successful_scrapes}/{total_products} products")
        return {
            "total_products": total_products,
            "queued_successfully": successful_scrapes
        }
        
    except Exception as e:
        logger.error(f"Error in scrape_all_products: {e}")
        raise
    finally:
        db.close()

@current_app.task(bind=True, max_retries=2)
def scrape_competitor_data(self, company_id: int):
    """Scrape competitor-specific data"""
    db = SessionLocal()
    try:
        scraper_service = ScraperService(db)
        results = await scraper_service.scrape_competitor_data(company_id)
        
        logger.info(f"Scraped competitor data for company {company_id}")
        return {"status": "success", "results": results}
        
    except Exception as e:
        logger.error(f"Error scraping competitor data for company {company_id}: {e}")
        raise self.retry(exc=e, countdown=120 * (2 ** self.request.retries))
    finally:
        db.close()
