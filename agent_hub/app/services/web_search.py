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
Web search service for MASX-HOTSPOTS Agentic AI System.

Provides unified interface for web search operations including Google Custom Search,
news extraction, and content aggregation. Supports multiple search providers and
configurable search parameters.

Usage: from app.services.web_search import WebSearchService
    search_service = WebSearchService()
    context = search_service.gather_context("global tension last 24 hours")
"""

import requests
from typing import List, Dict, Any, Optional, Tuple
from newspaper import Article, Config
import time

from ..config.settings import get_settings
from ..config.logging_config import get_logger
from ..core.exceptions import ExternalServiceException, ConfigurationException


class WebSearchService:
    """
    Service for web search operations and content extraction.

    Features:
    - Google Custom Search API integration
    - News article extraction and parsing
    - Content aggregation and deduplication
    - Rate limiting and error handling
    - Configurable search parameters
    """

    NEWS_FILTER = (
        "("
        "inurl:geopolitics OR inurl:foreign-policy OR inurl:territory OR inurl:border OR inurl:ceasefire OR "
        "inurl:sovereignty OR inurl:treaty OR inurl:airstrike OR inurl:missile OR inurl:military OR inurl:defense OR "
        "inurl:conflict OR inurl:clash OR inurl:invasion OR inurl:war OR inurl:proxy-war OR inurl:nuclear OR "
        "inurl:troops OR inurl:drill OR inurl:deterrence OR inurl:arms OR inurl:weapons OR inurl:sanctions OR "
        "inurl:economy OR inurl:economic OR inurl:finance OR inurl:inflation OR inurl:debt OR inurl:trade OR "
        "inurl:investment OR inurl:gdp OR inurl:markets OR inurl:currency OR inurl:interest-rates OR inurl:banking OR "
        "inurl:minority OR inurl:ethnic OR inurl:cultural OR "
        "inurl:nationhood OR inurl:demographic OR inurl:identity OR inurl:genocide OR inurl:refugee OR "
        "inurl:climate OR inurl:environment OR inurl:drought OR inurl:flood OR inurl:disaster OR inurl:energy OR "
        "inurl:oil OR inurl:gas OR inurl:water OR inurl:resources OR inurl:scarcity OR inurl:pollution OR "
        "inurl:tech OR inurl:ai OR inurl:cyber OR inurl:hack OR inurl:espionage OR inurl:surveillance OR "
        "inurl:malware OR inurl:ransomware OR inurl:intelligence OR inurl:spy OR inurl:detention OR inurl:terror OR "
        "inurl:resistance OR inurl:insurgency OR inurl:occupation OR inurl:hegemony OR inurl:sphere-of-influence"
        ")"
    )

    NEWS_FILTER_COMPLETE = (
        "("
        # GEO & STRATEGIC
        "inurl:geopolitics OR inurl:foreign-policy OR inurl:territory OR inurl:border OR inurl:ceasefire OR "
        "inurl:sovereignty OR inurl:treaty OR inurl:airstrike OR inurl:missile OR inurl:military OR inurl:defense OR "
        "inurl:conflict OR inurl:clash OR inurl:invasion OR inurl:war OR inurl:proxy-war OR inurl:nuclear OR "
        "inurl:troops OR inurl:drill OR inurl:deterrence OR inurl:arms OR inurl:weapons OR inurl:sanctions OR "
        # ECONOMIC
        "inurl:economy OR inurl:economic OR inurl:finance OR inurl:inflation OR inurl:debt OR inurl:trade OR "
        "inurl:investment OR inurl:gdp OR inurl:markets OR inurl:currency OR inurl:interest-rates OR inurl:banking OR "
        # SOCIO-CULTURAL / ETHNIC
        "inurl:minority OR inurl:ethnic OR inurl:cultural OR "
        "inurl:nationhood OR inurl:demographic OR inurl:identity OR inurl:genocide OR inurl:refugee OR "
        # CLIMATE / ENERGY
        "inurl:climate OR inurl:environment OR inurl:drought OR inurl:flood OR inurl:disaster OR inurl:energy OR "
        "inurl:oil OR inurl:gas OR inurl:water OR inurl:resources OR inurl:scarcity OR inurl:pollution OR "
        # CYBER / AI / INTELLIGENCE
        "inurl:tech OR inurl:ai OR inurl:cyber OR inurl:hack OR inurl:espionage OR inurl:surveillance OR "
        "inurl:malware OR inurl:ransomware OR inurl:intelligence OR inurl:spy OR inurl:detention OR inurl:terror OR "
        "inurl:resistance OR inurl:insurgency OR inurl:occupation OR inurl:hegemony OR inurl:sphere-of-influence"
        ") "
        # 🎯 NEWS-TARGETED FILTERS
        "site:cnn.com OR site:bbc.com OR site:nytimes.com OR site:reuters.com OR site:aljazeera.com OR "
        "site:theguardian.com OR site:politico.com OR site:timesofindia.indiatimes.com OR site:euronews.com OR "
        "site:dw.com OR site:hindustantimes.com OR site:apnews.com OR site:news.yahoo.com OR site:ft.com OR "
        "site:latimes.com OR site:globaltimes.cn OR site:japantimes.co.jp OR site:stripes.com OR "
        "inurl:/news/ OR inurl:/article/ OR inurl:/world/ OR inurl:/politics/ OR inurl:/international/ "
        "-filetype:pdf -filetype:doc -filetype:ppt"
    )

    def __init__(self, provider: str = "google"):
        """
        Initialize web search service.

        Args:
            provider: Search provider to use (currently supports 'google')
        """
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.provider = provider

        # Initialize provider-specific configuration
        self._init_provider_config()

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests

    def _init_provider_config(self):
        """Initialize provider-specific configuration."""
        if self.provider == "google":
            self.api_key = getattr(self.settings, "google_search_api_key", None)
            self.cx = getattr(self.settings, "google_cx", None)

            if not self.api_key or not self.cx:
                raise ConfigurationException(
                    "Google Search API key and CX not configured. "
                    "Set GOOGLE_SEARCH_API_KEY and GOOGLE_CX environment variables."
                )

            self.base_url = "https://www.googleapis.com/customsearch/v1"
        else:
            raise ConfigurationException(
                f"Unsupported search provider: {self.provider}"
            )

    def _rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def search_news(
        self,
        query: str,
        news_filter: bool = True,
        num_results: int = 10,
        date_restrict: str = "d1",
        sort_by: str = "date",
        page: int = 1,
    ) -> List[str]:
        """
        Search for news articles using the configured provider.

        Args:
            query: Search query string
            num_results: Number of results to return (max 10 for Google)
            date_restrict: Date restriction (d1 = last day, w1 = last week, etc.)
            sort_by: Sort order (date, relevance)

        Returns:
            List of article URLs

        Raises:
            ExternalServiceException: If search API call fails
        """
        try:
            self._rate_limit()

            if news_filter:
                query = f"{query} {self.NEWS_FILTER}"

            if self.provider == "google":
                urls = self._google_search(
                    query, num_results, date_restrict, sort_by, page
                )
                return urls
            else:
                raise ConfigurationException(f"Unsupported provider: {self.provider}")

        except Exception as e:
            raise ExternalServiceException(
                f"Search operation failed: {str(e)}",
                context={"provider": self.provider, "query": query},
            )

    def _google_search(
        self,
        query: str,
        num_results: int,
        date_restrict: str,
        sort_by: str,
        page: int = 1,
    ) -> List[str]:
        """Execute Google Custom Search API call."""
        # Calculate start index based on the page (Google starts at 1)
        start_index = (page - 1) * 10 + 1
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "dateRestrict": date_restrict,
            "sort": sort_by,
            "num": min(num_results, 10),  # Google API limit
            "start": start_index,
        }

        self.logger.debug(
            "Executing Google search",
            query=query,
            num_results=num_results,
            date_restrict=date_restrict,
        )

        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Extract URLs from search results
        urls = []
        for item in data.get("items", []):
            if "link" in item:
                urls.append(item["link"])

        self.logger.info(
            "Google search completed",
            query=query,
            results_found=len(urls),
            total_results=data.get("searchInformation", {}).get("totalResults", 0),
        )

        return urls

    def extract_article(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Extract article content from a URL.

        Args:
            url: Article URL to extract
            timeout: Request timeout in seconds

        Returns:
            Extracted article text or None if extraction fails
        """
        try:
            self.logger.debug(f"Extracting article from: {url}")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            config = Config()
            config.browser_user_agent = user_agent
            config.request_timeout = 10
            article = Article(url, config=config)
            article.download()
            time.sleep(2)
            article.parse()

            if article.text and len(article.text.strip()) > 100:
                self.logger.debug(
                    "Article extracted successfully",
                    url=url,
                    text_length=len(article.text),
                )
                return article.text
            else:
                self.logger.warning(
                    "Article extraction returned insufficient content",
                    url=url,
                    text_length=len(article.text) if article.text else 0,
                )
                return None

        except Exception as e:
            self.logger.warning("Article extraction failed", url=url, error=str(e))
            return None

    def gather_context(
        self,
        query: str,
        max_articles: int = 10,
        min_content_length: int = 100,
        page: int = 1,
        news_filter: bool = True,
    ) -> Tuple[str, List[str]]:
        """
        Gather context by searching and extracting multiple articles.

        Args:
            query: Search query
            max_articles: Maximum number of articles to process
            min_content_length: Minimum content length to include

        Returns:
            Aggregated context from all articles
        """
        try:
            self.logger.info(
                "Starting context gathering", query=query, max_articles=max_articles
            )

            # Search for articles
            urls = self.search_news(
                query, num_results=max_articles, page=page, news_filter=news_filter
            )

            if not urls:
                self.logger.warning("No search results found", query=query)
                return "", []  # Tuple[str, List[str]]

            # Extract content from articles
            contents = []
            successful_extractions = 0

            for i, url in enumerate(urls):
                self.logger.debug(f"Processing article {i+1}/{len(urls)}: {url}")

                content = self.extract_article(url)
                if content and len(content.strip()) >= min_content_length:
                    contents.append(content.strip())
                    successful_extractions += 1

                # Add small delay between extractions to be respectful
                time.sleep(0.5)

            # Combine all content
            combined_context = "\n\n".join(contents)

            self.logger.info(
                "Context gathering completed",
                query=query,
                urls_processed=len(urls),
                successful_extractions=successful_extractions,
                total_context_length=len(combined_context),
            )

            return combined_context, urls

        except Exception as e:
            self.logger.error("Context gathering failed", query=query, error=str(e))
            raise ExternalServiceException(
                f"Context gathering failed: {str(e)}", context={"query": query}
            )

    def search_with_exclusions(
        self, base_query: str, exclude_terms: List[str], news_filter: bool = True
    ) -> str:
        """
        Search with exclusion terms to avoid duplicate content.

        Args:
            base_query: Base search query
            exclude_terms: Terms to exclude from search

        Returns:
            Aggregated context from search results
        """
        # Build exclusion query
        exclusion_query = " ".join(f'-"{term}"' for term in exclude_terms)
        full_query = f"{base_query} {exclusion_query}".strip()

        self.logger.info(
            "Searching with exclusions",
            base_query=base_query,
            exclude_terms=exclude_terms,
            full_query=full_query,
        )

        return self.gather_context(full_query, news_filter=news_filter)

    def get_search_stats(self) -> Dict[str, Any]:
        """
        Get search service statistics.

        Returns:
            Dict containing search statistics
        """
        return {
            "provider": self.provider,
            "last_request_time": self.last_request_time,
            "min_request_interval": self.min_request_interval,
        }


# Factory function for easy service creation
def create_web_search_service(provider: str = "google") -> WebSearchService:
    """
    Create a web search service instance.

    Args:
        provider: Search provider to use

    Returns:
        WebSearchService: Configured search service instance
    """
    return WebSearchService(provider)
