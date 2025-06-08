"""
Test configuration and fixtures for the Market Intelligence Platform.
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import Mock
import fakeredis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.models.company import Company
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.models.report import Report

# Test database URL - using SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def redis_mock():
    """Create a fake Redis instance for testing."""
    fake_redis = fakeredis.FakeRedis()
    yield fake_redis
    fake_redis.flushall()

@pytest.fixture
def sample_company(db_session):
    """Create a sample company for testing."""
    company = Company(
        name="Test Company",
        domain="testcompany.com",
        industry="Technology",
        is_active=True,
        description="A test company for unit testing"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company

@pytest.fixture
def sample_competitor(db_session, sample_company):
    """Create a sample competitor company."""
    competitor = Company(
        name="Competitor Corp",
        domain="competitor.com",
        industry="Technology",
        competitor_to=sample_company.id,
        is_active=True,
        description="A competitor company for testing"
    )
    db_session.add(competitor)
    db_session.commit()
    db_session.refresh(competitor)
    return competitor

@pytest.fixture
def sample_product(db_session, sample_company):
    """Create a sample product for testing."""
    product = Product(
        company_id=sample_company.id,
        name="Test Product",
        category="Electronics",
        identifier="TEST-001",
        url="https://example.com/product/test-001",
        tracking_config={
            "selectors": {
                "price": ".price",
                "title": "h1",
                "availability": ".stock-status"
            },
            "enabled": True
        },
        is_active=True
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product

@pytest.fixture
def sample_datapoints(db_session, sample_product):
    """Create sample data points for testing."""
    from datetime import datetime, timedelta
    
    datapoints = []
    base_time = datetime.utcnow()
    
    # Create price data points over the last 7 days
    for i in range(7):
        datapoint = DataPoint(
            product_id=sample_product.id,
            metric_type="price",
            value=99.99 - (i * 2),  # Decreasing price trend
            source="amazon",
            metadata={
                "currency": "USD",
                "availability": "in_stock",
                "page_title": f"Test Product - Day {i}"
            },
            collected_at=base_time - timedelta(days=i)
        )
        datapoints.append(datapoint)
        db_session.add(datapoint)
    
    # Create sentiment data points
    sentiments = [0.8, 0.6, 0.7, 0.9, 0.5, 0.8, 0.7]
    for i, sentiment in enumerate(sentiments):
        datapoint = DataPoint(
            product_id=sample_product.id,
            metric_type="sentiment",
            value=sentiment,
            text_value=f"Great product, very satisfied! Day {i}",
            source="twitter",
            metadata={
                "followers": 1200 + (i * 100),
                "retweets": 5 + i,
                "platform": "twitter"
            },
            collected_at=base_time - timedelta(days=i)
        )
        datapoints.append(datapoint)
        db_session.add(datapoint)
    
    db_session.commit()
    return datapoints

@pytest.fixture
def mock_scraper():
    """Create a mock scraper for testing."""
    scraper = Mock()
    scraper.scrape.return_value = {
        "success": True,
        "data": {
            "price": 99.99,
            "title": "Test Product",
            "availability": "in_stock",
            "reviews_count": 150,
            "rating": 4.5
        },
        "metadata": {
            "scraped_at": "2024-01-15T10:00:00Z",
            "response_time": 1.2,
            "status_code": 200
        }
    }
    return scraper

@pytest.fixture
def mock_requests():
    """Mock requests for web scraping tests."""
    import responses
    
    # Mock successful Amazon product page
    responses.add(
        responses.GET,
        "https://amazon.com/product/test",
        body="""
        <html>
            <head><title>Test Product</title></head>
            <body>
                <h1>Test Product</h1>
                <span class="price">$99.99</span>
                <div class="stock-status">In Stock</div>
                <div class="reviews">150 reviews</div>
            </body>
        </html>
        """,
        status=200,
        content_type="text/html"
    )
    
    # Mock Twitter API response
    responses.add(
        responses.GET,
        "https://api.twitter.com/2/tweets/search/recent",
        json={
            "data": [
                {
                    "id": "12345",
                    "text": "Just bought the Test Product, amazing quality!",
                    "public_metrics": {
                        "retweet_count": 5,
                        "like_count": 20
                    }
                }
            ]
        },
        status=200
    )
    
    return responses

@pytest.fixture
def analytics_test_data():
    """Provide test data for analytics functions."""
    return {
        "price_data": [
            {"date": "2024-01-01", "price": 100.00},
            {"date": "2024-01-02", "price": 98.00},
            {"date": "2024-01-03", "price": 95.00},
            {"date": "2024-01-04", "price": 97.00},
            {"date": "2024-01-05", "price": 93.00},
        ],
        "sentiment_data": [
            {"date": "2024-01-01", "sentiment": 0.8, "mentions": 50},
            {"date": "2024-01-02", "sentiment": 0.7, "mentions": 65},
            {"date": "2024-01-03", "sentiment": 0.9, "mentions": 40},
            {"date": "2024-01-04", "sentiment": 0.6, "mentions": 75},
            {"date": "2024-01-05", "sentiment": 0.8, "mentions": 55},
        ]
    }

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

# Async test utilities
@pytest.fixture
def async_client(client):
    """Create an async test client."""
    return client

# Mock external services
@pytest.fixture
def mock_celery_task():
    """Mock Celery tasks for testing."""
    from unittest.mock import patch
    
    with patch('app.workers.scraping_tasks.scrape_product.delay') as mock_task:
        mock_task.return_value.id = "test-task-id"
        mock_task.return_value.status = "SUCCESS"
        yield mock_task
