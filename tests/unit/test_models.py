# tests/unit/test_models.py
import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.models.report import Report, ReportStatus, ReportType


class TestCompanyModel:
    """Unit tests for Company model"""
    
    def test_company_creation(self, db: Session):
        """Test creating a new company"""
        company = Company(
            name="Test Company",
            domain="test.com",
            industry="Technology",
            is_active=True,
            description="A test company"
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        
        assert company.id is not None
        assert company.name == "Test Company"
        assert company.domain == "test.com"
        assert company.industry == "Technology"
        assert company.is_active is True
        assert company.created_at is not None
    
    def test_company_competitor_relationship(self, db: Session):
        """Test competitor relationship"""
        parent_company = Company(name="Parent Company", domain="parent.com")
        db.add(parent_company)
        db.commit()
        db.refresh(parent_company)
        
        competitor = Company(
            name="Competitor",
            domain="competitor.com",
            competitor_to=parent_company.id
        )
        db.add(competitor)
        db.commit()
        
        assert competitor.competitor_to == parent_company.id
    
    def test_company_products_relationship(self, db: Session):
        """Test company-products relationship"""
        company = Company(name="Company", domain="company.com")
        db.add(company)
        db.commit()
        db.refresh(company)
        
        product = Product(
            company_id=company.id,
            name="Test Product",
            category="Electronics"
        )
        db.add(product)
        db.commit()
        
        # Test relationship
        assert len(company.products) == 1
        assert company.products[0].name == "Test Product"


class TestProductModel:
    """Unit tests for Product model"""
    
    def test_product_creation(self, db: Session, sample_company):
        """Test creating a new product"""
        product = Product(
            company_id=sample_company.id,
            name="iPhone 15",
            category="Smartphones",
            identifier="ASIN123",
            url="https://example.com/iphone15",
            tracking_config={"selector": ".price", "attribute": "text"},
            is_active=True
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        assert product.id is not None
        assert product.name == "iPhone 15"
        assert product.category == "Smartphones"
        assert product.identifier == "ASIN123"
        assert product.tracking_config["selector"] == ".price"
        assert product.is_active is True
        assert product.created_at is not None
    
    def test_product_company_relationship(self, db: Session, sample_company):
        """Test product-company relationship"""
        product = Product(
            company_id=sample_company.id,
            name="Test Product"
        )
        db.add(product)
        db.commit()
        
        assert product.company.name == sample_company.name
    
    def test_product_data_points_relationship(self, db: Session, sample_product):
        """Test product-datapoints relationship"""
        datapoint = DataPoint(
            product_id=sample_product.id,
            metric_type="price",
            value=999.99,
            source="amazon",
            collected_at=datetime.utcnow()
        )
        db.add(datapoint)
        db.commit()
        
        assert len(sample_product.data_points) == 1
        assert sample_product.data_points[0].value == 999.99


class TestDataPointModel:
    """Unit tests for DataPoint model"""
    
    def test_datapoint_creation(self, db: Session, sample_product):
        """Test creating a new data point"""
        datapoint = DataPoint(
            product_id=sample_product.id,
            metric_type="price",
            value=799.99,
            text_value="Best price ever!",
            source="amazon",
            metadata={"currency": "USD", "discount": "20%"},
            collected_at=datetime.utcnow()
        )
        db.add(datapoint)
        db.commit()
        db.refresh(datapoint)
        
        assert datapoint.id is not None
        assert datapoint.metric_type == "price"
        assert datapoint.value == 799.99
        assert datapoint.text_value == "Best price ever!"
        assert datapoint.source == "amazon"
        assert datapoint.metadata["currency"] == "USD"
        assert datapoint.collected_at is not None
    
    def test_datapoint_product_relationship(self, db: Session, sample_product):
        """Test datapoint-product relationship"""
        datapoint = DataPoint(
            product_id=sample_product.id,
            metric_type="sentiment",
            value=0.85,
            source="twitter",
            collected_at=datetime.utcnow()
        )
        db.add(datapoint)
        db.commit()
        
        assert datapoint.product.name == sample_product.name


class TestReportModel:
    """Unit tests for Report model"""
    
    def test_report_creation(self, db: Session):
        """Test creating a new report"""
        report = Report(
            title="Weekly Market Analysis",
            report_type=ReportType.WEEKLY,
            client_id=1,
            content={"summary": "Market trends up", "data": []},
            format="json",
            status=ReportStatus.PENDING,
            scheduled_for=datetime.utcnow()
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        assert report.id is not None
        assert report.title == "Weekly Market Analysis"
        assert report.report_type == ReportType.WEEKLY
        assert report.status == ReportStatus.PENDING
        assert report.content["summary"] == "Market trends up"
        assert report.created_at is not None
    
    def test_report_status_enum(self, db: Session):
        """Test report status enum values"""
        report = Report(
            title="Test Report",
            report_type=ReportType.DAILY,
            status=ReportStatus.COMPLETED
        )
        db.add(report)
        db.commit()
        
        assert report.status == ReportStatus.COMPLETED
        assert report.status.value == "completed"
    
    def test_report_type_enum(self, db: Session):
        """Test report type enum values"""
        report = Report(
            title="Custom Analysis",
            report_type=ReportType.CUSTOM,
            status=ReportStatus.PENDING
        )
        db.add(report)
        db.commit()
        
        assert report.report_type == ReportType.CUSTOM
        assert report.report_type.value == "custom"


class TestModelValidation:
    """Test model validation and constraints"""
    
    def test_company_required_fields(self, db: Session):
        """Test company required field validation"""
        with pytest.raises(Exception):
            company = Company()  # Missing required name field
            db.add(company)
            db.commit()
    
    def test_product_foreign_key_constraint(self, db: Session):
        """Test product foreign key constraint"""
        with pytest.raises(Exception):
            product = Product(
                company_id=99999,  # Non-existent company ID
                name="Invalid Product"
            )
            db.add(product)
            db.commit()
    
    def test_datapoint_required_fields(self, db: Session, sample_product):
        """Test datapoint required field validation"""
        with pytest.raises(Exception):
            datapoint = DataPoint(
                product_id=sample_product.id,
                # Missing required fields: metric_type, source, collected_at
            )
            db.add(datapoint)
            db.commit()


class TestModelUpdates:
    """Test model update functionality"""
    
    def test_company_update_timestamp(self, db: Session):
        """Test that updated_at timestamp changes on update"""
        company = Company(name="Original Name", domain="original.com")
        db.add(company)
        db.commit()
        original_updated_at = company.updated_at
        
        # Update company
        company.name = "Updated Name"
        db.commit()
        
        assert company.updated_at != original_updated_at
        assert company.name == "Updated Name"
    
    def test_product_update_timestamp(self, db: Session, sample_company):
        """Test that product updated_at timestamp changes"""
        product = Product(
            company_id=sample_company.id,
            name="Original Product"
        )
        db.add(product)
        db.commit()
        original_updated_at = product.updated_at
        
        # Update product
        product.name = "Updated Product"
        db.commit()
        
        assert product.updated_at != original_updated_at
        assert product.name == "Updated Product"
