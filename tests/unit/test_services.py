import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import pandas as pd
from app.services.analytics_service import AnalyticsService
from app.services.scraper_service import ScraperService
from app.services.report_service import ReportService
from app.services.notification_service import NotificationService
from app.models.datapoint import DataPoint
from app.models.product import Product
from app.models.company import Company


class TestAnalyticsService:
    """Unit tests for AnalyticsService"""
    
    def test_calculate_price_trends(self, db_session):
        """Test price trend calculation"""
        service = AnalyticsService(db_session)
        
        # Mock data points
        data_points = [
            Mock(value=100.0, collected_at=datetime.now() - timedelta(days=7)),
            Mock(value=105.0, collected_at=datetime.now() - timedelta(days=6)),
            Mock(value=110.0, collected_at=datetime.now() - timedelta(days=5)),
            Mock(value=115.0, collected_at=datetime.now() - timedelta(days=4)),
            Mock(value=120.0, collected_at=datetime.now() - timedelta(days=3)),
        ]
        
        trend_data = service._calculate_trend(data_points)
        
        assert trend_data["trend_direction"] == "increasing"
        assert trend_data["total_change"] == 20.0
        assert trend_data["percentage_change"] == 20.0
    
    def test_calculate_sentiment_analysis(self, db_session):
        """Test sentiment analysis calculation"""
        service = AnalyticsService(db_session)
        
        # Mock sentiment data points
        sentiment_points = [
            Mock(value=0.8, text_value="Great product!"),
            Mock(value=0.6, text_value="Good quality"),
            Mock(value=-0.2, text_value="Not bad"),
            Mock(value=0.9, text_value="Excellent!"),
        ]
        
        sentiment_summary = service._analyze_sentiment(sentiment_points)
        
        assert sentiment_summary["average_sentiment"] == 0.525
        assert sentiment_summary["positive_count"] == 3
        assert sentiment_summary["negative_count"] == 1
        assert sentiment_summary["neutral_count"] == 0
    
    @patch('app.services.analytics_service.pd.DataFrame')
    def test_generate_competitor_comparison(self, mock_df, db_session):
        """Test competitor comparison generation"""
        service = AnalyticsService(db_session)
        
        # Mock DataFrame for competitor data
        mock_df.return_value.groupby.return_value.agg.return_value = pd.DataFrame({
            'avg_price': [100.0, 110.0, 95.0],
            'min_price': [95.0, 105.0, 90.0],
            'max_price': [105.0, 115.0, 100.0]
        }, index=['Company A', 'Company B', 'Company C'])
        
        comparison = service.generate_competitor_comparison(
            product_ids=[1, 2, 3],
            date_range=30
        )
        
        assert "Company A" in comparison
        assert "Company B" in comparison
        assert "Company C" in comparison
    
    def test_detect_price_anomalies(self, db_session):
        """Test price anomaly detection"""
        service = AnalyticsService(db_session)
        
        # Mock data with anomaly
        normal_prices = [100.0] * 10
        anomaly_prices = normal_prices + [200.0, 95.0]  # High and low anomalies
        
        data_points = [
            Mock(value=price, collected_at=datetime.now() - timedelta(hours=i))
            for i, price in enumerate(anomaly_prices)
        ]
        
        anomalies = service._detect_anomalies(data_points, threshold=2.0)
        
        assert len(anomalies) == 2  # Should detect both anomalies
        assert any(a["value"] == 200.0 for a in anomalies)
        assert any(a["value"] == 95.0 for a in anomalies)


