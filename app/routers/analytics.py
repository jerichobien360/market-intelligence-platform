from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    PriceTrendResponse, 
    CompetitorAnalysisResponse,
    SentimentAnalysisResponse,
    MarketOverviewResponse,
    ProductPerformanceResponse
)

router = APIRouter()

@router.get("/price-trends/{product_id}", response_model=dict)
async def get_price_trends(
    product_id: int,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get price trend analysis for a specific product"""
    analytics = AnalyticsService(db)
    result = analytics.get_price_trends(product_id, days)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@router.get("/competitor-analysis/{company_id}", response_model=dict)
async def get_competitor_analysis(
    company_id: int,
    db: Session = Depends(get_db)
):
    """Get competitor analysis for a company"""
    analytics = AnalyticsService(db)
    result = analytics.competitor_analysis(company_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@router.get("/sentiment/{product_id}", response_model=dict)
async def get_sentiment_analysis(
    product_id: int,
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get sentiment analysis for a product"""
    analytics = AnalyticsService(db)
    result = analytics.sentiment_analysis(product_id, days)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@router.get("/market-overview", response_model=dict)
async def get_market_overview(db: Session = Depends(get_db)):
    """Get overall market overview statistics"""
    analytics = AnalyticsService(db)
    return analytics.get_market_overview()

@router.get("/product-performance/{product_id}", response_model=dict)
async def get_product_performance(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get comprehensive performance summary for a product"""
    analytics = AnalyticsService(db)
    result = analytics.product_performance_summary(product_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result

@router.get("/compare-products")
async def compare_products(
    product_ids: str = Query(..., description="Comma-separated product IDs"),
    metric: str = Query(default="price", description="Metric to compare (price, sentiment)"),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Compare multiple products on specified metrics"""
    try:
        ids = [int(id.strip()) for id in product_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product IDs format")
    
    analytics = AnalyticsService(db)
    comparison_data = []
    
    for product_id in ids:
        if metric == "price":
            data = analytics.get_price_trends(product_id, days)
        elif metric == "sentiment":
            data = analytics.sentiment_analysis(product_id, days)
        else:
            raise HTTPException(status_code=400, detail="Invalid metric. Use 'price' or 'sentiment'")
        
        if "error" not in data:
            comparison_data.append(data)
    
    return {
        "metric": metric,
        "period_days": days,
        "products_compared": len(comparison_data),
        "comparison_data": comparison_data
    }
