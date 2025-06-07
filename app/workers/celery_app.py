from celery import Celery
from app.config import settings

from celery import Celery
from app.config import settings

# Create Celery instance
celery_app = Celery(
    "market_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.scraping_tasks",
        "app.workers.analytics_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Schedule scraping tasks
        "scrape-products-every-hour": {
            "task": "app.workers.scraping_tasks.scrape_all_products",
            "schedule": 3600.0,  # Run every hour
        },
        "generate-daily-reports": {
            "task": "app.workers.analytics_tasks.generate_daily_reports",
            "schedule": 86400.0,  # Run daily
            "options": {"queue": "analytics"}
        },
        "cleanup-old-data": {
            "task": "app.workers.analytics_tasks.cleanup_old_data",
            "schedule": 604800.0,  # Run weekly
        }
    },
    task_routes={
        "app.workers.scraping_tasks.*": {"queue": "scraping"},
        "app.workers.analytics_tasks.*": {"queue": "analytics"},
    }
)
