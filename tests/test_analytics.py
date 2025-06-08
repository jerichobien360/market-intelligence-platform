"""
Tests for analytics functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.analytics_service import AnalyticsService
from app.models.datapoint import DataPoint
from app.models.product import Product
from app.models.company import Company


class TestAnalyticsService:
    """Test the analytics service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.analytics_service = AnalyticsService(self.mock_db)
        
        # Create mock data
        self.mock_company = Mock(spec=Company)
        self.mock_company.id = 1
        self.mock_company.name = "Test Company"
        
        self.mock_product = Mock(spec=Product)
        self.mock_product.id = 1
        self.mock_product.name = "Test Product"
        self.mock_product.company_id = 1
        
        # Sample data points
        self.sample_data_points = [
            Mock(spec=DataPoint, 
                 id=1, product_id=1, metric_type="price", value=99.99,
                 collected_at=datetime.now() - timedelta(days=7)),
            Mock(spec=DataPoint,
                 id=2, product_id=1, metric_type="price", value=95.99,
                 collected_at=datetime.now() - timedelta(days=6)),
            Mock(spec=DataPoint,
                 id=3, product_id=1, metric_type="price", value=89.99,
                 collected_at=datetime.now() - timedelta(days=5)),
            Mock(spec=DataPoint,
                 id=4, product_id=1, metric_type="sentiment", value=0.75,
                 collected_at=datetime.now() - timedelta(days=4)),
            Mock(spec=DataPoint,
                 id=5, product_id=1, metric_type="sentiment", value=0.82,
                 collected_at=datetime.now() - timedelta(days=3))
        ]

    def test_calculate_price_trends(self):
        """Test price trend calculation."""
        # Mock database query
        self.mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = \
            [dp for dp in self.sample_data_points if dp.metric_type == "price"]
        
        trends = self.analytics_service.calculate_price_trends(
            product_id=1,
            days=7
        )
        
        assert "trend_direction" in trends
        assert "price_change" in trends
        assert "percentage_change" in trends
        assert trends["trend_direction"] == "downward"
        assert trends["price_change"] == -10.0  # 99.99 to 89.99
        assert abs(trends["percentage_change"] - (-10.0)) < 0.1

    def test_sentiment_analysis(self):
        """Test sentiment analysis calculations."""
        self.mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = \
            [dp for dp in self.sample_data_points if dp.metric_type == "sentiment"]
        
        sentiment_data = self.analytics_service.analyze_sentiment(
            product_id=1,
            days=7
        )
        
        assert "average_sentiment" in sentiment_data
        assert "sentiment_trend" in sentiment_data
        assert "sentiment_distribution" in sentiment_data
        assert sentiment_data["average_sentiment"] == 0.785  # (0.75 + 0.82) / 2

    def test_competitor_comparison(self):
        """Test competitor price comparison."""
        # Mock competitor data
        competitor_data = [
            Mock(spec=DataPoint, product_id=2, metric_type="price", value=105.99,
                 collected_at=datetime.now()),
            Mock(spec=DataPoint, product_id=3, metric_type="price", value=92.99,
                 collected_at=datetime.now())
        ]
        
        self.mock_db.query.return_value.join.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = \
            competitor_data
        
        comparison = self.analytics_service.compare_competitors(
            company_id=1,
            metric_type="price"
        )
        
        assert "competitors" in comparison
        assert "market_position" in comparison
        assert len(comparison["competitors"]) == 2

    def test_market_share_calculation(self):
        """Test market share calculation."""
        # Mock market data
        market_data = [
            {"company_id": 1, "total_value": 1000000},
            {"company_id": 2, "total_value": 800000},
            {"company_id": 3, "total_value": 600000}
        ]
        
        with patch.object(self.analytics_service, '_get_market_data') as mock_market:
            mock_market.return_value = market_data
            
            market_share = self.analytics_service.calculate_market_share(
                company_id=1,
                industry="technology"
            )
            
            assert "market_share_percentage" in market_share
            assert "rank" in market_share
            assert market_share["market_share_percentage"] == 41.67  # 1M out of 2.4M
            assert market_share["rank"] == 1

    def test_forecasting(self):
        """Test price forecasting functionality."""
        # Create DataFrame with price data
        price_data = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=30, freq='D'),
            'price': [100 + i*0.5 for i in range(30)]  # Gradual price increase
        })
        
        with patch('pandas.DataFrame') as mock_df:
            mock_df.return_value = price_data
            
            forecast = self.analytics_service.forecast_prices(
                product_id=1,
                days_ahead=7
            )
            
            assert "forecasted_prices" in forecast
            assert "confidence_interval" in forecast
            assert "trend" in forecast
            assert len(forecast["forecasted_prices"]) == 7

    def test_anomaly_detection(self):
        """Test anomaly detection in price data."""
        # Create data with obvious anomaly
        anomaly_data = [
            Mock(spec=DataPoint, value=100.0, collected_at=datetime.now() - timedelta(days=10)),
            Mock(spec=DataPoint, value=101.0, collected_at=datetime.now() - timedelta(days=9)),
            Mock(spec=DataPoint, value=99.5, collected_at=datetime.now() - timedelta(days=8)),
            Mock(spec=DataPoint, value=150.0, collected_at=datetime.now() - timedelta(days=7)),  # Anomaly
            Mock(spec=DataPoint, value=100.5, collected_at=datetime.now() - timedelta(days=6)),
        ]
        
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = anomaly_data
        
        anomalies = self.analytics_service.detect_anomalies(
            product_id=1,
            metric_type="price",
            threshold=2.0
        )
        
        assert len(anomalies) == 1
        assert anomalies[0]["value"] == 150.0
        assert "deviation" in anomalies[0]

    def test_performance_metrics(self):
        """Test product performance metrics calculation."""
        # Mock various metrics
        self.mock_db.query.return_value.filter.return_value.first.return_value = Mock(
            avg_price=95.5,
            avg_sentiment=0.78,
            total_mentions=500
        )
        
        metrics = self.analytics_service.calculate_performance_metrics(
            product_id=1,
            period_days=30
        )
        
        assert "average_price" in metrics
        assert "sentiment_score" in metrics
        assert "market_visibility" in metrics
        assert metrics["average_price"] == 95.5
        assert metrics["sentiment_score"] == 0.78

    def test_correlation_analysis(self):
        """Test correlation between different metrics."""
        # Mock correlation data
        correlation_data = pd.DataFrame({
            'price': [100, 95, 90, 85, 80],
            'sentiment': [0.6, 0.65, 0.7, 0.75, 0.8],
            'mentions': [50, 55, 60, 65, 70]
        })
        
        with patch.object(self.analytics_service, '_get_correlation_data') as mock_data:
            mock_data.return_value = correlation_data
            
            correlations = self.analytics_service.analyze_correlations(
                product_id=1,
                metrics=["price", "sentiment", "mentions"]
            )
            
            assert "correlations" in correlations
            assert "insights" in correlations
            # Should show negative correlation between price and sentiment
            assert correlations["correlations"]["price_sentiment"] < 0

    def test_trend_identification(self):
        """Test trend identification in time series data."""
        # Create trending data
        trending_data = [
            Mock(value=100, collected_at=datetime.now() - timedelta(days=30)),
            Mock(value=105, collected_at=datetime.now() - timedelta(days=25)),
            Mock(value=110, collected_at=datetime.now() - timedelta(days=20)),
            Mock(value=115, collected_at=datetime.now() - timedelta(days=15)),
            Mock(value=120, collected_at=datetime.now() - timedelta(days=10)),
            Mock(value=125, collected_at=datetime.now() - timedelta(days=5))
        ]
        
        trends = self.analytics_service._identify_trends(trending_data, "price")
        
        assert trends["direction"] == "upward"
        assert trends["strength"] == "strong"
        assert trends["duration_days"] >= 25

    def test_statistical_analysis(self):
        """Test statistical analysis of data points."""
        values = [100, 102, 98, 105, 97, 103, 99, 104, 96, 101]
        
        stats = self.analytics_service._calculate_statistics(values)
        
        assert "mean" in stats
        assert "median" in stats
        assert "std_dev" in stats
        assert "variance" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["mean"] == 100.5
        assert stats["min"] == 96
        assert stats["max"] == 105

    def test_data_quality_validation(self):
        """Test data quality checks."""
        # Mock data with quality issues
        quality_data = [
            Mock(value=100.0, collected_at=datetime.now()),
            Mock(value=None, collected_at=datetime.now()),  # Missing value
            Mock(value=-50.0, collected_at=datetime.now()),  # Negative price (invalid)
            Mock(value=1000000.0, collected_at=datetime.now()),  # Outlier
        ]
        
        quality_report = self.analytics_service.validate_data_quality(quality_data)
        
        assert "missing_values" in quality_report
        assert "invalid_values" in quality_report
        assert "outliers" in quality_report
        assert quality_report["missing_values"] == 1
        assert quality_report["invalid_values"] == 1
        assert quality_report["outliers"] == 1

    def test_time_series_smoothing(self):
        """Test time series data smoothing."""
        # Noisy data
        noisy_data = [100 + (i % 3 - 1) * 10 for i in range(20)]  # Oscillating data
        
        smoothed = self.analytics_service._smooth_time_series(
            noisy_data,
            method="moving_average",
            window=3
        )
        
        assert len(smoothed) == len(noisy_data)
        # Smoothed data should have less variation
        assert max(smoothed) - min(smoothed) < max(noisy_data) - min(noisy_data)

    def test_seasonality_detection(self):
        """Test seasonal pattern detection."""
        # Create seasonal data (weekly pattern)
        seasonal_data = []
        for week in range(12):  # 12 weeks of data
            for day in range(7):
                # Higher values on weekends
                base_value = 100
                weekend_boost = 20 if day in [5, 6] else 0
                seasonal_data.append(base_value + weekend_boost)
        
        seasonality = self.analytics_service.detect_seasonality(
            values=seasonal_data,
            period=7  # Weekly pattern
        )
        
        assert "has_seasonality" in seasonality
        assert "period" in seasonality
        assert "strength" in seasonality
        assert seasonality["has_seasonality"] is True
        assert seasonality["period"] == 7

    @patch('app.services.analytics_service.AnalyticsService._send_alert')
    def test_alert_generation(self, mock_send_alert):
        """Test automated alert generation."""
        # Simulate significant price drop
        alert_condition = {
            "product_id": 1,
            "metric_type": "price",
            "threshold": 10.0,  # 10% change threshold
            "current_value": 90.0,
            "previous_value": 100.0
        }
        
        self.analytics_service.check_alert_conditions(alert_condition)
        
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args[0][0]
        assert call_args["type"] == "price_drop"
        assert call_args["severity"] == "medium"

    def test_custom_metrics_calculation(self):
        """Test custom business metrics calculation."""
        custom_config = {
            "metric_name": "price_volatility",
            "formula": "std_dev / mean",
            "data_points": [95, 100, 105, 98, 102, 97, 103]
        }
        
        result = self.analytics_service.calculate_custom_metric(custom_config)
        
        assert "value" in result
        assert "interpretation" in result
        assert result["value"] > 0
        assert result["value"] < 1  # Volatility should be reasonable

    def test_export_analytics_data(self):
        """Test exporting analytics data in different formats."""
        analytics_data = {
            "price_trends": {"trend": "upward", "change": 5.5},
            "sentiment": {"average": 0.75, "trend": "positive"},
            "performance": {"score": 8.2, "rank": 3}
        }
        
        # Test JSON export
        json_export = self.analytics_service.export_data(
            data=analytics_data,
            format="json"
        )
        
        assert isinstance(json_export, str)
        assert "price_trends" in json_export
        
        # Test CSV export
        csv_export = self.analytics_service.export_data(
            data=analytics_data,
            format="csv"
        )
        
        assert isinstance(csv_export, str)
        assert "," in csv_export  # CSV format

    def test_performance_optimization(self):
        """Test analytics performance with large datasets."""
        # Simulate large dataset
        large_dataset_size = 10000
        
        with patch.object(self.mock_db.query.return_value, 'count') as mock_count:
            mock_count.return_value = large_dataset_size
            
            # Test that service handles large datasets efficiently
            start_time = datetime.now()
            
            result = self.analytics_service.calculate_price_trends(
                product_id=1,
                days=365,
                optimize_for_large_dataset=True
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Should complete within reasonable time
            assert execution_time < 5.0  # 5 seconds max
            assert "trend_direction" in result

    def test_error_handling(self):
        """Test error handling in analytics calculations."""
        # Test with empty dataset
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(ValueError, match="No data available"):
            self.analytics_service.calculate_price_trends(product_id=999, days=7)
        
        # Test with invalid parameters
        with pytest.raises(ValueError, match="Invalid parameters"):
            self.analytics_service.calculate_price_trends(product_id=1, days=-1)

    def test_caching_functionality(self):
        """Test analytics result caching."""
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get.return_value = None  # Cache miss first time
            
            # First call should compute and cache
            result1 = self.analytics_service.calculate_price_trends(
                product_id=1,
                days=7,
                use_cache=True
            )
            
            # Verify cache set was called
            mock_redis_instance.setex.assert_called_once()
            
            # Second call should use cache
            mock_redis_instance.get.return_value = '{"cached": "result"}'
            result2 = self.analytics_service.calculate_price_trends(
                product_id=1,
                days=7,
                use_cache=True
            )
            
            # Should return cached result
            assert "cached" in str(result2)
