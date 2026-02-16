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
Entity Extractor Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Extracting entities (people, organizations, locations, etc.) from text
- Structuring extracted entities for downstream analysis
- Handling errors in entity extraction
"""

from typing import Dict, List, Any, Tuple
from datetime import datetime

from .base import BaseAgent, AgentResult
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger
from ..core.singleton.spacy_singleton import SpacySingleton
from ..core.enums.spacy_model_name import SpaCyModelName
from ..core.querystate import QueryState
from ..core.country_normalizer import CountryNormalizer
from ..services import LanguageService
from ..constants import GOOGLE_TRANSLATE_VARIANTS


class LanguageAgent(BaseAgent):
    """
    Entity Extractor Agent for extracting entities from text content.

    Responsibilities:
    - Extract entities (people, organizations, locations, etc.)
    - Structure extracted entities for downstream analysis
    - Handle errors in entity extraction
    """

    def __init__(self):
        """Initialize the Entity Extractor agent."""
        super().__init__("EntityExtractor")
        self.logger = get_agent_logger("EntityExtractor")
        # self.nlp_eng = SpacySingleton.get(SpaCyModelName.EN_CORE_WEB_SM)
        self.country_normalizer = CountryNormalizer()

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Synchronous entrypoint to extract entities (required by BaseAgent).

        Args:
            input_data: Dictionary with a list under 'items' key

        Returns:
            AgentResult with extracted entities
        """
        try:
            if not self.validate_input(input_data):
                raise AgentException("Invalid input: missing queries")

            queries: List[QueryState] = input_data.get("queries", [])
            if not isinstance(queries, list):
                raise AgentException(
                    "Missing or invalid 'queries' list for entity extraction"
                )

            self.logger.info(f"Extracting entities from {len(queries)} queries")

            for query in queries:
                entities = query.entities
                # get all languages associated with the entities
                languages, entity_languages = self._get_languages_from_entities(
                    entities
                )
                query.language = languages
                query.entity_languages = entity_languages

            self.logger.info("Language extraction completed", total_items=len(queries))

            result = {"queries": queries}

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return AgentResult(
                success=False,
                error=f"Entity extraction failed: {str(e)}",
                metadata={"agent": self.name},
            )

    def _get_languages_from_entities(
        self, entities: List[str]
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """Get all languages associated with the entities."""
        try:
            language_list = []
            entity_languages = {}
            for entity in entities:
                # get the language of the entity
                country = self.country_normalizer.normalize(entity)
                # get the alpha2 code of the country
                if not country:
                    country = self.country_normalizer.get_coco_country_name(
                        entity, return_all=True
                    )

                if country:
                    alpha2 = self.country_normalizer.country_name_to_alpha2(country)
                    if alpha2:
                        # get the language of the country
                        language = LanguageService.get_languages_for_country_code(
                            alpha2
                        )
                        language_list.extend(language)

                        if alpha2 not in entity_languages:
                            entity_languages[alpha2] = []
                        entity_languages[alpha2].extend(language)

                        continue

                # get the language of the entity
                language = LanguageService.get_languages_for_entity(entity)
                language_list.extend(language)
                if entity not in entity_languages:
                    entity_languages[entity] = []
                entity_languages[entity].extend(language)

        except Exception as e:
            self.logger.error(f"Error getting languages from entities: {e}")
            return []

        # every language_list must have english "en" the default
        if "en" not in language_list:
            language_list.append("en")

        # remove duplicates use dict key to remove duplicates
        language_list = list(dict.fromkeys(language_list))

        # replace if keys in GOOGLE_TRANSLATE_VARIANTS with values
        # append GOOGLE_TRANSLATE_VARIANTS[lang] to language_list if lang in GOOGLE_TRANSLATE_VARIANTS
        google_variants = []
        for lang in language_list:
            if lang in GOOGLE_TRANSLATE_VARIANTS:
                google_variants.extend(GOOGLE_TRANSLATE_VARIANTS[lang])
        language_list.extend(google_variants)
        language_list = list(dict.fromkeys(language_list))

        # sort the languages
        language_list.sort()
        # return the languages
        return language_list, entity_languages

    def _extract_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Stub entity extraction from text (replace with real NER in production)."""
        # In production, use spaCy or another NER library
        # Here, return a stub list
        if not text:
            return []

        # Simple stub: extract capitalized words as entities
        words = text.split()
        entities = []
        for word in words:
            if word.istitle() and len(word) > 2:
                entities.append({"text": word, "type": "UNKNOWN"})
        return entities

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for language agent.
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
