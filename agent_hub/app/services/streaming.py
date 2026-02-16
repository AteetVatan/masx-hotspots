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
Real-time Data Streaming Service for MASX-HOTSPOTS Agentic AI System.

Provides real-time data streaming capabilities:
- WebSocket connections for live data feeds
- Real-time article processing and analysis
- Live trend detection and alerts
- Streaming analytics and metrics
- Event-driven data processing

Features:
- Async WebSocket server
- Connection management and authentication
- Real-time data broadcasting
- Event filtering and routing
- Performance monitoring
- Scalable architecture
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

import structlog

# from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, validator

from app.core.exceptions import StreamingError, AuthenticationError
from app.services.data_sources import DataSourcesService, Article
from app.services.data_processing import DataProcessingPipeline, ProcessedArticle
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)


class StreamEventType(str, Enum):
    """Types of streaming events."""

    ARTICLE_UPDATE = "article_update"
    TREND_ALERT = "trend_alert"
    ANALYSIS_UPDATE = "analysis_update"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class StreamFilter(BaseModel):
    """Filter configuration for data streams."""

    categories: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    min_relevance: Optional[float] = 0.0
    min_quality: Optional[float] = 0.0
    languages: Optional[List[str]] = None
    event_types: Optional[List[StreamEventType]] = None

    def matches_article(self, article: ProcessedArticle) -> bool:
        """Check if article matches filter criteria."""
        # Category filter
        if self.categories and not any(
            cat in article.categories for cat in self.categories
        ):
            return False

        # Country filter
        if self.countries and not any(
            country in article.original.country for country in self.countries
        ):
            return False

        # Keyword filter
        if self.keywords and not any(
            keyword.lower() in " ".join(article.keywords).lower()
            for keyword in self.keywords
        ):
            return False

        # Relevance filter
        if self.min_relevance and article.relevance_score < self.min_relevance:
            return False

        # Quality filter
        if self.min_quality and article.quality_score < self.min_quality:
            return False

        # Language filter
        if self.languages and article.language not in self.languages:
            return False

        return True


@dataclass
class StreamEvent:
    """Streaming event model."""

    event_id: str
    event_type: StreamEventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "masx_system"
    priority: int = 1  # 1=low, 2=medium, 3=high

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())


# @dataclass
# class ClientConnection:
#     """Client WebSocket connection."""

#     websocket: WebSocket
#     client_id: str
#     filters: StreamFilter
#     connected_at: datetime
#     last_activity: datetime
#     subscription_topics: Set[str] = field(default_factory=set)
#     is_authenticated: bool = False

#     def update_activity(self):
#         """Update last activity timestamp."""
#         self.last_activity = datetime.now()


