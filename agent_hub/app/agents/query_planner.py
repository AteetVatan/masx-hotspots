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
Query Planner Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Formulating search queries based on domain classification
- Planning data source queries (Google News RSS, GDELT)
- Optimizing query parameters for better results
- Managing query history and avoiding duplicates
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import re
import time
from .base import BaseAgent, AgentResult
from ..services.llm_service import LLMService
from ..services.database import DatabaseService
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger
from ..core.querystate import QueryState, QueryTranslated
from ..config.settings import get_settings
from ..core.utils import safe_json_loads


class QueryPlanner(BaseAgent):
    """
    Query Planner Agent for formulating optimized search queries.

    Responsibilities:
    - Generate search queries based on domain and context
    - Plan GDELT API queries with appropriate filters
    - Optimize query parameters for maximum relevance
    - Track query history to avoid duplicates
    """

    def __init__(self):
        """Initialize the Query Planner agent."""
        super().__init__("QueryPlanner")
        self.llm_service = LLMService.get_instance()  # singleton
        self.database_service = DatabaseService()
        self.logger = get_agent_logger("QueryPlanner")
        self.settings = get_settings()

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        try:
            # Prepare input data
            # Validate input
            if not self.validate_input(input_data):
                raise AgentException(
                    "Invalid input: missing title or description or entities or domains"
                )

            return self.plan_queries(input_data)

        except KeyError as e:
            return AgentResult(success=False, error=f"Missing required input: {str(e)}")

        except Exception as e:
            return AgentResult(success=False, error=f"QueryPlanner failed: {str(e)}")

    def plan_queries(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Plan search queries based on domain and context.

        Args:
            input_data: Input data containing title, description, entities, and domains

        Returns:
            AgentResult: Contains planned queries for different sources
        """
        try:

            # input_data = {
            #     "title": title,
            #     "description": description,
            #     "entities": entities,
            #     "domains": domains,
            # }

            self.logger.info(
                "Planning queries",
                title=input_data.get("title", ""),
                description=input_data.get("description", ""),
                entities=input_data.get("entities", []),
                domains=input_data.get("domains", []),
            )

            # Generate Google News RSS queries
            queries = self._generate_news_queries(input_data)

            # Generate GDELT queries
            # gdelt_queries = self._generate_gdelt_queries(input_data)
            # instead of this use all entity combinations

            # Check for recent similar queries to avoid duplicates
            # self._check_query_history(news_queries + gdelt_queries)

            # queries validation
            # queries = self.safe_flatten_queries(queries)

            # if self.settings.debug:
            #     max_queries = 10
            # else:
            #     max_queries = 1000

            query_states = []
            for query in queries:
                entities = query.get("entities", [])
                query_text = query.get("query", "")

                query_state = QueryState(
                    query=query_text,
                    list_query_translated=[
                        QueryTranslated(language="en", query_translated=query_text)
                    ],
                    entities=entities,
                    language=["en"],
                    entity_languages={},
                    rss_urls=[],
                    google_feed_entries=[],
                )
                query_states.append(query_state)

            result = {
                "query_states": query_states,
                # "gdelt_queries": gdelt_queries,
                "domains": input_data.get("domains", []),
                "query_count": len(queries),  # + len(gdelt_queries),
            }

            self.logger.info(
                "Query planning completed",
                query_count=result["query_count"],
                queries=len(queries),
                # gdelt_queries=len(gdelt_queries),
            )

            return AgentResult(
                success=True,
                data=result,
                metadata={
                    "agent": self.name,
                    "timestamp": datetime.utcnow(),
                    "domains": input_data.get("domains", []),
                },
            )

        except Exception as e:
            self.logger.error(f"Query planning failed: {e}")
            raise AgentException(f"Query planning failed: {str(e)}")

    def _generate_news_queries(
        self, input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate Google News RSS queries."""

        title = input_data.get("title", "")
        description = input_data.get("description", "")
        entities = input_data.get("entities", [])
        domains = input_data.get("domains", [])

        prompt = f"""
        You are a geopolitical news analyst. Your task is to generate 100 search queries that people might use to find news related to a global flashpoint.
        Use diverse perspectives: military, economic, cultural, religious, tech, environmental, migration, ideological, legal, civilizational.
        Include synonyms, abbreviations, slang, location names, and domain-specific terms.
        Each query should be short (max 6 words), realistic, and phrased the way a journalist, civilian, policymaker, activist, or intelligence analyst might search.        
        for domains: {domains}
        Title: {title}
        Description: {description}
        Entities: {entities}
        Domains: {domains}
        Generate specific, relevant queries that will return high-quality news articles.
        Focus on current events, breaking news, and trending topics in this domain.        
        Return as JSON array with objects containing:
        - query: The search query string
        - entities: List of involved countries from the query example: ["Iran", "Israel"].
        """
        # - language: List of ISO 639-1 language codes associated with those countries example: ["fa", "he"].
        # response = self.llm_service.generate_text(prompt)

        max_attempts = 3
        queries = []

        for attempt in range(max_attempts):
            try:
                response = self.llm_service.generate_text(prompt)
                parsed = safe_json_loads(response)
                # if len(parsed) == 0:
                #     self.logger.warning(f"Attempt {attempt + 1} failed to parse LLM response")
                #     continue

                queries_generated: List[Dict[str, Any]] = (
                    self.validate_and_fix_query_response(parsed)
                )

                # Deduplicate only based on the 'query' field
                seen_queries = set()
                unique_queries = []
                for q in queries_generated:
                    q_text = q.get("query")
                    if q_text and q_text not in seen_queries:
                        seen_queries.add(q_text)
                        unique_queries.append(q)

                if len(unique_queries) >= 5:
                    queries = unique_queries
                    break  # Exit retry loop
                else:
                    self.logger.info(
                        f"Attempt {attempt + 1}: only {len(unique_queries)} unique queries, retrying..."
                    )

            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1} failed to parse LLM response: {e}"
                )
                time.sleep(2)
        if not queries:
            self.logger.warning(
                "Falling back to default query due to repeated LLM failures."
            )
            queries = [
                {
                    "query": f"{domains} news",
                    "source": "google_news",
                    "domains": domains,
                }
            ]

        return queries

    def _generate_gdelt_queries(
        self, input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate GDELT API queries."""

        title = input_data.get("title", "")
        description = input_data.get("description", "")
        entities = input_data.get("entities", [])
        domains = input_data.get("domains", [])

        prompt = f"""
        Generate GDELT API search parameters for domains: {domains}
        Title: {title}
        Description: {description}
        Entities: {entities}
        Domains: {domains}  
        
        Generate GDELT query configurations that will return relevant events.
        Consider themes, keywords, and geographic filters appropriate for this domain.
        
        Return as JSON array with objects containing:
        - keywords: List of relevant keywords
        - themes: GDELT theme codes if applicable
        - locations: Geographic locations to focus on
        - description: Brief description of what this query targets
        """

        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            try:
                response = self.llm_service.generate_text(prompt)

                try:
                    parsed = safe_json_loads(response)
                except Exception as e:
                    self.logger.warning(
                        f"[Attempt {attempt}] Failed to parse JSON: {e}, preview: {response[:200]}"
                    )
                    continue  # Retry JSON parsing

                # Must be a list of valid dicts with non-empty keywords
                if isinstance(parsed, list):
                    queries = []
                    for item in parsed:
                        keywords = item.get("keywords", [])
                        if isinstance(keywords, list) and keywords:
                            queries.append(
                                {
                                    "keywords": keywords,
                                    "themes": (
                                        item.get("themes", [])
                                        if isinstance(item.get("themes", []), list)
                                        else []
                                    ),
                                    "locations": (
                                        item.get("locations", [])
                                        if isinstance(item.get("locations", []), list)
                                        else []
                                    ),
                                    "description": (
                                        item.get("description", "")
                                        if isinstance(item.get("description", ""), str)
                                        else ""
                                    ),
                                    "domains": domains,
                                    "source": "gdelt",
                                }
                            )

                    if queries:
                        return queries

                self.logger.info(
                    f"[Attempt {attempt}] No valid query objects found. Retrying..."
                )

            except Exception as e:
                self.logger.warning(f"[Attempt {attempt}] LLM call failed: {e}")

            # Fallback if all attempts fail
            self.logger.warning("[LLM] All attempts failed. Returning fallback query.")
            return [
                {
                    "keywords": [domains],
                    "source": "gdelt",
                    "domains": domains,
                    "themes": [],
                    "locations": [],
                    "description": f"Fallback query for domain: {domains}",
                }
            ]

    def _check_query_history(self, queries: List[Dict[str, Any]]) -> None:
        """Check recent query history to avoid duplicates."""
        try:
            # Get recent queries from database
            recent_queries = self.database_service.get_recent_queries(hours=24)

            # Simple duplicate detection
            for query in queries:
                query_text = query.get("query", str(query.get("keywords", [])))
                for recent in recent_queries:
                    if query_text.lower() in recent.get("query", "").lower():
                        self.logger.info(
                            f"Similar query found in history: {query_text}"
                        )
                        # Could modify query or skip it

        except Exception as e:
            self.logger.warning(f"Failed to check query history: {e}")

    def optimize_queries(
        self, queries: List[Dict[str, Any]], feedback: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Optimize queries based on feedback or performance data.

        Args:
            queries: List of queries to optimize
            feedback: Performance feedback or results data

        Returns:
            AgentResult: Contains optimized queries
        """
        try:
            self.logger.info("Optimizing queries", query_count=len(queries))

            # Simple optimization logic
            optimized_queries = []
            for query in queries:
                # Add time-based modifiers for better results
                if "news" in query.get("query", "").lower():
                    query["query"] += " when:1d"

                optimized_queries.append(query)

            return AgentResult(
                success=True,
                data={"optimized_queries": optimized_queries},
                metadata={
                    "agent": self.name,
                    "timestamp": datetime.utcnow(),
                    "optimization_type": "time_modifiers",
                },
            )

        except Exception as e:
            self.logger.error(f"Query optimization failed: {e}")
            raise AgentException(f"Query optimization failed: {str(e)}")

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for query planner.
        Args: input_data: Input data to validate
        Returns: bool: True if input is valid

        input_data = {
            "title": title,
            "description": description,
            "entities": entities,
            "domains": domains,
        }
        """

        if not isinstance(input_data, dict):
            return False

        # Must have at least title or description
        title = input_data.get("title", "")
        description = input_data.get("description", "")
        entities = input_data.get("entities", [])
        domains = input_data.get("domains", [])

        return (
            bool(title.strip() or description.strip())
            or bool(entities)
            or bool(domains)
        )

    def is_valid_query_string(
        self, q: str, min_len: int = 4, max_len: int = 300
    ) -> bool:
        """
        Validates if a query string is meaningful and safe.
        """
        if not isinstance(q, str):
            return False

        q = q.strip()

        if not (min_len <= len(q) <= max_len):
            return False

        if not re.search(r"[a-zA-Z]", q):  # must contain at least one letter
            return False

        if re.search(r"[;#{}<>]", q):  # reject dangerous special characters
            return False

        if len(q.split()) < 2:
            return False  # optionally enforce minimum word count

        return True

    def validate_and_fix_query_response(self, parsed: Any) -> List[Dict[str, Any]]:
        """
        Validate and fix a parsed query-entity list.

        Args:
            parsed: A Python list of dicts (not a raw JSON string)

        Returns:
            List of cleaned {"query": str, "entities": List[str]} dicts
        """
        if not isinstance(parsed, list):
            self.logger.warning("Expected a list of query dicts")
            return []

        cleaned = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            # Ensure 'query'
            query_str = str(item.get("query", "")).strip()
            if not query_str:
                continue  # skip empty or missing query

            # Ensure 'entities'
            raw_entities = item.get("entities", [])
            if not isinstance(raw_entities, list):
                raw_entities = []

            # Clean each entity string
            entities = [
                str(e).strip() for e in raw_entities if isinstance(e, str) and e.strip()
            ]

            cleaned.append({"query": query_str, "entities": entities})

        return cleaned

    def safe_flatten_queries(self, queries):
        """
        Safely flatten and validate a list of queries that may include strings or lists of strings.
        Returns a cleaned list of valid, unique queries.

        queries = [
            {
                "query": "Iran drone strikes near Israel border",
                "entities": ["Iran", "Israel"]
            },
            {
                "query": "UN sanctions on Russia for Ukraine war",
                "entities": ["Russia", "Ukraine"]
            }
            ]

        """
        flat_queries = []

        for q in queries:
            entities = q.get("entities", [])
            query = q.get("query", "")

            if isinstance(query, str):
                cleaned = query.strip()
                if self.is_valid_query_string(cleaned):
                    flat_queries.append(cleaned, entities)

            elif isinstance(query, list):
                for sub_q in query:
                    if isinstance(sub_q, str):
                        cleaned = sub_q.strip()
                        if self.is_valid_query_string(cleaned):
                            flat_queries.append(cleaned)
                            break  # Only first valid string in list

        # Optional: remove duplicates
        return list(dict.fromkeys(flat_queries))
