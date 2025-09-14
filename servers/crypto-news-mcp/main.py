#!/usr/bin/env python3
"""
Crypto News MCP Server

Provides cryptocurrency news analysis, sentiment scoring, and regulatory event monitoring.
Supports RSS feeds, web scraping, and AI-powered sentiment analysis.
"""

import asyncio
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
import feedparser
from bs4 import BeautifulSoup

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared_types import NewsItem, NewsAnalysis, BaseResponse
from utils import setup_logger, safe_float, utc_now, make_http_request, cache
from constants import NewsSentiment


# Initialize server and logger
server = Server("crypto-news-mcp")
logger = setup_logger("crypto-news-mcp", log_file="logs/news_server.log")


# News source configurations
NEWS_SOURCES = {
    "cointelegraph": {
        "rss_url": "https://cointelegraph.com/rss",
        "base_url": "https://cointelegraph.com",
        "weight": NewsSentiment.NEWS_SOURCE_WEIGHTS["cointelegraph"]
    },
    "coindesk": {
        "rss_url": "https://coindesk.com/arc/outboundfeeds/rss/",
        "base_url": "https://coindesk.com",
        "weight": NewsSentiment.NEWS_SOURCE_WEIGHTS["coindesk"]
    },
    "decrypt": {
        "rss_url": "https://decrypt.co/feed",
        "base_url": "https://decrypt.co",
        "weight": NewsSentiment.NEWS_SOURCE_WEIGHTS["decrypt"]
    },
    "bitcoinist": {
        "rss_url": "https://bitcoinist.com/feed/",
        "base_url": "https://bitcoinist.com",
        "weight": NewsSentiment.NEWS_SOURCE_WEIGHTS["bitcoinist"]
    },
    "cryptopotato": {
        "rss_url": "https://cryptopotato.com/feed/",
        "base_url": "https://cryptopotato.com",
        "weight": NewsSentiment.NEWS_SOURCE_WEIGHTS["cryptopotato"]
    }
}

# Sentiment keywords
POSITIVE_KEYWORDS = [
    'adoption', 'bullish', 'rally', 'surge', 'breakthrough', 'partnership',
    'investment', 'growth', 'rise', 'increase', 'gain', 'positive', 'upgrade',
    'milestone', 'success', 'launch', 'expansion', 'integration', 'approve',
    'institutional', 'mainstream', 'innovation', 'revolutionary'
]

NEGATIVE_KEYWORDS = [
    'crash', 'bearish', 'dump', 'ban', 'hack', 'selloff', 'decline', 'drop',
    'fall', 'loss', 'negative', 'concern', 'risk', 'warning', 'investigation',
    'regulation', 'crackdown', 'penalty', 'lawsuit', 'fraud', 'scam',
    'bubble', 'volatility', 'uncertainty', 'rejection'
]

CRYPTO_KEYWORDS = [
    'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
    'blockchain', 'defi', 'nft', 'altcoin', 'stablecoin', 'trading',
    'wallet', 'exchange', 'mining', 'staking'
]