class StreamingService:
    """Real-time data streaming service."""

    def __init__(self):
        self.settings = get_settings()
        self.clients: Dict[str, ClientConnection] = {}
        self.data_sources: Optional[DataSourcesService] = None
        self.processing_pipeline: Optional[DataProcessingPipeline] = None
        self.streaming_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.event_handlers: Dict[StreamEventType, List[Callable]] = defaultdict(list)
        self.metrics = {
            "total_events_sent": 0,
            "active_connections": 0,
            "events_per_second": 0,
            "last_event_time": None,
        }

    async def start(self):
        """Start the streaming service."""
        if self.is_running:
            return

        self.is_running = True
        self.data_sources = DataSourcesService()
        self.processing_pipeline = DataProcessingPipeline()

        # Start background tasks
        self.streaming_task = asyncio.create_task(self._stream_data_loop())

        logger.info("Streaming service started")

    async def stop(self):
        """Stop the streaming service."""
        self.is_running = False

        if self.streaming_task:
            self.streaming_task.cancel()
            try:
                await self.streaming_task
            except asyncio.CancelledError:
                pass

        # Close all client connections
        for client in list(self.clients.values()):
            await self._disconnect_client(client.client_id)

        logger.info("Streaming service stopped")

    # async def connect_client(
    #     self,
    #     websocket: WebSocket,
    #     client_id: str,
    #     filters: Optional[StreamFilter] = None,
    # ) -> str:
    #     """Connect a new client."""
    #     await websocket.accept()

    #     if not filters:
    #         filters = StreamFilter()

    #     connection = ClientConnection(
    #         websocket=websocket,
    #         client_id=client_id,
    #         filters=filters,
    #         connected_at=datetime.now(),
    #         last_activity=datetime.now(),
    #     )

    #     self.clients[client_id] = connection
    #     self.metrics["active_connections"] = len(self.clients)

    #     # Send welcome message
    #     welcome_event = StreamEvent(
    #         event_type=StreamEventType.SYSTEM_STATUS,
    #         timestamp=datetime.now(),
    #         data={
    #         "message": "Connected to MASX streaming service",
    #         "client_id": client_id,
    #         "filters": filters.dict(),
    #         },
    #     )

    #     await self._send_event_to_client(client_id, welcome_event)
    #     logger.info("Client connected", client_id=client_id)

    #     return client_id

    # async def disconnect_client(self, client_id: str):
    #     """Disconnect a client."""
    #     await self._disconnect_client(client_id)

    # async def _disconnect_client(self, client_id: str):
    #     """Internal client disconnection."""
    #     if client_id in self.clients:
    #         client = self.clients[client_id]
    #         try:
    #             await client.websocket.close()
    #     except Exception:
    #         pass

    #         del self.clients[client_id]
    #         self.metrics["active_connections"] = len(self.clients)
    #         logger.info("Client disconnected", client_id=client_id)

    # async def _send_event_to_client(self, client_id: str, event: StreamEvent):
    #     """Send event to specific client."""
    #     if client_id not in self.clients:
    #         return

    #     client = self.clients[client_id]

    #     try:
    #         # Check if event matches client filters
    #         if event.event_type == StreamEventType.ARTICLE_UPDATE:
    #         article = event.data.get("article")
    #         if article and not client.filters.matches_article(article):
    #             return

    #         # Send event
    #         event_data = {
    #         "event_id": event.event_id,
    #         "event_type": event.event_type.value,
    #         "timestamp": event.timestamp.isoformat(),
    #         "data": event.data,
    #         "source": event.source,
    #         "priority": event.priority,
    #         }

    #         await client.websocket.send_text(json.dumps(event_data))
    #         client.update_activity()

    #         # Update metrics
    #         self.metrics["total_events_sent"] += 1
    #         self.metrics["last_event_time"] = datetime.now()

    #     except WebSocketDisconnect:
    #         await self._disconnect_client(client_id)
    #     except Exception as e:
    #         logger.error(
    #         "Failed to send event to client", client_id=client_id, error=str(e)
    #         )

    async def broadcast_event(
        self, event: StreamEvent, filter_func: Optional[Callable] = None
    ):
        """Broadcast event to all connected clients."""
        tasks = []

        for client_id in list(self.clients.keys()):
            if filter_func and not filter_func(client_id):
                continue

            task = asyncio.create_task(self._send_event_to_client(client_id, event))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _stream_data_loop(self):
        """Main data streaming loop."""
        async with self.data_sources:
            async for articles in self.data_sources.stream_articles(
                interval_seconds=300
            ):
                try:
                    # Process articles
                    processed_articles = (
                        await self.processing_pipeline.process_articles(articles)
                    )

                    # Send article updates
                    for article in processed_articles:
                        event = StreamEvent(
                            event_type=StreamEventType.ARTICLE_UPDATE,
                            timestamp=datetime.now(),
                            data={"article": article.dict()},
                        )
                        await self.broadcast_event(event)

                    # Analyze trends periodically
                    if len(processed_articles) > 10:
                        trends = await self.processing_pipeline.analyze_trends(
                            processed_articles
                        )

                        for trend in trends:
                            if trend.confidence > 0.7:  # High confidence trends
                                event = StreamEvent(
                                    event_type=StreamEventType.TREND_ALERT,
                                    timestamp=datetime.now(),
                                    data={"trend": trend.dict()},
                                    priority=3,
                                )
                                await self.broadcast_event(event)

                    # Send heartbeat
                    heartbeat_event = StreamEvent(
                        event_type=StreamEventType.HEARTBEAT,
                        timestamp=datetime.now(),
                        data={"processed_count": len(processed_articles)},
                    )
                    await self.broadcast_event(heartbeat_event)

                except Exception as e:
                    logger.error("Error in data streaming loop", error=str(e))
                    await asyncio.sleep(60)  # Wait before retry

    async def handle_client_message(self, client_id: str, message: str):
        """Handle incoming client message."""
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "subscribe":
                topics = data.get("topics", [])
                await self._subscribe_client(client_id, topics)

            elif message_type == "unsubscribe":
                topics = data.get("topics", [])
                await self._unsubscribe_client(client_id, topics)

            elif message_type == "update_filters":
                filters_data = data.get("filters", {})
                await self._update_client_filters(client_id, filters_data)

            elif message_type == "ping":
                await self._send_pong(client_id)

            else:
                logger.warning(
                    "Unknown message type", client_id=client_id, type=message_type
                )

        except json.JSONDecodeError:
            logger.warning("Invalid JSON message", client_id=client_id)
        except Exception as e:
            logger.error(
                "Error handling client message", client_id=client_id, error=str(e)
            )

    async def _subscribe_client(self, client_id: str, topics: List[str]):
        """Subscribe client to topics."""
        if client_id not in self.clients:
            return

        client = self.clients[client_id]
        client.subscription_topics.update(topics)

        event = StreamEvent(
            event_type=StreamEventType.SYSTEM_STATUS,
            timestamp=datetime.now(),
            data={
                "message": f"Subscribed to topics: {topics}",
                "topics": list(client.subscription_topics),
            },
        )

        await self._send_event_to_client(client_id, event)

    async def _unsubscribe_client(self, client_id: str, topics: List[str]):
        """Unsubscribe client from topics."""
        if client_id not in self.clients:
            return

        client = self.clients[client_id]
        client.subscription_topics.difference_update(topics)

        event = StreamEvent(
            event_type=StreamEventType.SYSTEM_STATUS,
            timestamp=datetime.now(),
            data={
                "message": f"Unsubscribed from topics: {topics}",
                "topics": list(client.subscription_topics),
            },
        )

        await self._send_event_to_client(client_id, event)

    async def _update_client_filters(
        self, client_id: str, filters_data: Dict[str, Any]
    ):
        """Update client filters."""
        if client_id not in self.clients:
            return

        client = self.clients[client_id]
        new_filters = StreamFilter(**filters_data)
        client.filters = new_filters

        event = StreamEvent(
            event_type=StreamEventType.SYSTEM_STATUS,
            timestamp=datetime.now(),
            data={"message": "Filters updated", "filters": new_filters.dict()},
        )

        await self._send_event_to_client(client_id, event)

    async def _send_pong(self, client_id: str):
        """Send pong response to ping."""
        event = StreamEvent(
            event_type=StreamEventType.HEARTBEAT,
            timestamp=datetime.now(),
            data={"type": "pong"},
        )

        await self._send_event_to_client(client_id, event)

    def add_event_handler(self, event_type: StreamEventType, handler: Callable):
        """Add event handler for specific event type."""
        self.event_handlers[event_type].append(handler)

    async def _trigger_event_handlers(self, event: StreamEvent):
        """Trigger event handlers for an event."""
        handlers = self.event_handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "Event handler failed", handler=handler.__name__, error=str(e)
                )

    def get_service_status(self) -> Dict[str, Any]:
        """Get streaming service status."""
        return {
            "is_running": self.is_running,
            "active_connections": len(self.clients),
            "metrics": self.metrics.copy(),
            "clients": [
                {
                    "client_id": client.client_id,
                    "connected_at": client.connected_at.isoformat(),
                    "last_activity": client.last_activity.isoformat(),
                    "subscription_topics": list(client.subscription_topics),
                    "is_authenticated": client.is_authenticated,
                }
                for client in self.clients.values()
            ],
        }

    async def cleanup_inactive_connections(self, max_idle_minutes: int = 30):
        """Clean up inactive client connections."""
        cutoff_time = datetime.now() - timedelta(minutes=max_idle_minutes)
        inactive_clients = [
            client_id
            for client_id, client in self.clients.items()
            if client.last_activity < cutoff_time
        ]

        for client_id in inactive_clients:
            logger.info("Cleaning up inactive connection", client_id=client_id)
            await self._disconnect_client(client_id)


# class WebSocketManager:
#     """WebSocket connection manager for FastAPI."""

#     def __init__(self, streaming_service: StreamingService):
#         self.streaming_service = streaming_service

#     async def connect(self, websocket: WebSocket, client_id: str):
#         """Handle WebSocket connection."""
#         await self.streaming_service.connect_client(websocket, client_id)

#         try:
#             while True:
#                 message = await websocket.receive_text()
#                 await self.streaming_service.handle_client_message(client_id, message)
#         except WebSocketDisconnect:
#             await self.streaming_service.disconnect_client(client_id)
#         except Exception as e:
#             logger.error("WebSocket error", client_id=client_id, error=str(e))
#             await self.streaming_service.disconnect_client(client_id)
