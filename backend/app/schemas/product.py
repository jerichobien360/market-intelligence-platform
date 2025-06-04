from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    identifier: Optional[str] = None
    url: Optional[str] = None
    tracking_config: Optional[Dict[str, Any]] = None
    is_active: bool = True

class ProductCreate(ProductBase):
    company_id: int

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    identifier: Optional[str] = None
    url: Optional[str] = None
    tracking_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class Product(ProductBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
