from celery import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.services.notification_service import NotificationService
from app.models.datapoint import DataPoint
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Database setup for workers
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@current_app.task
def generate_daily_reports():
    """Generate daily analytics reports"""
    db = SessionLocal()
    try:
        report_service = ReportService(db)
        analytics_service = AnalyticsService(db)
        
        # Generate summary data
        today = datetime.now().date()
        summary_data = {
            "date": today.isoformat(),
            "price_changes": analytics_service.get_daily_price_changes(today),
            "products_monitored": analytics_service.get_active_products_count(),
            "data_points_collected": analytics_service.get_daily_data_points_count(today),
            "alerts_triggered": analytics_service.get_daily_alerts_count(today),
            "top_insights": analytics_service.get_top_insights(today)
        }
        
        # Generate report
        report = await report_service.generate_daily_report(summary_data)
        
        # Send notification
        notification_service = NotificationService()
        recipients = ["admin@company.com"]  # Configure recipients
        await notification_service.send_daily_summary(summary_data, recipients)
        
        logger.info(f"Generated daily report: {report.id}")
        return {"status": "success", "report_id": report.id}
        
    except Exception as e:
        logger.error(f"Error generating daily reports: {e}")
        raise
    finally:
        db.close()

@current_app.task
def analyze_market_trends():
    """Analyze market trends and patterns"""
    db = SessionLocal()
    try:
        analytics_service = AnalyticsService(db)
        
        # Analyze price trends
        price_trends = analytics_service.analyze_price_trends()
        
        # Analyze competitor movements
        competitor_analysis = analytics_service.analyze_competitor_movements()
        
        # Detect anomalies
        anomalies = analytics_service.detect_anomalies()
        
        logger.info("Completed market trend analysis")
        return {
            "price_trends": len(price_trends),
            "competitor_analysis": len(competitor_analysis),
            "anomalies_detected": len(anomalies)
        }
        
    except Exception as e:
        logger.error(f"Error in market trend analysis: {e}")
        raise
    finally:
        db.close()

@current_app.task
def cleanup_old_data():
    """Clean up old data points and optimize database"""
    db = SessionLocal()
    try:
        # Delete data points older than 90 days
        cutoff_date = datetime.now() - timedelta(days=90)
        
        deleted_count = db.query(DataPoint).filter(
            DataPoint.created_at < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} old data points")
        return {"deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@current_app.task(bind=True, max_retries=3)
def process_bulk_data(self, data_points: List[dict]):
    """Process bulk data points for analytics"""
    db = SessionLocal()
    try:
        analytics_service = AnalyticsService(db)
        
        # Process data points
        processed_count = 0
        for data_point in data_points:
            try:
                analytics_service.process_data_point(data_point)
                processed_count += 1
            except Exception as e:
                logger.warning(f"Failed to process data point: {e}")
        
        logger.info(f"Processed {processed_count}/{len(data_points)} data points")
        return {"processed": processed_count, "total": len(data_points)}
        
    except Exception as e:
        logger.error(f"Error processing bulk data: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()
