from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from app.models.report import Report, ReportType, ReportStatus
from app.models.company import Company
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.services.analytics_service import AnalyticsService
import json

class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)
    
    def generate_daily_report(self, company_id: int) -> Report:
        """Generate daily intelligence report for a company"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError("Company not found")
        
        # Get yesterday's date for daily report
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        
        # Check if report already exists for this date
        existing_report = self.db.query(Report).filter(
            and_(
                Report.client_id == company_id,
                Report.report_type == ReportType.DAILY,
                Report.generated_at >= datetime.combine(yesterday, datetime.min.time()),
                Report.generated_at < datetime.combine(yesterday + timedelta(days=1), datetime.min.time())
            )
        ).first()
        
        if existing_report:
            return existing_report
        
        # Get company's products
        products = self.db.query(Product).filter(
            Product.company_id == company_id,
            Product.is_active == True
        ).all()
        
        # Collect analytics for each product
        product_analytics = []
        for product in products:
            price_trends = self.analytics.get_price_trends(product.id, days=1)
            sentiment = self.analytics.sentiment_analysis(product.id, days=1)
            
            product_analytics.append({
                "product_id": product.id,
                "product_name": product.name,
                "price_analysis": price_trends if "error" not in price_trends else None,
                "sentiment_analysis": sentiment if "error" not in sentiment else None
            })
        
        # Generate report content
        report_content = {
            "company": {
                "id": company.id,
                "name": company.name,
                "domain": company.domain
            },
            "report_date": yesterday.isoformat(),
            "products_analyzed": len(products),
            "product_analytics": product_analytics,
            "summary": {
                "total_data_points": sum(
                    1 for p in product_analytics 
                    if p["price_analysis"] and p["price_analysis"].get("data_points", 0) > 0
                ),
                "products_with_price_changes": sum(
                    1 for p in product_analytics 
                    if p["price_analysis"] and abs(p["price_analysis"].get("price_change_percent", 0)) > 1
                ),
                "average_sentiment": self._calculate_average_sentiment(product_analytics)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Create report record
        report = Report(
            title=f"Daily Report - {company.name} - {yesterday}",
            report_type=ReportType.DAILY,
            client_id=company_id,
            content=report_content,
            format="json",
            status=ReportStatus.COMPLETED,
            generated_at=datetime.utcnow()
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def generate_competitor_report(self, company_id: int) -> Report:
        """Generate competitor analysis report"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError("Company not found")
        
        # Get competitor analysis
        competitor_analysis = self.analytics.competitor_analysis(company_id)
        
        if "error" in competitor_analysis:
            raise ValueError(competitor_analysis["error"])
        
        # Enhanced competitor insights
        insights = self._generate_competitor_insights(competitor_analysis)
        
        report_content = {
            **competitor_analysis,
            "enhanced_insights": insights,
            "recommendations": self._generate_recommendations(competitor_analysis),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Create report record
        report = Report(
            title=f"Competitor Analysis - {company.name}",
            report_type=ReportType.COMPETITOR,
            client_id=company_id,
            content=report_content,
            format="json",
            status=ReportStatus.COMPLETED,
            generated_at=datetime.utcnow()
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def generate_weekly_report(self, company_id: int) -> Report:
        """Generate weekly summary report"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError("Company not found")
        
        # Get products for the company
        products = self.db.query(Product).filter(
            Product.company_id == company_id,
            Product.is_active == True
        ).all()
        
        # Collect weekly analytics
        weekly_analytics = []
        for product in products:
            price_trends = self.analytics.get_price_trends(product.id, days=7)
            sentiment = self.analytics.sentiment_analysis(product.id, days=7)
            
            weekly_analytics.append({
                "product_id": product.id,
                "product_name": product.name,
                "weekly_price_trends": price_trends if "error" not in price_trends else None,
                "weekly_sentiment": sentiment if "error" not in sentiment else None
            })
        
        # Generate weekly insights
        weekly_insights = self._generate_weekly_insights(weekly_analytics)
        
        report_content = {
            "company": {
                "id": company.id,
                "name": company.name,
                "domain": company.domain
            },
            "week_ending": datetime.utcnow().date().isoformat(),
            "products_analyzed": len(products),
            "weekly_analytics": weekly_analytics,
            "insights": weekly_insights,
            "key_metrics": self._calculate_weekly_metrics(weekly_analytics),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Create report record
        report = Report(
            title=f"Weekly Report - {company.name}",
            report_type=ReportType.WEEKLY,
            client_id=company_id,
            content=report_content,
            format="json",
            status=ReportStatus.COMPLETED,
            generated_at=datetime.utcnow()
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_report(self, report_id: int) -> Optional[Report]:
        """Get a specific report"""
        return self.db.query(Report).filter(Report.id == report_id).first()
    
    def list_reports(self, company_id: Optional[int] = None, report_type: Optional[ReportType] = None) -> List[Report]:
        """List reports with optional filters"""
        query = self.db.query(Report)
        
        if company_id:
            query = query.filter(Report.client_id == company_id)
        
        if report_type:
            query = query.filter(Report.report_type == report_type)
        
        return query.order_by(desc(Report.generated_at)).all()
    
    def _calculate_average_sentiment(self, product_analytics: List[Dict]) -> Optional[float]:
        """Calculate average sentiment across products"""
        sentiments = []
        for product in product_analytics:
            if product["sentiment_analysis"] and "average_sentiment" in product["sentiment_analysis"]:
                sentiments.append(product["sentiment_analysis"]["average_sentiment"])
        
        return sum(sentiments) / len(sentiments) if sentiments else None
    
    def _generate_competitor_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate enhanced insights from competitor analysis"""
        insights = []
        
        if analysis.get("competitors"):
            competitor_count = len(analysis["competitors"])
            insights.append(f"Monitoring {competitor_count} direct competitors")
            
            # Price comparison insights
            prices = [c["average_price"] for c in analysis["competitors"] if c.get("average_price")]
            if prices:
                avg_price = sum(prices) / len(prices)
                min_price = min(prices)
                max_price = max(prices)
                
                insights.append(f"Competitor price range: ${min_price:.2f} - ${max_price:.2f}")
                insights.append(f"Market average price: ${avg_price:.2f}")
        
        return insights
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if analysis.get("market_position", {}).get("avg_competitor_price"):
            avg_price = analysis["market_position"]["avg_competitor_price"]
            recommendations.append(f"Consider pricing strategy relative to market average of ${avg_price:.2f}")
        
        if len(analysis.get("competitors", [])) < 3:
            recommendations.append("Consider expanding competitor monitoring for better market coverage")
        
        return recommendations
    
    def _generate_weekly_insights(self, analytics: List[Dict]) -> List[str]:
        """Generate insights for weekly report"""
        insights = []
        
        # Price trend insights
        price_increases = sum(1 for a in analytics 
                            if a["weekly_price_trends"] and 
                            a["weekly_price_trends"].get("price_change_percent", 0) > 5)
        
        price_decreases = sum(1 for a in analytics 
                            if a["weekly_price_trends"] and 
                            a["weekly_price_trends"].get("price_change_percent", 0) < -5)
        
        if price_increases > 0:
            insights.append(f"{price_increases} products showed significant price increases this week")
        
        if price_decreases > 0:
            insights.append(f"{price_decreases} products showed significant price decreases this week")
        
        # Sentiment insights
        positive_sentiment = sum(1 for a in analytics 
                               if a["weekly_sentiment"] and 
                               a["weekly_sentiment"].get("average_sentiment", 0) > 0.6)
        
        if positive_sentiment > 0:
            insights.append(f"{positive_sentiment} products have positive sentiment trends")
        
        return insights
    
    def _calculate_weekly_metrics(self, analytics: List[Dict]) -> Dict[str, Any]:
        """Calculate key weekly metrics"""
        total_products = len(analytics)
        products_with_data = sum(1 for a in analytics if a["weekly_price_trends"])
        
        return {
            "total_products_tracked": total_products,
            "products_with_price_data": products_with_data,
            "data_coverage_percent": round((products_with_data / total_products) * 100, 1) if total_products > 0 else 0
        }
