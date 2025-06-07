import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime
import redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.notification_queue = "notifications:queue"
        
    async def send_price_alert(
        self, 
        product_name: str, 
        old_price: float, 
        new_price: float, 
        change_percentage: float,
        recipients: List[str]
    ):
        """Send price change alert"""
        subject = f"🔔 Price Alert: {product_name}"
        
        if change_percentage > 0:
            emoji = "📈"
            direction = "increased"
        else:
            emoji = "📉"
            direction = "decreased"
            
        message = f"""
        {emoji} Price Alert for {product_name}
        
        Price has {direction} by {abs(change_percentage):.2f}%
        • Previous Price: ${old_price:.2f}
        • Current Price: ${new_price:.2f}
        • Change: ${new_price - old_price:.2f}
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self._send_email(recipients, subject, message)
        
    async def send_competitor_alert(
        self,
        competitor_name: str,
        action: str,
        details: Dict[str, Any],
        recipients: List[str]
    ):
        """Send competitor activity alert"""
        subject = f"🎯 Competitor Alert: {competitor_name}"
        
        message = f"""
        🎯 Competitor Activity Detected
        
        Competitor: {competitor_name}
        Action: {action}
        
        Details:
        {json.dumps(details, indent=2)}
        
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self._send_email(recipients, subject, message)
        
    async def send_daily_summary(
        self,
        summary_data: Dict[str, Any],
        recipients: List[str]
    ):
        """Send daily summary report"""
        subject = f"📊 Daily Market Intelligence Summary - {datetime.now().strftime('%Y-%m-%d')}"
        
        message = f"""
        📊 Daily Market Intelligence Summary
        
        📈 Price Changes: {summary_data.get('price_changes', 0)}
        🔍 Products Monitored: {summary_data.get('products_monitored', 0)}
        📊 Data Points Collected: {summary_data.get('data_points_collected', 0)}
        ⚠️ Alerts Triggered: {summary_data.get('alerts_triggered', 0)}
        
        🏆 Top Insights:
        {self._format_insights(summary_data.get('top_insights', []))}
        
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self._send_email(recipients, subject, message)
        
    async def _send_email(self, recipients: List[str], subject: str, message: str):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USER
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            # Send to all recipients
            for recipient in recipients:
                msg['To'] = recipient
                text = msg.as_string()
                server.sendmail(settings.SMTP_USER, recipient, text)
                logger.info(f"Email sent to {recipient}: {subject}")
                
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            # Queue for retry
            await self._queue_notification({
                'recipients': recipients,
                'subject': subject,
                'message': message,
                'retry_count': 0
            })
    
    async def _queue_notification(self, notification_data: Dict[str, Any]):
        """Queue notification for retry"""
        self.redis_client.lpush(
            self.notification_queue,
            json.dumps(notification_data)
        )
        
    def _format_insights(self, insights: List[Dict[str, Any]]) -> str:
        """Format insights for email"""
        if not insights:
            return "No significant insights today."
            
        formatted = []
        for insight in insights[:5]:  # Top 5 insights
            formatted.append(f"• {insight.get('description', 'N/A')}")
            
        return '\n'.join(formatted)
        
    async def check_alert_conditions(self, data_point: Dict[str, Any]) -> bool:
        """Check if data point triggers any alerts"""
        # Price change threshold (5% change)
        if data_point.get('metric_type') == 'price':
            # Get previous price from Redis cache
            cache_key = f"last_price:{data_point['product_id']}"
            last_price = self.redis_client.get(cache_key)
            
            if last_price:
                last_price = float(last_price)
                current_price = data_point.get('value', 0)
                
                if last_price > 0:
                    change_percentage = ((current_price - last_price) / last_price) * 100
                    
                    if abs(change_percentage) >= 5.0:  # 5% threshold
                        return True
                        
        return False
