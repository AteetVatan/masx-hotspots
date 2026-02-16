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
Agent implementations for MASX-HOTSPOTS Agentic AI System.
This package contains all specialized agents for the multi-agent system including:
- Base agent classes and interfaces
- Domain classification and query planning agents
- News fetching and event processing agents
- Analysis and validation agents
Usage: from app.agents import BaseAgent, DomainClassifier, QueryPlanner
"""

from .base import BaseAgent, AgentResult
from .domain_classifier import DomainClassifier
from .query_planner import QueryPlanner
from .news_fetcher import NewsFetcher
from .gdelt_fetcher_agent import GdeltFetcherAgent
from .merge_deduplicator import MergeDeduplicator
from .language_resolver import LanguageResolver
from .translator import Translator
from .language_agent import LanguageAgent
from .event_analyzer import EventAnalyzer
from .fact_checker import FactChecker
from .validator import Validator
from .memory_manager import MemoryManager
from .logging_auditor import LoggingAuditor
from .flashpoint_llm_agent import FlashpointLLMAgent
from .flashpoint_validator_agent import FlashpointValidatorAgent
from .google_rss_agent import GoogleRssFeederAgent
from .gdelt_fetcher_agent import GdeltFetcherAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "DomainClassifier",
    "QueryPlanner",
    "NewsFetcher",
    "GdeltFetcherAgent",
    "MergeDeduplicator",
    "LanguageResolver",
    "Translator",
    "LanguageAgent",
    "EventAnalyzer",
    "FactChecker",
    "Validator",
    "MemoryManager",
    "LoggingAuditor",
    "FlashpointLLMAgent",
    "FlashpointValidatorAgent",
    "GoogleRssFeederAgent",
    "GdeltFetcherAgent",
]
