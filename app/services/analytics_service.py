from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.models.datapoint import DataPoint
from app.models.product import Product
from app.models.company import Company
import pandas as pd
from datetime import datetime, timedelta
import statistics

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_price_trends(self, product_id: int, days: int = 30) -> Dict[str, Any]:
        """Analyze price trends for a product over specified days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get price data points
        price_data = self.db.query(DataPoint).filter(
            and_(
                DataPoint.product_id == product_id,
                DataPoint.metric_type == "price",
                DataPoint.collected_at >= start_date,
                DataPoint.collected_at <= end_date
            )
        ).order_by(DataPoint.collected_at).all()
        
        if not price_data:
            return {"error": "No price data found for this product"}
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([{
            'date': dp.collected_at,
            'price': dp.value,
            'source': dp.source
        } for dp in price_data])
        
        # Calculate trend metrics
        prices = [dp.value for dp in price_data if dp.value]
        current_price = prices[-1] if prices else 0
        avg_price = statistics.mean(prices) if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        # Calculate trend direction
        if len(prices) >= 2:
            price_change = ((current_price - prices[0]) / prices[0]) * 100
            trend = "increasing" if price_change > 5 else "decreasing" if price_change < -5 else "stable"
        else:
            price_change = 0
            trend = "stable"
        
        return {
            "product_id": product_id,
            "period_days": days,
            "current_price": current_price,
            "average_price": round(avg_price, 2),
            "min_price": min_price,
            "max_price": max_price,
            "price_change_percent": round(price_change, 2),
            "trend": trend,
            "data_points": len(price_data),
            "price_history": [{"date": dp.collected_at.isoformat(), "price": dp.value, "source": dp.source} 
                             for dp in price_data[-10:]]  # Last 10 data points
        }
    
    def competitor_analysis(self, company_id: int) -> Dict[str, Any]:
        """Compare company against its competitors"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"error": "Company not found"}
        
        # Get competitors
        competitors = self.db.query(Company).filter(
            Company.competitor_to == company_id
        ).all()
        
        if not competitors:
            return {"error": "No competitors found for this company"}
        
        analysis = {
            "company": {
                "id": company.id,
                "name": company.name,
                "domain": company.domain
            },
            "competitors": [],
            "market_position": {},
            "insights": []
        }
        
        # Analyze each competitor
        for competitor in competitors:
            competitor_products = self.db.query(Product).filter(
                Product.company_id == competitor.id
            ).all()
            
            # Get recent price data for competitor products
            recent_prices = []
            for product in competitor_products:
                latest_price = self.db.query(DataPoint).filter(
                    and_(
                        DataPoint.product_id == product.id,
                        DataPoint.metric_type == "price"
                    )
                ).order_by(desc(DataPoint.collected_at)).first()
                
                if latest_price and latest_price.value:
                    recent_prices.append(latest_price.value)
            
            avg_price = statistics.mean(recent_prices) if recent_prices else 0
            
            competitor_data = {
                "id": competitor.id,
                "name": competitor.name,
                "domain": competitor.domain,
                "product_count": len(competitor_products),
                "average_price": round(avg_price, 2) if avg_price else None,
                "recent_activity": len(recent_prices)
            }
            
            analysis["competitors"].append(competitor_data)
        
        # Generate insights
        if analysis["competitors"]:
            avg_competitor_price = statistics.mean([
                c["average_price"] for c in analysis["competitors"] 
                if c["average_price"] and c["average_price"] > 0
            ])
            
            analysis["market_position"] = {
                "total_competitors": len(competitors),
                "avg_competitor_price": round(avg_competitor_price, 2) if avg_competitor_price else None,
                "analysis_date": datetime.utcnow().isoformat()
            }
            
            # Generate basic insights
            if avg_competitor_price:
                analysis["insights"].append(
                    f"Market average price is ${avg_competitor_price:.2f}"
                )
        
        return analysis
    
    def sentiment_analysis(self, product_id: int, days: int = 7) -> Dict[str, Any]:
        """Analyze sentiment for a product over recent days"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get sentiment data points
        sentiment_data = self.db.query(DataPoint).filter(
            and_(
                DataPoint.product_id == product_id,
                DataPoint.metric_type == "sentiment",
                DataPoint.collected_at >= start_date
            )
        ).all()
        
        if not sentiment_data:
            return {"error": "No sentiment data found for this product"}
        
        # Calculate sentiment metrics
        sentiments = [dp.value for dp in sentiment_data if dp.value is not None]
        
        if not sentiments:
            return {"error": "No valid sentiment scores found"}
        
        avg_sentiment = statistics.mean(sentiments)
        sentiment_trend = "positive" if avg_sentiment > 0.6 else "negative" if avg_sentiment < 0.4 else "neutral"
        
        # Group by source
        source_breakdown = {}
        for dp in sentiment_data:
            source = dp.source
            if source not in source_breakdown:
                source_breakdown[source] = []
            if dp.value is not None:
                source_breakdown[source].append(dp.value)
        
        source_averages = {
            source: statistics.mean(scores) 
            for source, scores in source_breakdown.items()
        }
        
        return {
            "product_id": product_id,
            "period_days": days,
            "average_sentiment": round(avg_sentiment, 3),
            "sentiment_trend": sentiment_trend,
            "total_mentions": len(sentiment_data),
            "source_breakdown": {
                source: {
                    "average": round(avg, 3),
                    "count": len(scores)
                }
                for source, (avg, scores) in zip(source_averages.keys(), 
                                               zip(source_averages.values(), source_breakdown.values()))
            },
            "recent_mentions": [
                {
                    "date": dp.collected_at.isoformat(),
                    "sentiment": dp.value,
                    "source": dp.source,
                    "text": dp.text_value[:100] + "..." if dp.text_value and len(dp.text_value) > 100 else dp.text_value
                }
                for dp in sentiment_data[-5:]  # Last 5 mentions
            ]
        }
    
    def get_market_overview(self) -> Dict[str, Any]:
        """Get overall market overview statistics"""
        # Total companies
        total_companies = self.db.query(Company).filter(Company.is_active == True).count()
        
        # Total products being tracked
        total_products = self.db.query(Product).filter(Product.is_active == True).count()
        
        # Recent data points (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_data_points = self.db.query(DataPoint).filter(
            DataPoint.collected_at >= yesterday
        ).count()
        
        # Top sources by data volume
        source_stats = self.db.query(
            DataPoint.source,
            func.count(DataPoint.id).label('count')
        ).group_by(DataPoint.source).order_by(desc('count')).limit(5).all()
        
        return {
            "total_companies": total_companies,
            "total_products": total_products,
            "recent_data_points_24h": recent_data_points,
            "top_sources": [
                {"source": stat.source, "data_points": stat.count}
                for stat in source_stats
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def product_performance_summary(self, product_id: int) -> Dict[str, Any]:
        """Get comprehensive performance summary for a product"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": "Product not found"}
        
        # Get various metrics
        price_trends = self.get_price_trends(product_id, days=30)
        sentiment = self.sentiment_analysis(product_id, days=7)
        
        # Recent activity
        recent_activity = self.db.query(DataPoint).filter(
            DataPoint.product_id == product_id
        ).order_by(desc(DataPoint.collected_at)).limit(10).all()
        
        return {
            "product": {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "company": product.company.name if product.company else None
            },
            "price_analysis": price_trends,
            "sentiment_analysis": sentiment,
            "recent_activity": [
                {
                    "date": dp.collected_at.isoformat(),
                    "metric_type": dp.metric_type,
                    "value": dp.value,
                    "source": dp.source
                }
                for dp in recent_activity
            ],
            "summary_generated": datetime.utcnow().isoformat()
        }
