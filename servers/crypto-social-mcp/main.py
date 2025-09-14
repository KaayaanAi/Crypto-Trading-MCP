#!/usr/bin/env python3
"""
Crypto Social Sentiment MCP Server

Provides social media sentiment analysis for cryptocurrencies including:
- Twitter sentiment analysis
- Reddit discussions monitoring
- Fear & Greed Index tracking
- Influencer sentiment weighting
- Social volume and engagement metrics
"""

import asyncio
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
import re
import json
from dataclasses import dataclass

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared_types import SocialMetric, SocialAnalysis
from utils import setup_logger, safe_float, utc_now, load_env_var, cache
from constants import SocialSentiment


# Initialize server and logger
server = Server("crypto-social-mcp")
logger = setup_logger("crypto-social-mcp", log_file="logs/social_server.log")


@dataclass
class SocialPost:
    """Social media post data"""
    platform: str
    text: str
    author: str
    timestamp: datetime
    engagement: int  # likes, retweets, upvotes, etc.
    followers: Optional[int] = None
    is_influencer: bool = False


class SocialSentimentAnalyzer:
    """Social media sentiment analysis"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.twitter_bearer_token = load_env_var("TWITTER_BEARER_TOKEN")
        self.reddit_client_id = load_env_var("REDDIT_CLIENT_ID")
        self.reddit_client_secret = load_env_var("REDDIT_CLIENT_SECRET")

        # Crypto influencers (simplified list)
        self.crypto_influencers = {
            'twitter': [
                'elonmusk', 'michael_saylor', 'satoshi_nakamoto', 'cz_binance',
                'brian_armstrong', 'aantonop', 'naval', 'balajis',
                'VitalikButerin', 'justinsuntron', 'novogratz', 'RaoulGMI'
            ],
            'reddit': [
                'crypto_enthusiast', 'bitcoin_maximalist', 'ethereum_dev'
            ]
        }

        # Sentiment keywords
        self.positive_keywords = [
            'bullish', 'moon', 'hodl', 'buy', 'bull', 'rally', 'surge', 'pump',
            'adoption', 'institutional', 'breakthrough', 'innovation', 'positive',
            'up', 'green', 'profit', 'gain', 'rise', 'breakout', 'accumulate'
        ]

        self.negative_keywords = [
            'bearish', 'dump', 'crash', 'sell', 'bear', 'decline', 'drop',
            'fear', 'panic', 'bubble', 'overvalued', 'correction', 'negative',
            'down', 'red', 'loss', 'fall', 'breakdown', 'liquidation'
        ]

        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'blockchain', 'altcoin', 'defi', 'nft', 'web3', 'satoshi'
        ]

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def calculate_text_sentiment(self, text: str) -> float:
        """Calculate sentiment score for text (-1 to 1)"""
        text_lower = text.lower()

        # Count positive and negative keywords
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text_lower)

        # Calculate sentiment score
        total_words = len(text_lower.split())
        if total_words == 0:
            return 0.0

        positive_ratio = positive_count / total_words
        negative_ratio = negative_count / total_words

        sentiment_score = (positive_ratio - negative_ratio) * 5  # Scale factor
        return max(-1.0, min(1.0, sentiment_score))

    def is_crypto_relevant(self, text: str) -> bool:
        """Check if post is cryptocurrency-relevant"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.crypto_keywords)

    async def fetch_twitter_sentiment(self, keywords: List[str], max_tweets: int = 100) -> List[SocialPost]:
        """
        Fetch Twitter sentiment data

        Note: This is a simplified implementation. In production, you would need:
        - Twitter API v2 Bearer Token
        - Proper Twitter API integration
        - Rate limiting handling
        """
        try:
            if not self.twitter_bearer_token:
                logger.warning("Twitter Bearer Token not configured, using mock data")
                return self._generate_mock_twitter_data(keywords, max_tweets)

            # Cache check
            cache_key = f"twitter_{'-'.join(keywords)}_{max_tweets}"
            cached_posts = cache.get(cache_key)
            if cached_posts:
                logger.info("Using cached Twitter data")
                return cached_posts

            # In a real implementation, you would make actual Twitter API calls here
            # For now, returning mock data
            mock_posts = self._generate_mock_twitter_data(keywords, max_tweets)

            # Cache for 10 minutes
            cache.set(cache_key, mock_posts, ttl_seconds=600)

            return mock_posts

        except Exception as e:
            logger.error(f"Error fetching Twitter sentiment: {e}")
            return []

    def _generate_mock_twitter_data(self, keywords: List[str], count: int) -> List[SocialPost]:
        """Generate mock Twitter data for demonstration"""
        import random

        mock_tweets = [
            "Bitcoin is looking bullish! 🚀 Time to buy more #BTC",
            "Ethereum upgrade is revolutionary! #ETH #blockchain",
            "Crypto market seems bearish today, might be a good time to accumulate",
            "This crypto dump is scary, but HODLing strong 💪",
            "Institutional adoption is driving Bitcoin to the moon! 🌙",
            "DeFi protocols are the future of finance #DeFi #crypto",
            "Market correction is healthy for long-term growth",
            "Panic selling again... weak hands 📉",
            "Alt season incoming! Time to diversify portfolio",
            "Regulation news causing FUD in the market"
        ]

        posts = []
        for i in range(min(count, 50)):  # Limit mock data
            tweet_text = random.choice(mock_tweets)
            is_influencer = random.random() < 0.1  # 10% chance of being influencer

            post = SocialPost(
                platform="twitter",
                text=tweet_text,
                author=f"user_{i}" if not is_influencer else random.choice(self.crypto_influencers['twitter']),
                timestamp=utc_now() - timedelta(hours=random.randint(0, 24)),
                engagement=random.randint(10, 1000),
                followers=random.randint(100, 100000) if is_influencer else random.randint(10, 1000),
                is_influencer=is_influencer
            )
            posts.append(post)

        return posts

    async def fetch_reddit_sentiment(self, subreddits: List[str], max_posts: int = 50) -> List[SocialPost]:
        """
        Fetch Reddit sentiment data

        Note: This is a simplified implementation. In production, you would use PRAW
        """
        try:
            cache_key = f"reddit_{'-'.join(subreddits)}_{max_posts}"
            cached_posts = cache.get(cache_key)
            if cached_posts:
                logger.info("Using cached Reddit data")
                return cached_posts

            # Generate mock Reddit data
            mock_posts = self._generate_mock_reddit_data(subreddits, max_posts)

            # Cache for 15 minutes
            cache.set(cache_key, mock_posts, ttl_seconds=900)

            return mock_posts

        except Exception as e:
            logger.error(f"Error fetching Reddit sentiment: {e}")
            return []

    def _generate_mock_reddit_data(self, subreddits: List[str], count: int) -> List[SocialPost]:
        """Generate mock Reddit data for demonstration"""
        import random

        mock_posts = [
            "Just bought more Bitcoin during this dip, dollar cost averaging!",
            "Ethereum 2.0 staking rewards are amazing, already seeing gains",
            "This bear market is testing my diamond hands 💎",
            "Regulatory clarity will be huge for crypto adoption",
            "DeFi yields are crazy high, but watch out for rug pulls",
            "Bitcoin maximalists vs Ethereum supporters, let's discuss",
            "Market manipulation by whales is obvious today",
            "Web3 gaming is the next big thing in crypto",
            "Stablecoin depegging events are concerning",
            "Crypto winter or just a healthy correction?"
        ]

        posts = []
        for i in range(min(count, 30)):  # Limit mock data
            post_text = random.choice(mock_posts)

            post = SocialPost(
                platform="reddit",
                text=post_text,
                author=f"reddit_user_{i}",
                timestamp=utc_now() - timedelta(hours=random.randint(0, 48)),
                engagement=random.randint(5, 500),  # upvotes
                is_influencer=random.random() < 0.05  # 5% chance
            )
            posts.append(post)

        return posts

    async def get_fear_greed_index(self) -> Optional[float]:
        """
        Fetch Crypto Fear & Greed Index
        Uses Alternative.me API (free)
        """
        try:
            cache_key = "fear_greed_index"
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            url = "https://api.alternative.me/fng/"

            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                if data.get("data") and len(data["data"]) > 0:
                    fear_greed_value = safe_float(data["data"][0]["value"])

                    # Cache for 1 hour
                    cache.set(cache_key, fear_greed_value, ttl_seconds=3600)

                    return fear_greed_value

        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")

        return None

    def analyze_social_posts(self, posts: List[SocialPost]) -> SocialMetric:
        """Analyze sentiment from social media posts"""
        if not posts:
            return SocialMetric(
                platform="unknown",
                sentiment_score=0.0,
                volume=0,
                confidence=0.0,
                trending_topics=[]
            )

        platform = posts[0].platform
        sentiment_scores = []
        total_engagement = 0
        influencer_posts = 0
        all_text = ""

        for post in posts:
            if self.is_crypto_relevant(post.text):
                sentiment = self.calculate_text_sentiment(post.text)

                # Weight influencer posts more heavily
                weight = 3.0 if post.is_influencer else 1.0
                for _ in range(int(weight)):
                    sentiment_scores.append(sentiment)

                total_engagement += post.engagement
                if post.is_influencer:
                    influencer_posts += 1

                all_text += " " + post.text.lower()

        if not sentiment_scores:
            return SocialMetric(
                platform=platform,
                sentiment_score=0.0,
                volume=0,
                confidence=0.0,
                trending_topics=[]
            )

        # Calculate overall sentiment
        overall_sentiment = sum(sentiment_scores) / len(sentiment_scores)

        # Calculate confidence based on volume and engagement
        volume_factor = min(1.0, len(posts) / 100.0)
        engagement_factor = min(1.0, total_engagement / 10000.0)
        influencer_factor = min(1.0, influencer_posts / 5.0)

        confidence = (volume_factor + engagement_factor + influencer_factor) / 3.0

        # Extract trending topics
        words = all_text.split()
        word_counts = {}
        for word in words:
            if word in self.crypto_keywords or word in self.positive_keywords or word in self.negative_keywords:
                word_counts[word] = word_counts.get(word, 0) + 1

        trending_topics = sorted(word_counts.keys(), key=lambda x: word_counts[x], reverse=True)[:5]

        return SocialMetric(
            platform=platform,
            sentiment_score=overall_sentiment,
            volume=len(posts),
            confidence=confidence,
            trending_topics=trending_topics
        )


