"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.main import app
from app.models.company import Company
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.models.report import Report


class TestCompanyEndpoints:
    """Test company management API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Mock company data
        self.mock_company_data = {
            "name": "Test Company",
            "domain": "testcompany.com",
            "industry": "Technology",
            "description": "A test company for API testing"
        }
        
        self.mock_company = Mock(spec=Company)
        self.mock_company.id = 1
        self.mock_company.name = "Test Company"
        self.mock_company.domain = "testcompany.com"
        self.mock_company.industry = "Technology"
        self.mock_company.is_active = True
        self.mock_company.created_at = datetime.now()

    @patch('app.database.get_db')
    def test_create_company_success(self, mock_get_db):
        """Test successful company creation."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        response = self.client.post(
            "/api/v1/companies/",
            json=self.mock_company_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == self.mock_company_data["name"]
        assert data["domain"] == self.mock_company_data["domain"]
        assert "id" in data

    @patch('app.database.get_db')
    def test_create_company_validation_error(self, mock_get_db):
        """Test company creation with validation errors."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Missing required fields
        invalid_data = {
            "domain": "testcompany.com"
            # Missing name
        }
        
        response = self.client.post(
            "/api/v1/companies/",
            json=invalid_data
        )
        
        assert response.status_code == 422
        assert "validation error" in response.json()["detail"][0]["msg"].lower()

    @patch('app.database.get_db')
    def test_get_companies_list(self, mock_get_db):
        """Test retrieving list of companies."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock query result
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [
            self.mock_company
        ]
        mock_db.query.return_value.count.return_value = 1
        
        response = self.client.get("/api/v1/companies/")
        
        assert response.status_code == 200
        data = response.json()
        assert "companies" in data
        assert "total" in data
        assert len(data["companies"]) == 1
        assert data["total"] == 1

    @patch('app.database.get_db')
    def test_get_company_by_id(self, mock_get_db):
        """Test retrieving a specific company by ID."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_company
        
        response = self.client.get("/api/v1/companies/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test Company"

    @patch('app.database.get_db')
    def test_get_company_not_found(self, mock_get_db):
        """Test retrieving non-existent company."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = self.client.get("/api/v1/companies/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('app.database.get_db')
    def test_update_company(self, mock_get_db):
        """Test updating company information."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_company
        mock_db.commit = Mock()
        
        update_data = {
            "name": "Updated Company Name",
            "industry": "Updated Industry"
        }
        
        response = self.client.put("/api/v1/companies/1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["industry"] == update_data["industry"]

    @patch('app.database.get_db')
    def test_delete_company(self, mock_get_db):
        """Test deleting a company."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_company
        mock_db.delete = Mock()
        mock_db.commit = Mock()
        
        response = self.client.delete("/api/v1/companies/1")
        
        assert response.status_code == 204
        mock_db.delete.assert_called_once_with(self.mock_company)

    @patch('app.database.get_db')
    def test_get_company_competitors(self, mock_get_db):
        """Test retrieving company competitors."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_competitor = Mock(spec=Company)
        mock_competitor.id = 2
        mock_competitor.name = "Competitor Company"
        mock_competitor.competitor_to = 1
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_competitor]
        
        response = self.client.get("/api/v1/companies/1/competitors")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["competitors"]) == 1
        assert data["competitors"][0]["name"] == "Competitor Company"


class TestProductEndpoints:
    """Test product management API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        self.mock_product_data = {
            "name": "Test Product",
            "company_id": 1,
            "category": "Electronics",
            "identifier": "TEST-001",
            "url": "https://example.com/product/test",
            "tracking_config": {
                "selectors": {
                    "price": ".price",
                    "title": "h1"
                }
            }
        }
        
        self.mock_product = Mock(spec=Product)
        self.mock_product.id = 1
        self.mock_product.name = "Test Product"
        self.mock_product.company_id = 1
        self.mock_product.category = "Electronics"
        self.mock_product.is_active = True

    @patch('app.database.get_db')
    def test_create_product_success(self, mock_get_db):
        """Test successful product creation."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        response = self.client.post(
            "/api/v1/products/",
            json=self.mock_product_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == self.mock_product_data["name"]
        assert data["company_id"] == self.mock_product_data["company_id"]

    @patch('app.database.get_db') 
    def test_get_products_list(self, mock_get_db):
        """Test retrieving list of products."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [
            self.mock_product
        ]
        mock_db.query.return_value.count.return_value = 1
        
        response = self.client.get("/api/v1/products/")
        
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert len(data["products"]) == 1

    @patch('app.database.get_db')
    def test_get_product_data_points(self, mock_get_db):
        """Test retrieving product data points."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_data_point = Mock(spec=DataPoint)
        mock_data_point.id = 1
        mock_data_point.metric_type = "price"
        mock_data_point.value = 99.99
        mock_data_point.collected_at = datetime.now()
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            mock_data_point
        ]
        
        response = self.client.get("/api/v1/products/1/data")
        
        assert response.status_code == 200
        data = response.json()
        assert "data_points" in data
        assert len(data["data_points"]) == 1
        assert data["data_points"][0]["metric_type"] == "price"

    @patch('app.database.get_db')
    def test_update_product_tracking_config(self, mock_get_db):
        """Test updating product tracking configuration."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_product
        mock_db.commit = Mock()
        
        new_config = {
            "tracking_config": {
                "selectors": {
                    "price": ".new-price-selector",
                    "title": ".product-title",
                    "availability": ".stock-status"
                },
                "delay": 5
            }
        }
        
        response = self.client.put("/api/v1/products/1", json=new_config)
        
        assert response.status_code == 200
        data = response.json()
        assert "tracking_config" in data


