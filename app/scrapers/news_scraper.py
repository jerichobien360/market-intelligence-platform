import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import logging
from bs4 import BeautifulSoup
import re

from .base_scraper import BaseScraper
from ..models.datapoint import DataPoint

logger = logging.getLogger(__name__)

class NewsArticleScraper(BaseScraper):
    """Scraper for news articles and press releases"""
    
    def __init__(self, session: aiohttp.ClientSession = None):
        super().__init__(session)
        self.news_sources = {
            'techcrunch': {
                'base_url': 'https://techcrunch.com',
                'search_url': 'https://techcrunch.com/search/{query}',
                'selectors': {
                    'articles': 'article.post-block',
                    'title': 'h2.post-block__title a',
                    'link': 'h2.post-block__title a',
                    'date': 'time.river-byline__time',
                    'summary': '.post-block__content'
                }
            },
            'reuters': {
                'base_url': 'https://www.reuters.com',
                'search_url': 'https://www.reuters.com/site-search/?query={query}',
                'selectors': {
                    'articles': '[data-testid="MediaStoryCard"]',
                    'title': '[data-testid="Heading"]',
                    'link': 'a',
                    'date': 'time',
                    'summary': '[data-testid="Body"]'
                }
            },
            'generic': {
                'selectors': {
                    'articles': 'article, .article, .news-item, .post',
                    'title': 'h1, h2, h3, .title, .headline',
                    'link': 'a',
                    'date': 'time, .date, .published',
                    'summary': '.summary, .excerpt, .description, p'
                }
            }
        }
    
    async def scrape_news_mentions(self, company_name: str, keywords: List[str] = None, 
                                 days_back: int = 7) -> List[Dict]:
        """Scrape news mentions for a company"""
        try:
            results = []
            search_terms = [company_name]
            if keywords:
                search_terms.extend(keywords)
            
            for source_name, config in self.news_sources.items():
                if source_name == 'generic':
                    continue
                    
                for term in search_terms:
                    articles = await self._scrape_source(source_name, term, days_back)
                    results.extend(articles)
                    
                    # Rate limiting
                    await asyncio.sleep(self.delay)
            
            return self._deduplicate_articles(results)
            
        except Exception as e:
            logger.error(f"Error scraping news mentions: {e}")
            return []
    
    async def _scrape_source(self, source_name: str, query: str, days_back: int) -> List[Dict]:
        """Scrape articles from a specific news source"""
        config = self.news_sources[source_name]
        search_url = config['search_url'].format(query=query.replace(' ', '+'))
        
        try:
            html = await self.get_page_content(search_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = []
            
            for article_elem in soup.select(config['selectors']['articles'])[:10]:  # Limit to 10 per source
                article_data = await self._extract_article_data(article_elem, config, source_name)
                if article_data and self._is_recent_article(article_data.get('date'), days_back):
                    articles.append(article_data)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            return []
    
    async def _extract_article_data(self, article_elem, config: Dict, source: str) -> Optional[Dict]:
        """Extract article data from HTML element"""
        try:
            title_elem = article_elem.select_one(config['selectors']['title'])
            link_elem = article_elem.select_one(config['selectors']['link'])
            date_elem = article_elem.select_one(config['selectors']['date'])
            summary_elem = article_elem.select_one(config['selectors']['summary'])
            
            if not title_elem or not link_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            link = link_elem.get('href', '')
            
            # Handle relative URLs
            if link.startswith('/'):
                link = urljoin(config['base_url'], link)
            
            date_str = date_elem.get_text(strip=True) if date_elem else ''
            summary = summary_elem.get_text(strip=True) if summary_elem else ''
            
            return {
                'title': title,
                'url': link,
                'source': source,
                'published_date': self._parse_date(date_str),
                'summary': summary[:500],  # Limit summary length
                'scraped_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error extracting article data: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        # Common date formats
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY or M/D/YYYY
            r'(\d{1,2} \w+ \d{4})',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    from dateutil import parser
                    return parser.parse(match.group(1))
                except:
                    continue
        
        return None
    
    def _is_recent_article(self, article_date: Optional[datetime], days_back: int) -> bool:
        """Check if article is within the specified time range"""
        if not article_date:
            return True  # Include articles without dates
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        return article_date >= cutoff_date
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        unique_articles = []
        seen_titles = set()
        
        for article in articles:
            title_normalized = re.sub(r'[^\w\s]', '', article['title'].lower())
            title_normalized = ' '.join(title_normalized.split())
            
            if title_normalized not in seen_titles:
                seen_titles.add(title_normalized)
                unique_articles.append(article)
        
        return unique_articles
    
    async def scrape_company_press_releases(self, company_domain: str) -> List[Dict]:
        """Scrape press releases from company website"""
        try:
            # Common press release page patterns
            press_release_paths = [
                '/news', '/press-releases', '/media', '/newsroom',
                '/press', '/news-events', '/investor-relations'
            ]
            
            results = []
            for path in press_release_paths:
                url = f"https://{company_domain}{path}"
                articles = await self._scrape_press_release_page(url)
                results.extend(articles)
                
                await asyncio.sleep(self.delay)
            
            return results[:20]  # Limit to 20 most recent
            
        except Exception as e:
            logger.error(f"Error scraping press releases for {company_domain}: {e}")
            return []
    
    async def _scrape_press_release_page(self, url: str) -> List[Dict]:
        """Scrape press releases from a specific page"""
        html = await self.get_page_content(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        config = self.news_sources['generic']
        
        articles = []
        for article_elem in soup.select(config['selectors']['articles'])[:10]:
            article_data = await self._extract_article_data(article_elem, config, 'company_website')
            if article_data:
                articles.append(article_data)
        
        return articles


class IndustryNewsScraper(BaseScraper):
    """Scraper for industry-specific news and trends"""
    
    def __init__(self, session: aiohttp.ClientSession = None):
        super().__init__(session)
        self.industry_sources = {
            'technology': [
                'https://techcrunch.com',
                'https://arstechnica.com',
                'https://www.theverge.com'
            ],
            'finance': [
                'https://www.bloomberg.com',
                'https://www.reuters.com/business/finance',
                'https://www.wsj.com'
            ],
            'retail': [
                'https://nrf.com/news',
                'https://retaildive.com',
                'https://www.retailwire.com'
            ],
            'healthcare': [
                'https://www.healthcaredive.com',
                'https://www.modernhealthcare.com',
                'https://www.fiercehealthcare.com'
            ]
        }
    
    async def scrape_industry_trends(self, industry: str, keywords: List[str] = None) -> List[Dict]:
        """Scrape industry-specific news and trends"""
        try:
            if industry.lower() not in self.industry_sources:
                logger.warning(f"Industry '{industry}' not supported")
                return []
            
            sources = self.industry_sources[industry.lower()]
            results = []
            
            for source_url in sources:
                articles = await self._scrape_industry_source(source_url, keywords)
                results.extend(articles)
                await asyncio.sleep(self.delay)
            
            return results[:50]  # Limit results
            
        except Exception as e:
            logger.error(f"Error scraping industry trends: {e}")
            return []
    
    async def _scrape_industry_source(self, source_url: str, keywords: List[str] = None) -> List[Dict]:
        """Scrape articles from an industry source"""
        try:
            html = await self.get_page_content(source_url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = []
            
            # Look for article elements
            article_selectors = [
                'article', '.article', '.news-item', '.story',
                '.post', '.entry', '[data-testid*="article"]'
            ]
            
            for selector in article_selectors:
                elements = soup.select(selector)
                if elements:
                    for elem in elements[:10]:
                        article = await self._extract_industry_article(elem, source_url)
                        if article and self._matches_keywords(article, keywords):
                            articles.append(article)
                    break
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping {source_url}: {e}")
            return []
    
    async def _extract_industry_article(self, elem, source_url: str) -> Optional[Dict]:
        """Extract article information from HTML element"""
        try:
            # Try different selectors for title
            title_selectors = ['h1', 'h2', 'h3', '.title', '.headline', 'a']
            title = None
            
            for selector in title_selectors:
                title_elem = elem.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 10:  # Ensure it's a meaningful title
                        break
            
            if not title:
                return None
            
            # Extract link
            link_elem = elem.select_one('a')
            link = link_elem.get('href', '') if link_elem else ''
            
            if link.startswith('/'):
                parsed_url = urlparse(source_url)
                link = f"{parsed_url.scheme}://{parsed_url.netloc}{link}"
            
            # Extract summary
            summary_elem = elem.select_one('.summary, .excerpt, p')
            summary = summary_elem.get_text(strip=True)[:300] if summary_elem else ''
            
            return {
                'title': title,
                'url': link,
                'source': urlparse(source_url).netloc,
                'summary': summary,
                'scraped_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error extracting industry article: {e}")
            return None
    
    def _matches_keywords(self, article: Dict, keywords: List[str] = None) -> bool:
        """Check if article matches specified keywords"""
        if not keywords:
            return True
        
        content = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        return any(keyword.lower() in content for keyword in keywords)