class NewsAnalyzer:
    """News analysis and sentiment scoring"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_rss_feed(self, source_name: str, source_config: Dict) -> List[NewsItem]:
        """Fetch news items from RSS feed"""
        try:
            logger.info(f"Fetching RSS feed: {source_name}")

            # Check cache first
            cache_key = f"rss_{source_name}"
            cached_items = cache.get(cache_key)
            if cached_items:
                logger.info(f"Using cached RSS data for {source_name}")
                return cached_items

            async with self.session.get(
                source_config["rss_url"],
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                rss_content = await response.text()

            # Parse RSS feed
            feed = feedparser.parse(rss_content)
            news_items = []

            for entry in feed.entries[:20]:  # Limit to 20 most recent items
                try:
                    # Parse publication date
                    published_at = utc_now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6])

                    # Extract description
                    description = ""
                    if hasattr(entry, 'summary'):
                        description = BeautifulSoup(entry.summary, 'html.parser').get_text().strip()
                    elif hasattr(entry, 'description'):
                        description = BeautifulSoup(entry.description, 'html.parser').get_text().strip()

                    news_item = NewsItem(
                        title=entry.title,
                        description=description[:500],  # Limit description length
                        url=entry.link,
                        published_at=published_at,
                        source=source_name
                    )

                    news_items.append(news_item)

                except Exception as e:
                    logger.error(f"Error parsing news item from {source_name}: {e}")
                    continue

            # Cache results for 15 minutes
            cache.set(cache_key, news_items, ttl_seconds=900)
            logger.info(f"Fetched {len(news_items)} items from {source_name}")

            return news_items

        except Exception as e:
            logger.error(f"Error fetching RSS feed {source_name}: {e}")
            return []

    def calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score based on keyword analysis"""
        text_lower = text.lower()

        # Count positive and negative keywords
        positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text_lower)
        negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text_lower)

        # Calculate raw score
        total_words = len(text_lower.split())
        if total_words == 0:
            return 0.0

        positive_ratio = positive_count / total_words
        negative_ratio = negative_count / total_words

        # Calculate final score (-1 to 1)
        raw_score = positive_ratio - negative_ratio

        # Apply scaling factor
        sentiment_score = max(-1.0, min(1.0, raw_score * 10))

        return sentiment_score

    def is_crypto_relevant(self, text: str) -> bool:
        """Check if news item is crypto-relevant"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in CRYPTO_KEYWORDS)

    async def analyze_news_items(self, news_items: List[NewsItem]) -> NewsAnalysis:
        """Analyze news items and calculate overall sentiment"""
        if not news_items:
            return NewsAnalysis(
                news_items=[],
                overall_sentiment=0.0,
                confidence=0.0,
                impact_level="low",
                key_topics=[]
            )

        # Filter crypto-relevant news
        relevant_items = []
        sentiment_scores = []
        all_topics = []

        for item in news_items:
            full_text = f"{item.title} {item.description}"

            if self.is_crypto_relevant(full_text):
                # Calculate sentiment for this item
                sentiment = self.calculate_sentiment_score(full_text)
                item.sentiment_score = sentiment

                relevant_items.append(item)
                sentiment_scores.append(sentiment)

                # Extract topics (simple keyword extraction)
                text_lower = full_text.lower()
                topics = [keyword for keyword in CRYPTO_KEYWORDS if keyword in text_lower]
                all_topics.extend(topics)

        if not relevant_items:
            return NewsAnalysis(
                news_items=[],
                overall_sentiment=0.0,
                confidence=0.0,
                impact_level="low",
                key_topics=[]
            )

        # Calculate overall sentiment
        overall_sentiment = sum(sentiment_scores) / len(sentiment_scores)

        # Calculate confidence based on number of sources and recency
        confidence = min(1.0, len(relevant_items) / 20.0)

        # Determine impact level
        impact_level = "low"
        if len(relevant_items) >= 10:
            if abs(overall_sentiment) > 0.3:
                impact_level = "high"
            elif abs(overall_sentiment) > 0.1:
                impact_level = "medium"

        # Get top topics
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        key_topics = sorted(topic_counts.keys(),
                           key=lambda x: topic_counts[x],
                           reverse=True)[:5]

        return NewsAnalysis(
            news_items=relevant_items,
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            impact_level=impact_level,
            key_topics=key_topics
        )


# MCP Server Tools
@server.call_tool()
async def fetch_crypto_news(
    sources: Optional[List[str]] = None,
    timeframe: str = "24h",
    keywords: Optional[List[str]] = None,
    max_items: int = 50
) -> Dict[str, Any]:
    """
    Fetch latest cryptocurrency news from multiple sources

    Args:
        sources: List of news sources to fetch from (default: all)
        timeframe: Time range for news (1h, 6h, 24h, 7d)
        keywords: Additional keywords to filter by
        max_items: Maximum number of news items to return

    Returns:
        Dict containing news items and metadata
    """
    try:
        logger.info(f"Fetching crypto news - timeframe: {timeframe}, max_items: {max_items}")

        # Use all sources if none specified
        if not sources:
            sources = list(NEWS_SOURCES.keys())

        # Validate sources
        valid_sources = [s for s in sources if s in NEWS_SOURCES]
        if not valid_sources:
            return {
                "success": False,
                "error": f"No valid news sources provided. Available: {list(NEWS_SOURCES.keys())}"
            }

        async with NewsAnalyzer() as analyzer:
            # Fetch from all sources concurrently
            tasks = []
            for source_name in valid_sources:
                source_config = NEWS_SOURCES[source_name]
                task = analyzer.fetch_rss_feed(source_name, source_config)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results
            all_news_items = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching from {valid_sources[i]}: {result}")
                    continue
                all_news_items.extend(result)

            # Filter by timeframe
            cutoff_time = utc_now()
            if timeframe == "1h":
                cutoff_time -= timedelta(hours=1)
            elif timeframe == "6h":
                cutoff_time -= timedelta(hours=6)
            elif timeframe == "24h":
                cutoff_time -= timedelta(hours=24)
            elif timeframe == "7d":
                cutoff_time -= timedelta(days=7)

            filtered_items = [
                item for item in all_news_items
                if item.published_at >= cutoff_time
            ]

            # Sort by publication date (most recent first)
            filtered_items.sort(key=lambda x: x.published_at, reverse=True)

            # Limit number of items
            filtered_items = filtered_items[:max_items]

            return {
                "success": True,
                "news_items": [item.dict() for item in filtered_items],
                "total_count": len(filtered_items),
                "sources_used": valid_sources,
                "timeframe": timeframe,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in fetch_crypto_news: {e}")
        return {
            "success": False,
            "error": f"Failed to fetch crypto news: {str(e)}"
        }


@server.call_tool()
async def analyze_news_sentiment(
    news_items: Optional[List[Dict[str, Any]]] = None,
    sources: Optional[List[str]] = None,
    timeframe: str = "6h"
) -> Dict[str, Any]:
    """
    Analyze sentiment of cryptocurrency news

    Args:
        news_items: Pre-fetched news items to analyze (optional)
        sources: News sources to fetch from if news_items not provided
        timeframe: Time range for analysis if fetching news

    Returns:
        Dict containing sentiment analysis results
    """
    try:
        logger.info("Analyzing news sentiment")

        async with NewsAnalyzer() as analyzer:
            # If news items not provided, fetch them
            if not news_items:
                fetch_result = await fetch_crypto_news(
                    sources=sources,
                    timeframe=timeframe,
                    max_items=100
                )

                if not fetch_result.get("success"):
                    return fetch_result

                news_items = fetch_result["news_items"]

            # Convert to NewsItem objects
            news_item_objects = []
            for item_data in news_items:
                try:
                    news_item = NewsItem(**item_data)
                    news_item_objects.append(news_item)
                except Exception as e:
                    logger.error(f"Error parsing news item: {e}")
                    continue

            # Perform sentiment analysis
            analysis = await analyzer.analyze_news_items(news_item_objects)

            return {
                "success": True,
                "overall_sentiment": analysis.overall_sentiment,
                "confidence": analysis.confidence,
                "impact_level": analysis.impact_level,
                "key_topics": analysis.key_topics,
                "analyzed_items": len(analysis.news_items),
                "sentiment_distribution": {
                    "positive": len([item for item in analysis.news_items
                                   if item.sentiment_score > 0.1]),
                    "neutral": len([item for item in analysis.news_items
                                  if -0.1 <= item.sentiment_score <= 0.1]),
                    "negative": len([item for item in analysis.news_items
                                   if item.sentiment_score < -0.1])
                },
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in analyze_news_sentiment: {e}")
        return {
            "success": False,
            "error": f"Failed to analyze news sentiment: {str(e)}"
        }


@server.call_tool()
async def get_regulatory_events(
    region: str = "global",
    days_ahead: int = 30
) -> Dict[str, Any]:
    """
    Get upcoming regulatory events and announcements

    Args:
        region: Geographic region (global, us, eu, asia)
        days_ahead: Number of days to look ahead

    Returns:
        Dict containing regulatory events
    """
    try:
        logger.info(f"Fetching regulatory events for {region}")

        # This would integrate with regulatory calendar APIs
        # For now, returning a structured placeholder

        # Simulate some common regulatory events
        regulatory_events = [
            {
                "date": (utc_now() + timedelta(days=7)).isoformat(),
                "event": "SEC Cryptocurrency Regulation Hearing",
                "region": "US",
                "impact_level": "high",
                "description": "Senate hearing on cryptocurrency regulation framework"
            },
            {
                "date": (utc_now() + timedelta(days=14)).isoformat(),
                "event": "EU MiCA Implementation Update",
                "region": "EU",
                "impact_level": "medium",
                "description": "European Union Markets in Crypto-Assets regulation update"
            },
            {
                "date": (utc_now() + timedelta(days=21)).isoformat(),
                "event": "CBDC Development Report",
                "region": "Global",
                "impact_level": "medium",
                "description": "Central Bank Digital Currency development progress report"
            }
        ]

        # Filter by region if not global
        if region.lower() != "global":
            regulatory_events = [
                event for event in regulatory_events
                if event["region"].lower() == region.lower() or event["region"].lower() == "global"
            ]

        return {
            "success": True,
            "events": regulatory_events,
            "region": region,
            "days_ahead": days_ahead,
            "total_events": len(regulatory_events),
            "timestamp": utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in get_regulatory_events: {e}")
        return {
            "success": False,
            "error": f"Failed to get regulatory events: {str(e)}"
        }


@server.call_tool()
async def search_news(
    query: str,
    sources: Optional[List[str]] = None,
    timeframe: str = "24h",
    sentiment_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for specific cryptocurrency news

    Args:
        query: Search query keywords
        sources: News sources to search in
        timeframe: Time range for search
        sentiment_filter: Filter by sentiment (positive, negative, neutral)

    Returns:
        Dict containing search results
    """
    try:
        logger.info(f"Searching news for query: {query}")

        # Fetch news items
        fetch_result = await fetch_crypto_news(
            sources=sources,
            timeframe=timeframe,
            max_items=100
        )

        if not fetch_result.get("success"):
            return fetch_result

        news_items = fetch_result["news_items"]

        # Filter by search query
        query_lower = query.lower()
        matching_items = []

        for item in news_items:
            title_lower = item["title"].lower()
            description_lower = item["description"].lower()

            if (query_lower in title_lower or query_lower in description_lower):
                matching_items.append(item)

        # Apply sentiment filter if specified
        if sentiment_filter:
            async with NewsAnalyzer() as analyzer:
                filtered_items = []
                for item_data in matching_items:
                    full_text = f"{item_data['title']} {item_data['description']}"
                    sentiment_score = analyzer.calculate_sentiment_score(full_text)

                    if sentiment_filter.lower() == "positive" and sentiment_score > 0.1:
                        filtered_items.append(item_data)
                    elif sentiment_filter.lower() == "negative" and sentiment_score < -0.1:
                        filtered_items.append(item_data)
                    elif sentiment_filter.lower() == "neutral" and -0.1 <= sentiment_score <= 0.1:
                        filtered_items.append(item_data)

                matching_items = filtered_items

        return {
            "success": True,
            "query": query,
            "results": matching_items,
            "total_matches": len(matching_items),
            "sentiment_filter": sentiment_filter,
            "timeframe": timeframe,
            "timestamp": utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in search_news: {e}")
        return {
            "success": False,
            "error": f"Failed to search news: {str(e)}"
        }


async def main():
    """Main server entry point"""
    logger.info("Starting Crypto News MCP Server")

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