class TestScraperService:
    """Unit tests for ScraperService"""
    
    def test_scraper_registration(self):
        """Test scraper registration"""
        service = ScraperService()
        mock_scraper = Mock()
        mock_scraper.name = "test_scraper"
        
        service.register_scraper("test", mock_scraper)
        
        assert "test" in service.scrapers
        assert service.scrapers["test"] == mock_scraper
    
    @patch('app.services.scraper_service.get_db')
    async def test_execute_scraping_job(self, mock_get_db):
        """Test scraping job execution"""
        service = ScraperService()
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock scraper
        mock_scraper = AsyncMock()
        mock_scraper.scrape.return_value = [
            {"price": 99.99, "availability": "in_stock"}
        ]
        service.scrapers["amazon"] = mock_scraper
        
        # Mock product
        mock_product = Mock()
        mock_product.id = 1
        mock_product.url = "https://amazon.com/product/123"
        mock_product.tracking_config = {"selector": ".price"}
        
        result = await service.execute_scraping_job(
            product=mock_product,
            scraper_type="amazon"
        )
        
        assert result["success"] is True
        assert result["data_points_created"] == 1
        mock_scraper.scrape.assert_called_once()
    
    def test_get_scraper_status(self):
        """Test scraper status retrieval"""
        service = ScraperService()
        
        # Add mock scrapers
        mock_scraper1 = Mock()
        mock_scraper1.is_healthy.return_value = True
        mock_scraper1.last_run = datetime.now()
        
        mock_scraper2 = Mock()
        mock_scraper2.is_healthy.return_value = False
        mock_scraper2.last_run = None
        
        service.scrapers = {
            "scraper1": mock_scraper1,
            "scraper2": mock_scraper2
        }
        
        status = service.get_scrapers_status()
        
        assert status["scraper1"]["healthy"] is True
        assert status["scraper2"]["healthy"] is False
        assert "last_run" in status["scraper1"]
    
    def test_validate_scraping_config(self):
        """Test scraping configuration validation"""
        service = ScraperService()
        
        valid_config = {
            "url": "https://example.com",
            "selector": ".price",
            "delay": 2
        }
        
        invalid_config = {
            "selector": ".price"
            # Missing required 'url' field
        }
        
        assert service._validate_config(valid_config) is True
        assert service._validate_config(invalid_config) is False


class TestReportService:
    """Unit tests for ReportService"""
    
    def test_generate_daily_report(self, db_session):
        """Test daily report generation"""
        service = ReportService(db_session)
        
        with patch.object(service, '_get_daily_data') as mock_get_data:
            mock_get_data.return_value = {
                "price_changes": [{"product": "iPhone", "change": 5.0}],
                "new_mentions": 15,
                "sentiment_score": 0.7
            }
            
            report = service.generate_daily_report(client_id=1)
            
            assert report["report_type"] == "daily"
            assert report["client_id"] == 1
            assert "price_changes" in report["content"]
            assert "generated_at" in report
    
    def test_generate_competitor_report(self, db_session):
        """Test competitor analysis report generation"""
        service = ReportService(db_session)
        
        with patch.object(service, '_analyze_competitors') as mock_analyze:
            mock_analyze.return_value = {
                "top_competitors": ["Company A", "Company B"],
                "market_share": {"Company A": 0.35, "Company B": 0.25},
                "price_comparison": {"Company A": 105.0, "Company B": 110.0}
            }
            
            report = service.generate_competitor_report(
                company_id=1,
                period_days=30
            )
            
            assert report["report_type"] == "competitor"
            assert "top_competitors" in report["content"]
            assert len(report["content"]["top_competitors"]) == 2
    
    def test_export_report_pdf(self, db_session):
        """Test PDF report export"""
        service = ReportService(db_session)
        
        report_data = {
            "title": "Test Report",
            "content": {"summary": "This is a test"},
            "generated_at": datetime.now()
        }
        
        with patch('app.services.report_service.generate_pdf') as mock_pdf:
            mock_pdf.return_value = b"PDF content"
            
            pdf_data = service.export_to_pdf(report_data)
            
            assert pdf_data == b"PDF content"
            mock_pdf.assert_called_once()
    
    def test_schedule_report(self, db_session):
        """Test report scheduling"""
        service = ReportService(db_session)
        
        schedule_data = {
            "report_type": "weekly",
            "client_id": 1,
            "schedule": "0 9 * * 1",  # Every Monday at 9 AM
            "email_recipients": ["client@example.com"]
        }
        
        with patch.object(service, '_create_scheduled_task') as mock_create:
            mock_create.return_value = {"task_id": "task_123"}
            
            result = service.schedule_report(schedule_data)
            
            assert result["success"] is True
            assert "task_id" in result
            mock_create.assert_called_once()


