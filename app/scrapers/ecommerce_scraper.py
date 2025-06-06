from typing import Dict, List, Optional, Any
import re
from datetime import datetime
from urllib.parse import urlparse
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class EcommerceScraper(BaseScraper):
    """
    E-commerce scraper for tracking product prices and availability
    Supports Amazon, eBay, and other major platforms
    """
    
    SUPPORTED_DOMAINS = {
        'amazon.com': 'amazon',
        'amazon.co.uk': 'amazon',
        'amazon.ca': 'amazon',
        'ebay.com': 'ebay',
        'ebay.co.uk': 'ebay',
        'shopify.com': 'shopify',
        'bigcommerce.com': 'bigcommerce'
    }
    
    def __init__(self):
        super().__init__(use_selenium=True)  # E-commerce sites often need JS
    
    def validate_url(self, url: str) -> bool:
        """Check if URL is from a supported e-commerce platform"""
        try:
            domain = urlparse(url).netloc.lower()
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
            return any(supported in domain for supported in self.SUPPORTED_DOMAINS.keys())
        except Exception:
            return False
    
    def _detect_platform(self, url: str) -> Optional[str]:
        """Detect which e-commerce platform the URL belongs to"""
        try:
            domain = urlparse(url).netloc.lower()
            domain = re.sub(r'^www\.', '', domain)
            
            for supported_domain, platform in self.SUPPORTED_DOMAINS.items():
                if supported_domain in domain:
                    return platform
            return None
        except Exception:
            return None
    
    def scrape_product(self, product_url: str, product_config: Dict) -> Dict[str, Any]:
        """
        Scrape product data from e-commerce URL
        
        Args:
            product_url: Product page URL
            product_config: Configuration with selectors and options
            
        Returns:
            Dict with scraped product data
        """
        if not self.validate_url(product_url):
            raise ValueError(f"Unsupported URL: {product_url}")
        
        platform = self._detect_platform(product_url)
        logger.info(f"Scraping {platform} product: {product_url}")
        
        # Fetch page content
        html_content = self.fetch_page(product_url, wait_for='.price, [data-price], .a-price')
        if not html_content:
            return {'error': 'Failed to fetch page content'}
        
        soup = self.parse_html(html_content)
        
        # Platform-specific scraping
        if platform == 'amazon':
            return self._scrape_amazon(soup, product_config)
        elif platform == 'ebay':
            return self._scrape_ebay(soup, product_config)
        else:
            return self._scrape_generic(soup, product_config)
    
    def _scrape_amazon(self, soup, config: Dict) -> Dict[str, Any]:
        """Scrape Amazon product page"""
        result = {
            'platform': 'amazon',
            'scraped_at': datetime.utcnow().isoformat(),
            'success': False
        }
        
        try:
            # Product title
            title_selectors = [
                '#productTitle',
                '.product-title',
                'h1.a-size-large'
            ]
            title = self._find_element_text(soup, title_selectors)
            
            # Price - Amazon has multiple price formats
            price_selectors = [
                '.a-price-whole',
                '.a-offscreen',
                '#price_inside_buybox',
                '.a-price .a-offscreen',
                '#kindle-price',
                '.a-color-price'
            ]
            price_text = self._find_element_text(soup, price_selectors)
            price = self.extract_number(price_text) if price_text else None
            
            # Availability
            availability_selectors = [
                '#availability span',
                '.a-color-success',
                '.a-color-state',
                '#outOfStock'
            ]
            availability_text = self._find_element_text(soup, availability_selectors)
            in_stock = self._parse_availability(availability_text)
            
            # Rating
            rating_selectors = [
                '.a-icon-alt',
                '[data-hook="average-star-rating"] .a-icon-alt',
                '.a-star-mini .a-icon-alt'
            ]
            rating_text = self._find_element_text(soup, rating_selectors)
            rating = self._extract_rating(rating_text)
            
            # Review count
            review_selectors = [
                '[data-hook="total-review-count"]',
                '#acrCustomerReviewText',
                '.a-link-normal[href*="reviews"]'
            ]
            review_text = self._find_element_text(soup, review_selectors)
            review_count = self.extract_number(review_text) if review_text else None
            
            # Image URL
            image_selectors = [
                '#landingImage',
                '.a-dynamic-image',
                '#imgTagWrapperId img'
            ]
            image_url = self._find_element_attr(soup, image_selectors, 'src')
            
            result.update({
                'title': title,
                'price': price,
                'currency': 'USD',  # Could be enhanced to detect currency
                'in_stock': in_stock,
                'availability_text': availability_text,
                'rating': rating,
                'review_count': review_count,
                'image_url': image_url,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Amazon scraping error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _scrape_ebay(self, soup, config: Dict) -> Dict[str, Any]:
        """Scrape eBay product page"""
        result = {
            'platform': 'ebay',
            'scraped_at': datetime.utcnow().isoformat(),
            'success': False
        }
        
        try:
            # Product title
            title_selectors = [
                '#x-title-label-lbl',
                '.x-item-title-label',
                'h1#it-ttl'
            ]
            title = self._find_element_text(soup, title_selectors)
            
            # Price
            price_selectors = [
                '.notranslate',
                '#prcIsum',
                '.u-flL.condText',
                '[itemprop="price"]'
            ]
            price_text = self._find_element_text(soup, price_selectors)
            price = self.extract_number(price_text) if price_text else None
            
            # Availability
            availability_selectors = [
                '#qtySubTxt',
                '.u-flL.condText .vi-acc-del-range',
                '.notranslate'
            ]
            availability_text = self._find_element_text(soup, availability_selectors)
            in_stock = self._parse_availability(availability_text)
            
            # Seller info
            seller_selectors = [
                '.mbg-nw',
                '#seller-name'
            ]
            seller = self._find_element_text(soup, seller_selectors)
            
            result.update({
                'title': title,
                'price': price,
                'currency': 'USD',
                'in_stock': in_stock,
                'availability_text': availability_text,
                'seller': seller,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"eBay scraping error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _scrape_generic(self, soup, config: Dict) -> Dict[str, Any]:
        """Generic scraper for other e-commerce platforms"""
        result = {
            'platform': 'generic',
            'scraped_at': datetime.utcnow().isoformat(),
            'success': False
        }
        
        try:
            # Use custom selectors from config if provided
            selectors = config.get('selectors', {})
            
            # Generic selectors as fallback
            title_selectors = selectors.get('title', [
                'h1',
                '.product-title',
                '.product-name',
                '[data-product-title]'
            ])
            
            price_selectors = selectors.get('price', [
                '.price',
                '.product-price',
                '[data-price]',
                '.cost',
                '.amount'
            ])
            
            title = self._find_element_text(soup, title_selectors)
            price_text = self._find_element_text(soup, price_selectors)
            price = self.extract_number(price_text) if price_text else None
            
            result.update({
                'title': title,
                'price': price,
                'price_text': price_text,
                'success': True
            })
            
        except Exception as e:
            logger.error(f"Generic scraping error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _find_element_text(self, soup, selectors: List[str]) -> Optional[str]:
        """Find first matching element and return its text"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return self.extract_text(element)
        return None
    
    def _find_element_attr(self, soup, selectors: List[str], attr: str) -> Optional[str]:
        """Find first matching element and return specified attribute"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get(attr):
                return element.get(attr)
        return None
    
    def _parse_availability(self, text: str) -> bool:
        """Parse availability text to determine if item is in stock"""
        if not text:
            return False
        
        text = text.lower()
        out_of_stock_indicators = [
            'out of stock',
            'unavailable',
            'sold out',
            'not available',
            'discontinued',
            'temporarily out',
            'currently unavailable'
        ]
        
        in_stock_indicators = [
            'in stock',
            'available',
            'ships',
            'delivery',
            'add to cart',
            'buy now'
        ]
        
        # Check for out of stock first (more specific)
        if any(indicator in text for indicator in out_of_stock_indicators):
            return False
        
        # Then check for in stock indicators
        if any(indicator in text for indicator in in_stock_indicators):
            return True
        
        # Default to available if unclear
        return True
    
    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract rating from text like '4.5 out of 5 stars'"""
        if not text:
            return None
        
        # Look for pattern like "4.5 out of 5" or "4.5/5"
        rating_patterns = [
            r'(\d+\.?\d*)\s*out\s*of\s*5',
            r'(\d+\.?\d*)\s*/\s*5',
            r'(\d+\.?\d*)\s*stars?',
            r'rating:\s*(\d+\.?\d*)'
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def get_price_history(self, product_url: str, days: int = 30) -> List[Dict]:
        """
        Get price history for a product (placeholder for future implementation)
        This would integrate with the database to retrieve historical data
        """
        # This would query the DataPoint model for historical price data
        # For now, return empty list
        return []
    
    def monitor_price_change(self, product_url: str, threshold_percent: float = 5.0) -> Dict:
        """
        Monitor for significant price changes
        Returns alert info if price changed by more than threshold
        """
        # This would compare current price with last known price
        # and return alert data if significant change detected
        current_data = self.scrape_product(product_url, {})
        
        # Placeholder - would implement database comparison
        return {
            'alert': False,
            'current_price': current_data.get('price'),
            'change_percent': 0.0,
            'message': 'Price monitoring not yet implemented'
        }