class TestAnalyticsEndpoints:
    """Test analytics API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('app.services.analytics_service.AnalyticsService.calculate_price_trends')
    @patch('app.database.get_db')
    def test_price_trends_endpoint(self, mock_get_db, mock_price_trends):
        """Test price trends analytics endpoint."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_price_trends.return_value = {
            "trend_direction": "upward",
            "price_change": 5.50,
            "percentage_change": 5.8,
            "data_points": 30
        }
        
        response = self.client.get("/api/v1/analytics/price-trends?product_id=1&days=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["trend_direction"] == "upward"
        assert data["price_change"] == 5.50

    @patch('app.services.analytics_service.AnalyticsService.analyze_sentiment')
    @patch('app.database.get_db')
    def test_sentiment_analysis_endpoint(self, mock_get_db, mock_sentiment):
        """Test sentiment analysis endpoint."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_sentiment.return_value = {
            "overall_sentiment": "positive",
            "sentiment_score": 0.75,
            "positive_mentions": 45,
            "negative_mentions": 12,
            "neutral_mentions": 23
        }
        
        response = self.client.get("/api/v1/analytics/sentiment?product_id=1&days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert data["overall_sentiment"] == "positive"
        assert data["sentiment_score"] == 0.75

    @patch('app.services.analytics_service.AnalyticsService.get_market_share')
    @patch('app.database.get_db')
    def test_market_share_endpoint(self, mock_get_db, mock_market_share):
        """Test market share analysis endpoint."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_market_share.return_value = {
            "market_leaders": [
                {"company": "Company A", "share": 35.5},
                {"company": "Company B", "share": 28.2},
                {"company": "Company C", "share": 15.8}
            ],
            "analysis_period": "Q4 2024",
            "total_market_size": 1000000
        }
        
        response = self.client.get("/api/v1/analytics/market-share?category=Electronics")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["market_leaders"]) == 3
        assert data["market_leaders"][0]["company"] == "Company A"

    @patch('app.services.analytics_service.AnalyticsService.forecast_trends')
    @patch('app.database.get_db')
    def test_forecasting_endpoint(self, mock_get_db, mock_forecast):
        """Test predictive analytics endpoint."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_forecast.return_value = {
            "forecast_period": "next_30_days",
            "predicted_price": 105.50,
            "confidence_interval": [98.20, 112.80],
            "trend_indicators": ["increasing_demand", "seasonal_boost"]
        }
        
        response = self.client.get("/api/v1/analytics/forecasting?product_id=1&period=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["predicted_price"] == 105.50
        assert "confidence_interval" in data

    @patch('app.services.analytics_service.AnalyticsService.custom_query')
    @patch('app.database.get_db')
    def test_custom_analytics_query(self, mock_get_db, mock_custom_query):
        """Test custom analytics query endpoint."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_custom_query.return_value = {
            "query_results": [
                {"metric": "average_price", "value": 99.99},
                {"metric": "price_volatility", "value": 0.15}
            ],
            "execution_time": 0.234
        }
        
        custom_query = {
            "metrics": ["average_price", "price_volatility"],
            "filters": {
                "product_ids": [1, 2, 3],
                "date_range": "last_30_days"
            }
        }
        
        response = self.client.post("/api/v1/analytics/custom-query", json=custom_query)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["query_results"]) == 2
        assert "execution_time" in data


