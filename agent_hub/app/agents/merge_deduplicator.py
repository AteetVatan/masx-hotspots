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
Merge Deduplicator Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Merging articles and events from different sources
- Detecting and removing duplicates
- Standardizing data formats
- Quality control of merged data
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseAgent, AgentResult
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger


class MergeDeduplicator(BaseAgent):
    """
    Merge Deduplicator Agent for combining and cleaning data sources.

    Responsibilities:
    - Merge articles and events from multiple sources
    - Detect and remove duplicate content
    - Standardize data formats
    - Ensure data quality
    """

    def __init__(self):
        """Initialize the Merge Deduplicator agent."""
        super().__init__("MergeDeduplicator")
        self.logger = get_agent_logger("MergeDeduplicator")

    async def merge_and_deduplicate(
        self, articles: List[Dict[str, Any]], events: List[Dict[str, Any]]
    ) -> AgentResult:
        """
        Merge articles and events, removing duplicates.

        Args:
            articles: List of news articles
            events: List of GDELT events

        Returns:
            AgentResult: Contains merged and deduplicated data
        """
        try:
            self.logger.info(
                "Merging and deduplicating data",
                article_count=len(articles),
                event_count=len(events),
            )

            # Convert all items to unified format
            unified_items = []

            # Add articles
            for article in articles:
                unified_items.append(
                    {
                        "type": "article",
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("source", ""),
                        "published_date": article.get("published_date", ""),
                        "content": article.get("snippet", ""),
                        "original_data": article,
                    }
                )

            # Add events
            for event in events:
                unified_items.append(
                    {
                        "type": "event",
                        "title": event.get("title", ""),
                        "url": event.get("url", ""),
                        "source": event.get("source", ""),
                        "published_date": event.get("published_date", ""),
                        "content": event.get("title", ""),  # Use title as content
                        "original_data": event,
                    }
                )

            # Deduplicate items
            deduplicated_items = await self._deduplicate_items(unified_items)

            # Separate back into articles and events
            merged_articles = []
            merged_events = []

            for item in deduplicated_items:
                if item["type"] == "article":
                    merged_articles.append(item["original_data"])
                else:
                    merged_events.append(item["original_data"])

            result = {
                "merged_articles": merged_articles,
                "merged_events": merged_events,
                "total_merged": len(deduplicated_items),
                "duplicates_removed": len(unified_items) - len(deduplicated_items),
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                "Merge and deduplication completed",
                total_merged=len(deduplicated_items),
                duplicates_removed=result["duplicates_removed"],
            )

            return AgentResult(
                success=True,
                data=result,
                metadata={
                    "agent": self.name,
                    "timestamp": datetime.utcnow(),
                    "input_articles": len(articles),
                    "input_events": len(events),
                },
            )

        except Exception as e:
            self.logger.error(f"Merge and deduplication failed: {e}")
            raise AgentException(f"Merge and deduplication failed: {str(e)}")

    async def _deduplicate_items(
        self, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate items based on similarity."""
        if not items:
            return []

        deduplicated = [items[0]]  # Keep first item

        for item in items[1:]:
            is_duplicate = False

            for existing_item in deduplicated:
                if self._is_duplicate(item, existing_item):
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(item)

        return deduplicated

    def _is_duplicate(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Check if two items are duplicates."""
        # Check URL similarity
        url1 = item1.get("url", "").lower()
        url2 = item2.get("url", "").lower()

        if url1 and url2 and url1 == url2:
            return True

        # Check title similarity
        title1 = item1.get("title", "").lower()
        title2 = item2.get("title", "").lower()

        if title1 and title2:
            # Simple similarity check (in production, use more sophisticated methods)
            words1 = set(title1.split())
            words2 = set(title2.split())

            if len(words1) > 0 and len(words2) > 0:
                similarity = len(words1.intersection(words2)) / len(
                    words1.union(words2)
                )
                if similarity > 0.8:  # 80% similarity threshold
                    return True

        return False

    async def standardize_format(self, items: List[Dict[str, Any]]) -> AgentResult:
        """
        Standardize the format of merged items.

        Args:
            items: List of items to standardize

        Returns:
            AgentResult: Contains standardized items
        """
        try:
            self.logger.info(f"Standardizing format for {len(items)} items")

            standardized_items = []

            for item in items:
                standardized_item = {
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", ""),
                    "published_date": item.get("published_date", ""),
                    "content": item.get("content", ""),
                    "type": item.get("type", "unknown"),
                    "metadata": {
                        "standardized_at": datetime.utcnow().isoformat(),
                        "original_keys": list(item.keys()),
                    },
                }
                standardized_items.append(standardized_item)

            result = {
                "standardized_items": standardized_items,
                "total_count": len(standardized_items),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Format standardization failed: {e}")
            raise AgentException(f"Format standardization failed: {str(e)}")

    async def validate_merged_data(self, merged_data: Dict[str, Any]) -> AgentResult:
        """
        Validate the quality of merged data.

        Args:
            merged_data: Merged data to validate

        Returns:
            AgentResult: Contains validation results
        """
        try:
            self.logger.info("Validating merged data")

            articles = merged_data.get("merged_articles", [])
            events = merged_data.get("merged_events", [])

            validation_results = {
                "articles": {
                    "total": len(articles),
                    "valid": 0,
                    "invalid": 0,
                    "issues": [],
                },
                "events": {
                    "total": len(events),
                    "valid": 0,
                    "invalid": 0,
                    "issues": [],
                },
            }

            # Validate articles
            for article in articles:
                if self._is_valid_item(article):
                    validation_results["articles"]["valid"] += 1
                else:
                    validation_results["articles"]["invalid"] += 1
                    validation_results["articles"]["issues"].append(
                        f"Invalid article: {article.get('title', 'No title')}"
                    )

            # Validate events
            for event in events:
                if self._is_valid_item(event):
                    validation_results["events"]["valid"] += 1
                else:
                    validation_results["events"]["invalid"] += 1
                    validation_results["events"]["issues"].append(
                        f"Invalid event: {event.get('title', 'No title')}"
                    )

            result = {
                "validation_results": validation_results,
                "overall_quality": self._calculate_quality_score(validation_results),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Data validation failed: {e}")
            raise AgentException(f"Data validation failed: {str(e)}")

    def _is_valid_item(self, item: Dict[str, Any]) -> bool:
        """Check if an item is valid."""
        required_fields = ["title", "url"]

        for field in required_fields:
            if not item.get(field):
                return False

        return True

    def _calculate_quality_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall quality score."""
        total_items = 0
        valid_items = 0

        for category in ["articles", "events"]:
            total_items += validation_results[category]["total"]
            valid_items += validation_results[category]["valid"]

        if total_items == 0:
            return 0.0

        return valid_items / total_items
