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
Data Analytics Service for MASX-HOTSPOTS Agentic AI System.

Provides advanced analytics capabilities:
- Data aggregation and statistical analysis
- Trend detection and forecasting
- Correlation analysis and pattern recognition
- Geographic and temporal analysis
- Risk assessment and scoring
- Performance metrics and reporting

Features:
- Real-time analytics processing
- Configurable analysis pipelines
- Machine learning integration
- Visualization data preparation
- Export and reporting capabilities
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict, Counter
import numpy as np
from scipy import stats
import pandas as pd

import structlog
from pydantic import BaseModel, validator
import plotly.graph_objects as go

from app.core.exceptions import AnalyticsError, ValidationError
from app.services.data_processing import ProcessedArticle, TrendAnalysis
from app.services.database import DatabaseService
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)


class AnalysisType(str, Enum):
    """Types of analytics analysis."""

    TREND = "trend"
    CORRELATION = "correlation"
    CLUSTERING = "clustering"
    FORECASTING = "forecasting"
    RISK_ASSESSMENT = "risk_assessment"
    GEOGRAPHIC = "geographic"
    TEMPORAL = "temporal"


class TimeGranularity(str, Enum):
    """Time granularity for temporal analysis."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class AnalyticsMetrics:
    """Analytics performance metrics."""

    analysis_type: AnalysisType
    start_time: datetime
    end_time: Optional[datetime] = None
    input_count: int = 0
    output_count: int = 0
    processing_time: Optional[float] = None
    accuracy_score: Optional[float] = None

    def complete(self, output_count: int, accuracy_score: Optional[float] = None):
        """Mark analysis as complete."""
        self.end_time = datetime.now()
        self.output_count = output_count
        self.accuracy_score = accuracy_score
        self.processing_time = (self.end_time - self.start_time).total_seconds()


class GeographicAnalysis(BaseModel):
    """Geographic analysis results."""

    country_code: str
    country_name: str
    article_count: int
    avg_sentiment: float
    key_topics: List[str]
    risk_score: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    metadata: Dict[str, Any] = {}


class CorrelationAnalysis(BaseModel):
    """Correlation analysis results."""

    variable1: str
    variable2: str
    correlation_coefficient: float
    p_value: float
    significance: str  # "high", "medium", "low"
    sample_size: int
    interpretation: str
    metadata: Dict[str, Any] = {}


class RiskAssessment(BaseModel):
    """Risk assessment results."""

    risk_id: str
    risk_type: str
    risk_level: str  # "low", "medium", "high", "critical"
    confidence: float
    factors: List[str]
    impact_score: float
    probability_score: float
    recommendations: List[str]
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class AnalyticsReport(BaseModel):
    """Comprehensive analytics report."""

    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any]
    trends: List[TrendAnalysis]
    geographic_analysis: List[GeographicAnalysis]
    correlations: List[CorrelationAnalysis]
    risk_assessments: List[RiskAssessment]
    visualizations: Dict[str, Any]
    metadata: Dict[str, Any] = {}


class DataAnalyticsService:
    """Main data analytics service."""

    def __init__(self):
        self.settings = get_settings()
        self.database: Optional[DatabaseService] = None
        self.metrics: List[AnalyticsMetrics] = []
        self.cache: Dict[str, Any] = {}

    async def _setup_database(self):
        """Initialize database connection."""
        if not self.database:
            self.database = DatabaseService()

    async def analyze_trends(
        self, articles: List[ProcessedArticle], period_days: int = 7
    ) -> List[TrendAnalysis]:
        """Analyze trends in articles over time."""
        start_metrics = AnalyticsMetrics(
            analysis_type=AnalysisType.TREND,
            start_time=datetime.now(),
            input_count=len(articles),
        )

        try:
            if not articles:
                return []

            # Group articles by time periods
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            # Create time buckets
            time_buckets = defaultdict(list)
            for article in articles:
                if start_date <= article.original.published_at <= end_date:
                    day = article.original.published_at.date()
                    time_buckets[day].append(article)

            # Extract topics and analyze trends
            topics = await self._extract_topics(articles)
            trends = []

            for topic in topics[:15]:  # Top 15 topics
                trend = await self._analyze_topic_trend(
                    topic, time_buckets, start_date, end_date
                )
                if trend and trend.confidence > 0.5:
                    trends.append(trend)

            # Sort by confidence and volume
            trends.sort(key=lambda x: (x.confidence, x.volume_trend), reverse=True)

            start_metrics.complete(
                len(trends), statistics.mean([t.confidence for t in trends])
            )
            self.metrics.append(start_metrics)

            logger.info("Trend analysis completed", trends_count=len(trends))
            return trends

        except Exception as e:
            logger.error("Trend analysis failed", error=str(e))
            start_metrics.complete(0)
            self.metrics.append(start_metrics)
            raise AnalyticsError(f"Trend analysis failed: {e}")

    async def analyze_geographic_patterns(
        self, articles: List[ProcessedArticle]
    ) -> List[GeographicAnalysis]:
        """Analyze geographic patterns in articles."""
        start_metrics = AnalyticsMetrics(
            analysis_type=AnalysisType.GEOGRAPHIC,
            start_time=datetime.now(),
            input_count=len(articles),
        )

        try:
            # Group articles by country
            country_articles = defaultdict(list)
            for article in articles:
                if article.original.country:
                    country_articles[article.original.country].append(article)

            geographic_analyses = []

            for country_code, country_articles_list in country_articles.items():
                if len(country_articles_list) < 3:  # Minimum articles for analysis
                    continue

                # Calculate metrics
                sentiments = [
                    a.sentiment
                    for a in country_articles_list
                    if a.sentiment is not None
                ]
                avg_sentiment = statistics.mean(sentiments) if sentiments else 0.0

                # Extract key topics
                all_keywords = []
                for article in country_articles_list:
                    all_keywords.extend(article.keywords)
                key_topics = [
                    topic for topic, count in Counter(all_keywords).most_common(5)
                ]

                # Calculate risk score
                risk_score = await self._calculate_geographic_risk(
                    country_articles_list
                )

                # Determine trend direction
                trend_direction = await self._determine_trend_direction(
                    country_articles_list
                )

                analysis = GeographicAnalysis(
                    country_code=country_code,
                    country_name=country_code,  # Could be enhanced with country name mapping
                    article_count=len(country_articles_list),
                    avg_sentiment=avg_sentiment,
                    key_topics=key_topics,
                    risk_score=risk_score,
                    trend_direction=trend_direction,
                )

                geographic_analyses.append(analysis)

            # Sort by risk score
            geographic_analyses.sort(key=lambda x: x.risk_score, reverse=True)

            start_metrics.complete(len(geographic_analyses))
            self.metrics.append(start_metrics)

            logger.info(
                "Geographic analysis completed",
                countries_count=len(geographic_analyses),
            )
            return geographic_analyses

        except Exception as e:
            logger.error("Geographic analysis failed", error=str(e))
            start_metrics.complete(0)
            self.metrics.append(start_metrics)
            raise AnalyticsError(f"Geographic analysis failed: {e}")

    async def analyze_correlations(
        self, articles: List[ProcessedArticle]
    ) -> List[CorrelationAnalysis]:
        """Analyze correlations between different variables."""
        start_metrics = AnalyticsMetrics(
            analysis_type=AnalysisType.CORRELATION,
            start_time=datetime.now(),
            input_count=len(articles),
        )

        try:
            correlations = []

            # Prepare data for correlation analysis
            data = []
            for article in articles:
                if article.sentiment is not None and article.relevance_score > 0:
                    data.append(
                        {
                            "sentiment": article.sentiment,
                            "relevance": article.relevance_score,
                            "quality": article.quality_score,
                            "entity_count": len(article.entities),
                            "keyword_count": len(article.keywords),
                        }
                    )

            if len(data) < 10:  # Need minimum data points
                return []

            df = pd.DataFrame(data)

            # Analyze correlations
            correlation_pairs = [
                ("sentiment", "relevance"),
                ("sentiment", "quality"),
                ("relevance", "quality"),
                ("entity_count", "relevance"),
                ("keyword_count", "relevance"),
            ]

            for var1, var2 in correlation_pairs:
                if var1 in df.columns and var2 in df.columns:
                    correlation, p_value = stats.pearsonr(df[var1], df[var2])

                    # Determine significance
                    if p_value < 0.01:
                        significance = "high"
                    elif p_value < 0.05:
                        significance = "medium"
                    else:
                        significance = "low"

                    # Generate interpretation
                    interpretation = await self._interpret_correlation(
                        var1, var2, correlation, p_value
                    )

                    correlation_analysis = CorrelationAnalysis(
                        variable1=var1,
                        variable2=var2,
                        correlation_coefficient=correlation,
                        p_value=p_value,
                        significance=significance,
                        sample_size=len(df),
                        interpretation=interpretation,
                    )

                    correlations.append(correlation_analysis)

            start_metrics.complete(len(correlations))
            self.metrics.append(start_metrics)

            logger.info(
                "Correlation analysis completed", correlations_count=len(correlations)
            )
            return correlations

        except Exception as e:
            logger.error("Correlation analysis failed", error=str(e))
            start_metrics.complete(0)
            self.metrics.append(start_metrics)
            raise AnalyticsError(f"Correlation analysis failed: {e}")

    async def assess_risks(
        self, articles: List[ProcessedArticle]
    ) -> List[RiskAssessment]:
        """Assess risks based on article analysis."""
        start_metrics = AnalyticsMetrics(
            analysis_type=AnalysisType.RISK_ASSESSMENT,
            start_time=datetime.now(),
            input_count=len(articles),
        )

        try:
            risks = []

            # Analyze different risk types
            risk_types = [
                ("sentiment_risk", self._assess_sentiment_risk),
                ("geographic_risk", self._assess_geographic_risk),
                ("temporal_risk", self._assess_temporal_risk),
                ("content_risk", self._assess_content_risk),
            ]

            for risk_type, assessor_func in risk_types:
                try:
                    risk = await assessor_func(articles)
                    if risk:
                        risks.append(risk)
                except Exception as e:
                    logger.warning(
                        f"Risk assessment failed for {risk_type}", error=str(e)
                    )
                    continue

            start_metrics.complete(len(risks))
            self.metrics.append(start_metrics)

            logger.info("Risk assessment completed", risks_count=len(risks))
            return risks

        except Exception as e:
            logger.error("Risk assessment failed", error=str(e))
            start_metrics.complete(0)
            self.metrics.append(start_metrics)
            raise AnalyticsError(f"Risk assessment failed: {e}")

    async def generate_comprehensive_report(
        self, articles: List[ProcessedArticle], period_days: int = 7
    ) -> AnalyticsReport:
        """Generate comprehensive analytics report."""
        try:
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            # Run all analyses
            trends = await self.analyze_trends(articles, period_days)
            geographic_analysis = await self.analyze_geographic_patterns(articles)
            correlations = await self.analyze_correlations(articles)
            risk_assessments = await self.assess_risks(articles)

            # Generate summary
            summary = await self._generate_summary(
                articles, trends, geographic_analysis, risk_assessments
            )

            # Generate visualizations
            visualizations = await self._generate_visualizations(
                articles, trends, geographic_analysis
            )

            report = AnalyticsReport(
                report_id=report_id,
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                summary=summary,
                trends=trends,
                geographic_analysis=geographic_analysis,
                correlations=correlations,
                risk_assessments=risk_assessments,
                visualizations=visualizations,
            )

            logger.info("Comprehensive report generated", report_id=report_id)
            return report

        except Exception as e:
            logger.error("Report generation failed", error=str(e))
            raise AnalyticsError(f"Report generation failed: {e}")

    async def _extract_topics(self, articles: List[ProcessedArticle]) -> List[str]:
        """Extract main topics from articles."""
        all_keywords = []
        for article in articles:
            all_keywords.extend(article.keywords)

        keyword_counts = Counter(all_keywords)
        return [keyword for keyword, count in keyword_counts.most_common(20)]

    async def _analyze_topic_trend(
        self, topic: str, time_buckets: Dict, start_date: datetime, end_date: datetime, period_days: int = 7
    ) -> Optional[TrendAnalysis]:
        """Analyze trend for a specific topic."""
        topic_articles = []
        for day_articles in time_buckets.values():
            for article in day_articles:
                if topic.lower() in " ".join(article.keywords).lower():
                    topic_articles.append(article)

        if len(topic_articles) < 3:
            return None

        # Calculate volume trend
        volume_trend = len(topic_articles) / len(time_buckets)

        # Calculate sentiment trend
        sentiments = [a.sentiment for a in topic_articles if a.sentiment is not None]
        sentiment_trend = statistics.mean(sentiments) if sentiments else 0.0

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

    async def _calculate_geographic_risk(
        self, articles: List[ProcessedArticle]
    ) -> float:
        """Calculate risk score for geographic region."""
        if not articles:
            return 0.0

        # Factors for risk calculation
        negative_sentiment_ratio = len(
            [a for a in articles if a.sentiment and a.sentiment < -0.2]
        ) / len(articles)
        high_relevance_ratio = len(
            [a for a in articles if a.relevance_score > 0.8]
        ) / len(articles)
        conflict_keywords = ["conflict", "war", "tension", "crisis", "dispute"]
        conflict_ratio = len(
            [
                a
                for a in articles
                if any(
                    keyword in " ".join(a.keywords).lower()
                    for keyword in conflict_keywords
                )
            ]
        ) / len(articles)

        # Weighted risk score
        risk_score = (
            negative_sentiment_ratio * 0.4
            + high_relevance_ratio * 0.3
            + conflict_ratio * 0.3
        )

        return min(risk_score, 1.0)

    async def _determine_trend_direction(self, articles: List[ProcessedArticle]) -> str:
        """Determine trend direction for articles."""
        if len(articles) < 2:
            return "stable"

        # Sort by publication date
        sorted_articles = sorted(articles, key=lambda x: x.original.published_at)

        # Calculate sentiment trend
        early_sentiments = [
            a.sentiment
            for a in sorted_articles[: len(sorted_articles) // 2]
            if a.sentiment is not None
        ]
        late_sentiments = [
            a.sentiment
            for a in sorted_articles[len(sorted_articles) // 2 :]
            if a.sentiment is not None
        ]

        if early_sentiments and late_sentiments:
            early_avg = statistics.mean(early_sentiments)
            late_avg = statistics.mean(late_sentiments)

            if late_avg - early_avg > 0.1:
                return "increasing"
            elif early_avg - late_avg > 0.1:
                return "decreasing"

        return "stable"

    async def _interpret_correlation(
        self, var1: str, var2: str, correlation: float, p_value: float
    ) -> str:
        """Interpret correlation results."""
        strength = (
            "strong"
            if abs(correlation) > 0.7
            else "moderate" if abs(correlation) > 0.3 else "weak"
        )
        direction = "positive" if correlation > 0 else "negative"
        significance = "significant" if p_value < 0.05 else "not significant"

        return f"{strength} {direction} correlation ({correlation:.3f}) that is {significance} (p={p_value:.3f})"

    async def _assess_sentiment_risk(
        self, articles: List[ProcessedArticle]
    ) -> Optional[RiskAssessment]:
        """Assess sentiment-based risks."""
        if not articles:
            return None

        negative_articles = [a for a in articles if a.sentiment and a.sentiment < -0.3]
        negative_ratio = len(negative_articles) / len(articles)

        if negative_ratio > 0.3:  # High negative sentiment
            risk_level = "high" if negative_ratio > 0.5 else "medium"

            return RiskAssessment(
                risk_id=f"sentiment_risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                risk_type="sentiment_risk",
                risk_level=risk_level,
                confidence=negative_ratio,
                factors=[f"High negative sentiment ratio: {negative_ratio:.2f}"],
                impact_score=0.7,
                probability_score=negative_ratio,
                recommendations=[
                    "Monitor sentiment trends closely",
                    "Investigate sources of negative sentiment",
                    "Prepare response strategies",
                ],
                timestamp=datetime.now(),
            )

        return None

    async def _assess_geographic_risk(
        self, articles: List[ProcessedArticle]
    ) -> Optional[RiskAssessment]:
        """Assess geographic-based risks."""
        # Group by country and analyze
        country_articles = defaultdict(list)
        for article in articles:
            if article.original.country:
                country_articles[article.original.country].append(article)

        high_risk_countries = []
        for country, country_articles_list in country_articles.items():
            if len(country_articles_list) >= 3:
                risk_score = await self._calculate_geographic_risk(
                    country_articles_list
                )
                if risk_score > 0.6:
                    high_risk_countries.append((country, risk_score))

        if high_risk_countries:
            max_risk_country, max_risk_score = max(
                high_risk_countries, key=lambda x: x[1]
            )

            return RiskAssessment(
                risk_id=f"geographic_risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                risk_type="geographic_risk",
                risk_level="high" if max_risk_score > 0.8 else "medium",
                confidence=max_risk_score,
                factors=[f"High risk in {max_risk_country}: {max_risk_score:.2f}"],
                impact_score=0.8,
                probability_score=max_risk_score,
                recommendations=[
                    f"Focus monitoring on {max_risk_country}",
                    "Analyze regional implications",
                    "Coordinate with regional experts",
                ],
                timestamp=datetime.now(),
            )

        return None

    async def _assess_temporal_risk(
        self, articles: List[ProcessedArticle]
    ) -> Optional[RiskAssessment]:
        """Assess temporal-based risks."""
        if len(articles) < 5:
            return None

        # Analyze recent vs historical patterns
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_articles = [
            a for a in articles if a.original.published_at >= recent_cutoff
        ]

        if len(recent_articles) > len(articles) * 0.5:  # High recent activity
            recent_sentiments = [
                a.sentiment for a in recent_articles if a.sentiment is not None
            ]
            if recent_sentiments:
                avg_recent_sentiment = statistics.mean(recent_sentiments)

                if avg_recent_sentiment < -0.2:  # Negative recent sentiment
                    return RiskAssessment(
                        risk_id=f"temporal_risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        risk_type="temporal_risk",
                        risk_level="medium",
                        confidence=0.6,
                        factors=["High recent activity with negative sentiment"],
                        impact_score=0.6,
                        probability_score=0.6,
                        recommendations=[
                            "Monitor for escalation patterns",
                            "Prepare rapid response protocols",
                            "Increase monitoring frequency",
                        ],
                        timestamp=datetime.now(),
                    )

        return None

    async def _assess_content_risk(
        self, articles: List[ProcessedArticle]
    ) -> Optional[RiskAssessment]:
        """Assess content-based risks."""
        high_risk_keywords = ["crisis", "emergency", "urgent", "breaking", "alert"]
        high_relevance_articles = [a for a in articles if a.relevance_score > 0.8]

        risk_articles = []
        for article in high_relevance_articles:
            if any(
                keyword in " ".join(article.keywords).lower()
                for keyword in high_risk_keywords
            ):
                risk_articles.append(article)

        if risk_articles:
            risk_ratio = len(risk_articles) / len(articles)

            return RiskAssessment(
                risk_id=f"content_risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                risk_type="content_risk",
                risk_level="high" if risk_ratio > 0.1 else "medium",
                confidence=risk_ratio,
                factors=[f"High-risk content detected: {len(risk_articles)} articles"],
                impact_score=0.8,
                probability_score=risk_ratio,
                recommendations=[
                    "Review high-risk content immediately",
                    "Assess potential escalation scenarios",
                    "Prepare crisis communication protocols",
                ],
                timestamp=datetime.now(),
            )

        return None

    async def _generate_summary(
        self,
        articles: List[ProcessedArticle],
        trends: List[TrendAnalysis],
        geographic_analysis: List[GeographicAnalysis],
        risk_assessments: List[RiskAssessment],
        period_days: int = 7,
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not articles:
            return {}

        # Basic statistics
        total_articles = len(articles)
        avg_sentiment = statistics.mean(
            [a.sentiment for a in articles if a.sentiment is not None]
        )
        avg_relevance = statistics.mean([a.relevance_score for a in articles])
        avg_quality = statistics.mean([a.quality_score for a in articles])

        # Top categories
        all_categories = []
        for article in articles:
            all_categories.extend(article.categories)
        top_categories = [cat for cat, count in Counter(all_categories).most_common(5)]

        # Risk summary
        high_risks = [
            r for r in risk_assessments if r.risk_level in ["high", "critical"]
        ]
        medium_risks = [r for r in risk_assessments if r.risk_level == "medium"]

        return {
            "total_articles": total_articles,
            "avg_sentiment": avg_sentiment,
            "avg_relevance": avg_relevance,
            "avg_quality": avg_quality,
            "top_categories": top_categories,
            "trends_count": len(trends),
            "countries_analyzed": len(geographic_analysis),
            "high_risks": len(high_risks),
            "medium_risks": len(medium_risks),
            "analysis_period": f"{period_days} days",
        }

    async def _generate_visualizations(
        self,
        articles: List[ProcessedArticle],
        trends: List[TrendAnalysis],
        geographic_analysis: List[GeographicAnalysis],
    ) -> Dict[str, Any]:
        """Generate visualization data."""
        visualizations = {}

        try:
            # Sentiment distribution
            sentiments = [a.sentiment for a in articles if a.sentiment is not None]
            if sentiments:
                fig_sentiment = go.Figure(data=[go.Histogram(x=sentiments, nbinsx=20)])
                fig_sentiment.update_layout(
                    title="Sentiment Distribution",
                    xaxis_title="Sentiment",
                    yaxis_title="Count",
                )
                visualizations["sentiment_distribution"] = fig_sentiment.to_json()

            # Geographic risk map
            if geographic_analysis:
                countries = [g.country_code for g in geographic_analysis]
                risk_scores = [g.risk_score for g in geographic_analysis]

                fig_map = go.Figure(
                    data=go.Choropleth(
                        locations=countries,
                        z=risk_scores,
                        locationmode="ISO-3166-1-alpha-2",
                        colorscale="Reds",
                        colorbar_title="Risk Score",
                    )
                )
                fig_map.update_layout(title="Geographic Risk Map")
                visualizations["geographic_risk_map"] = fig_map.to_json()

            # Trend analysis
            if trends:
                topics = [t.topic for t in trends[:10]]
                confidences = [t.confidence for t in trends[:10]]

                fig_trends = go.Figure(data=[go.Bar(x=topics, y=confidences)])
                fig_trends.update_layout(
                    title="Top Trends by Confidence",
                    xaxis_title="Topic",
                    yaxis_title="Confidence",
                )
                visualizations["trend_analysis"] = fig_trends.to_json()

        except Exception as e:
            logger.warning("Visualization generation failed", error=str(e))

        return visualizations

    def get_analytics_metrics(self) -> Dict[str, Any]:
        """Get analytics performance metrics."""
        if not self.metrics:
            return {}

        return {
            "total_analyses": len(self.metrics),
            "average_processing_time": statistics.mean(
                [m.processing_time or 0 for m in self.metrics]
            ),
            "total_articles_processed": sum(m.input_count for m in self.metrics),
            "analysis_types": {
                analysis_type.value: len(
                    [m for m in self.metrics if m.analysis_type == analysis_type]
                )
                for analysis_type in AnalysisType
            },
        }

    def clear_metrics(self):
        """Clear analytics metrics."""
        self.metrics.clear()
