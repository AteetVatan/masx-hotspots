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
Data Processing Pipeline for MASX-HOTSPOTS Agentic AI System.

Provides ETL, filtering, enrichment, and analytics capabilities:
- Article processing and normalization
- Content filtering and deduplication
- Sentiment analysis and keyword extraction
- Geographic and entity recognition
- Trend analysis and correlation detection
- Data aggregation and reporting

Features:
- Async processing with concurrency control
- Configurable processing pipelines
- Quality scoring and validation
- Performance monitoring and metrics
- Extensible processing stages
"""

import asyncio
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict, Counter

import structlog
from pydantic import BaseModel, validator
import spacy
from textblob import TextBlob
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from app.core.exceptions import ProcessingError, ValidationError
from app.services.data_sources import Article, GDELTEvent
from app.services.translation import TranslationService
from app.services.embedding import EmbeddingService

logger = structlog.get_logger(__name__)


class ProcessingStage(str, Enum):
    """Data processing stages."""

    VALIDATION = "validation"
    CLEANING = "cleaning"
    ENRICHMENT = "enrichment"
    ANALYSIS = "analysis"
    AGGREGATION = "aggregation"


@dataclass
class ProcessingMetrics:
    """Metrics for processing performance."""

    stage: ProcessingStage
    start_time: datetime
    end_time: Optional[datetime] = None
    input_count: int = 0
    output_count: int = 0
    error_count: int = 0
    processing_time: Optional[float] = None

    def complete(self, output_count: int, error_count: int = 0):
        """Mark processing as complete."""
        self.end_time = datetime.now()
        self.output_count = output_count
        self.error_count = error_count
        self.processing_time = (self.end_time - self.start_time).total_seconds()


class ProcessedArticle(BaseModel):
    """Enhanced article with processing results."""

    original: Article
    processed_at: datetime
    quality_score: float = 0.0
    language: str = "en"
    entities: List[Dict[str, Any]] = []
    keywords: List[str] = []
    sentiment: Optional[float] = None
    sentiment_confidence: Optional[float] = None
    categories: List[str] = []
    geographic_entities: List[Dict[str, Any]] = []
    political_entities: List[Dict[str, Any]] = []
    relevance_score: float = 0.0
    duplicate_of: Optional[str] = None
    processing_metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class TrendAnalysis(BaseModel):
    """Trend analysis results."""

    topic: str
    period: str
    start_date: datetime
    end_date: datetime
    volume_trend: float  # Change in volume
    sentiment_trend: float  # Change in sentiment
    key_entities: List[Dict[str, Any]]
    related_topics: List[str]
    confidence: float
    metadata: Dict[str, Any] = {}


class DataProcessingPipeline:
    """Main data processing pipeline."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.metrics: List[ProcessingMetrics] = []
        self.nlp = None
        self.translation_service = None
        self.embedding_service = None
        self._setup_nlp()

    def _setup_nlp(self):
        """Initialize NLP components."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("NLP model loaded successfully")
        except OSError:
            logger.warning("NLP model not found, using basic processing")
            self.nlp = None

    async def _setup_services(self):
        """Initialize processing services."""
        if not self.translation_service:
            self.translation_service = TranslationService()
        if not self.embedding_service:
            self.embedding_service = EmbeddingService()

    async def process_articles(
        self, articles: List[Article], stages: Optional[List[ProcessingStage]] = None
    ) -> List[ProcessedArticle]:
        """Process articles through the pipeline."""
        if not stages:
            stages = list(ProcessingStage)

        processed = articles
        for stage in stages:
            start_metrics = ProcessingMetrics(
                stage=stage, start_time=datetime.now(), input_count=len(processed)
            )

            try:
                if stage == ProcessingStage.VALIDATION:
                    processed = await self._validate_articles(processed)
                elif stage == ProcessingStage.CLEANING:
                    processed = await self._clean_articles(processed)
                elif stage == ProcessingStage.ENRICHMENT:
                    processed = await self._enrich_articles(processed)
                elif stage == ProcessingStage.ANALYSIS:
                    processed = await self._analyze_articles(processed)
                elif stage == ProcessingStage.AGGREGATION:
                    processed = await self._aggregate_articles(processed)

                start_metrics.complete(len(processed))
                self.metrics.append(start_metrics)

            except Exception as e:
                logger.error("Processing stage failed", stage=stage, error=str(e))
                start_metrics.complete(0, len(processed))
                self.metrics.append(start_metrics)
                raise ProcessingError(f"Stage {stage} failed: {e}")

        return processed

    async def _validate_articles(self, articles: List[Article]) -> List[Article]:
        """Validate articles for processing."""
        valid_articles = []

        for article in articles:
            try:
                # Basic validation
                if not article.title or len(article.title.strip()) < 10:
                    continue
                if not article.url:
                    continue
                if article.published_at < datetime.now() - timedelta(days=30):
                    continue  # Skip old articles

                valid_articles.append(article)

            except Exception as e:
                logger.warning(
                    "Article validation failed", article_id=article.id, error=str(e)
                )
                continue

        logger.info(
            "Article validation completed",
            input=len(articles),
            output=len(valid_articles),
        )
        return valid_articles

    async def _clean_articles(self, articles: List[Article]) -> List[Article]:
        """Clean and normalize articles."""
        cleaned_articles = []

        for article in articles:
            try:
                # Clean title
                article.title = re.sub(r"\s+", " ", article.title.strip())
                article.title = re.sub(r"[^\w\s\-.,!?]", "", article.title)

                # Clean description
                if article.description:
                    article.description = re.sub(
                        r"\s+", " ", article.description.strip()
                    )
                    article.description = re.sub(
                        r"[^\w\s\-.,!?]", "", article.description
                    )

                # Remove HTML tags
                if article.content:
                    article.content = re.sub(r"<[^>]+>", "", article.content)
                    article.content = re.sub(r"\s+", " ", article.content.strip())

                cleaned_articles.append(article)

            except Exception as e:
                logger.warning(
                    "Article cleaning failed", article_id=article.id, error=str(e)
                )
                continue

        logger.info(
            "Article cleaning completed",
            input=len(articles),
            output=len(cleaned_articles),
        )
        return cleaned_articles

    async def _enrich_articles(self, articles: List[Article]) -> List[ProcessedArticle]:
        """Enrich articles with additional data."""
        await self._setup_services()
        enriched_articles = []

        async def enrich_article(article: Article) -> Optional[ProcessedArticle]:
            async with self.semaphore:
                try:
                    processed = ProcessedArticle(
                        original=article, processed_at=datetime.now()
                    )

                    # Language detection
                    text = f"{article.title} {article.description or ''}"
                    processed.language = await self._detect_language(text)

                    # Entity extraction
                    if self.nlp:
                        doc = self.nlp(text)
                        processed.entities = [
                            {
                                "text": ent.text,
                                "label": ent.label_,
                                "start": ent.start_char,
                                "end": ent.end_char,
                            }
                            for ent in doc.ents
                        ]

                        # Extract geographic and political entities
                        processed.geographic_entities = [
                            ent
                            for ent in processed.entities
                            if ent["label"] in ["GPE", "LOC"]
                        ]
                        processed.political_entities = [
                            ent
                            for ent in processed.entities
                            if ent["label"] in ["ORG", "PERSON"]
                        ]

                    # Keyword extraction
                    processed.keywords = await self._extract_keywords(text)

                    # Category classification
                    processed.categories = await self._classify_categories(text)

                    # Quality scoring
                    processed.quality_score = await self._calculate_quality_score(
                        processed
                    )

                    return processed

                except Exception as e:
                    logger.warning(
                        "Article enrichment failed", article_id=article.id, error=str(e)
                    )
                    return None

        # Process articles concurrently
        tasks = [enrich_article(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ProcessedArticle):
                enriched_articles.append(result)

        logger.info(
            "Article enrichment completed",
            input=len(articles),
            output=len(enriched_articles),
        )
        return enriched_articles

    async def _analyze_articles(
        self, articles: List[ProcessedArticle]
    ) -> List[ProcessedArticle]:
        """Analyze articles for sentiment and relevance."""
        analyzed_articles = []

        for article in articles:
            try:
                # Sentiment analysis
                text = f"{article.original.title} {article.original.description or ''}"
                blob = TextBlob(text)
                article.sentiment = blob.sentiment.polarity
                article.sentiment_confidence = abs(blob.sentiment.subjectivity)

                # Relevance scoring
                article.relevance_score = await self._calculate_relevance_score(article)

                analyzed_articles.append(article)

            except Exception as e:
                logger.warning(
                    "Article analysis failed",
                    article_id=article.original.id,
                    error=str(e),
                )
                continue

        logger.info(
            "Article analysis completed",
            input=len(articles),
            output=len(analyzed_articles),
        )
        return analyzed_articles

    async def _aggregate_articles(
        self, articles: List[ProcessedArticle]
    ) -> List[ProcessedArticle]:
        """Aggregate and deduplicate articles."""
        # Remove duplicates based on similarity
        unique_articles = await self._deduplicate_articles(articles)

        # Sort by relevance and quality
        unique_articles.sort(
            key=lambda x: (x.relevance_score, x.quality_score), reverse=True
        )

        logger.info(
            "Article aggregation completed",
            input=len(articles),
            output=len(unique_articles),
        )
        return unique_articles

    async def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        try:
            if self.translation_service:
                return await self.translation_service.detect_language(text)
            return "en"  # Default to English
        except Exception:
            return "en"

    async def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        try:
            if not self.nlp:
                # Basic keyword extraction
                words = re.findall(r"\b\w+\b", text.lower())
                stop_words = {
                    "the",
                    "a",
                    "an",
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
                    "by",
                }
                keywords = [
                    word for word in words if word not in stop_words and len(word) > 3
                ]
                return list(set(keywords))[:10]

            # Use spaCy for better keyword extraction
            doc = self.nlp(text)
            keywords = []

            # Extract noun phrases and named entities
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) <= 3:  # Limit to 3-word phrases
                    keywords.append(chunk.text.lower())

            for ent in doc.ents:
                keywords.append(ent.text.lower())

            return list(set(keywords))[:15]

        except Exception as e:
            logger.warning("Keyword extraction failed", error=str(e))
            return []

    async def _classify_categories(self, text: str) -> List[str]:
        """Classify article into categories."""
        categories = []
        text_lower = text.lower()

        # Simple rule-based classification
        category_keywords = {
            "geopolitics": [
                "geopolitics",
                "diplomacy",
                "foreign policy",
                "international relations",
            ],
            "conflict": ["conflict", "war", "tension", "dispute", "crisis"],
            "economy": ["economy", "economic", "trade", "finance", "market"],
            "security": ["security", "defense", "military", "terrorism"],
            "environment": ["climate", "environment", "sustainability"],
            "technology": ["technology", "cyber", "digital", "innovation"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)

        return categories[:3]  # Limit to 3 categories

    async def _calculate_quality_score(self, article: ProcessedArticle) -> float:
        """Calculate quality score for article."""
        score = 0.0

        # Title quality
        if len(article.original.title) > 20:
            score += 0.2

        # Description quality
        if article.original.description and len(article.original.description) > 50:
            score += 0.2

        # Entity richness
        if len(article.entities) > 5:
            score += 0.2

        # Source reliability (basic heuristic)
        reliable_sources = ["reuters", "ap", "bbc", "cnn", "nytimes"]
        if any(
            source in article.original.source.lower() for source in reliable_sources
        ):
            score += 0.2

        # Recency
        hours_old = (
            datetime.now() - article.original.published_at
        ).total_seconds() / 3600
        if hours_old < 24:
            score += 0.2

        return min(score, 1.0)

    async def _calculate_relevance_score(self, article: ProcessedArticle) -> float:
        """Calculate relevance score for geopolitical analysis."""
        score = 0.0

        # Geographic entities
        if len(article.geographic_entities) > 0:
            score += 0.3

        # Political entities
        if len(article.political_entities) > 0:
            score += 0.3

        # Categories
        relevant_categories = ["geopolitics", "conflict", "diplomacy", "security"]
        if any(cat in article.categories for cat in relevant_categories):
            score += 0.2

        # Keywords
        relevant_keywords = [
            "diplomacy",
            "foreign",
            "international",
            "policy",
            "relations",
        ]
        if any(keyword in article.keywords for keyword in relevant_keywords):
            score += 0.2

        return min(score, 1.0)

    async def _deduplicate_articles(
        self, articles: List[ProcessedArticle]
    ) -> List[ProcessedArticle]:
        """Remove duplicate articles based on similarity."""
        if len(articles) <= 1:
            return articles

        # Use TF-IDF for similarity detection
        texts = [f"{a.original.title} {a.original.description or ''}" for a in articles]

        try:
            vectorizer = TfidfVectorizer(max_features=1000, stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(texts)

            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(tfidf_matrix)

            # Find duplicates
            duplicates = set()
            for i in range(len(similarity_matrix)):
                for j in range(i + 1, len(similarity_matrix)):
                    if similarity_matrix[i][j] > 0.8:  # High similarity threshold
                        # Keep the article with higher quality score
                        if articles[i].quality_score < articles[j].quality_score:
                            duplicates.add(i)
                        else:
                            duplicates.add(j)

            unique_articles = [
                articles[i] for i in range(len(articles)) if i not in duplicates
            ]

        except Exception as e:
            logger.warning(
                "Deduplication failed, returning original articles", error=str(e)
            )
            unique_articles = articles

        return unique_articles

    async def analyze_trends(
        self, articles: List[ProcessedArticle], period_days: int = 7
    ) -> List[TrendAnalysis]:
        """Analyze trends in articles."""
        if not articles:
            return []

        trends = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        # Group articles by time periods
        period_articles = defaultdict(list)
        for article in articles:
            if start_date <= article.original.published_at <= end_date:
                day = article.original.published_at.date()
                period_articles[day].append(article)

        # Analyze trends for each topic
        topics = await self._extract_topics(articles)

        for topic in topics[:10]:  # Limit to top 10 topics
            try:
                trend = await self._analyze_topic_trend(
                    topic, period_articles, start_date, end_date
                )
                if trend:
                    trends.append(trend)
            except Exception as e:
                logger.warning("Topic trend analysis failed", topic=topic, error=str(e))
                continue

        return trends

    async def _extract_topics(self, articles: List[ProcessedArticle]) -> List[str]:
        """Extract main topics from articles."""
        all_keywords = []
        for article in articles:
            all_keywords.extend(article.keywords)

        # Count keyword frequency
        keyword_counts = Counter(all_keywords)
        return [keyword for keyword, count in keyword_counts.most_common(20)]

    async def _analyze_topic_trend(
        self,
        topic: str,
        period_articles: Dict,
        start_date: datetime,
        end_date: datetime,
        period_days: int = 7,
    ) -> Optional[TrendAnalysis]:
        """Analyze trend for a specific topic."""
        topic_articles = []
        for day_articles in period_articles.values():
            for article in day_articles:
                if topic.lower() in " ".join(article.keywords).lower():
                    topic_articles.append(article)

        if len(topic_articles) < 3:  # Need minimum articles for trend
            return None

        # Calculate volume trend
        volume_trend = len(topic_articles) / len(period_articles)

        # Calculate sentiment trend
        sentiments = [a.sentiment for a in topic_articles if a.sentiment is not None]
        if sentiments:
            sentiment_trend = statistics.mean(sentiments)
        else:
            sentiment_trend = 0.0

        # Extract key entities
        all_entities = []
        for article in topic_articles:
            all_entities.extend(article.entities)

        entity_counts = Counter([e["text"] for e in all_entities])
        key_entities = [
            {"text": entity, "count": count}
            for entity, count in entity_counts.most_common(5)
        ]

        return TrendAnalysis(
            topic=topic,
            period=f"{period_days} days",
            start_date=start_date,
            end_date=end_date,
            volume_trend=volume_trend,
            sentiment_trend=sentiment_trend,
            key_entities=key_entities,
            related_topics=await self._find_related_topics(topic, topic_articles),
            confidence=min(len(topic_articles) / 10.0, 1.0),
        )

    async def _find_related_topics(
        self, topic: str, articles: List[ProcessedArticle]
    ) -> List[str]:
        """Find topics related to the main topic."""
        related_keywords = []
        for article in articles:
            if topic.lower() in " ".join(article.keywords).lower():
                related_keywords.extend(article.keywords)

        keyword_counts = Counter(related_keywords)
        return [
            keyword
            for keyword, count in keyword_counts.most_common(5)
            if keyword != topic
        ]

    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing performance metrics."""
        if not self.metrics:
            return {}

        total_metrics = {
            "total_articles_processed": sum(m.input_count for m in self.metrics),
            "total_processing_time": sum(m.processing_time or 0 for m in self.metrics),
            "average_processing_time": statistics.mean(
                [m.processing_time or 0 for m in self.metrics]
            ),
            "stage_metrics": {},
        }

        for stage in ProcessingStage:
            stage_metrics = [m for m in self.metrics if m.stage == stage]
            if stage_metrics:
                total_metrics["stage_metrics"][stage.value] = {
                    "total_processed": sum(m.input_count for m in stage_metrics),
                    "total_output": sum(m.output_count for m in stage_metrics),
                    "total_errors": sum(m.error_count for m in stage_metrics),
                    "average_time": statistics.mean(
                        [m.processing_time or 0 for m in stage_metrics]
                    ),
                }

        return total_metrics

    def clear_metrics(self):
        """Clear processing metrics."""
        self.metrics.clear()
