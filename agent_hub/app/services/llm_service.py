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
LLM service for MASX-HOTSPOTS Agentic AI System.
Provides unified interface for LLM interactions with:
- Multiple provider support (OpenAI, Mistral)
- Retry logic with exponential backoff
- Token counting and cost tracking
- Structured output validation
Usage: from app.services.llm_service import LLMService
    llm_service = LLMService()
    result = llm_service.generate_text(prompt, temperature=0.0)
"""

import json
import time
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional

import tiktoken
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from asyncio_throttle import Throttler

from ..config.settings import get_settings
from ..core.exceptions import ExternalServiceException, ConfigurationException
from ..core.utils import retry_with_backoff, safe_json_loads
from ..config.logging_config import get_logger


class LLMService:
    """
    Service for LLM interactions with multiple provider support.
    Handles:
    - OpenAI and Mistral API integration
    - Retry logic and error handling
    - Token counting and cost tracking
    - Structured output generation
    """

    _instance = None

    @classmethod
    def get_instance(cls, provider: Optional[str] = None):
        if cls._instance is None:
            cls._instance = cls(provider)
        return cls._instance

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM service.
        Args: provider: LLM provider to use ('openai', 'mistral', or None for auto-detect)
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized = True

        self.settings = get_settings()
        self.logger = get_logger(__name__)

        # Determine provider
        if provider:
            self.provider = provider
        else:
            self.provider = self.settings.primary_llm_provider

        # Initialize provider-specific clients
        self._init_provider()

        # Token counting
        self.tokenizer = self.__safe_encoding_for_model()

        # Cost tracking
        self.total_tokens = 0
        self.total_cost = 0.0

        # Throttling for mistral
        self._throttler = None
        # self._throttler = Throttler(rate_limit=4, period=60) if self.provider == "mistral" else None

    def _init_provider(self):
        """Initialize the selected LLM provider."""
        if self.provider == "openai":
            if not self.settings.has_openai_config:
                raise ConfigurationException("OpenAI not configured")

            config = self.settings.get_llm_config("openai")
            self.client = ChatOpenAI(
                model_name=config["model"],
                openai_api_key=config["api_key"],
                temperature=config["temperature"],
            )
            self.model = config["model"]
            self.temperature = config["temperature"]
            self.max_tokens = config["max_tokens"]

        elif self.provider == "mistral":
            if not self.settings.has_mistral_config:
                raise ConfigurationException("Mistral not configured")

            config = self.settings.get_llm_config("mistral")
            self.client = None  # use aiohttp directly
            self.model = config["model"]
            self.temperature = config.get("temperature", 0.0)
            self.max_tokens = config["max_tokens"]
            self.token_ref = config["token_ref"]
            self.api_base = config["api_base"].rstrip("/")
            self.api_key = config["api_key"]

        else:
            raise ConfigurationException(f"Unsupported LLM provider: {self.provider}")

    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def generate_text(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate text using the configured LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional provider-specific parameters

        Returns:
            str: Generated text response
        """
        try:
            if self.provider == "openai":
                return self._generate_openai(
                    user_prompt, system_prompt, temperature, max_tokens, **kwargs
                )
            elif self.provider == "mistral":
                return asyncio.run(
                    self._generate_mistral_async(
                        user_prompt, system_prompt, temperature, max_tokens, **kwargs
                    )
                )
            else:
                raise ConfigurationException(f"Unsupported provider: {self.provider}")

        except Exception as e:
            raise ExternalServiceException(
                f"LLM generation failed: {str(e)}", context={"provider": self.provider}
            )

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate text using OpenAI API."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs,
        )

        self._track_usage(
            response.usage.prompt_tokens, response.usage.completion_tokens
        )

        return response.choices[0].message.content

    async def _generate_mistral_async(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Async Mistral call using direct HTTP with throttle and retry.
        """
        if self._throttler is None:
            self._throttler = Throttler(rate_limit=4, period=60)

        async with self._throttler:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or 0.0,
                "max_tokens": max_tokens or self.max_tokens,
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            url = f"{self.api_base}/chat/completions"

            for attempt in range(3):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url, headers=headers, json=payload
                        ) as resp:
                            if resp.status == 429:
                                await asyncio.sleep(2**attempt)
                                continue
                            resp.raise_for_status()
                            data = await resp.json()
                            content = data["choices"][0]["message"]["content"]
                            estimated_tokens = len(user_prompt.split()) + len(
                                content.split()
                            )
                            self._track_usage(
                                estimated_tokens // 2, estimated_tokens // 2
                            )
                            return content
                except Exception as e:
                    self.logger.error(
                        f"*****Mistral async call failed attempt {attempt}: {str(e)}",
                        exc_info=True,
                    )
                    if attempt == 2:
                        raise ExternalServiceException(
                            f"Mistral async call failed: {str(e)}",
                            context={"provider": "mistral"},
                        )
                    await asyncio.sleep(2**attempt)

    def generate_structured_output(
        self,
        user_prompt: str,
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate structured output in JSON format.

        Args:
            prompt: User prompt
            output_schema: Expected output schema
            system_prompt: Optional system prompt
            temperature: Generation temperature (0.0 for deterministic)
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: Structured output matching the schema
        """
        json_prompt = f"""
        {user_prompt}

        Respond with ONLY valid JSON that matches this schema:
        {json.dumps(output_schema, indent=2)}

        Do not include any explanation or additional text.
        """

        response = self.generate_text(
            json_prompt, system_prompt=system_prompt, temperature=temperature, **kwargs
        )

        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            parsed = json.loads(cleaned_response.strip())
            return parsed

        except json.JSONDecodeError as e:
            raise ExternalServiceException(
                f"Failed to parse JSON response: {str(e)}",
                context={"response": response},
            )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            int: Number of tokens
        """
        return len(self.tokenizer.encode(text))

    def _track_usage(self, input_tokens: int, output_tokens: int):
        """Track token usage and calculate costs.
        embede actual cost of openAI and Mistral.
        """
        self.total_tokens += input_tokens + output_tokens

        if self.provider == "openai":
            input_cost = (input_tokens / 1000) * 0.01
            output_cost = (output_tokens / 1000) * 0.03
            self.total_cost += input_cost + output_cost

        self.logger.debug(
            "Token usage tracked",
            provider=self.provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=self.total_cost,
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        Returns:  Dict[str, Any]: Usage statistics
        """
        return {
            "provider": self.provider,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "model": self.model,
        }

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.total_tokens = 0
        self.total_cost = 0.0

    def __safe_encoding_for_model(self):
        try:
            return tiktoken.encoding_for_model(self.model)
        except KeyError:
            if self.token_ref:
                return tiktoken.get_encoding(self.token_ref)
            else:
                return tiktoken.get_encoding(self.model)
