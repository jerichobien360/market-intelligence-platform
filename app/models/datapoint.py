from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class DataPoint(Base):
    __tablename__ = "data_points"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    metric_type = Column(String(50), nullable=False, index=True)  # price, sentiment, stock, etc.
    value = Column(Float, nullable=True)  # Numerical values
    text_value = Column(Text, nullable=True)  # Text data like reviews, mentions
    source = Column(String(100), nullable=False, index=True)  # amazon, twitter, etc.
    metadata = Column(JSON, nullable=True)  # Additional context
    
    collected_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="data_points")
