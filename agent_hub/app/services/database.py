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
Database service for MASX-HOTSPOTS Agentic AI System.

Provides Supabase integration with:
- Connection management and pooling
- CRUD operations for hotspots, articles, and embeddings
- Vector similarity search using pgvector
- Transaction management and error handling
- Performance monitoring and logging

Usage:
    from app.services.database import DatabaseService

    db = DatabaseService()
    hotspots = await db.get_hotspots(limit=10)
    await db.store_hotspot(hotspot_data)
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

import asyncpg
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from ..core.exceptions import DatabaseException, ConfigurationException
from ..core.utils import measure_execution_time
from ..config.settings import get_settings
from ..config.logging_config import get_service_logger


@dataclass
class HotspotRecord:
    """Database record for a hotspot."""

    id: Optional[str] = None
    title: str = ""
    summary: str = ""
    domains: List[str] = None
    entities: Dict[str, List[str]] = None
    articles: List[str] = None
    embedding: Optional[List[float]] = None
    confidence_score: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    run_id: Optional[str] = None

    def __post_init__(self):
        if self.domains is None:
            self.domains = []
        if self.entities is None:
            self.entities = {}
        if self.articles is None:
            self.articles = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class ArticleRecord:
    """Database record for an article."""

    id: Optional[str] = None
    url: str = ""
    title: str = ""
    content: str = ""
    source: str = ""
    language: str = "en"
    published_at: Optional[datetime] = None
    embedding: Optional[List[float]] = None
    entities: Dict[str, List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class WorkflowLogRecord:
    """Database record for workflow logs."""

    id: Optional[str] = None
    run_id: str = ""
    agent: str = ""
    action: str = ""
    status: str = "success"
    input_data: Dict[str, Any] = None
    output_data: Dict[str, Any] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.input_data is None:
            self.input_data = {}
        if self.output_data is None:
            self.output_data = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class DatabaseService:
    """
    Database service for Supabase integration.

    Provides:
    - Connection management and pooling
    - CRUD operations for all data types
    - Vector similarity search
    - Transaction management
    - Performance monitoring
    """

    def __init__(self):
        """Initialize the database service."""
        self.settings = get_settings()
        self.logger = get_service_logger("DatabaseService")
        self.client: Optional[Client] = None
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_params = {}
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize database connection parameters."""
        try:
            # Supabase configuration
            if not self.settings.supabase_url or not self.settings.supabase_anon_key:
                raise ConfigurationException("Supabase URL and key are required")

            # Database Configuration (Supabase)
            # SUPABASE_URL=https://your-project.supabase.co
            # SUPABASE_ANON_KEY=your_supabase_anon_key_here
            # SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
            # SUPABASE_DB_PASSWORD=your_database_password_here
            # SUPABASE_DB_URL=your_database_connection_url

            self._connection_params = {
                "supabase_url": self.settings.supabase_url,
                "supabase_key": self.settings.supabase_anon_key,
                "database_url": self.settings.supabase_db_url,
                "max_connections": self.settings.database_max_connections or 10,
                "min_connections": self.settings.database_min_connections or 1,
            }

            # test connection
            # import asyncio
            # asyncio.run(self.connect())

            self.logger.info("Database connection parameters initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise DatabaseException(f"Database initialization failed: {str(e)}")

    async def connect(self):
        """Establish database connections."""
        try:
            # Initialize Supabase client
            options = ClientOptions(
                schema="public", headers={"X-Client-Info": "masx-ai-system"}
            )

            self.client = create_client(
                self._connection_params["supabase_url"],
                self._connection_params["supabase_key"],
                options=options,
            )

            # Validate and establish PostgreSQL pool
            database_url = self._connection_params.get("database_url")
            if database_url:
                if not self.is_valid_postgres_url(database_url):
                    raise ConfigurationException(
                        f"Invalid PostgreSQL connection URL: {database_url}"
                    )

                # Initialize connection pool for direct PostgreSQL access
                self.pool = await asyncpg.create_pool(
                    database_url,
                    min_size=self._connection_params["min_connections"],
                    max_size=self._connection_params["max_connections"],
                    command_timeout=60,
                    server_settings={"application_name": "masx_ai_system"},
                )

            self.logger.info("Database connections established successfully")

        except Exception as e:
            self.logger.error(f"Failed to establish database connections: {e}")
            raise DatabaseException(f"Database connection failed: {str(e)}")

    async def disconnect(self):
        """Close database connections."""
        try:
            if self.pool:
                await self.pool.close()
                self.pool = None

            if self.client:
                self.client = None

            self.logger.info("Database connections closed")

        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    # Hotspot operations
    async def store_hotspot(self, hotspot: HotspotRecord) -> str:
        """
        Store a hotspot in the database.

        Args:
            hotspot: Hotspot record to store

        Returns:
            str: ID of the stored hotspot
        """
        with measure_execution_time("store_hotspot"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                # Prepare data for insertion
                data = asdict(hotspot)
                data["updated_at"] = datetime.utcnow().isoformat()

                # Remove None values
                data = {k: v for k, v in data.items() if v is not None}

                # Insert using Supabase
                result = self.client.table("hotspots").insert(data).execute()

                if result.data:
                    hotspot_id = result.data[0]["id"]
                    self.logger.info(f"Hotspot stored successfully: {hotspot_id}")
                    return hotspot_id
                else:
                    raise DatabaseException(
                        "Failed to store hotspot - no data returned"
                    )

            except Exception as e:
                self.logger.error(f"Failed to store hotspot: {e}")
                raise DatabaseException(f"Hotspot storage failed: {str(e)}")

    async def get_hotspot(self, hotspot_id: str) -> Optional[HotspotRecord]:
        """
        Retrieve a hotspot by ID.

        Args:
            hotspot_id: ID of the hotspot to retrieve

        Returns:
            HotspotRecord or None if not found
        """
        with measure_execution_time("get_hotspot"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                result = (
                    self.client.table("hotspots")
                    .select("*")
                    .eq("id", hotspot_id)
                    .execute()
                )

                if result.data:
                    data = result.data[0]
                    return HotspotRecord(**data)
                else:
                    return None

            except Exception as e:
                self.logger.error(f"Failed to retrieve hotspot {hotspot_id}: {e}")
                raise DatabaseException(f"Hotspot retrieval failed: {str(e)}")

    async def get_hotspots(
        self,
        limit: int = 100,
        offset: int = 0,
        domains: Optional[List[str]] = None,
        run_id: Optional[str] = None,
    ) -> List[HotspotRecord]:
        """
        Retrieve hotspots with optional filtering.

        Args:
            limit: Maximum number of hotspots to return
            offset: Number of hotspots to skip
            domains: Filter by domains
            run_id: Filter by run ID

        Returns:
            List of hotspot records
        """
        with measure_execution_time("get_hotspots"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                query = self.client.table("hotspots").select("*")

                # Apply filters
                if domains:
                    query = query.overlaps("domains", domains)

                if run_id:
                    query = query.eq("run_id", run_id)

                # Apply pagination and ordering
                result = (
                    query.order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )

                hotspots = [HotspotRecord(**data) for data in result.data]
                self.logger.info(f"Retrieved {len(hotspots)} hotspots")

                return hotspots

            except Exception as e:
                self.logger.error(f"Failed to retrieve hotspots: {e}")
                raise DatabaseException(f"Hotspots retrieval failed: {str(e)}")

    async def search_hotspots_by_similarity(
        self, embedding: List[float], limit: int = 10, similarity_threshold: float = 0.7
    ) -> List[HotspotRecord]:
        """
        Search hotspots by vector similarity.

        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of similar hotspot records
        """
        with measure_execution_time("search_hotspots_by_similarity"):
            try:
                if not self.pool:
                    raise DatabaseException("Direct database connection not available")

                async with self.pool.acquire() as conn:
                    # Use pgvector for similarity search
                    query = """
                    SELECT *, 
                           (embedding <=> $1) as similarity
                    FROM hotspots 
                    WHERE embedding IS NOT NULL
                    AND (embedding <=> $1) < $2
                    ORDER BY embedding <=> $1
                    LIMIT $3
                    """

                    rows = await conn.fetch(
                        query, embedding, 1 - similarity_threshold, limit
                    )

                    hotspots = []
                    for row in rows:
                        data = dict(row)
                        # Remove similarity score from data
                        similarity = data.pop("similarity")
                        hotspot = HotspotRecord(**data)
                        # Add similarity as metadata
                        hotspot.confidence_score = 1 - similarity
                        hotspots.append(hotspot)

                    self.logger.info(f"Found {len(hotspots)} similar hotspots")
                    return hotspots

            except Exception as e:
                self.logger.error(f"Failed to search hotspots by similarity: {e}")
                raise DatabaseException(f"Similarity search failed: {str(e)}")

    async def update_hotspot(self, hotspot_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a hotspot.

        Args:
            hotspot_id: ID of the hotspot to update
            updates: Dictionary of fields to update

        Returns:
            bool: True if update was successful
        """
        with measure_execution_time("update_hotspot"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                updates["updated_at"] = datetime.utcnow().isoformat()

                result = (
                    self.client.table("hotspots")
                    .update(updates)
                    .eq("id", hotspot_id)
                    .execute()
                )

                success = len(result.data) > 0
                if success:
                    self.logger.info(f"Hotspot {hotspot_id} updated successfully")
                else:
                    self.logger.warning(f"No hotspot found with ID {hotspot_id}")

                return success

            except Exception as e:
                self.logger.error(f"Failed to update hotspot {hotspot_id}: {e}")
                raise DatabaseException(f"Hotspot update failed: {str(e)}")

    async def delete_hotspot(self, hotspot_id: str) -> bool:
        """
        Delete a hotspot.

        Args:
            hotspot_id: ID of the hotspot to delete

        Returns:
            bool: True if deletion was successful
        """
        with measure_execution_time("delete_hotspot"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                result = (
                    self.client.table("hotspots")
                    .delete()
                    .eq("id", hotspot_id)
                    .execute()
                )

                success = len(result.data) > 0
                if success:
                    self.logger.info(f"Hotspot {hotspot_id} deleted successfully")
                else:
                    self.logger.warning(f"No hotspot found with ID {hotspot_id}")

                return success

            except Exception as e:
                self.logger.error(f"Failed to delete hotspot {hotspot_id}: {e}")
                raise DatabaseException(f"Hotspot deletion failed: {str(e)}")

    # Article operations
    async def store_article(self, article: ArticleRecord) -> str:
        """
        Store an article in the database.

        Args:
            article: Article record to store

        Returns:
            str: ID of the stored article
        """
        with measure_execution_time("store_article"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                data = asdict(article)
                data["updated_at"] = datetime.utcnow().isoformat()
                data = {k: v for k, v in data.items() if v is not None}

                result = self.client.table("articles").insert(data).execute()

                if result.data:
                    article_id = result.data[0]["id"]
                    self.logger.info(f"Article stored successfully: {article_id}")
                    return article_id
                else:
                    raise DatabaseException(
                        "Failed to store article - no data returned"
                    )

            except Exception as e:
                self.logger.error(f"Failed to store article: {e}")
                raise DatabaseException(f"Article storage failed: {str(e)}")

    async def get_articles(
        self,
        limit: int = 100,
        offset: int = 0,
        language: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[ArticleRecord]:
        """
        Retrieve articles with optional filtering.

        Args:
            limit: Maximum number of articles to return
            offset: Number of articles to skip
            language: Filter by language
            source: Filter by source

        Returns:
            List of article records
        """
        with measure_execution_time("get_articles"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                query = self.client.table("articles").select("*")

                if language:
                    query = query.eq("language", language)

                if source:
                    query = query.eq("source", source)

                result = (
                    query.order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )

                articles = [ArticleRecord(**data) for data in result.data]
                self.logger.info(f"Retrieved {len(articles)} articles")

                return articles

            except Exception as e:
                self.logger.error(f"Failed to retrieve articles: {e}")
                raise DatabaseException(f"Articles retrieval failed: {str(e)}")

    # Workflow log operations
    async def store_workflow_log(self, log: WorkflowLogRecord) -> str:
        """
        Store a workflow log entry.

        Args:
            log: Workflow log record to store

        Returns:
            str: ID of the stored log entry
        """
        with measure_execution_time("store_workflow_log"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                data = asdict(log)
                data = {k: v for k, v in data.items() if v is not None}

                result = self.client.table("workflow_logs").insert(data).execute()

                if result.data:
                    log_id = result.data[0]["id"]
                    self.logger.debug(f"Workflow log stored: {log_id}")
                    return log_id
                else:
                    raise DatabaseException(
                        "Failed to store workflow log - no data returned"
                    )

            except Exception as e:
                self.logger.error(f"Failed to store workflow log: {e}")
                raise DatabaseException(f"Workflow log storage failed: {str(e)}")

    async def get_workflow_logs(
        self,
        run_id: Optional[str] = None,
        agent: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorkflowLogRecord]:
        """
        Retrieve workflow logs with optional filtering.

        Args:
            run_id: Filter by run ID
            agent: Filter by agent
            status: Filter by status
            limit: Maximum number of logs to return
            offset: Number of logs to skip

        Returns:
            List of workflow log records
        """
        with measure_execution_time("get_workflow_logs"):
            try:
                if not self.client:
                    raise DatabaseException("Database not connected")

                query = self.client.table("workflow_logs").select("*")

                if run_id:
                    query = query.eq("run_id", run_id)

                if agent:
                    query = query.eq("agent", agent)

                if status:
                    query = query.eq("status", status)

                result = (
                    query.order("created_at", desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )

                logs = [WorkflowLogRecord(**data) for data in result.data]
                self.logger.info(f"Retrieved {len(logs)} workflow logs")

                return logs

            except Exception as e:
                self.logger.error(f"Failed to retrieve workflow logs: {e}")
                raise DatabaseException(f"Workflow logs retrieval failed: {str(e)}")

    # Utility operations
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        try:
            if not self.pool:
                raise DatabaseException("Direct database connection not available")

            async with self.pool.acquire() as conn:
                stats = {}

                # Count records in each table
                tables = ["hotspots", "articles", "workflow_logs"]
                for table in tables:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = count

                # Get recent activity
                recent_hotspots = await conn.fetchval(
                    "SELECT COUNT(*) FROM hotspots WHERE created_at > NOW() - INTERVAL '24 hours'"
                )
                stats["recent_hotspots_24h"] = recent_hotspots

                recent_logs = await conn.fetchval(
                    "SELECT COUNT(*) FROM workflow_logs WHERE created_at > NOW() - INTERVAL '24 hours'"
                )
                stats["recent_logs_24h"] = recent_logs

                return stats

        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            raise DatabaseException(f"Database stats retrieval failed: {str(e)}")

    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Clean up old data from the database.

        Args:
            days: Number of days to keep data for

        Returns:
            Dictionary with cleanup statistics
        """
        try:
            if not self.pool:
                raise DatabaseException("Direct database connection not available")

            async with self.pool.acquire() as conn:
                cleanup_stats = {}

                # Clean up old workflow logs
                deleted_logs = await conn.execute(
                    "DELETE FROM workflow_logs WHERE created_at < NOW() - INTERVAL $1 days",
                    days,
                )
                cleanup_stats["deleted_logs"] = int(deleted_logs.split()[-1])

                # Clean up old articles (keep for longer)
                deleted_articles = await conn.execute(
                    "DELETE FROM articles WHERE created_at < NOW() - INTERVAL $1 days",
                    days * 2,
                )
                cleanup_stats["deleted_articles"] = int(deleted_articles.split()[-1])

                self.logger.info(f"Cleanup completed: {cleanup_stats}")
                return cleanup_stats

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            raise DatabaseException(f"Data cleanup failed: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.

        Returns:
            Dictionary with health check results
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": {},
            }

            # Check Supabase connection
            if self.client:
                try:
                    # Simple query to test connection
                    result = (
                        self.client.table("hotspots").select("id").limit(1).execute()
                    )
                    health_status["connections"]["supabase"] = "connected"
                except Exception as e:
                    health_status["connections"]["supabase"] = f"error: {str(e)}"
                    health_status["status"] = "unhealthy"
            else:
                health_status["connections"]["supabase"] = "not_initialized"
                health_status["status"] = "unhealthy"

            # Check direct database connection
            if self.pool:
                try:
                    async with self.pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                    health_status["connections"]["postgres"] = "connected"
                except Exception as e:
                    health_status["connections"]["postgres"] = f"error: {str(e)}"
                    health_status["status"] = "unhealthy"
            else:
                health_status["connections"]["postgres"] = "not_initialized"

            return health_status

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def is_valid_postgres_url(self, url: str) -> bool:
        return bool(re.match(r"^postgres(?:ql)?://.+:.+@.+:\d+/.+", url))
