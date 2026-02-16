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
Flashpoint detection service for MASX-HOTSPOTS Agentic AI System.

Provides entity tracking, country validation, and flashpoint deduplication logic
for the flashpoint detection workflow. Manages entity combinations and ensures
geographic relevance of detected flashpoints.

Usage: from app.services.flashpoint_detection import FlashpointDetectionService
    service = FlashpointDetectionService()
    tracker = service.get_entity_tracker()
"""

import pycountry
from typing import List, Dict, Any, Set, Optional
from pydantic import BaseModel
import country_converter as coco

from ..config.logging_config import get_logger
from ..core.country_normalizer import CountryNormalizer


class Flashpoint(BaseModel):
    """Data model for a flashpoint with title, description, and entities."""

    title: str
    description: str
    entities: List[str]


class EntityTracker:
    """
    Tracks entities across flashpoint detection iterations to avoid duplicates.

    Features:
    - Entity combination tracking
    - Duplicate detection and prevention
    - Search query exclusion generation
    - Entity statistics and analytics
    """

    def __init__(self):
        """Initialize entity tracker."""
        self.seen_entities: Set[str] = set()
        self.entity_combinations: Set[tuple] = set()
        self.search_run = 0
        self.llm_run = 0
        self.logger = get_logger(__name__)

    def is_new_combo(self, entities: List[str]) -> bool:
        """
        Check if entity combination is new.

        Args:
            entities: List of entity names

        Returns:
            bool: True if combination is new, False if already seen
        """
        # Normalize entities for comparison
        normalized = tuple(sorted([e.lower().strip() for e in entities]))
        return normalized not in self.entity_combinations

    def add(self, entities: List[str], geo_entities: List[str] = None):
        """
        Add entities to the tracker.

        Args:
            entities: List of entity names to track
        """
        if geo_entities:
            for entity in geo_entities:
                self.seen_entities.add(entity.lower().strip())
        else:
            for entity in entities:
                self.seen_entities.add(entity.lower().strip())

        # Add combination
        normalized = tuple(sorted([e.lower().strip() for e in entities]))
        self.entity_combinations.add(normalized)

        self.logger.debug(
            "Entities added to tracker",
            entities=entities,
            total_entities=len(self.seen_entities),
            total_combinations=len(self.entity_combinations),
        )

    def update_seen_entities(self, entities: List[str]):
        """
        Update seen entities without creating new combinations.

        Args:
            entities: List of entity names to mark as seen
        """
        for entity in entities:
            if entity.lower().strip() not in self.seen_entities:
                self.seen_entities.add(entity.lower().strip())

    def get_exclude_query(self) -> str:
        """
        Generate exclusion query for search to avoid duplicate content.

        Returns:
            str: Space-separated exclusion terms for search query
        """
        exclude_terms = [f'-"{entity}"' for entity in self.seen_entities]
        return " ".join(exclude_terms)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get entity tracking statistics.

        Returns:
            Dict containing tracking statistics
        """
        return {
            "total_entities": len(self.seen_entities),
            "total_combinations": len(self.entity_combinations),
            "search_runs": self.search_run,
            "llm_runs": self.llm_run,
            "entities": list(self.seen_entities),
        }

    def reset(self):
        """Reset tracker state for new session."""
        self.seen_entities.clear()
        self.entity_combinations.clear()
        self.search_run = 0
        self.llm_run = 0

        self.logger.info("Entity tracker reset")