class TestNotificationService:
    """Unit tests for NotificationService"""
    
    def test_create_price_alert(self):
        """Test price alert creation"""
        service = NotificationService()
        
        alert_data = {
            "product_id": 1,
            "threshold": 100.0,
            "direction": "below",
            "email": "user@example.com"
        }
        
        alert = service.create_alert(alert_data)
        
        assert alert["product_id"] == 1
        assert alert["threshold"] == 100.0
        assert alert["direction"] == "below"
        assert alert["active"] is True
    
    @patch('app.services.notification_service.send_email')
    def test_trigger_price_alert(self, mock_send_email):
        """Test price alert triggering"""
        service = NotificationService()
        
        alert = {
            "id": 1,
            "product_id": 1,
            "threshold": 100.0,
            "direction": "below",
            "email": "user@example.com",
            "active": True
        }
        
        # Mock current price below threshold
        current_price = 95.0
        
        service.check_and_trigger_alert(alert, current_price)
        
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert "user@example.com" in call_args[0]
        assert "Price Alert" in call_args[1]["subject"]
    
    def test_create_sentiment_alert(self):
        """Test sentiment alert creation"""
        service = NotificationService()
        
        alert_data = {
            "product_id": 1,
            "sentiment_threshold": -0.5,
            "direction": "below",
            "webhook_url": "https://hooks.slack.com/webhook"
        }
        
        alert = service.create_sentiment_alert(alert_data)
        
        assert alert["product_id"] == 1
        assert alert["sentiment_threshold"] == -0.5
        assert alert["direction"] == "below"
        assert "webhook_url" in alert
    
    @patch('requests.post')
    def test_send_webhook_notification(self, mock_post):
        """Test webhook notification sending"""
        service = NotificationService()
        
        webhook_data = {
            "url": "https://hooks.slack.com/webhook",
            "message": "Sentiment alert triggered!",
            "data": {"product": "iPhone", "sentiment": -0.6}
        }
        
        mock_post.return_value.status_code = 200
        
        result = service.send_webhook(webhook_data)
        
        assert result["success"] is True
        mock_post.assert_called_once()
        
        # Verify webhook payload
        call_args = mock_post.call_args
        assert call_args[0][0] == webhook_data["url"]
        assert "message" in call_args[1]["json"]
    
    def test_validate_email_format(self):
        """Test email format validation"""
        service = NotificationService()
        
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "firstname.lastname@company.org"
        ]
        
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user space@domain.com"
        ]
        
        for email in valid_emails:
            assert service._validate_email(email) is True
        
        for email in invalid_emails:
            assert service._validate_email(email) is False
    
    def test_rate_limiting(self):
        """Test notification rate limiting"""
        service = NotificationService()
        
        # Mock rate limit check
        with patch.object(service, '_check_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = False  # Rate limit exceeded
            
            result = service.send_notification({
                "email": "user@example.com",
                "message": "Test notification"
            })
            
            assert result["success"] is False
            assert "rate limit" in result["error"].lower()


class TestServiceIntegration:
    """Test service integration and dependencies"""
    
    def test_analytics_service_with_scraper_data(self, db_session):
        """Test analytics service using scraper service data"""
        analytics = AnalyticsService(db_session)
        scraper = ScraperService()
        
        # Mock scraped data
        mock_data = [
            {"price": 99.99, "timestamp": datetime.now()},
            {"price": 105.50, "timestamp": datetime.now() - timedelta(hours=1)},
            {"price": 95.25, "timestamp": datetime.now() - timedelta(hours=2)}
        ]
        
        with patch.object(scraper, 'get_recent_data') as mock_get_data:
            mock_get_data.return_value = mock_data
            
            # Analyze the data
            trends = analytics.analyze_price_trends(product_id=1, hours=24)
            
            assert "current_price" in trends
            assert "price_change" in trends
            assert "trend_direction" in trends
    
    def test_report_service_with_analytics(self, db_session):
        """Test report service using analytics service"""
        report_service = ReportService(db_session)
        analytics_service = AnalyticsService(db_session)
        
        with patch.object(analytics_service, 'get_market_summary') as mock_summary:
            mock_summary.return_value = {
                "total_products": 50,
                "price_changes": 15,
                "sentiment_score": 0.75
            }
            
            report = report_service.generate_market_summary_report()
            
            assert report["content"]["total_products"] == 50
            assert report["content"]["price_changes"] == 15
            assert report["content"]["sentiment_score"] == 0.75
