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
Translation service for MASX-HOTSPOTS Agentic AI System.

Provides multilingual translation capabilities with:
- Google Translate integration
- DeepL integration
- Local translation models
- Language detection
- Caching and rate limiting
- Error handling and fallbacks

Usage:
    from app.services.translation import TranslationService

    translator = TranslationService()
    translated = await translator.translate("Hello world", target_lang="es")
    detected = await translator.detect_language("Bonjour le monde")
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import aiohttp
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

from ..core.exceptions import TranslationException, ConfigurationException
from ..core.utils import measure_execution_time
from ..config.settings import get_settings
from ..config.logging_config import get_service_logger
from ..core.singleton import NLLBTranslatorSingleton
from ..constants import ISO_TO_NLLB_MERGED


class TranslationProvider(Enum):
    """Supported translation providers."""

    GOOGLE = "google"
    DEEPL = "deepl"
    LOCAL = "local"
    NLLB = "nllb"


@dataclass
class TranslationRequest:
    """Translation request data."""

    text: str
    source_lang: Optional[str] = None
    target_lang: str = "en"
    provider: TranslationProvider = TranslationProvider.GOOGLE
    cache_key: Optional[str] = None

    def __post_init__(self):
        if self.cache_key is None:
            # Generate cache key from text and languages
            key_data = f"{self.text}:{self.source_lang}:{self.target_lang}"
            self.cache_key = hashlib.md5(key_data.encode()).hexdigest()


@dataclass
class TranslationResult:
    """Translation result data."""

    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    confidence: float = 1.0
    provider: TranslationProvider = TranslationProvider.GOOGLE
    execution_time: float = 0.0
    cached: bool = False


@dataclass
class LanguageDetectionResult:
    """Language detection result data."""

    text: str
    detected_lang: str
    confidence: float = 1.0
    execution_time: float = 0.0


