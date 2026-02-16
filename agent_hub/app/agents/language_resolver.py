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
Language Resolver Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Detecting language of content
- Resolving language codes
- Routing content for translation
- Managing multilingual processing
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseAgent, AgentResult
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger


class LanguageResolver(BaseAgent):
    """
    Language Resolver Agent for detecting and managing content languages.

    Responsibilities:
    - Detect language of content
    - Resolve language codes
    - Route content for translation
    - Manage multilingual processing
    """

    def __init__(self):
        """Initialize the Language Resolver agent."""
        super().__init__("LanguageResolver")
        self.logger = get_agent_logger("LanguageResolver")

    async def detect_languages(self, items: List[Dict[str, Any]]) -> AgentResult:
        """
        Detect languages for a list of content items.

        Args:
            items: List of content items to analyze

        Returns:
            AgentResult: Contains language detection results
        """
        try:
            self.logger.info(f"Detecting languages for {len(items)} items")

            results = []

            for item in items:
                content = item.get("title", "") + " " + item.get("content", "")
                detected_lang = self._detect_language(content)

                results.append(
                    {
                        "item_id": item.get("id", ""),
                        "detected_language": detected_lang,
                        "confidence": 0.9,  # Placeholder confidence
                        "needs_translation": detected_lang != "en",
                        "original_item": item,
                    }
                )

            result = {
                "language_results": results,
                "total_items": len(items),
                "languages_detected": list(
                    set(r["detected_language"] for r in results)
                ),
                "items_needing_translation": len(
                    [r for r in results if r["needs_translation"]]
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                "Language detection completed",
                total_items=len(items),
                languages_detected=result["languages_detected"],
            )

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            raise AgentException(f"Language detection failed: {str(e)}")

    def _detect_language(self, text: str) -> str:
        """Detect language of text content."""
        # Simple language detection (in production, use proper library)
        if not text:
            return "unknown"

        # Basic heuristics for common languages
        text_lower = text.lower()

        # Check for common English words
        english_words = [
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
        ]
        english_count = sum(1 for word in english_words if word in text_lower)

        if english_count > 2:
            return "en"

        # Add more language detection logic here
        # For now, default to English
        return "en"

    async def resolve_language_codes(
        self, language_results: List[Dict[str, Any]]
    ) -> AgentResult:
        """
        Resolve and standardize language codes.

        Args:
            language_results: List of language detection results

        Returns:
            AgentResult: Contains resolved language codes
        """
        try:
            self.logger.info(
                f"Resolving language codes for {len(language_results)} items"
            )

            resolved_results = []

            for result in language_results:
                detected_lang = result.get("detected_language", "unknown")
                resolved_lang = self._resolve_language_code(detected_lang)

                resolved_results.append(
                    {
                        **result,
                        "resolved_language": resolved_lang,
                        "language_name": self._get_language_name(resolved_lang),
                    }
                )

            result = {
                "resolved_results": resolved_results,
                "language_mapping": self._get_language_mapping(),
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Language code resolution failed: {e}")
            raise AgentException(f"Language code resolution failed: {str(e)}")

    def _resolve_language_code(self, code: str) -> str:
        """Resolve language code to standard format."""
        # Standardize common language codes
        language_map = {
            "en": "en",
            "english": "en",
            "eng": "en",
            "es": "es",
            "spanish": "es",
            "fr": "fr",
            "french": "fr",
            "de": "de",
            "german": "de",
            "zh": "zh",
            "chinese": "zh",
            "ja": "ja",
            "japanese": "ja",
            "ko": "ko",
            "korean": "ko",
            "ar": "ar",
            "arabic": "ar",
            "ru": "ru",
            "russian": "ru",
        }

        return language_map.get(code.lower(), code.lower())

    def _get_language_name(self, code: str) -> str:
        """Get human-readable language name."""
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "ru": "Russian",
        }

        return language_names.get(code, "Unknown")

    def _get_language_mapping(self) -> Dict[str, str]:
        """Get mapping of detected to resolved language codes."""
        return {
            "en": "en",
            "english": "en",
            "eng": "en",
            "es": "es",
            "spanish": "es",
            "fr": "fr",
            "french": "fr",
            "de": "de",
            "german": "de",
            "zh": "zh",
            "chinese": "zh",
            "ja": "ja",
            "japanese": "ja",
            "ko": "ko",
            "korean": "ko",
            "ar": "ar",
            "arabic": "ar",
            "ru": "ru",
            "russian": "ru",
        }

    async def route_for_translation(
        self, items: List[Dict[str, Any]], target_language: str = "en"
    ) -> AgentResult:
        """
        Route items that need translation.

        Args:
            items: List of items to route
            target_language: Target language for translation

        Returns:
            AgentResult: Contains routing information
        """
        try:
            self.logger.info(
                f"Routing {len(items)} items for translation",
                target_language=target_language,
            )

            items_to_translate = []
            items_no_translation = []

            for item in items:
                current_lang = item.get("detected_language", "unknown")

                if current_lang != target_language and current_lang != "unknown":
                    items_to_translate.append(
                        {
                            **item,
                            "translation_needed": True,
                            "source_language": current_lang,
                            "target_language": target_language,
                        }
                    )
                else:
                    items_no_translation.append({**item, "translation_needed": False})

            result = {
                "items_to_translate": items_to_translate,
                "items_no_translation": items_no_translation,
                "translation_stats": {
                    "total": len(items),
                    "needs_translation": len(items_to_translate),
                    "no_translation": len(items_no_translation),
                },
                "target_language": target_language,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return AgentResult(
                success=True,
                data=result,
                metadata={
                    "agent": self.name,
                    "timestamp": datetime.utcnow(),
                    "target_language": target_language,
                },
            )

        except Exception as e:
            self.logger.error(f"Translation routing failed: {e}")
            raise AgentException(f"Translation routing failed: {str(e)}")
