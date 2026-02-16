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
Google RSS Agent for MASX-HOTSPOTS Agentic AI System.

Extracts RSS feeds from Google News.

Usage:
    from app.agents.google_rss_agent import GoogleRssAgent

    agent = GoogleRssAgent()
    result = agent.run({"queries": [{"query": "...", "entity_languages": {"US": ["en"]}}]})
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from .base import BaseAgent, AgentResult
from ..core.exceptions import AgentException
from ..core.querystate import QueryState
from ..services import FeedParserService
from datetime import datetime
from ..config.logging_config import get_agent_logger


class GoogleRssFeederAgent(BaseAgent):

    def __init__(self):
        """Initialize the Google RSS Feeder Agent."""
        super().__init__(
            name="GoogleRssFeederAgent",
            description="Extracts RSS feeds from Google News",
        )
        self.feed_parser_service = FeedParserService()
        self.logger = get_agent_logger("GoogleRssFeederAgent")

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute Google RSS Feeder Agent.
        Args: input_data: Dictionary containing 'queries' field
        Returns: AgentResult: Result with RSS URLs and feed entries
        """
        try:
            # Validate input
            if not self.validate_input(input_data):
                raise AgentException("Invalid input: missing queries")

            queries = [
                QueryState.model_validate(q) for q in input_data.get("queries", [])
            ]
            rss_urls = []
            feed_entries = []
            for query in queries:
                query.rss_urls = self._get_rss_urls(query)
                query = self.feed_parser_service.run(query)
                rss_urls.extend(query.rss_urls)
                feed_entries.extend(query.google_feed_entries)

            result = {
                "queries": queries,
                "rss_urls": rss_urls,
                "feed_entries": feed_entries,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Google RSS Agent failed: {str(e)}",
                metadata={"exception_type": type(e).__name__},
            )

    def _get_rss_urls(self, query: QueryState) -> List[str]:
        """
        Build Google News RSS feed URLs for all translated queries.
        """
        rss_urls = []

        for translated in query.list_query_translated:
            lang = translated.language
            query_text = translated.query_translated

            query_encoded = self._get_query_encoded(query_text)
            alpha2 = self._get_alpha2_for_lang(lang, query.entity_languages)
            ceid = self._get_ceid(lang, alpha2)

            url = f"https://news.google.com/rss/search?q={query_encoded}&hl={lang.lower()}"
            if ceid:
                url += f"&ceid={ceid}"

            rss_urls.append(url)
        return list(set(rss_urls))

    def _get_alpha2_for_lang(
        self, lang: str, entity_languages: Dict[str, List[str]]
    ) -> Optional[str]:
        """
        Get the alpha-2 code for a given language from entity-language mapping.
        """
        for entity, languages in entity_languages.items():
            if lang in languages:
                return entity
        return None

    def _get_query_encoded(self, query: str) -> str:
        """
        Safely encode the query for Google News RSS.
        """
        return quote_plus(query.strip())

    def _get_ceid(self, lang: str, alpha2: Optional[str]) -> Optional[str]:
        """
        Construct the CEID field if alpha2 is provided.
        """
        if alpha2:
            return f"{alpha2.upper()}:{lang.upper()}"
        return None

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for google rss agent.
        Args: input_data: Input data to validate
        Returns: bool: True if input is valid

          input_data = {
                "queries": flashpoint.queries, # list[QueryState]
            }

        """
        if not isinstance(input_data, dict):
            return False
        queries = input_data.get("queries", [])
        if not isinstance(queries, list):
            return False
        for query in queries:
            if not isinstance(query, QueryState):
                return False
        return True
