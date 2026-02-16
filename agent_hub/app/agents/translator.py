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
Translator Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Translating content between languages
- Managing translation quality
- Caching translations
- Handling translation errors
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseAgent, AgentResult
from ..services.translation import TranslationService
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..core.querystate import QueryState, QueryTranslated
from ..config.logging_config import get_agent_logger


class Translator(BaseAgent):
    """
    Translator Agent for translating content between languages.

    Responsibilities:
    - Translate content between languages
    - Manage translation quality
    - Cache translations for performance
    - Handle translation errors
    """

    def __init__(self):
        """Initialize the Translator agent."""
        super().__init__("Translator")
        self.translation_service = TranslationService()
        self.logger = get_agent_logger("Translator")

    def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute method required by BaseAgent. Routes translation request.

        Args:
            input_data: Dictionary with 'items' (list of dicts), 'target_language'

        Returns:
            AgentResult: Translation result
        """
        try:
            if not self.validate_input(input_data):
                raise AgentException("Invalid input: missing queries")

            input_queries = input_data.get("queries", [])
            queries: List[QueryState] = [
                QueryState.model_validate(q) for q in input_queries
            ]

            translated_items = []
            failed_translations = []
            for query in queries:
                for lang in query.language:
                    try:
                        if lang == "en" or lang == "uk":
                            translated_text = query.query
                        else:
                            hf_model_used, translated_text = (
                                self.translation_service.translate(
                                    target_lang=lang, source_lang="en", text=query.query
                                )
                            )
                            self.logger.info(
                                f"Translated query: {query.query} to {lang} with text: {translated_text}"
                            )
                            self.logger.info(
                                f"For translation: {lang} used {self.translation_service.nllb_translator.model_name if hf_model_used else 'google'}"
                            )
                            translated_items.append(translated_text)
                            query_translated = QueryTranslated(
                                language=lang, query_translated=translated_text
                            )
                            query.list_query_translated.append(query_translated)

                    except Exception as e:
                        self.logger.warning(f"Translation failed for item: {e}")
                        failed_item = {
                            "query": query.model_dump(),
                            "target_lang": lang,
                            "translation_status": "failed",
                            "error": str(e),
                        }
                        failed_translations.append(failed_item)

            result = {
                "queries": queries,
                "failed_translations": failed_translations,
                "translation_stats": {
                    "total": len(queries),
                    "successful": len(translated_items),
                    "failed": len(failed_translations),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            raise AgentException(f"Translation failed: {str(e)}")

    def batch_translate(
        self,
        texts: List[str],
        source_language: str = "auto",
        target_language: str = "en",
    ) -> AgentResult:
        """
        Translate a batch of texts.

        Args:
            texts: List of texts to translate
            source_language: Source language
            target_language: Target language

        Returns:
            AgentResult: Contains translated texts
        """
        try:
            self.logger.info(
                f"Batch translating {len(texts)} texts",
                source_language=source_language,
                target_language=target_language,
            )

            translated_texts = []

            for text in texts:
                try:
                    translated_text = self.translation_service.translate(
                        text=text,
                        source_lang=source_language,
                        target_lang=target_language,
                    )
                    translated_texts.append(translated_text)
                except Exception as e:
                    self.logger.warning(f"Failed to translate text: {e}")
                    translated_texts.append(text)  # Keep original on failure

            result = {
                "translated_texts": translated_texts,
                "original_texts": texts,
                "source_language": source_language,
                "target_language": target_language,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Batch translation failed: {e}")
            raise AgentException(f"Batch translation failed: {str(e)}")

    def validate_translation(
        self,
        original_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
    ) -> AgentResult:
        """
        Validate translation quality.

        Args:
            original_text: Original text
            translated_text: Translated text
            source_language: Source language
            target_language: Target language

        Returns:
            AgentResult: Contains validation results
        """
        try:
            self.logger.info("Validating translation quality")

            # Simple validation checks
            validation_results = {
                "length_ratio": len(translated_text) / max(len(original_text), 1),
                "has_content": bool(translated_text.strip()),
                "language_appropriate": True,  # Placeholder
                "quality_score": 0.9,  # Placeholder
            }

            # Determine if translation is acceptable
            is_acceptable = (
                validation_results["length_ratio"] > 0.1
                and validation_results["has_content"]
                and validation_results["quality_score"] > 0.7
            )

            result = {
                "validation_results": validation_results,
                "is_acceptable": is_acceptable,
                "original_text": original_text,
                "translated_text": translated_text,
                "source_language": source_language,
                "target_language": target_language,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Translation validation failed: {e}")
            raise AgentException(f"Translation validation failed: {str(e)}")

    def get_supported_languages(self) -> AgentResult:
        """
        Get list of supported languages.

        Returns:
            AgentResult: Contains supported languages
        """
        try:
            self.logger.info("Getting supported languages")

            # Common supported languages
            supported_languages = [
                {"code": "en", "name": "English"},
                {"code": "es", "name": "Spanish"},
                {"code": "fr", "name": "French"},
                {"code": "de", "name": "German"},
                {"code": "zh", "name": "Chinese"},
                {"code": "ja", "name": "Japanese"},
                {"code": "ko", "name": "Korean"},
                {"code": "ar", "name": "Arabic"},
                {"code": "ru", "name": "Russian"},
                {"code": "pt", "name": "Portuguese"},
                {"code": "it", "name": "Italian"},
                {"code": "nl", "name": "Dutch"},
            ]

            result = {
                "supported_languages": supported_languages,
                "total_count": len(supported_languages),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Failed to get supported languages: {e}")
            raise AgentException(f"Failed to get supported languages: {str(e)}")

    def detect_language(self, text: str) -> AgentResult:
        """
        Detect the language of text.

        Args:
            text: Text to analyze

        Returns:
            AgentResult: Contains language detection results
        """
        try:
            self.logger.info("Detecting language of text")

            # Simple language detection (in production, use proper service)
            detected_language = "en"  # Placeholder

            result = {
                "detected_language": detected_language,
                "confidence": 0.9,  # Placeholder
                "text_length": len(text),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            raise AgentException(f"Language detection failed: {str(e)}")

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for translator agent.
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