# MCP Server Tools
@server.call_tool()
async def get_twitter_sentiment(
    keywords: List[str] = None,
    max_tweets: int = 100,
    influencer_weights: bool = True
) -> Dict[str, Any]:
    """
    Get Twitter sentiment analysis for cryptocurrency topics

    Args:
        keywords: Keywords to search for (default: crypto-related)
        max_tweets: Maximum number of tweets to analyze
        influencer_weights: Whether to weight influencer tweets more heavily

    Returns:
        Dict containing Twitter sentiment analysis
    """
    try:
        if not keywords:
            keywords = ["#bitcoin", "#crypto", "#btc", "#ethereum", "#eth"]

        logger.info(f"Analyzing Twitter sentiment for keywords: {keywords}")

        async with SocialSentimentAnalyzer() as analyzer:
            posts = await analyzer.fetch_twitter_sentiment(keywords, max_tweets)

            if not posts:
                return {
                    "success": False,
                    "error": "No Twitter data available"
                }

            metric = analyzer.analyze_social_posts(posts)

            return {
                "success": True,
                "platform": "twitter",
                "sentiment_score": metric.sentiment_score,
                "volume": metric.volume,
                "confidence": metric.confidence,
                "trending_topics": metric.trending_topics,
                "influencer_posts": len([p for p in posts if p.is_influencer]),
                "total_engagement": sum(p.engagement for p in posts),
                "keywords": keywords,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in get_twitter_sentiment: {e}")
        return {
            "success": False,
            "error": f"Failed to analyze Twitter sentiment: {str(e)}"
        }


@server.call_tool()
async def get_reddit_sentiment(
    subreddits: List[str] = None,
    max_posts: int = 50,
    time_filter: str = "day"
) -> Dict[str, Any]:
    """
    Get Reddit sentiment analysis for cryptocurrency discussions

    Args:
        subreddits: Subreddits to analyze (default: crypto-related)
        max_posts: Maximum number of posts to analyze
        time_filter: Time filter for posts (hour, day, week)

    Returns:
        Dict containing Reddit sentiment analysis
    """
    try:
        if not subreddits:
            subreddits = ["cryptocurrency", "bitcoin", "ethereum", "cryptomarkets"]

        logger.info(f"Analyzing Reddit sentiment for subreddits: {subreddits}")

        async with SocialSentimentAnalyzer() as analyzer:
            posts = await analyzer.fetch_reddit_sentiment(subreddits, max_posts)

            if not posts:
                return {
                    "success": False,
                    "error": "No Reddit data available"
                }

            metric = analyzer.analyze_social_posts(posts)

            return {
                "success": True,
                "platform": "reddit",
                "sentiment_score": metric.sentiment_score,
                "volume": metric.volume,
                "confidence": metric.confidence,
                "trending_topics": metric.trending_topics,
                "subreddits": subreddits,
                "total_upvotes": sum(p.engagement for p in posts),
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in get_reddit_sentiment: {e}")
        return {
            "success": False,
            "error": f"Failed to analyze Reddit sentiment: {str(e)}"
        }


@server.call_tool()
async def get_fear_greed_index() -> Dict[str, Any]:
    """
    Get current Crypto Fear & Greed Index

    Returns:
        Dict containing Fear & Greed Index data
    """
    try:
        logger.info("Fetching Crypto Fear & Greed Index")

        async with SocialSentimentAnalyzer() as analyzer:
            fear_greed_value = await analyzer.get_fear_greed_index()

            if fear_greed_value is None:
                return {
                    "success": False,
                    "error": "Unable to fetch Fear & Greed Index"
                }

            # Interpret the index
            if fear_greed_value <= 20:
                sentiment = "Extreme Fear"
            elif fear_greed_value <= 40:
                sentiment = "Fear"
            elif fear_greed_value <= 60:
                sentiment = "Neutral"
            elif fear_greed_value <= 80:
                sentiment = "Greed"
            else:
                sentiment = "Extreme Greed"

            return {
                "success": True,
                "fear_greed_index": fear_greed_value,
                "sentiment": sentiment,
                "normalized_score": (fear_greed_value - 50) / 50,  # -1 to 1 scale
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in get_fear_greed_index: {e}")
        return {
            "success": False,
            "error": f"Failed to fetch Fear & Greed Index: {str(e)}"
        }


@server.call_tool()
async def analyze_social_sentiment(
    platforms: List[str] = None,
    keywords: List[str] = None,
    include_fear_greed: bool = True
) -> Dict[str, Any]:
    """
    Comprehensive social sentiment analysis across multiple platforms

    Args:
        platforms: Platforms to analyze (twitter, reddit)
        keywords: Keywords to search for
        include_fear_greed: Whether to include Fear & Greed Index

    Returns:
        Dict containing comprehensive social sentiment analysis
    """
    try:
        if not platforms:
            platforms = ["twitter", "reddit"]

        if not keywords:
            keywords = ["#bitcoin", "#crypto", "#ethereum"]

        logger.info(f"Comprehensive social sentiment analysis: {platforms}")

        results = {}
        overall_sentiment_scores = []

        async with SocialSentimentAnalyzer() as analyzer:
            # Twitter analysis
            if "twitter" in platforms:
                try:
                    twitter_posts = await analyzer.fetch_twitter_sentiment(keywords, 100)
                    twitter_metric = analyzer.analyze_social_posts(twitter_posts)

                    results["twitter"] = {
                        "sentiment_score": twitter_metric.sentiment_score,
                        "volume": twitter_metric.volume,
                        "confidence": twitter_metric.confidence,
                        "trending_topics": twitter_metric.trending_topics
                    }
                    overall_sentiment_scores.append(twitter_metric.sentiment_score)

                except Exception as e:
                    logger.error(f"Error in Twitter analysis: {e}")
                    results["twitter"] = {"error": str(e)}

            # Reddit analysis
            if "reddit" in platforms:
                try:
                    reddit_posts = await analyzer.fetch_reddit_sentiment(["cryptocurrency", "bitcoin"], 50)
                    reddit_metric = analyzer.analyze_social_posts(reddit_posts)

                    results["reddit"] = {
                        "sentiment_score": reddit_metric.sentiment_score,
                        "volume": reddit_metric.volume,
                        "confidence": reddit_metric.confidence,
                        "trending_topics": reddit_metric.trending_topics
                    }
                    overall_sentiment_scores.append(reddit_metric.sentiment_score)

                except Exception as e:
                    logger.error(f"Error in Reddit analysis: {e}")
                    results["reddit"] = {"error": str(e)}

            # Fear & Greed Index
            if include_fear_greed:
                try:
                    fear_greed_value = await analyzer.get_fear_greed_index()
                    if fear_greed_value is not None:
                        normalized_fg = (fear_greed_value - 50) / 50  # Normalize to -1 to 1
                        results["fear_greed"] = {
                            "index": fear_greed_value,
                            "normalized_score": normalized_fg
                        }
                        overall_sentiment_scores.append(normalized_fg)
                except Exception as e:
                    logger.error(f"Error fetching Fear & Greed Index: {e}")

            # Calculate overall sentiment
            if overall_sentiment_scores:
                overall_sentiment = sum(overall_sentiment_scores) / len(overall_sentiment_scores)
            else:
                overall_sentiment = 0.0

            # Determine sentiment level
            if overall_sentiment > 0.3:
                sentiment_level = "bullish"
            elif overall_sentiment < -0.3:
                sentiment_level = "bearish"
            else:
                sentiment_level = "neutral"

            return {
                "success": True,
                "overall_sentiment": overall_sentiment,
                "sentiment_level": sentiment_level,
                "platform_results": results,
                "platforms_analyzed": [p for p in platforms if p in results and "error" not in results[p]],
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in analyze_social_sentiment: {e}")
        return {
            "success": False,
            "error": f"Failed to analyze social sentiment: {str(e)}"
        }


async def main():
    """Main server entry point"""
    logger.info("Starting Crypto Social Sentiment MCP Server")

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    try:
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1],
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())