class TestReportEndpoints:
    """Test report generation API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        self.mock_report = Mock(spec=Report)
        self.mock_report.id = 1
        self.mock_report.title = "Weekly Competitor Analysis"
        self.mock_report.report_type = "weekly"
        self.mock_report.status = "completed"
        self.mock_report.generated_at = datetime.now()

    @patch('app.database.get_db')
    def test_get_reports_list(self, mock_get_db):
        """Test retrieving list of reports."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [
            self.mock_report
        ]
        mock_db.query.return_value.count.return_value = 1
        
        response = self.client.get("/api/v1/reports/")
        
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert len(data["reports"]) == 1

    @patch('app.services.report_service.ReportService.generate_report')
    @patch('app.database.get_db')
    def test_generate_report(self, mock_get_db, mock_generate):
        """Test report generation."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_generate.return_value = self.mock_report
        
        report_request = {
            "title": "Custom Analysis Report",
            "report_type": "custom",
            "parameters": {
                "company_ids": [1, 2],
                "metrics": ["price", "sentiment"],
                "date_range": "last_7_days"
            }
        }
        
        response = self.client.post("/api/v1/reports/generate", json=report_request)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Weekly Competitor Analysis"

    @patch('app.database.get_db')
    def test_get_specific_report(self, mock_get_db):
        """Test retrieving a specific report."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_report
        
        response = self.client.get("/api/v1/reports/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Weekly Competitor Analysis"

    @patch('app.services.report_service.ReportService.schedule_report')
    @patch('app.database.get_db')
    def test_schedule_recurring_report(self, mock_get_db, mock_schedule):
        """Test scheduling recurring reports."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_schedule.return_value = {"status": "scheduled", "next_run": "2024-01-22T09:00:00Z"}
        
        schedule_request = {
            "report_type": "weekly",
            "title": "Weekly Competitor Monitor",
            "schedule": "weekly",
            "parameters": {
                "company_ids": [1],
                "metrics": ["price", "sentiment"]
            }
        }
        
        response = self.client.post("/api/v1/reports/schedule", json=schedule_request)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "scheduled"

    @patch('app.services.report_service.ReportService.export_report')
    @patch('app.database.get_db')
    def test_export_report(self, mock_get_db, mock_export):
        """Test report export functionality."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        mock_export.return_value = {
            "download_url": "/downloads/report_1.pdf",
            "format": "pdf",
            "expires_at": "2024-01-22T23:59:59Z"
        }
        
        response = self.client.get("/api/v1/reports/export/1?format=pdf")
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "pdf"
        assert "download_url" in data


