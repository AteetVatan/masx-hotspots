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
Event Fetcher Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Fetching events from GDELT 2.0 API
- Processing GDELT event data
- Rate limiting and error handling
- Filtering events by relevance
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from itertools import combinations
import json
import re
from .base import BaseAgent, AgentResult
from ..services.data_sources import DataSourcesService
from ..core.state import AgentState
from ..core import QueryState, QueryTranslated, FeedEntry
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger
from ..services import MasxGdeltService
from ..core.country_normalizer import CountryNormalizer
from ..core.language_utils import LanguageUtils
from ..services.llm_service import LLMService
from ..core import DateUtils
from ..services import FeedParserService
from ..config.settings import get_settings
from ..core.utils import safe_json_loads


class GdeltFetcherAgent(BaseAgent):
    """
    Event Fetcher Agent for retrieving events from GDELT 2.0.

    Responsibilities:
    - Fetch events from GDELT API
    - Process and filter event data
    - Handle rate limiting and errors
    - Apply relevance filters
    """

    def __init__(self):
        """Initialize the GDELT Fetcher agent."""
        super().__init__(
            name="GdeltFetcherAgent",
            description="Extracts RSS feeds from Google News",
        )
        # self.feed_parser_service = FeedParserService()
        self.logger = get_agent_logger("GdeltFetcherAgent")
        self.masx_gdelt_service = MasxGdeltService()
        self.country_normalizer = CountryNormalizer()
        self.llm_service = LLMService()
        self.feed_parser_service = FeedParserService()
        self.settings = get_settings()

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

            result: AgentResult = self.fetch_events(queries)

            return result
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Gdelt Fetcher Agent failed: {str(e)}",
                metadata={"exception_type": type(e).__name__},
            )

    def fetch_events(
        self, queries: List[QueryState], max_events: Optional[int] = 1000
    ) -> AgentResult:
        """
        Fetch events from GDELT based on queries.

        Args:
            queries: List of GDELT query configurations
            max_events: Maximum number of events to fetch per query

        Returns:
            AgentResult: Contains fetched GDELT events
        """
        try:
            self.logger.info(
                "Fetching GDELT events", query_count=len(queries), max_events=max_events
            )

            combo_set = set()  # for deduplication (keyword, country)
            start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            all_combo_list = []
            for query in queries:

                maxrecords = 250
                countries = self.country_normalizer.get_country_names_from_pycountry(
                    query.entities
                )

                if len(countries) == 0:
                    # in case of no countries, ask llM to add countries
                    countries = self._get_related_countries_from_llm(
                        query.query, query.entities
                    )
                    # valid country name
                    countries = (
                        self.country_normalizer.get_country_names_from_pycountry(
                            countries
                        )
                    )
                    if not countries:
                        continue  # if no countries, skip this query

                combo_list = []
                if len(query.entities) > 1:
                    default_combo = {
                        "start_date": start_date,
                        "end_date": end_date,
                        "maxrecords": maxrecords,
                        "keyword": ", ".join(query.entities),
                    }
                    combo_list.append(default_combo)

                for r in range(1, len(query.entities) + 1):
                    for keyword_combo in combinations(query.entities, r):
                        keyword_str = ", ".join(keyword_combo)

                        for country in countries:
                            if keyword_str == country:
                                continue
                            combo_key = (keyword_str, country)
                            if combo_key in combo_set:
                                continue
                            combo_set.add(combo_key)

                            # make the keyword length more then 5 characters
                            if len(keyword_str) <= 5:
                                key_len = len(keyword_str)
                                n = 5 - key_len
                                keyword_str = keyword_str + " " * n

                            combo = {
                                "start_date": start_date,
                                "end_date": end_date,
                                "maxrecords": maxrecords,
                                "keyword": keyword_str,
                                "country": country,
                            }

                            combo_list.append(combo)

                # remove all combos that are already in all_combo_list
                combo_list = [
                    combo for combo in combo_list if combo not in all_combo_list
                ]

                if not combo_list:
                    query.gdelt_feed_entries = []
                    continue

                # Fetch in batch (threaded)
                # if self.settings.debug:
                # combo_list = combo_list[:3]

                results = self.masx_gdelt_service.fetch_articles_batch_threaded(
                    combo_list
                )
                # Convert articles to FeedEntry
                query.gdelt_feed_entries = (
                    self.feed_parser_service.process_gdelt_feed_entries(results)
                )
                all_combo_list.extend(combo_list)

            return AgentResult(
                success=True,
                data={"queries": queries, "timestamp": datetime.utcnow().isoformat()},
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Gdelt Fetcher Agent failed: {str(e)}",
                metadata={"exception_type": type(e).__name__},
            )

    def _get_related_countries_from_llm(
        self, query: str, entities: List[str]
    ) -> list[str]:
        """Use LLM to infer geopolitically related countries for given entities."""

        system_prompt = (
            "You are a geopolitical analyst.\n"
            "Given named entities, return countries directly involved, affected, or influential.\n"
            "Output must be JSON with:\n"
            "- countries: list of country names [country_1, country_2, ...]\n"
            "Be precise. No guessing."
        )

        user_prompt = f"""
        Query: "{query}"
        Entities: {entities}
        Which countries are geopolitically related?
        """

        max_attempts = 1  # TODO: remove this
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.llm_service.generate_text(
                    user_prompt=user_prompt.strip(),
                    system_prompt=system_prompt,
                    temperature=0,
                    max_tokens=512,
                )

                result = self.validate_related_countries_json(response)
                if result:
                    return result

                self.logger.info(
                    f"[Attempt {attempt}] Empty or invalid country list, retrying..."
                )

            except Exception as e:
                self.logger.warning(
                    f"[Attempt {attempt}] LLM failed to infer related countries: {e}"
                )

        return []

    def validate_related_countries_json(self, response_text: str) -> list[str]:
        try:
            # Extract first JSON object using regex
            match = re.search(r"\{[\s\S]*?\}", response_text)
            if not match:
                raise ValueError("No JSON object found in response.")

            json_part = match.group(0)
            data = safe_json_loads(json_part)

            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object.")

            if "countries" not in data or not isinstance(data["countries"], list):
                raise ValueError("Missing or invalid 'countries' list.")

            return data["countries"]

        except Exception as e:
            self.logger.warning(f"[Validator] Failed to parse related countries: {e}")
            return []

    def _calculate_relevance_score(self, event: Dict[str, Any]) -> float:
        """Calculate relevance score for an event."""
        # Simple scoring based on presence of key fields
        score = 0.0

        if event.get("title"):
            score += 0.3
        if event.get("url"):
            score += 0.2
        if event.get("source"):
            score += 0.2
        if event.get("published_date"):
            score += 0.2
        if event.get("keywords"):
            score += 0.1

        return min(score, 1.0)

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
