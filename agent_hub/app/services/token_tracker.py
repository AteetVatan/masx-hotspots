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
Token cost tracking service for MASX-HOTSPOTS Agentic AI System.

Provides centralized token usage tracking and cost calculation for LLM API calls
across all agents and services. Supports multiple LLM providers with configurable
pricing models.

Usage: from app.services.token_tracker import TokenCostTracker
    tracker = TokenCostTracker()
    tracker.add_call(input_tokens=1000, output_tokens=500)
    summary = tracker.get_summary()
"""

import tiktoken
from transformers import AutoTokenizer
from typing import Dict, Any, Optional
from datetime import datetime

from ..config.settings import get_settings
from ..config.logging_config import get_logger


class TokenCostTracker:
    """
    Service for tracking token usage and calculating costs across LLM API calls.

    Features:
    - Multi-provider support (OpenAI, Mistral, etc.)
    - Configurable pricing models
    - Detailed usage statistics
    - Cost optimization insights
    - Session-based tracking
    """

    # Default pricing (as of 2025) - can be overridden via settings
    DEFAULT_PRICING = {
        "openai": {
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        },
        "mistral": {
            "mistral-large": {"input": 0.007, "output": 0.024},
            "mistral-medium": {"input": 0.4, "output": 2.0},
            "mistral-small": {
                "input": 0.1,
                "output": 0.3,
            },  # official API pricing per 1M tokens
        },
    }

    def __init__(self, provider: str = "openai", model: str = "gpt-4-turbo"):
        """
        Initialize token cost tracker.

        Args:
            provider: LLM provider name (openai, mistral, etc.)
            model: Specific model name for pricing
        """
        self.settings = get_settings()
        self.logger = get_logger(__name__)

        self.provider = provider
        self.model = model

        # Initialize tokenizer for the specified model
        self._init_tokenizer()

        # Initialize pricing model
        self._init_pricing()

        # Session tracking
        self.session_id = datetime.utcnow().isoformat()
        self.reset_session()

    def _init_tokenizer(self):
        """Initialize the appropriate tokenizer for the model."""

        # todo: remove this
        # for now use only openai
        self.provider = "openai"
        if self.provider == "openai":
            try:
                self.encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                self.logger.warning(f"Model {self.model} not found, using cl100k_base")
                self.encoding = tiktoken.get_encoding("cl100k_base")
            self.tokenizer = self.encoding.encode  # unified interface
        elif self.provider == "mistral":
            self.tokenizer = AutoTokenizer.from_pretrained(
                "mistralai/Mistral-7B-Instruct-v0.1"
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_pricing(self):
        """Initialize pricing model from settings or defaults."""
        # Try to get pricing from settings first
        pricing_config = getattr(self.settings, "llm_pricing", None)

        if pricing_config and self.provider in pricing_config:
            self.pricing = pricing_config[self.provider].get(
                self.model, self.DEFAULT_PRICING[self.provider][self.model]
            )
        else:
            # Use default pricing
            self.pricing = self.DEFAULT_PRICING.get(self.provider, {}).get(
                self.model, {"input": 0.01, "output": 0.03}  # Conservative default
            )

    def reset_session(self):
        """Reset session statistics for a new tracking session."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0
        self.session_start = datetime.utcnow()

        self.logger.info(
            "Token cost tracking session started",
            session_id=self.session_id,
            provider=self.provider,
            model=self.model,
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using the appropriate tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            int: Number of tokens
        """
        if not text:
            return 0
        if self.provider == "openai":
            return len(self.encoding.encode(text))
        elif self.provider == "mistral":
            return len(self.tokenizer.encode(text))
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for input and output tokens.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            float: Calculated cost in USD
        """
        input_cost = (input_tokens / 1000) * self.pricing["input"]
        output_cost = (output_tokens / 1000) * self.pricing["output"]
        return input_cost + output_cost

    def add_call(
        self,
        input_tokens: int,
        output_tokens: int,
        call_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Add a new API call to the tracker.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            call_context: Optional context about the call (agent, operation, etc.)
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        call_cost = self.calculate_cost(input_tokens, output_tokens)
        self.total_cost += call_cost
        self.call_count += 1

        # Log the call
        self.logger.debug(
            "Token usage tracked",
            call_number=self.call_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            call_cost=call_cost,
            total_cost=self.total_cost,
            context=call_context,
        )

        # Log detailed info for expensive calls (>$0.10)
        if call_cost > 0.10:
            self.logger.info(
                "High-cost API call detected",
                call_cost=call_cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                context=call_context,
            )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive usage summary.

        Returns:
            Dict containing usage statistics and cost breakdown
        """
        session_duration = datetime.utcnow() - self.session_start

        return {
            "session_id": self.session_id,
            "provider": self.provider,
            "model": self.model,
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "avg_cost_per_call": (
                self.total_cost / self.call_count if self.call_count > 0 else 0
            ),
            "avg_tokens_per_call": (
                (self.total_input_tokens + self.total_output_tokens) / self.call_count
                if self.call_count > 0
                else 0
            ),
            "session_duration_seconds": session_duration.total_seconds(),
            "calls_per_minute": (
                self.call_count / (session_duration.total_seconds() / 60)
                if session_duration.total_seconds() > 0
                else 0
            ),
            "pricing_model": self.pricing,
        }

    def print_summary(self):
        """Print a formatted summary to console."""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("TOKEN COST TRACKING SUMMARY")
        print("=" * 60)
        print(f"Session ID: {summary['session_id']}")
        print(f"Provider: {summary['provider']}")
        print(f"Model: {summary['model']}")
        print(f"Total API calls: {summary['total_calls']}")
        print(f"Total input tokens: {summary['total_input_tokens']:,}")
        print(f"Total output tokens: {summary['total_output_tokens']:,}")
        print(f"Total cost: ${summary['total_cost']:.4f}")
        print(f"Average cost per call: ${summary['avg_cost_per_call']:.4f}")
        print(f"Session duration: {summary['session_duration_seconds']:.1f} seconds")
        print(f"Calls per minute: {summary['calls_per_minute']:.2f}")
        print("=" * 60)

    def get_cost_estimate(
        self, input_text: str, expected_output_length: int = 100
    ) -> float:
        """
        Estimate cost for a potential API call.

        Args:
            input_text: Input text to estimate tokens for
            expected_output_length: Expected output length in characters

        Returns:
            float: Estimated cost in USD
        """
        input_tokens = self.count_tokens(input_text)
        output_tokens = self.count_tokens(
            "x" * expected_output_length
        )  # Rough estimate

        return self.calculate_cost(input_tokens, output_tokens)

    def get_optimization_suggestions(self) -> Dict[str, Any]:
        """
        Get cost optimization suggestions based on usage patterns.

        Returns:
            Dict containing optimization recommendations
        """
        suggestions = {
            "high_cost_calls": [],
            "efficiency_tips": [],
            "model_recommendations": [],
        }

        if self.call_count > 0:
            avg_cost = self.total_cost / self.call_count

            if avg_cost > 0.05:
                suggestions["high_cost_calls"].append(
                    f"Average call cost (${avg_cost:.4f}) is high. Consider batching requests."
                )

            if self.total_input_tokens > self.total_output_tokens * 10:
                suggestions["efficiency_tips"].append(
                    "Input tokens are much higher than output tokens. Consider shorter prompts."
                )

            if self.total_cost > 1.0:
                suggestions["model_recommendations"].append(
                    "Consider using a cheaper model for non-critical operations."
                )

        return suggestions


# Global instance for easy access across the application
_global_tracker: Optional[TokenCostTracker] = None


# get_token_tracker(provider="mistral", model="mistral-small-2407")
def get_token_tracker(
    provider: str = "mistral", model: str = "gpt-4-turbo"
) -> TokenCostTracker:
    """
    Get or create a global token tracker instance.

    Args:
        provider: LLM provider name
        model: Model name for pricing

    Returns:
        TokenCostTracker: Global tracker instance
    """
    global _global_tracker

    if _global_tracker is None:
        _global_tracker = TokenCostTracker(provider, model)

    return _global_tracker


def reset_global_tracker():
    """Reset the global token tracker session."""
    global _global_tracker
    if _global_tracker:
        _global_tracker.reset_session()