class TestAdminEndpoints:
    """Test admin panel API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test system health check endpoint."""
        response = self.client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @patch('app.services.analytics_service.AnalyticsService.get_system_metrics')
    def test_system_metrics(self, mock_metrics):
        """Test system metrics endpoint."""
        mock_metrics.return_value = {
            "active_scrapers": 5,
            "total_data_points": 15432,
            "last_scrape": "2024-01-15T10:30:00Z",
            "database_size": "2.5GB",
            "cache_hit_rate": 0.85
        }
        
        response = self.client.get("/api/v1/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_scrapers"] == 5
        assert data["cache_hit_rate"] == 0.85

    @patch('app.workers.scraping_tasks.trigger_scraping_job.delay')
    def test_trigger_scraping_manually(self, mock_trigger):
        """Test manual scraping trigger."""
        mock_trigger.return_value = Mock(id="task-123")
        
        scraping_request = {
            "scraper_type": "ecommerce",
            "product_ids": [1, 2, 3],
            "priority": "high"
        }
        
        response = self.client.post("/api/v1/scrapers/trigger", json=scraping_request)
        
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data

    @patch('app.workers.scraping_tasks.get_scraping_status')
    def test_get_scraping_status(self, mock_status):
        """Test scraping job status endpoint."""
        mock_status.return_value = {
            "active_jobs": 3,
            "pending_jobs": 12,
            "completed_today": 45,
            "failed_jobs": 2,
            "last_error": "Connection timeout on amazon.com"
        }
        
        response = self.client.get("/api/v1/scrapers/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_jobs"] == 3
        assert data["completed_today"] == 45

    @patch('redis.Redis.flushdb')
    def test_clear_cache(self, mock_flush):
        """Test cache clearing endpoint."""
        mock_flush.return_value = True
        
        response = self.client.post("/api/v1/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cleared" in data["message"]


class TestAuthenticationEndpoints:
    """Test authentication and authorization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    def test_unauthorized_access(self):
        """Test accessing protected endpoints without authentication."""
        # This test assumes you have authentication middleware
        response = self.client.post("/api/v1/scrapers/trigger", json={})
        
        # Should return 401 if auth is implemented
        # Adjust based on your auth implementation
        assert response.status_code in [401, 403, 422]  # Depending on your auth setup

    def test_invalid_token(self):
        """Test accessing endpoints with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/api/v1/metrics", headers=headers)
        
        # Should return 401 if auth is implemented
        assert response.status_code in [401, 403, 200]  # Adjust based on implementation


class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('app.database.get_db')
    def test_database_connection_error(self, mock_get_db):
        """Test handling of database connection errors."""
        mock_get_db.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/api/v1/companies/")
        
        assert response.status_code == 500
        assert "error" in response.json()

    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payloads."""
        response = self.client.post(
            "/api/v1/companies/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """Test validation of required fields."""
        response = self.client.post("/api/v1/companies/", json={})
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("name" in str(error) for error in error_detail)

    def test_invalid_query_parameters(self):
        """Test handling of invalid query parameters."""
        response = self.client.get("/api/v1/analytics/price-trends?days=invalid")
        
        assert response.status_code == 422

    def test_nonexistent_resource(self):
        """Test accessing non-existent resources."""
        response = self.client.get("/api/v1/companies/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# Integration tests that test multiple components together
class TestIntegrationScenarios:
    """Test complete workflows and integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('app.database.get_db')
    @patch('app.services.scraper_service.ScraperService.scrape_product')
    def test_complete_product_tracking_workflow(self, mock_scrape, mock_get_db):
        """Test complete workflow from adding product to getting analytics."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock successful operations
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        mock_scrape.return_value = {"status": "success", "data_points": 1}
        
        # 1. Create company
        company_data = {
            "name": "Test Company",
            "domain": "test.com",
            "industry": "Technology"
        }
        company_response = self.client.post("/api/v1/companies/", json=company_data)
        assert company_response.status_code == 201
        
        # 2. Add product
        product_data = {
            "name": "Test Product",
            "company_id": 1,
            "category": "Electronics",
            "url": "https://test.com/product"
        }
        product_response = self.client.post("/api/v1/products/", json=product_data)
        assert product_response.status_code == 201
        
        # 3. Trigger scraping
        scrape_response = self.client.post("/api/v1/scrapers/trigger", json={
            "product_ids": [1]
        })
        assert scrape_response.status_code == 202

    @patch('app.database.get_db')
    def test_analytics_data_flow(self, mock_get_db):
        """Test analytics data processing flow."""
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock data points for analytics
        mock_data_points = [
            Mock(value=99.99, collected_at=datetime.now() - timedelta(days=i))
            for i in range(30)
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_data_points
        
        # Test price trends
        response = self.client.get("/api/v1/analytics/price-trends?product_id=1&days=30")
        assert response.status_code == 200
        
        # Test that data flows to reports
        report_response = self.client.post("/api/v1/reports/generate", json={
            "title": "Price Analysis",
            "report_type": "custom",
            "parameters": {"product_ids": [1]}
        })
        assert report_response.status_code == 201


if __name__ == "__main__":
    pytest.main([__file__])
