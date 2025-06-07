from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PriceTrendResponse(BaseModel):
    product_id: int
    period_days: int
    current_price: float
    average_price: float
    min_price: float
    max_price: float
    price_change_percent: float
    trend: str
    data_points: int
    price_history: List[Dict[str, Any]]

class CompetitorInfo(BaseModel):
    id: int
    name: str
    domain: Optional[str]
    product_count: int
    average_price: Optional[float]
    recent_activity: int

class CompetitorAnalysisResponse(BaseModel):
    company: Dict[str, Any]
    competitors: List[CompetitorInfo]
    market_position: Dict[str, Any]
    insights: List[str]

class SentimentMention(BaseModel):
    date: str
    sentiment: float
    source: str
    text: Optional[str]

class SentimentAnalysisResponse(BaseModel):
    product_id: int
    period_days: int
    average_sentiment: float
    sentiment_trend: str
    total_mentions: int
    source_breakdown: Dict[str, Dict[str, Any]]
    recent_mentions: List[SentimentMention]

class MarketOverviewResponse(BaseModel):
    total_companies: int
    total_products: int
    recent_data_points_24h: int
    top_sources: List[Dict[str, Any]]
    last_updated: str

class ProductPerformanceResponse(BaseModel):
    product: Dict[str, Any]
    price_analysis: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]
    summary_generated: str
