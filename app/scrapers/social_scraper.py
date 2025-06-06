import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper
from app.config import settings

class SocialScraper(BaseScraper):
    """
    Social media monitoring scraper for tracking brand mentions,
    sentiment, and engagement across various platforms.
    """
    
    def __init__(self):
        super().__init__()
        self.platforms = {
            'twitter': self._scrape_twitter_mentions,
            'reddit': self._scrape_reddit_mentions,
            'youtube': self._scrape_youtube_comments,
            'instagram': self._scrape_instagram_posts,
        }
    
    async def scrape_social_mentions(self, product_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape social media mentions for a specific product/brand.
        
        Args:
            product_config: Configuration containing search terms, platforms, etc.
            
        Returns:
            List of social media data points
        """
        try:
            search_terms = product_config.get('search_terms', [])
            platforms = product_config.get('platforms', ['twitter', 'reddit'])
            date_range = product_config.get('date_range', 7)  # Last 7 days
            
            all_mentions = []
            
            for platform in platforms:
                if platform in self.platforms:
                    self.logger.info(f"Scraping {platform} for terms: {search_terms}")
                    
                    platform_mentions = await self.platforms[platform](
                        search_terms, date_range
                    )
                    all_mentions.extend(platform_mentions)
                    
                    # Rate limiting between platforms
                    await asyncio.sleep(self.delay)
            
            return all_mentions
            
        except Exception as e:
            self.logger.error(f"Error scraping social mentions: {str(e)}")
            return []
    
    async def _scrape_twitter_mentions(self, search_terms: List[str], days: int) -> List[Dict[str, Any]]:
        """
        Scrape Twitter mentions using web scraping (since API requires paid access).
        Note: This is a simplified implementation for educational purposes.
        """
        mentions = []
        
        try:
            for term in search_terms:
                # Using Twitter's web interface search
                search_url = f"https://twitter.com/search?q={term}&src=typed_query&f=live"
                
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': settings.USER_AGENT,
                        'Accept-Language': 'en-US,en;q=0.9',
                    }
                    
                    async with session.get(search_url, headers=headers) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extract tweet data (simplified - Twitter's structure changes frequently)
                            tweets = soup.find_all('article', {'data-testid': 'tweet'})
                            
                            for tweet in tweets[:10]:  # Limit to first 10 tweets
                                mention_data = self._extract_twitter_data(tweet, term)
                                if mention_data:
                                    mentions.append(mention_data)
                
                await asyncio.sleep(self.delay)
                
        except Exception as e:
            self.logger.error(f"Error scraping Twitter: {str(e)}")
        
        return mentions
    
    async def _scrape_reddit_mentions(self, search_terms: List[str], days: int) -> List[Dict[str, Any]]:
        """
        Scrape Reddit mentions using the JSON API.
        """
        mentions = []
        
        try:
            for term in search_terms:
                # Reddit search API
                search_url = f"https://www.reddit.com/search.json"
                params = {
                    'q': term,
                    'sort': 'new',
                    'limit': 25,
                    't': 'week'  # Time filter
                }
                
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': f'{settings.USER_AGENT} (Educational Research Bot)',
                    }
                    
                    async with session.get(search_url, headers=headers, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for post in data.get('data', {}).get('children', []):
                                mention_data = self._extract_reddit_data(post['data'], term)
                                if mention_data:
                                    mentions.append(mention_data)
                
                await asyncio.sleep(self.delay)
                
        except Exception as e:
            self.logger.error(f"Error scraping Reddit: {str(e)}")
        
        return mentions
    
    async def _scrape_youtube_comments(self, search_terms: List[str], days: int) -> List[Dict[str, Any]]:
        """
        Scrape YouTube video comments for product mentions.
        """
        mentions = []
        
        try:
            for term in search_terms:
                # YouTube search (simplified - would need YouTube API for production)
                search_url = f"https://www.youtube.com/results?search_query={term}"
                
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'User-Agent': settings.USER_AGENT,
                    }
                    
                    async with session.get(search_url, headers=headers) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Extract video URLs (simplified)
                            video_urls = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                            
                            # Limit to first 3 videos to avoid overwhelming
                            for video_id in video_urls[:3]:
                                video_mentions = await self._scrape_video_comments(video_id, term)
                                mentions.extend(video_mentions)
                
                await asyncio.sleep(self.delay)
                
        except Exception as e:
            self.logger.error(f"Error scraping YouTube: {str(e)}")
        
        return mentions
    
    async def _scrape_instagram_posts(self, search_terms: List[str], days: int) -> List[Dict[str, Any]]:
        """
        Scrape Instagram posts (very limited without API access).
        This is a placeholder for demonstration.
        """
        mentions = []
        
        # Instagram requires authentication for meaningful scraping
        # This would typically use Instagram Basic Display API or Instagram Graph API
        self.logger.warning("Instagram scraping requires API access - placeholder implementation")
        
        return mentions
    
    def _extract_twitter_data(self, tweet_element, search_term: str) -> Optional[Dict[str, Any]]:
        """Extract data from a Twitter tweet element."""
        try:
            # Extract tweet text
            text_element = tweet_element.find('div', {'data-testid': 'tweetText'})
            text = text_element.get_text() if text_element else ""
            
            # Extract engagement metrics (likes, retweets, etc.)
            engagement = self._extract_twitter_engagement(tweet_element)
            
            # Calculate basic sentiment
            sentiment = self._calculate_basic_sentiment(text)
            
            return {
                'platform': 'twitter',
                'text_value': text,
                'search_term': search_term,
                'engagement': engagement,
                'sentiment_score': sentiment,
                'collected_at': datetime.now(),
                'metadata': {
                    'platform_specific': {
                        'retweets': engagement.get('retweets', 0),
                        'likes': engagement.get('likes', 0),
                        'replies': engagement.get('replies', 0),
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Twitter data: {str(e)}")
            return None
    
    def _extract_reddit_data(self, post_data: Dict, search_term: str) -> Optional[Dict[str, Any]]:
        """Extract data from Reddit post data."""
        try:
            title = post_data.get('title', '')
            selftext = post_data.get('selftext', '')
            text = f"{title} {selftext}".strip()
            
            # Calculate sentiment
            sentiment = self._calculate_basic_sentiment(text)
            
            return {
                'platform': 'reddit',
                'text_value': text,
                'search_term': search_term,
                'sentiment_score': sentiment,
                'collected_at': datetime.now(),
                'metadata': {
                    'platform_specific': {
                        'subreddit': post_data.get('subreddit_name_prefixed'),
                        'score': post_data.get('score', 0),
                        'num_comments': post_data.get('num_comments', 0),
                        'upvote_ratio': post_data.get('upvote_ratio', 0),
                        'permalink': post_data.get('permalink'),
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting Reddit data: {str(e)}")
            return None
    
    def _extract_twitter_engagement(self, tweet_element) -> Dict[str, int]:
        """Extract engagement metrics from Twitter tweet."""
        engagement = {'likes': 0, 'retweets': 0, 'replies': 0}
        
        try:
            # Find engagement buttons and extract numbers
            buttons = tweet_element.find_all('button')
            for button in buttons:
                aria_label = button.get('aria-label', '').lower()
                if 'like' in aria_label:
                    likes = re.search(r'(\d+)', aria_label)
                    engagement['likes'] = int(likes.group(1)) if likes else 0
                elif 'retweet' in aria_label:
                    retweets = re.search(r'(\d+)', aria_label)
                    engagement['retweets'] = int(retweets.group(1)) if retweets else 0
                elif 'repl' in aria_label:
                    replies = re.search(r'(\d+)', aria_label)
                    engagement['replies'] = int(replies.group(1)) if replies else 0
                    
        except Exception as e:
            self.logger.error(f"Error extracting engagement: {str(e)}")
        
        return engagement
    
    async def _scrape_video_comments(self, video_id: str, search_term: str) -> List[Dict[str, Any]]:
        """Scrape comments from a specific YouTube video."""
        mentions = []
        
        try:
            # This would require YouTube API in production
            # Placeholder implementation
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': settings.USER_AGENT}
                
                async with session.get(video_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Extract basic video info
                        title_match = re.search(r'"title":"([^"]+)"', html)
                        title = title_match.group(1) if title_match else "Unknown"
                        
                        # For demo purposes, create a sample mention
                        if search_term.lower() in title.lower():
                            mentions.append({
                                'platform': 'youtube',
                                'text_value': f"Video title: {title}",
                                'search_term': search_term,
                                'sentiment_score': self._calculate_basic_sentiment(title),
                                'collected_at': datetime.now(),
                                'metadata': {
                                    'platform_specific': {
                                        'video_id': video_id,
                                        'video_url': video_url,
                                        'type': 'video_title'
                                    }
                                }
                            })
                            
        except Exception as e:
            self.logger.error(f"Error scraping video comments: {str(e)}")
        
        return mentions
    
    def _calculate_basic_sentiment(self, text: str) -> float:
        """
        Calculate basic sentiment score using simple word matching.
        Returns value between -1 (negative) and 1 (positive).
        """
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'awesome', 'fantastic',
            'love', 'like', 'best', 'perfect', 'wonderful', 'outstanding',
            'brilliant', 'superb', 'incredible', 'phenomenal'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'worst',
            'disappointing', 'useless', 'garbage', 'trash', 'sucks',
            'pathetic', 'disgusting', 'annoying', 'frustrating'
        ]
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return 0.0  # Neutral
        
        sentiment_score = (positive_count - negative_count) / total_sentiment_words
        return max(-1.0, min(1.0, sentiment_score))  # Clamp between -1 and 1
    
    async def get_trending_topics(self, platform: str = 'twitter') -> List[Dict[str, Any]]:
        """
        Get trending topics from a specific platform.
        """
        trending = []
        
        try:
            if platform == 'twitter':
                # Scrape Twitter trending topics
                trending_url = "https://twitter.com/explore/tabs/trending"
                
                async with aiohttp.ClientSession() as session:
                    headers = {'User-Agent': settings.USER_AGENT}
                    
                    async with session.get(trending_url, headers=headers) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extract trending topics (structure may vary)
                            trend_elements = soup.find_all('span', class_=re.compile(r'.*trend.*'))
                            
                            for element in trend_elements[:10]:  # Top 10 trends
                                trend_text = element.get_text().strip()
                                if trend_text and len(trend_text) > 1:
                                    trending.append({
                                        'platform': platform,
                                        'topic': trend_text,
                                        'collected_at': datetime.now()
                                    })
                                    
        except Exception as e:
            self.logger.error(f"Error getting trending topics: {str(e)}")
        
        return trending
    
    def get_supported_platforms(self) -> List[str]:
        """Return list of supported social media platforms."""
        return list(self.platforms.keys())
    
    def get_scraper_info(self) -> Dict[str, Any]:
        """Return information about this scraper."""
        return {
            'name': 'Social Media Scraper',
            'version': '1.0.0',
            'supported_platforms': self.get_supported_platforms(),
            'capabilities': [
                'Brand mention tracking',
                'Sentiment analysis',
                'Engagement metrics',
                'Trending topics',
                'Multi-platform monitoring'
            ],
            'rate_limits': {
                'requests_per_minute': 30,
                'delay_between_requests': self.delay
            }
        }
