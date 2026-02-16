# ┌───────────────────────────────────────────────────────────────┐
# │  Copyright (c) 2025 Ateet Vatan Bahmani                      │
# │  Project: MASX AI – Strategic Agentic AI System              │
# │  All rights reserved.                                        │
# └───────────────────────────────────────────────────────────────┘
#
# MASX AI is a proprietary software system developed and owned by Ateet Vatan Bahmani.
# The source code, documentation, workflows, designs, and naming (including "MASX AI")
# are protected by applicable copyright and trademark laws.
#
# Redistribution, modification, commercial use, or publication of any portion of this
# project without explicit written consent is strictly prohibited.
#
# This project is not open-source and is intended solely for internal, research,
# or demonstration use by the author.
#
# Contact: ab@masxai.com | MASXAI.com

"""
Data Sources Service for MASX-HOTSPOTS Agentic AI System.

Provides integration with external data sources:
- Google News RSS feeds
- GDELT (Global Database of Events, Language, and Tone)
- Custom RSS feeds
- News API integration

Features:
- Rate limiting and caching
- Data validation and sanitization
- Error handling and retry logic
- Real-time data streaming
- Configurable filtering and enrichment
"""

import asyncio
import aiohttp
import feedparser
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from urllib.parse import urljoin, urlparse
import json
import hashlib
import time
from dataclasses import dataclass
from enum import Enum

import structlog
from pydantic import BaseModel, HttpUrl, validator
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import DataSourceError, ValidationError
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)


class DataSourceType(str, Enum):
    """Supported data source types."""

    GOOGLE_NEWS_RSS = "google_news_rss"
    GDELT_API = "gdelt_api"
    CUSTOM_RSS = "custom_rss"
    NEWS_API = "news_api"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""

    name: str
    source_type: DataSourceType
    url: str
    api_key: Optional[str] = None
    rate_limit: int = 100  # requests per minute
    cache_ttl: int = 300  # seconds
    enabled: bool = True
    filters: Optional[Dict[str, Any]] = None