class FlashpointDetectionService:
    """
    Service for flashpoint detection operations and entity management.

    Features:
    - Entity tracking and deduplication
    - Country validation
    - Flashpoint filtering and validation
    - Geographic relevance checking
    """

    def __init__(self):
        """Initialize flashpoint detection service."""
        self.logger = get_logger(__name__)
        self.entity_tracker = EntityTracker()
        self.country_normalizer = CountryNormalizer()

    def get_entity_tracker(self) -> EntityTracker:
        """
        Get the entity tracker instance.

        Returns:
            EntityTracker: Current entity tracker instance
        """
        return self.entity_tracker

    def validate_flashpoint(self, flashpoint: Flashpoint) -> bool:
        """
        Validate a flashpoint for inclusion.

        Args:
            flashpoint: Flashpoint to validate

        Returns:
            bool: True if flashpoint is valid
        """
        # Check if flashpoint has required fields
        if (
            not flashpoint.title
            or not flashpoint.description
            or not flashpoint.entities
        ):
            return False

        # Check if at least one entity is a recognized country
        has_country = any(
            self.country_normalizer.is_country(entity) for entity in flashpoint.entities
        )
        if not has_country:
            self.logger.debug(
                "Flashpoint rejected - no recognized country",
                title=flashpoint.title,
                entities=flashpoint.entities,
            )
            return False

        # Check if entity combination is new
        if not self.entity_tracker.is_new_combo(flashpoint.entities):
            self.logger.debug(
                "Flashpoint rejected - duplicate entity combination",
                title=flashpoint.title,
                entities=flashpoint.entities,
            )
            return False

        return True

    def deduplicate_flashpoints(
        self, flashpoints: List[Flashpoint]
    ) -> List[Flashpoint]:
        """
        Remove duplicate flashpoints based on entity overlap.

        Args:
            flashpoints: List of flashpoints to deduplicate

        Returns:
            List of deduplicated flashpoints
        """
        if not flashpoints:
            return []

        deduplicated = []

        for flashpoint in flashpoints:
            overlap_found = False

            # Check for overlap with existing flashpoints
            for existing in deduplicated:
                if set(flashpoint.entities) & set(existing.entities):
                    # Merge overlapping flashpoints
                    existing.title += f" / {flashpoint.title}"
                    existing.description += f" {flashpoint.description}"
                    existing.entities = list(
                        set(existing.entities + flashpoint.entities)
                    )

                    # Update entity tracker
                    self.entity_tracker.update_seen_entities(flashpoint.entities)
                    overlap_found = True
                    break

            # Add new flashpoint if no overlap and valid
            if not overlap_found and self.validate_flashpoint(flashpoint):
                self.entity_tracker.add(flashpoint.entities)
                deduplicated.append(flashpoint)

        self.logger.info(
            "Flashpoint deduplication completed",
            original_count=len(flashpoints),
            deduplicated_count=len(deduplicated),
        )

        return deduplicated

    def filter_flashpoints(
        self,
        flashpoints: List[Flashpoint],
        min_entities: int = 1,
        max_entities: int = 10,
    ) -> List[Flashpoint]:
        """
        Filter flashpoints based on criteria.

        Args:
            flashpoints: List of flashpoints to filter
            min_entities: Minimum number of entities required
            max_entities: Maximum number of entities allowed

        Returns:
            List of filtered flashpoints
        """
        filtered = []

        for flashpoint in flashpoints:
            # Check entity count
            if (
                len(flashpoint.entities) < min_entities
                or len(flashpoint.entities) > max_entities
            ):
                continue

            # Check if valid
            if self.validate_flashpoint(flashpoint):
                filtered.append(flashpoint)

        self.logger.info(
            "Flashpoint filtering completed",
            original_count=len(flashpoints),
            filtered_count=len(filtered),
        )

        return filtered

    def get_geographic_distribution(
        self, flashpoints: List[Flashpoint]
    ) -> Dict[str, int]:
        """
        Get geographic distribution of flashpoints by country.

        Args:
            flashpoints: List of flashpoints to analyze

        Returns:
            Dict mapping country names to flashpoint counts
        """
        distribution = {}

        for flashpoint in flashpoints:
            for entity in flashpoint.entities:
                if self.country_normalizer.is_country(entity):
                    country = entity.lower()
                    distribution[country] = distribution.get(country, 0) + 1

        return distribution

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive service statistics.

        Returns:
            Dict containing service statistics
        """
        return {
            "entity_tracker": self.entity_tracker.get_stats(),
            "service_name": "FlashpointDetectionService",
        }

    def reset(self):
        """Reset service state for new session."""
        self.entity_tracker.reset()
        self.logger.info("Flashpoint detection service reset")


# Factory function for easy service creation
def create_flashpoint_detection_service() -> FlashpointDetectionService:
    """
    Create a flashpoint detection service instance.

    Returns:
        FlashpointDetectionService: Configured service instance
    """
    return FlashpointDetectionService()