class TranslationService:
    """Service for translating text using deep-translator's GoogleTranslator."""

    def __init__(self, source_lang: str = "auto", target_lang: str = "en"):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translator = GoogleTranslator(
            source=self.source_lang, target=self.target_lang
        )
        self.nllb_translator = NLLBTranslatorSingleton()
        self.logger = get_service_logger("TranslationService")

    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ) -> str:
        """
        Translate text from source_lang to target_lang using NLLB if available,
        otherwise fall back to GoogleTranslator from deep-translator.

        Args:
            text (str): The input text to translate
            source_lang (str): ISO 639-1 source language code (e.g. 'en')
            target_lang (str): ISO 639-1 target language code (e.g. 'ar')

        Returns:
            str: Translated text
        """
        src = source_lang or self.source_lang
        tgt = target_lang or self.target_lang

        try:
            hf_model_used = False
            # NLLB Path
            if src in ISO_TO_NLLB_MERGED and tgt in ISO_TO_NLLB_MERGED:
                src_nllb = ISO_TO_NLLB_MERGED[src]
                tgt_nllb = ISO_TO_NLLB_MERGED[tgt]
                hf_model_used = True
                return hf_model_used, self.nllb_translator.translate(
                    text, src_nllb, tgt_nllb
                )

            # Google Fallback
            return hf_model_used, GoogleTranslator(source=src, target=tgt).translate(
                text
            )

        except Exception as e:
            self.logger.error(f"Translation failed: {e}", exc_info=True)
            return f"[TranslationError] Could not translate text from '{src}' to '{tgt}' with {self.nllb_translator.model_name if hf_model_used else 'google'}"

    async def translate_batch(
        self,
        texts: List[str],
        target_lang: str = "en",
        source_lang: Optional[str] = None,
        provider: Optional[TranslationProvider] = None,
        max_concurrent: int = 5,
    ) -> List[TranslationResult]:
        """
        Translate multiple texts in parallel.

        Args:
            texts: List of texts to translate
            target_lang: Target language code
            source_lang: Source language code
            provider: Translation provider to use
            max_concurrent: Maximum concurrent translations

        Returns:
            List of translation results
        """
        with measure_execution_time("translate_batch"):
            try:
                semaphore = asyncio.Semaphore(max_concurrent)

                async def translate_single(text: str) -> TranslationResult:
                    async with semaphore:
                        return await self.translate(
                            text=text,
                            target_lang=target_lang,
                            source_lang=source_lang,
                            provider=provider,
                        )

                tasks = [translate_single(text) for text in texts]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Handle exceptions
                translation_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Translation {i} failed: {result}")
                        # Return original text as fallback
                        translation_results.append(
                            TranslationResult(
                                original_text=texts[i],
                                translated_text=texts[i],
                                source_lang=source_lang or "unknown",
                                target_lang=target_lang,
                                confidence=0.0,
                            )
                        )
                    else:
                        translation_results.append(result)

                self.logger.info(
                    f"Batch translation completed: {len(translation_results)} texts"
                )
                return translation_results

            except Exception as e:
                self.logger.error(f"Batch translation failed: {e}")
                raise TranslationException(f"Batch translation failed: {str(e)}")

    async def _check_rate_limit(self, provider: TranslationProvider):
        """Check and enforce rate limits for providers."""
        current_time = asyncio.get_event_loop().time()
        last_request = self._rate_limiters.get(provider, 0)

        # Rate limits (requests per second)
        rate_limits = {
            TranslationProvider.GOOGLE: 10,  # 10 requests per second
            TranslationProvider.DEEPL: 5,  # 5 requests per second
            TranslationProvider.LOCAL: 100,  # 100 requests per second
            TranslationProvider.NLLB: 10,  # 10 requests per second
        }

        min_interval = 1.0 / rate_limits.get(provider, 10)

        if current_time - last_request < min_interval:
            sleep_time = min_interval - (current_time - last_request)
            await asyncio.sleep(sleep_time)

        self._rate_limiters[provider] = current_time

    def get_supported_languages(self, provider: TranslationProvider) -> Dict[str, str]:
        """
        Get supported languages for a provider.

        Args:
            provider: Translation provider

        Returns:
            Dictionary mapping language codes to language names
        """
        # Common language mappings
        languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "nl": "Dutch",
            "pl": "Polish",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mt": "Maltese",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "ms": "Malay",
            "tl": "Filipino",
            "sw": "Swahili",
            "af": "Afrikaans",
            "is": "Icelandic",
            "ga": "Irish",
            "cy": "Welsh",
            "eu": "Basque",
            "ca": "Catalan",
            "gl": "Galician",
            "sq": "Albanian",
            "mk": "Macedonian",
            "sr": "Serbian",
            "bs": "Bosnian",
            "me": "Montenegrin",
            "uk": "Ukrainian",
            "be": "Belarusian",
            "kk": "Kazakh",
            "ky": "Kyrgyz",
            "uz": "Uzbek",
            "tg": "Tajik",
            "mn": "Mongolian",
            "ka": "Georgian",
            "hy": "Armenian",
            "az": "Azerbaijani",
            "fa": "Persian",
            "ur": "Urdu",
            "bn": "Bengali",
            "si": "Sinhala",
            "my": "Burmese",
            "km": "Khmer",
            "lo": "Lao",
            "ne": "Nepali",
            "gu": "Gujarati",
            "pa": "Punjabi",
            "or": "Odia",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "ml": "Malayalam",
            "as": "Assamese",
            "mr": "Marathi",
            "sa": "Sanskrit",
            "am": "Amharic",
            "ti": "Tigrinya",
            "so": "Somali",
            "ha": "Hausa",
            "yo": "Yoruba",
            "ig": "Igbo",
            "zu": "Zulu",
            "xh": "Xhosa",
            "st": "Southern Sotho",
            "tn": "Tswana",
            "ss": "Swati",
            "ve": "Venda",
            "ts": "Tsonga",
            "nr": "Southern Ndebele",
            "nd": "Northern Ndebele",
        }

        return languages

    def clear_cache(self):
        """Clear the translation cache."""
        cache_size = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Translation cache cleared: {cache_size} entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get translation cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "rate_limiters": {
                provider.value: last_request
                for provider, last_request in self._rate_limiters.items()
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform translation service health check.

        Returns:
            Dictionary with health check results
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "providers": {},
            }

            # Check Google Translate
            if self._google_translator:
                try:
                    # Simple translation test
                    test_result = await self.translate("Hello", target_lang="es")
                    health_status["providers"]["google"] = {
                        "status": "healthy",
                        "test_result": test_result.translated_text,
                    }
                except Exception as e:
                    health_status["providers"]["google"] = {
                        "status": "error",
                        "error": str(e),
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["providers"]["google"] = {"status": "not_configured"}

            # Check DeepL
            if self._deepl_api_key:
                health_status["providers"]["deepl"] = {"status": "configured"}
            else:
                health_status["providers"]["deepl"] = {"status": "not_configured"}

            # Check local model
            if self._local_model:
                health_status["providers"]["local"] = {"status": "configured"}
            else:
                health_status["providers"]["local"] = {"status": "not_configured"}

            return health_status

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "timestamp": asyncio.get_event_loop().time(),
                "error": str(e),
            }
