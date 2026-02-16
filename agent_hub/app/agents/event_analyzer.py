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
Event Analyzer Agent for MASX-HOTSPOTS Agentic AI System.

This agent is responsible for:
- Analyzing merged articles and events
- Clustering related items into hotspots
- Summarizing clusters
- Handling analysis errors
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseAgent, AgentResult
from ..core.state import AgentState
from ..core.exceptions import AgentException
from ..config.logging_config import get_agent_logger


class EventAnalyzer(BaseAgent):
    """
    Event Analyzer Agent for clustering and summarizing events.

    Responsibilities:
    - Analyze merged articles and events
    - Cluster related items into hotspots
    - Summarize clusters
    - Handle analysis errors
    """

    def __init__(self):
        """Initialize the Event Analyzer agent."""
        super().__init__("EventAnalyzer")
        self.logger = get_agent_logger("EventAnalyzer")

    async def analyze_events(
        self, merged_articles: List[Dict[str, Any]], merged_events: List[Dict[str, Any]]
    ) -> AgentResult:
        """
        Analyze and cluster merged articles and events.

        Args:
            merged_articles: List of merged news articles
            merged_events: List of merged GDELT events

        Returns:
            AgentResult: Contains clustered hotspots and summaries
        """
        try:
            self.logger.info(
                "Analyzing events and clustering into hotspots",
                article_count=len(merged_articles),
                event_count=len(merged_events),
            )

            # Stub: group all items into a single cluster
            all_items = merged_articles + merged_events
            cluster = {
                "hotspot_id": "hotspot-1",
                "items": all_items,
                "summary": self._summarize_cluster(all_items),
                "cluster_size": len(all_items),
            }

            result = {
                "hotspots": [cluster],
                "total_hotspots": 1,
                "total_items": len(all_items),
                "timestamp": datetime.utcnow().isoformat(),
            }

            self.logger.info(
                "Event analysis completed", total_hotspots=1, total_items=len(all_items)
            )

            return AgentResult(
                success=True,
                data=result,
                metadata={"agent": self.name, "timestamp": datetime.utcnow()},
            )

        except Exception as e:
            self.logger.error(f"Event analysis failed: {e}")
            raise AgentException(f"Event analysis failed: {str(e)}")

    def _summarize_cluster(self, items: List[Dict[str, Any]]) -> str:
        """Stub summary for a cluster of items."""
        if not items:
            return "No items to summarize."
        titles = [item.get("title", "") for item in items if item.get("title")]
        return f"Cluster of {len(items)} items. Titles: " + "; ".join(titles[:3])
