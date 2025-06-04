from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    competitor_to: Optional[int] = None
    is_active: bool = True
    description: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    competitor_to: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class Company(CompanyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
