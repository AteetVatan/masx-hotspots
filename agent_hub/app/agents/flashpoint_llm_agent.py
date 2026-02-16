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
Flashpoint LLM Agent for MASX-HOTSPOTS Agentic AI System.

Implements iterative flashpoint detection using LLM reasoning and web search.
Detects global geopolitical flashpoints through multi-domain analysis with
entity tracking and deduplication.

Usage: from app.agents.flashpoint_llm_agent import FlashpointLLMAgent
    agent = FlashpointLLMAgent()
    result = agent.run({"max_iterations": 5, "target_flashpoints": 10})
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, ValidationError, RootModel
from copy import deepcopy

from .base import BaseAgent, AgentResult
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..core.country_normalizer import CountryNormalizer
from ..services.llm_service import LLMService
from ..services.web_search import WebSearchService
from ..services.flashpoint_detection import FlashpointDetectionService, Flashpoint
from ..services.token_tracker import get_token_tracker
from ..config.logging_config import get_logger
from ..config.settings import get_settings
from ..core.flashpoint import FlashpointDataset, FlashpointItem
from ..core.utils import safe_json_loads


class FlashpointLLMAgent(BaseAgent):
    """
    Agent for detecting global geopolitical flashpoints using LLM reasoning.

    Features:
    - Iterative search and reasoning cycles
    - Entity tracking and deduplication
    - Multi-domain geopolitical analysis
    - JSON validation and error handling
    - Token cost tracking
    """

    # System prompt for flashpoint detection
    SYSTEM_PROMPT = (
        "You are a global strategic signal analyst.\n"
        "Your mission is to detect the top 10 most active or unstable global regions in the last 24 hours, "
        "based on multi-domain tension signals.\n\n"
        "Include ALL of the following domains:\n"
        "- Geopolitical, Military, Economic, Cultural, Religious, Tech, Cybersecurity, Environmental, Demographics, Sovereignty.\n\n"
        "Each output must include:\n"
        "- title: short phrase (e.g., 'US–China Chip War')\n"
        "- description: one factual sentence (≤200 chars)\n"
        "- entities: list of involved countries, organizations, regions, or non-state actors\n\n"
        "Output: JSON list of 10 dictionaries.\n"
        "NO extra text, bullets, or explanation. JUST clean JSON.\n"
        'Example: [{"title": "X", "description": "Y", "entities": ["Israel", "Iran"]}]'
    )

    USER_PROMPT = (
        "List 10 top global flashpoints from the past 24 hours with title, description, and involved entities "
        "(countries, regions, organizations, or non-state actors).\n\n"
        "Return only valid JSON."
    )

    def __init__(self):
        """Initialize FlashpointLLMAgent with required services."""
        super().__init__(
            name="flashpoint_llm_agent",
            description="Agent for detecting global geopolitical flashpoints using LLM reasoning",
        )

        self.settings = get_settings()

        # Initialize services
        self.llm_service = LLMService.get_instance()  # singleton
        self.web_search = WebSearchService()
        self.flashpoint_service = FlashpointDetectionService()
        # self.token_tracker = get_token_tracker(
        #     provider="mistral", model="mistral-small-2407"
        # )
        self.token_tracker = get_token_tracker()  # for now using default token tracker
        self.country_normalizer = CountryNormalizer()
        # Get entity tracker
        self.entity_tracker = self.flashpoint_service.get_entity_tracker()
        self.query_cache = {}  # key = news_filter +":" +query, value = context, urls
        self.query_urls = set()  # urls that have been searched

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute flashpoint detection workflow.

        Args:
            input_data: Input configuration and context
                - max_iterations: Maximum search-reason cycles (default: 5)
                - target_flashpoints: Target number of flashpoints (default: 10)
                - max_context_length: Max tokens for context (default: 15000)
                - context: Optional existing context

        Returns:
            AgentResult: Standardized result containing flashpoints and statistics
        """
        try:
            self.logger.info("Starting flashpoint detection", input_data=input_data)

            # Extract configuration
            config = self._extract_config(input_data)

            # Execute flashpoint detection
            result = self._execute_flashpoint_detection(config)

            self.logger.info(
                "Flashpoint detection completed successfully",
                flashpoints_count=len(result.get("flashpoints", [])),
                iterations=result.get("iterations", 0),
            )

            return AgentResult(
                success=True,
                data=result,
                error=None,
                metadata={
                    "flashpoints_count": len(result.get("flashpoints", [])),
                    "iterations": result.get("iterations", 0),
                    "search_runs": result.get("search_runs", 0),
                    "llm_runs": result.get("llm_runs", 0),
                },
            )

        except Exception as e:
            # Handle errors
            error_msg = f"Flashpoint detection failed: {str(e)}"
            self.logger.error("Flashpoint detection error", error=str(e), exc_info=True)

            return AgentResult(
                success=False,
                data={},
                error=error_msg,
                metadata={"exception_type": type(e).__name__},
            )

    def _extract_config(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate configuration from input data."""
        return {
            "max_iterations": input_data.get("max_iterations", 5),
            "target_flashpoints": input_data.get("target_flashpoints", 10),
            "max_context_length": input_data.get("max_context_length", 15000),
            "context": input_data.get("context", ""),
            "existing_flashpoints": input_data.get("existing_flashpoints", []),
        }

    def _execute_flashpoint_detection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the main flashpoint detection workflow.

        Args:
            config: Configuration parameters

        Returns:
            Dict containing flashpoints and statistics
        """
        accumulated_flashpoints = FlashpointDataset()
        iterations = 0

        while (
            iterations < config["max_iterations"]
            and len(accumulated_flashpoints) < config["target_flashpoints"]
        ):
            iterations += 1

            self.logger.info(
                f"Starting iteration {iterations}",
                current_flashpoints=len(accumulated_flashpoints),
                target=config["target_flashpoints"],
            )

            try:
                context, urls = self._search_with_cache()
            except Exception as e:
                self.logger.error(
                    f"Search with cache failed in iteration {iterations}: {e}"
                )
                break

            if not context:
                self.logger.warning("Search exhausted: No context returned.")
                break

            try:
                new_flashpoints: FlashpointDataset = self._generate_flashpoints(context)
            except Exception as e:
                self.logger.error(
                    f"LLM generation failed in iteration {iterations}: {e}"
                )
                continue

            if not new_flashpoints:
                self.logger.warning(
                    f"No flashpoints generated in iteration {iterations}"
                )
                continue

            try:
                accumulated_flashpoints = self._process_flashpoints(
                    new_flashpoints, accumulated_flashpoints
                )
            except Exception as e:
                self.logger.error(
                    f"Flashpoint processing failed in iteration {iterations}: {e}"
                )
                continue

            self.logger.info(
                f"Iteration {iterations} completed",
                new_flashpoints=len(new_flashpoints),
                total_flashpoints=len(accumulated_flashpoints),
            )

        return {
            "flashpoints": [fp.model_dump() for fp in accumulated_flashpoints],
            "iterations": iterations,
            "search_runs": self.entity_tracker.search_run,
            "llm_runs": self.entity_tracker.llm_run,
            "token_usage": self.token_tracker.get_summary(),
            "entity_stats": self.entity_tracker.get_stats(),
            "geographic_distribution": self.flashpoint_service.get_geographic_distribution(
                accumulated_flashpoints
            ),
        }

    def _search_with_cache(self) -> Tuple[str, List[str]]:
        page = 1
        news_filter = True
        urls = []
        context = None
        all_exhausted = False
        overlap_threshold = 0.5
        max_pages = 3
        max_iterations = 6
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            while page <= max_pages:
                query = self.get_query()
                query_key = f"{page}:{news_filter}:{query}"

                if query_key in self.query_cache:
                    context, new_urls = self.query_cache[query_key]
                else:
                    context, new_urls = self._fetch_context(
                        page=page, news_filter=news_filter
                    )
                    self.query_cache[query_key] = (context, new_urls)

                if not context or not new_urls:
                    if news_filter:
                        self.logger.info(
                            "No results with filter. Switching to unfiltered search."
                        )
                        news_filter = False
                        page = 1
                        continue  # Restart outer loop with unfiltered
                    else:
                        self.logger.warning(
                            f"No results at page {page} (news_filter={news_filter})."
                        )
                        all_exhausted = True
                        break

                # Check for overlapping URLs
                overlap = len(set(self.query_urls) & set(new_urls)) / max(
                    len(new_urls), 1
                )
                if overlap > overlap_threshold:
                    self.logger.debug(
                        f"High overlap ({overlap:.2f}). Skipping page {page}."
                    )
                    page += 1
                    continue

                urls = new_urls
                self.query_urls.update(new_urls)
                break  # Exit inner loop if successful

            # Final exit condition
            if urls and context:
                break

            if all_exhausted or not news_filter or page > max_pages:
                self.logger.warning("Exiting: No results found.")
                break

        return context or "", urls or []

    def get_query(self):
        exclude_terms = self.entity_tracker.get_exclude_query()
        query = self.settings.hotspot_query + " " + exclude_terms
        return query

    def _fetch_context(
        self, page: int = 1, news_filter: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Fetch news context for flashpoint detection.

        Returns:
            str: Aggregated news context
        """
        self.entity_tracker.search_run += 1

        # Build search query with exclusions
        query = self.get_query()

        self.logger.info(
            "[SearchAgent] Fetching news context...",
            search_run=self.entity_tracker.search_run,
            query=query,
        )

        try:
            context, urls = self.web_search.gather_context(
                query, page=page, news_filter=news_filter
            )
            return context, urls
        except Exception as e:
            self.logger.error("Context fetching failed", error=str(e))
            return ""

    def _generate_flashpoints(self, context: str) -> FlashpointDataset:
        """
        Generate flashpoints using LLM reasoning.

        Args:
            context: News context to analyze

        Returns:
            FlashpointDataset of generated flashpoints
        """
        self.entity_tracker.llm_run += 1

        self.logger.info(
            "[LLMAgent] Generating flashpoints...",
            llm_run=self.entity_tracker.llm_run,
            context_length=len(context),
        )

        try:

            full_prompt = self.SYSTEM_PROMPT + self.USER_PROMPT + context

            # Count total tokens
            context_token_count = self.token_tracker.count_tokens(full_prompt)
            # het llm inputtoke
            llm_input_token = self.llm_service.max_tokens

            if context_token_count > llm_input_token:
                # summarize context
                pass

            self.logger.info(
                "Context token count", context_token_count=context_token_count
            )
            # if context token count is greater than 15000, truncate context

            # Generate response using LLM service
            response = self.llm_service.generate_text(
                user_prompt=self.USER_PROMPT + f"\n\nContext:\n{context[:15000]}",
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.0,
            )

            # Validate JSON response
            validated_flashpoints: FlashpointDataset = self._validate_json_response(
                response
            )

            if validated_flashpoints:
                self.logger.info(
                    "Flashpoints generated successfully",
                    flashpoints_count=len(validated_flashpoints),
                )
                return validated_flashpoints
            else:
                self.logger.warning(
                    "Invalid JSON response from  LLM", response_preview=response[:200]
                )
                return FlashpointDataset()

        except Exception as e:
            self.logger.error("Flashpoint generation failed", error=str(e))
            return None

    def _validate_json_response(self, response: str) -> FlashpointDataset:
        """
        Validate and parse JSON response from LLM.

        Args:
            response: Raw LLM response

        Returns:
            FlashpointDataset of validated flashpoints or None if invalid
        """
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                # Clean response (remove ```json ... ``` wrappers)
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]

                # Parse JSON
                data = safe_json_loads(cleaned_response.strip())

                # Validate with Pydantic model
                flashpoint_list = FlashpointDataset.model_validate(data)
                return flashpoint_list

            except (json.JSONDecodeError, ValidationError) as e:
                self.logger.warning(
                    f"[Attempt {attempt}/{max_attempts}] JSON validation failed",
                    error=str(e),
                    response_preview=response[:200],
                )
                if attempt == max_attempts:
                    return None  # Final failure

    def _process_flashpoints(
        self,
        new_flashpoints: FlashpointDataset,
        accumulated_flashpoints: FlashpointDataset,
    ) -> FlashpointDataset:
        """
        Process and deduplicate flashpoints.

        Args:
            new_flashpoints: Newly generated flashpoints
            existing_flashpoints: Previously accumulated flashpoints

        Returns:
            List of processed flashpoints
        """
        processed = FlashpointDataset()

        existing_flashpoints = deepcopy(accumulated_flashpoints)

        for flashpoint in new_flashpoints:
            overlap_found = False

            # Check for overlap with existing flashpoints
            for existing in existing_flashpoints:
                if set(flashpoint.entities) & set(existing.entities):
                    # Merge overlapping flashpoints
                    existing.title += f" / {flashpoint.title}"
                    existing.description += f" {flashpoint.description}"
                    existing.entities = list(
                        set(existing.entities + flashpoint.entities)
                    )

                    # Update entity tracker
                    # check if flashpoint.entities is a country
                    geo_entities = self.get_geo_entities(flashpoint.entities)
                    self.entity_tracker.update_seen_entities(geo_entities)

                    overlap_found = True
                    break

            # Add new flashpoint if no overlap and valid
            if not overlap_found and self.flashpoint_service.validate_flashpoint(
                flashpoint
            ):
                geo_entities = self.get_geo_entities(flashpoint.entities)
                self.entity_tracker.add(flashpoint.entities, geo_entities)
                existing_flashpoints.append(flashpoint)

            # remove all flashpoints with no geo entities
            existing_flashpoints = FlashpointDataset(
                [
                    fp
                    for fp in existing_flashpoints
                    if self.get_geo_entities(fp.entities)
                ]
            )

        processed = existing_flashpoints

        self.logger.info(
            "Flashpoint processing completed",
            new_flashpoints=len(new_flashpoints),
            processed_flashpoints=len(processed),
            duplicates_filtered=len(new_flashpoints) - len(processed),
        )

        return processed

    def get_geo_entities(self, entities: List[str]):
        geo_entities = []
        for entity in entities:
            if self.country_normalizer.is_country(entity):
                geo_entities.append(entity)
        return list(set(geo_entities))

    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive agent statistics.

        Returns:
            Dict containing agent statistics
        """
        return {
            "agent_name": self.name,
            "state": self.state.model_dump() if self.state else None,
            "entity_tracker": self.entity_tracker.get_stats(),
            "token_usage": self.token_tracker.get_summary(),
            "service_stats": self.flashpoint_service.get_service_stats(),
        }

    def reset(self):
        """Reset agent state for new session."""
        self.entity_tracker.reset()
        self.flashpoint_service.reset()
        self._state = None

        self.logger.info("FlashpointLLMAgent reset")
