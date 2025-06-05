from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class ReportStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ReportType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    COMPETITOR = "competitor"
    CUSTOM = "custom"

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    client_id = Column(Integer, nullable=True)  # For multi-tenant setup
    content = Column(JSON, nullable=True)  # Report data and insights
    format = Column(String(20), default="json")  # json, pdf, html
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING)
    
    generated_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
