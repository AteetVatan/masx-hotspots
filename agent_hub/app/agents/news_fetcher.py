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
News Fetcher Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Fetching news articles from Google News RSS feeds
- Processing RSS feed data
- Rate limiting and error handling
- Caching results for performance
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseAgent, AgentResult
from ..services.data_sources import DataSourcesService
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger


class NewsFetcher(BaseAgent):
    """
    News Fetcher Agent for retrieving news articles from Google News RSS.

    Responsibilities:
    - Fetch news from Google News RSS feeds
    - Process and parse RSS data
    - Handle rate limiting and errors
    - Cache results for performance
    """

    def __init__(self):
        """Initialize the News Fetcher agent."""
        super().__init__("NewsFetcher")
        self.data_sources_service = DataSourcesService()
        self.logger = get_agent_logger("NewsFetcher")

    def execute(
        self, queries: List[Dict[str, Any]], max_articles: Optional[int] = 100
    ) -> AgentResult:
        """
        Fetch news articles from Google News RSS based on queries.

        Args:
            queries: List of search queries to execute
            max_articles: Maximum number of articles to fetch per query

        Returns:
            AgentResult: Contains fetched news articles
        """
        try:
            self.logger.info(
                "Fetching news articles",
                query_count=len(queries),
                max_articles=max_articles,
            )

            all_articles = []

            for query in queries:
                query_text = query.get("query", "")
                if not query_text:
                    continue

                # Fetch articles for this query
                articles = self._fetch_articles_for_query(query_text, max_articles)
                all_articles.extend(articles)

                self.logger.info(
                    f"Fetched {len(articles)} articles for query: {query_text}"
                )

            result = {
                "articles": all_articles,
                "total_count": len(all_articles),
                "queries_executed": len(queries),
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                "News fetching completed",
                total_articles=len(all_articles),
                queries_executed=len(queries),
            )

            return AgentResult(
                success=True,
                data=result,
                metadata={
                    "agent": self.name,
                    "timestamp": datetime.utcnow(),
                    "query_count": len(queries),
                },
            )

        except Exception as e:
            self.logger.error(f"News fetching failed: {e}")
            raise AgentException(f"News fetching failed: {str(e)}")

    def _fetch_articles_for_query(
        self, query: str, max_articles: int
    ) -> List[Dict[str, Any]]:
        """Fetch articles for a specific query."""
        try:
            # Use the data sources service to fetch from Google News RSS
            articles = self.data_sources_service.fetch_google_news_rss(
                query=query, max_results=max_articles
            )

            # Convert to standard format
            formatted_articles = []
            for article in articles:
                formatted_articles.append(
                    {
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "snippet": article.get("snippet", ""),
                        "source": article.get("source", ""),
                        "published_date": article.get("published_date", ""),
                        "query": query,
                    }
                )

            return formatted_articles

        except Exception as e:
            self.logger.warning(f"Failed to fetch articles for query '{query}': {e}")
            return []

    def fetch_trending_news(
        self, categories: Optional[List[str]] = None, max_articles: Optional[int] = 50
    ) -> AgentResult:
        """
        Fetch trending news articles from popular categories.

        Args:
            categories: List of news categories to fetch
            max_articles: Maximum number of articles per category

        Returns:
            AgentResult: Contains trending news articles
        """
        try:
            self.logger.info(
                "Fetching trending news",
                categories=categories,
                max_articles=max_articles,
            )

            # Default categories if none provided
            if not categories:
                categories = ["world", "business", "technology", "politics"]

            all_articles = []

            for category in categories:
                query = f"category:{category}"
                articles = self._fetch_articles_for_query(query, max_articles)
                all_articles.extend(articles)

            result = {
                "articles": all_articles,
                "categories": categories,
                "total_count": len(all_articles),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={
                    "agent": self.name,
                    "timestamp": datetime.utcnow(),
                    "categories": categories,
                },
            )

        except Exception as e:
            self.logger.error(f"Trending news fetching failed: {e}")
            raise AgentException(f"Trending news fetching failed: {str(e)}")

    def validate_articles(self, articles: List[Dict[str, Any]]) -> AgentResult:
        """
        Validate fetched articles for quality and relevance.

        Args:
            articles: List of articles to validate

        Returns:
            AgentResult: Contains validation results
        """
        try:
            self.logger.info(f"Validating {len(articles)} articles")

            valid_articles = []
            invalid_articles = []

            for article in articles:
                # Basic validation
                if self._is_valid_article(article):
                    valid_articles.append(article)
                else:
                    invalid_articles.append(article)

            result = {
                "valid_articles": valid_articles,
                "invalid_articles": invalid_articles,
                "validation_stats": {
                    "total": len(articles),
                    "valid": len(valid_articles),
                    "invalid": len(invalid_articles),
                },
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Article validation failed: {e}")
            raise AgentException(f"Article validation failed: {str(e)}")

    def _is_valid_article(self, article: Dict[str, Any]) -> bool:
        """Check if an article is valid."""
        required_fields = ["title", "url"]

        for field in required_fields:
            if not article.get(field):
                return False

        # Check if URL is valid
        url = article.get("url", "")
        if not url.startswith(("http://", "https://")):
            return False

        return True