class Article(BaseModel):
    """Standardized article model."""

    id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: HttpUrl
    source: str
    published_at: datetime
    language: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[float] = None
    keywords: List[str] = []
    metadata: Dict[str, Any] = {}

    @validator("id", pre=True, always=True)
    def generate_id(cls, v, values):
        """Generate unique ID if not provided."""
        if v:
            return v
        # Generate ID from URL and title
        url = values.get("url", "")
        title = values.get("title", "")
        content = f"{url}{title}{values.get('published_at', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class GDELTEvent(BaseModel):
    """GDELT event model."""

    event_id: str
    event_time: datetime
    actor1_name: Optional[str] = None
    actor2_name: Optional[str] = None
    event_code: Optional[str] = None
    event_base_code: Optional[str] = None
    event_root_code: Optional[str] = None
    quad_class: Optional[int] = None
    goldstein_scale: Optional[float] = None
    num_mentions: Optional[int] = None
    num_sources: Optional[int] = None
    num_articles: Optional[int] = None
    avg_tone: Optional[float] = None
    actor1_geo_country_code: Optional[str] = None
    actor2_geo_country_code: Optional[str] = None
    action_geo_country_code: Optional[str] = None
    source_url: Optional[str] = None
    mentions: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class DataSourcesService:
    """Service for managing and querying data sources."""

    def __init__(self):
        self.settings = get_settings()
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Any] = {}
        self.rate_limiters: Dict[str, float] = {}
        self.sources: Dict[str, DataSourceConfig] = {}
        self._setup_sources()

    def _setup_sources(self):
        """Initialize data sources from configuration."""
        # Google News RSS sources
        google_news_sources = [
            "https://news.google.com/rss/search?q=geopolitics&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=international+relations&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=diplomacy&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=conflict&hl=en-US&gl=US&ceid=US:en",
        ]

        for i, url in enumerate(google_news_sources):
            self.sources[f"google_news_{i}"] = DataSourceConfig(
                name=f"Google News {i+1}",
                source_type=DataSourceType.GOOGLE_NEWS_RSS,
                url=url,
                rate_limit=60,
                cache_ttl=300,
            )

        # GDELT API
        if self.settings.gdelt_api_key:
            self.sources["gdelt"] = DataSourceConfig(
                name="GDELT API",
                source_type=DataSourceType.GDELT_API,
                url="https://api.gdeltproject.org/api/v2",
                api_key=self.settings.gdelt_api_key,
                rate_limit=30,
                cache_ttl=600,
            )

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "MASX-AI-System/1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(
        self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None
    ) -> str:
        """Make HTTP request with retry logic."""
        if not self.session:
            raise DataSourceError("Session not initialized")

        try:
            async with self.session.get(
                url, params=params, headers=headers
            ) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error("HTTP request failed", url=url, error=str(e))
            raise DataSourceError(f"HTTP request failed: {e}")

    def _check_rate_limit(self, source_name: str) -> bool:
        """Check if rate limit allows request."""
        now = time.time()
        last_request = self.rate_limiters.get(source_name, 0)
        source = self.sources.get(source_name)

        if not source:
            return False

        min_interval = 60.0 / source.rate_limit
        if now - last_request < min_interval:
            return False

        self.rate_limiters[source_name] = now
        return True

    async def fetch_google_news_rss(self, source_name: str) -> List[Article]:
        """Fetch articles from Google News RSS feed."""
        if not self._check_rate_limit(source_name):
            raise DataSourceError(f"Rate limit exceeded for {source_name}")

        source = self.sources[source_name]
        cache_key = f"rss_{source_name}_{int(time.time() // source.cache_ttl)}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            content = await self._make_request(source.url)
            feed = feedparser.parse(content)

            articles = []
            for entry in feed.entries[:50]:  # Limit to 50 articles
                try:
                    # Parse publication date
                    published = datetime.now()
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])

                    article = Article(
                        title=entry.title,
                        description=getattr(entry, "summary", None),
                        url=entry.link,
                        source=(
                            entry.source.title
                            if hasattr(entry, "source")
                            else "Google News"
                        ),
                        published_at=published,
                        language="en",
                        country="US",
                        category="geopolitics",
                        keywords=entry.get("tags", []),
                    )
                    articles.append(article)
                except Exception as e:
                    logger.warning(
                        "Failed to parse RSS entry",
                        error=str(e),
                        entry=entry.get("title", "Unknown"),
                    )
                    continue

            self.cache[cache_key] = articles
            logger.info(
                "Fetched Google News RSS articles",
                source=source_name,
                count=len(articles),
            )
            return articles

        except Exception as e:
            logger.error(
                "Failed to fetch Google News RSS", source=source_name, error=str(e)
            )
            raise DataSourceError(f"Failed to fetch RSS: {e}")

    async def fetch_gdelt_events(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[GDELTEvent]:
        """Fetch events from GDELT API."""
        source_name = "gdelt"
        if not self._check_rate_limit(source_name):
            raise DataSourceError(f"Rate limit exceeded for {source_name}")

        source = self.sources[source_name]
        if not source.api_key:
            raise DataSourceError("GDELT API key not configured")

        # Build query parameters
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": 100,
        }

        if start_date:
            params["startdatetime"] = start_date.strftime("%Y%m%d%H%M%S")
        if end_date:
            params["enddatetime"] = end_date.strftime("%Y%m%d%H%M%S")

        cache_key = f"gdelt_{hash(query)}_{int(time.time() // source.cache_ttl)}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            content = await self._make_request(
                f"{source.url}/doc/doc",
                params=params,
                headers={"Authorization": f"Bearer {source.api_key}"},
            )

            data = json.loads(content)
            events = []

            for item in data.get("articles", []):
                try:
                    event = GDELTEvent(
                        event_id=item.get("seendate", ""),
                        event_time=datetime.strptime(
                            item.get("seendate", "20240101"), "%Y%m%d%H%M%S"
                        ),
                        source_url=item.get("url", ""),
                        num_mentions=item.get("nummentions", 0),
                        avg_tone=item.get("avgtone", 0.0),
                        mentions=item.get("mentions", []),
                        metadata=item,
                    )
                    events.append(event)
                except Exception as e:
                    logger.warning("Failed to parse GDELT event", error=str(e))
                    continue

            self.cache[cache_key] = events
            logger.info("Fetched GDELT events", query=query, count=len(events))
            return events

        except Exception as e:
            logger.error("Failed to fetch GDELT events", query=query, error=str(e))
            raise DataSourceError(f"Failed to fetch GDELT events: {e}")

    async def fetch_all_sources(self, max_age_hours: int = 24) -> List[Article]:
        """Fetch articles from all enabled sources."""
        all_articles = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        for source_name, source in self.sources.items():
            if not source.enabled:
                continue

            try:
                if source.source_type == DataSourceType.GOOGLE_NEWS_RSS:
                    articles = await self.fetch_google_news_rss(source_name)
                    # Filter by age
                    articles = [a for a in articles if a.published_at >= cutoff_time]
                    all_articles.extend(articles)

                elif source.source_type == DataSourceType.GDELT_API:
                    # GDELT events are handled separately
                    continue

            except Exception as e:
                logger.error(
                    "Failed to fetch from source", source=source_name, error=str(e)
                )
                continue

        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

        logger.info("Fetched articles from all sources", total=len(unique_articles))
        return unique_articles

    async def stream_articles(
        self, interval_seconds: int = 300
    ) -> AsyncGenerator[List[Article], None]:
        """Stream articles continuously."""
        while True:
            try:
                articles = await self.fetch_all_sources()
                yield articles
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error("Error in article streaming", error=str(e))
                await asyncio.sleep(60)  # Wait before retry

    def get_source_status(self) -> Dict[str, Any]:
        """Get status of all data sources."""
        status = {}
        for name, source in self.sources.items():
            status[name] = {
                "name": source.name,
                "type": source.source_type.value,
                "enabled": source.enabled,
                "rate_limit": source.rate_limit,
                "cache_ttl": source.cache_ttl,
                "last_request": self.rate_limiters.get(name, 0),
            }
        return status

    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Data sources cache cleared")

    def add_custom_source(self, config: DataSourceConfig):
        """Add a custom data source."""
        self.sources[config.name] = config
        logger.info(
            "Added custom data source", name=config.name, type=config.source_type.value
        )
