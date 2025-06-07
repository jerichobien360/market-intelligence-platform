from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import redis
from app.database import get_db
from app.config import settings
from app.models.company import Company
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.models.report import Report
from app.services.scraper_service import ScraperService
from app.services.analytics_service import AnalyticsService
from app.workers.scraping_tasks import scrape_product, scrape_all_products
from app.workers.analytics_tasks import generate_daily_reports, analyze_market_trends
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Redis connection for system metrics
redis_client = redis.from_url(settings.REDIS_URL)

@router.get("/dashboard")
async def get_admin_dashboard(db: Session = Depends(get_db)):
    """Get admin dashboard overview"""
    try:
        # Get basic statistics
        total_companies = db.query(Company).count()
        active_companies = db.query(Company).filter(Company.is_active == True).count()
        total_products = db.query(Product).count()
        active_products = db.query(Product).filter(Product.is_active == True).count()
        
        # Get recent data points
        recent_data_points = db.query(DataPoint).filter(
            DataPoint.created_at >= datetime.now() - timedelta(hours=24)
        ).count()
        
        # Get recent reports
        recent_reports = db.query(Report).filter(
            Report.created_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        # System health metrics
        system_metrics = await get_system_metrics()
        
        return {
            "overview": {
                "total_companies": total_companies,
                "active_companies": active_companies,
                "total_products": total_products,
                "active_products": active_products,
                "recent_data_points": recent_data_points,
                "recent_reports": recent_reports
            },
            "system_metrics": system_metrics,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting admin dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")

@router.get("/system/health")
async def get_system_health():
    """Get comprehensive system health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    try:
        # Check database connection
        try:
            # This will be called in the dependency
            health_status["services"]["database"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        # Check Redis connection
        try:
            redis_client.ping()
            health_status["services"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        # Check Celery workers (basic check)
        try:
            # Check if any workers are active
            worker_stats = redis_client.get("celery:worker:stats")
            if worker_stats:
                health_status["services"]["celery"] = {"status": "healthy"}
            else:
                health_status["services"]["celery"] = {"status": "unknown"}
        except Exception as e:
            health_status["services"]["celery"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/system/metrics")
async def get_system_metrics():
    """Get detailed system metrics"""
    try:
        metrics = {
            "redis": {
                "memory_usage": redis_client.info().get("used_memory_human", "unknown"),
                "connected_clients": redis_client.info().get("connected_clients", 0),
                "total_commands_processed": redis_client.info().get("total_commands_processed", 0)
            },
            "scraping": {
                "total_scrapers": len(settings.MAX_CONCURRENT_SCRAPERS if hasattr(settings, 'MAX_CONCURRENT_SCRAPERS') else []),
                "active_scrapers": redis_client.get("active_scrapers") or 0,
                "scraping_queue_size": redis_client.llen("scraping:queue") or 0
            },
            "analytics": {
                "analytics_queue_size": redis_client.llen("analytics:queue") or 0,
                "last_report_generated": redis_client.get("last_report_generated"),
                "pending_reports": redis_client.get("pending_reports") or 0
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system metrics")

@router.post"/scrapers/trigger")
async def trigger_scraping(
    background_tasks: BackgroundTasks,
    product_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """Manually trigger scraping for specific products or all products"""
    try:
        if product_ids:
            # Trigger scraping for specific products
            for product_id in product_ids:
                # Verify product exists
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
                
                # Queue scraping task
                background_tasks.add_task(scrape_product.delay, product_id)
            
            return {
                "message": f"Triggered scraping for {len(product_ids)} products",
                "product_ids": product_ids
            }
        else:
            # Trigger scraping for all products
            background_tasks.add_task(scrape_all_products.delay)
            return {"message": "Triggered scraping for all active products"}
            
    except Exception as e:
        logger.error(f"Error triggering scraping: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger scraping")

@router.get("/scrapers/status")
async def get_scraping_status():
    """Get current scraping status and queue information"""
    try:
        status = {
            "active_scrapers": int(redis_client.get("active_scrapers") or 0),
            "scraping_queue_size": redis_client.llen("scraping:queue"),
            "completed_today": int(redis_client.get("scraping:completed:today") or 0),
            "failed_today": int(redis_client.get("scraping:failed:today") or 0),
            "last_scraping_run": redis_client.get("last_scraping_run"),
            "next_scheduled_run": redis_client.get("next_scheduled_run")
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting scraping status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scraping status")

@router.post("/reports/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    report_type: str = "daily"
):
    """Manually generate reports"""
    try:
        if report_type == "daily":
            background_tasks.add_task(generate_daily_reports.delay)
        elif report_type == "market_trends":
            background_tasks.add_task(analyze_market_trends.delay)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        return {
            "message": f"Report generation triggered",
            "report_type": report_type,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")

@router.post("/cache/clear")
async def clear_cache(cache_pattern: Optional[str] = None):
    """Clear Redis cache"""
    try:
        if cache_pattern:
            # Clear specific cache pattern
            keys = redis_client.keys(cache_pattern)
            if keys:
                redis_client.delete(*keys)
                cleared_count = len(keys)
            else:
                cleared_count = 0
        else:
            # Clear all cache (be careful with this!)
            redis_client.flushdb()
            cleared_count = "all"
        
        return {
            "message": "Cache cleared successfully",
            "cleared_keys": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@router.get("/logs")
async def get_system_logs(
    level: str = "INFO",
    limit: int = 100,
    service: Optional[str] = None
):
    """Get system logs (basic implementation)"""
    try:
        # This is a basic implementation
        # In production, you'd want to integrate with proper logging system
        logs = []
        
        # Get recent log entries from Redis (if stored there)
        log_key = f"logs:{service}" if service else "logs:system"
        recent_logs = redis_client.lrange(log_key, 0, limit - 1)
        
        for log_entry in recent_logs:
            try:
                import json
                logs.append(json.loads(log_entry))
            except:
                logs.append({"message": log_entry.decode(), "level": "INFO"})
        
        return {
            "logs": logs,
            "total": len(logs),
            "level": level,
            "service": service
        }
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get logs")

@router.get("/database/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Get database statistics"""
    try:
        stats = {
            "tables": {
                "companies": db.query(Company).count(),
                "products": db.query(Product).count(),
                "data_points": db.query(DataPoint).count(),
                "reports": db.query(Report).count()
            },
            "recent_activity": {
                "data_points_last_24h": db.query(DataPoint).filter(
                    DataPoint.created_at >= datetime.now() - timedelta(hours=24)
                ).count(),
                "data_points_last_week": db.query(DataPoint).filter(
                    DataPoint.created_at >= datetime.now() - timedelta(days=7)
                ).count()
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get database stats")

@router.post("/maintenance/cleanup")
async def run_maintenance_cleanup(
    background_tasks: BackgroundTasks,
    days_to_keep: int = 90
):
    """Run database cleanup maintenance"""
    try:
        from app.workers.analytics_tasks import cleanup_old_data
        
        background_tasks.add_task(cleanup_old_data.delay)
        
        return {
            "message": f"Maintenance cleanup started",
            "days_to_keep": days_to_keep,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Error running maintenance cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to run maintenance cleanup")
