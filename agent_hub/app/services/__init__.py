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
Services for MASX-HOTSPOTS Agentic AI System.

This package contains service layer components including:
- Database service with Supabase integration
- Translation service for multilingual support
- Embedding service for vector operations
- Data sources integration (Google News RSS, GDELT)
- Data processing and ETL pipelines
- Real-time streaming and WebSocket support
- Advanced analytics and reporting
- External API integrations

Usage:
    from app.services import DatabaseService, TranslationService, EmbeddingService
"""

from .database import DatabaseService
from .translation import TranslationService
from .embedding import EmbeddingService
from .llm_service import LLMService
from .feed_parser_service import FeedParserService
from .data_sources import DataSourcesService, Article, GDELTEvent
from .data_processing import DataProcessingPipeline, ProcessedArticle, TrendAnalysis
from .streaming import StreamingService, StreamEvent, StreamFilter

# from .streaming import WebSocketManager  # Commented out WebSocket functionality
from .analytics import DataAnalyticsService, AnalyticsReport, RiskAssessment
from .token_tracker import TokenCostTracker, get_token_tracker
from .web_search import WebSearchService, create_web_search_service
from .language_service import LanguageService
from .masx_gdelt_service import MasxGdeltService
from .flashpoint_detection import (
    FlashpointDetectionService,
    Flashpoint,
    create_flashpoint_detection_service,
)
from .ping_apis_service import PingApisService
from .flashpoint_db_service import (
    FlashpointDatabaseService,
    FlashpointRecord,
    FeedRecord,
)

__all__ = [
    "DatabaseService",
    "TranslationService",
    "EmbeddingService",
    "LLMService",
    "FeedParserService",
    "DataSourcesService",
    "Article",
    "GDELTEvent",
    "DataProcessingPipeline",
    "ProcessedArticle",
    "TrendAnalysis",
    "StreamingService",
    # "WebSocketManager",  # Commented out WebSocket functionality
    "StreamEvent",
    "StreamFilter",
    "DataAnalyticsService",
    "AnalyticsReport",
    "RiskAssessment",
    "TokenCostTracker",
    "get_token_tracker",
    "WebSearchService",
    "create_web_search_service",
    "FlashpointDetectionService",
    "Flashpoint",
    "create_flashpoint_detection_service",
    "LanguageService",
    "MasxGdeltService",
    "PingApisService",
    "FlashpointDatabaseService",
    "FlashpointRecord",
    "FeedRecord",
]
