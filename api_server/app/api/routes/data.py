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
Data retrieval endpoints for MASX-HOTSPOTS Agentic AI System.

This module provides RESTful API endpoints for accessing flashpoint and feed data
from the Supabase database with built-in rate limiting and pagination support.

Key Features:
- Flashpoint data retrieval with paging
- Feed data retrieval with paging
- Analytics and statistics
- Search and filtering capabilities
- Rate limiting (60 requests per minute)
- Health monitoring

Example Usage:
    # Get all flashpoints (page 1, 50 items)
    GET /api/data/flashpoints?page=1&page_size=50

    # Get feeds for specific flashpoint
    GET /api/data/flashpoints/123e4567-e89b-12d3-a456-426614174000/feeds?page=1&page_size=25

    # Get all feeds with filtering
    GET /api/data/feeds?page=1&page_size=100&language=en&domain=news.com

    # Check rate limit status
    GET /api/data/rate-limit

    # Get statistics
    GET /api/data/stats?date=2025-01-20
"""

# Standard library imports
from typing import Any, Optional, List
from datetime import datetime
from collections import defaultdict
import json
import threading
import time

# Third-party imports
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Local imports
from ...config.logging_config import get_api_logger
from ...config.settings import get_settings
from ...core.exceptions import DatabaseException, ConfigurationException

# Initialize router and logger
router = APIRouter()
logger = get_api_logger("DataRoutes")

# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================

# Rate limiting settings - 1000 requests per minute per client IP
RATE_LIMIT_REQUESTS = 1000  # Maximum requests allowed
RATE_LIMIT_WINDOW = 60  # Time window in seconds (1 minute)

# Global storage for rate limiting (client IP -> list of request timestamps)
client_requests = defaultdict(list)
rate_limit_lock = threading.RLock()  # Thread-safe lock for concurrent access

# =============================================================================
# PYDANTIC MODELS FOR API RESPONSES
# =============================================================================


class FlashpointResponse(BaseModel):
    """Response model for flashpoint data."""

    id: str
    title: str
    description: str
    entities: List[str]
    domains: List[str]
    run_id: Optional[str]
    created_at: str
    updated_at: str


class FeedResponse(BaseModel):
    """Response model for feed data."""

    id: str
    flashpoint_id: str
    url: str
    title: str
    seendate: Optional[str]
    domain: Optional[str]
    language: Optional[str]
    sourcecountry: Optional[str]
    description: Optional[str]
    image: Optional[str]
    created_at: str
    updated_at: str


class PaginatedResponse(BaseModel):
    """Wrapper for paginated API responses."""

    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class RateLimitResponse(BaseModel):
    """Response model for rate limit information."""

    remaining: int
    reset_time: str
    limit: int


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


async def get_supabase_client() -> Client:
    """
    Create and return a configured Supabase client.

    Returns:
        Client: Configured Supabase client instance

    Raises:
        ConfigurationException: If Supabase credentials are missing
    """
    settings = get_settings()

    # Validate required configuration
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise ConfigurationException("Supabase URL and key are required")

    # Configure client options
    options = ClientOptions(
        schema="public", headers={"X-Client-Info": "masx-ai-system"}
    )

    # Create and return client
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=options,
    )

    return client


def get_daily_table_name(base: str, date: Optional[datetime] = None) -> str:
    """
    Generate daily table name using the format: base_YYYYMMDD.

    Args:
        base: Base table name (e.g., 'flash_point', 'feed_entries')
        date: Target date (defaults to current UTC date)

    Returns:
        str: Formatted table name
    """
    date = date or datetime.utcnow()
    return f"{base}_{date.strftime('%Y%m%d')}"


def parse_json_field(field_value: Any) -> List[str]:
    """
    Safely parse JSON field that might be stored as string or list.

    Args:
        field_value: Field value that could be JSON string or list

    Returns:
        List[str]: Parsed list of strings
    """
    if isinstance(field_value, str):
        try:
            return json.loads(field_value)
        except json.JSONDecodeError:
            return []
    elif isinstance(field_value, list):
        return field_value
    else:
        return []


# =============================================================================
# RATE LIMITING FUNCTIONS
# =============================================================================


async def check_rate_limit(request: Request) -> RateLimitResponse:
    """
    Check and enforce rate limiting for the incoming request.

    This function implements a sliding window rate limiter that tracks
    requests per client IP address within a 1-minute window.

    Args:
        request: FastAPI request object

    Returns:
        RateLimitResponse: Rate limit information

    Raises:
        HTTPException: 429 status when rate limit is exceeded
    """
    client_ip = request.client.host

    with rate_limit_lock:
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Get client's request history and clean expired entries
        client_history = client_requests[client_ip]
        client_history = [
            req_time for req_time in client_history if req_time >= window_start
        ]
        client_requests[client_ip] = client_history

        # Calculate remaining requests
        remaining = max(0, RATE_LIMIT_REQUESTS - len(client_history))

        # Calculate reset time (when oldest request expires)
        reset_time = None
        if client_history:
            oldest_request = min(client_history)
            reset_time = datetime.fromtimestamp(oldest_request + RATE_LIMIT_WINDOW)

        # If client has requests remaining, add current request
        if remaining > 0:
            client_history.append(now)
            client_requests[client_ip] = client_history
            remaining -= 1

        # Raise exception if rate limit exceeded
        if remaining <= 0:
            raise HTTPException(
                status_code=429, detail=f"Rate limit exceeded. Reset time: {reset_time}"
            )

        return RateLimitResponse(
            remaining=remaining,
            reset_time=reset_time.isoformat() if reset_time else "",
            limit=RATE_LIMIT_REQUESTS,
        )


# =============================================================================
# API ENDPOINTS
# =============================================================================


@router.get("/flashpoints", response_model=PaginatedResponse)
async def get_all_flashpoints(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD format)"),
    run_id: Optional[str] = Query(None, description="Filter by run ID"),
    rate_limit: RateLimitResponse = Depends(check_rate_limit),
):
    """
    Retrieve all flashpoints with pagination and filtering support.

    This endpoint returns flashpoint data from the daily flashpoint table
    with support for pagination, date filtering, and run ID filtering.

    Args:
        request: FastAPI request object
        page: Page number (1-based indexing)
        page_size: Number of items per page (1-200)
        date: Optional date filter in YYYY-MM-DD format
        run_id: Optional run ID filter
        rate_limit: Rate limit check (injected dependency)

    Returns:
        PaginatedResponse: Paginated flashpoint data

    Raises:
        HTTPException: 400 for invalid date format, 500 for server errors
    """
    logger.info(f"Flashpoints retrieval requested - page: {page}, size: {page_size}")

    try:
        # Get Supabase client
        client = await get_supabase_client()

        # Determine table name based on date parameter
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                table_name = get_daily_table_name("flash_point", target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            table_name = get_daily_table_name("flash_point")

        # Calculate pagination offset
        offset = (page - 1) * page_size

        # Build base query
        query = client.table(table_name).select("*")

        # Apply run_id filter if provided
        if run_id:
            query = query.eq("run_id", run_id)

        # Get total count for pagination metadata
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0

        # Get paginated data
        result = query.range(offset, offset + page_size - 1).execute()

        # Handle empty results
        if not result.data:
            return PaginatedResponse(
                data=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                has_next=False,
                has_prev=False,
            )

        # Convert database records to response models
        flashpoints = []
        for fp in result.data:
            flashpoints.append(
                FlashpointResponse(
                    id=fp.get("id", ""),
                    title=fp.get("title", ""),
                    description=fp.get("description", ""),
                    entities=parse_json_field(fp.get("entities")),
                    domains=parse_json_field(fp.get("domains")),
                    run_id=fp.get("run_id"),
                    created_at=fp.get("created_at", ""),
                    updated_at=fp.get("updated_at", ""),
                )
            )

        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size

        logger.info(
            f"Flashpoints retrieved: {len(flashpoints)} records, total: {total}"
        )

        return PaginatedResponse(
            data=flashpoints,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flashpoints retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Flashpoints retrieval failed: {str(e)}"
        )


@router.get("/flashpoints/{flashpoint_id}/feeds", response_model=PaginatedResponse)
async def get_feeds_per_flashpoint(
    flashpoint_id: str,
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD format)"),
    rate_limit: RateLimitResponse = Depends(check_rate_limit),
):
    """
    Retrieve feeds associated with a specific flashpoint.

    This endpoint returns feed data that belongs to the specified flashpoint,
    with support for pagination and date filtering.

    Args:
        flashpoint_id: UUID of the flashpoint
        request: FastAPI request object
        page: Page number (1-based indexing)
        page_size: Number of items per page (1-200)
        date: Optional date filter in YYYY-MM-DD format
        rate_limit: Rate limit check (injected dependency)

    Returns:
        PaginatedResponse: Paginated feed data for the flashpoint

    Raises:
        HTTPException: 400 for invalid date format, 500 for server errors
    """
    logger.info(
        f"Feeds per flashpoint requested - flashpoint_id: {flashpoint_id}, page: {page}"
    )

    try:
        # Get Supabase client
        client = await get_supabase_client()

        # Determine table name based on date parameter
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                feed_table = get_daily_table_name("feed_entries", target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            feed_table = get_daily_table_name("feed_entries")

        # Calculate pagination offset
        offset = (page - 1) * page_size

        # Build query for feeds belonging to the flashpoint
        query = client.table(feed_table).select("*").eq("flashpoint_id", flashpoint_id)

        # Get total count for pagination metadata
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0

        # Get paginated data
        result = query.range(offset, offset + page_size - 1).execute()

        # Handle empty results
        if not result.data:
            return PaginatedResponse(
                data=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                has_next=False,
                has_prev=False,
            )

        # Convert database records to response models
        feeds = []
        for feed in result.data:
            feeds.append(
                FeedResponse(
                    id=feed.get("id", ""),
                    flashpoint_id=feed.get("flashpoint_id", ""),
                    url=feed.get("url", ""),
                    title=feed.get("title", ""),
                    seendate=feed.get("seendate"),
                    domain=feed.get("domain"),
                    language=feed.get("language"),
                    sourcecountry=feed.get("sourcecountry"),
                    description=feed.get("description"),
                    image=feed.get("image"),
                    created_at=feed.get("created_at", ""),
                    updated_at=feed.get("updated_at", ""),
                )
            )

        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size

        logger.info(
            f"Feeds per flashpoint retrieved: {len(feeds)} records, total: {total}"
        )

        return PaginatedResponse(
            data=feeds,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feeds per flashpoint retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Feeds per flashpoint retrieval failed: {str(e)}"
        )


@router.get("/feeds", response_model=PaginatedResponse)
async def get_all_feeds(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD format)"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    domain: Optional[str] = Query(None, description="Filter by domain name"),
    rate_limit: RateLimitResponse = Depends(check_rate_limit),
):
    """
    Retrieve all feeds with pagination and filtering support.

    This endpoint returns feed data from the daily feed entries table
    with support for pagination, date filtering, language filtering,
    and domain filtering.

    Args:
        request: FastAPI request object
        page: Page number (1-based indexing)
        page_size: Number of items per page (1-200)
        date: Optional date filter in YYYY-MM-DD format
        language: Optional language filter (e.g., 'en', 'es', 'fr')
        domain: Optional domain filter (e.g., 'news.com', 'blog.org')
        rate_limit: Rate limit check (injected dependency)

    Returns:
        PaginatedResponse: Paginated feed data

    Raises:
        HTTPException: 400 for invalid date format, 500 for server errors
    """
    logger.info(f"All feeds retrieval requested - page: {page}, size: {page_size}")

    try:
        # Get Supabase client
        client = await get_supabase_client()

        # Determine table name based on date parameter
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                feed_table = get_daily_table_name("feed_entries", target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            feed_table = get_daily_table_name("feed_entries")

        # Calculate pagination offset
        offset = (page - 1) * page_size

        # Build base query
        query = client.table(feed_table).select("*")

        # Apply filters if provided
        if language:
            query = query.eq("language", language)

        if domain:
            query = query.eq("domain", domain)

        # Get total count for pagination metadata
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0

        # Get paginated data
        result = query.range(offset, offset + page_size - 1).execute()

        # Handle empty results
        if not result.data:
            return PaginatedResponse(
                data=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                has_next=False,
                has_prev=False,
            )

        # Convert database records to response models
        feeds = []
        for feed in result.data:
            feeds.append(
                FeedResponse(
                    id=feed.get("id", ""),
                    flashpoint_id=feed.get("flashpoint_id", ""),
                    url=feed.get("url", ""),
                    title=feed.get("title", ""),
                    seendate=feed.get("seendate"),
                    domain=feed.get("domain"),
                    language=feed.get("language"),
                    sourcecountry=feed.get("sourcecountry"),
                    description=feed.get("description"),
                    image=feed.get("image"),
                    created_at=feed.get("created_at", ""),
                    updated_at=feed.get("updated_at", ""),
                )
            )

        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size

        logger.info(f"All feeds retrieved: {len(feeds)} records, total: {total}")

        return PaginatedResponse(
            data=feeds,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"All feeds retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"All feeds retrieval failed: {str(e)}"
        )


@router.get("/rate-limit", response_model=RateLimitResponse)
async def get_rate_limit_status(request: Request):
    """
    Get current rate limit status for the requesting client.

    This endpoint provides information about the client's current rate limit
    status without consuming a request from their quota.

    Args:
        request: FastAPI request object

    Returns:
        RateLimitResponse: Current rate limit information
    """
    client_ip = request.client.host

    with rate_limit_lock:
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Get client's request history and clean expired entries
        client_history = client_requests[client_ip]
        client_history = [
            req_time for req_time in client_history if req_time >= window_start
        ]
        client_requests[client_ip] = client_history

        # Calculate remaining requests
        remaining = max(0, RATE_LIMIT_REQUESTS - len(client_history))

        # Calculate reset time
        reset_time = None
        if client_history:
            oldest_request = min(client_history)
            reset_time = datetime.fromtimestamp(oldest_request + RATE_LIMIT_WINDOW)

        return RateLimitResponse(
            remaining=remaining,
            reset_time=reset_time.isoformat() if reset_time else "",
            limit=RATE_LIMIT_REQUESTS,
        )


@router.get("/stats")
async def get_data_stats(
    request: Request,
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD format)"),
    rate_limit: RateLimitResponse = Depends(check_rate_limit),
):
    """
    Get comprehensive statistics about flashpoints and feeds data.

    This endpoint provides aggregated statistics including total counts,
    domain distribution, language distribution, and table information.

    Args:
        request: FastAPI request object
        date: Optional date filter in YYYY-MM-DD format
        rate_limit: Rate limit check (injected dependency)

    Returns:
        dict: Statistics data including counts and distributions

    Raises:
        HTTPException: 400 for invalid date format, 500 for server errors
    """
    logger.info("Data statistics requested")

    try:
        # Get Supabase client
        client = await get_supabase_client()

        # Determine table names based on date parameter
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                flashpoint_table = get_daily_table_name("flash_point", target_date)
                feed_table = get_daily_table_name("feed_entries", target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )
        else:
            flashpoint_table = get_daily_table_name("flash_point")
            feed_table = get_daily_table_name("feed_entries")

        # Get flashpoint count
        flashpoint_result = (
            client.table(flashpoint_table).select("id", count="exact").execute()
        )
        flashpoint_count = (
            flashpoint_result.count
            if hasattr(flashpoint_result, "count")
            else len(flashpoint_result.data or [])
        )

        # Get feed count
        feed_result = client.table(feed_table).select("id", count="exact").execute()
        feed_count = (
            feed_result.count
            if hasattr(feed_result, "count")
            else len(feed_result.data or [])
        )

        # Get domain distribution from feeds
        domain_result = client.table(feed_table).select("domain").execute()
        domain_distribution = defaultdict(int)
        if domain_result.data:
            for feed in domain_result.data:
                domain = feed.get("domain")
                if domain:
                    domain_distribution[domain] += 1

        # Get language distribution from feeds
        language_result = client.table(feed_table).select("language").execute()
        language_distribution = defaultdict(int)
        if language_result.data:
            for feed in language_result.data:
                language = feed.get("language")
                if language:
                    language_distribution[language] += 1

        # Compile statistics
        stats = {
            "total_flashpoints": flashpoint_count,
            "total_feeds": feed_count,
            "domain_distribution": dict(domain_distribution),
            "language_distribution": dict(language_distribution),
            "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
            "tables": {"flashpoint_table": flashpoint_table, "feed_table": feed_table},
        }

        logger.info(f"Statistics generated: {stats}")
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Statistics generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Statistics generation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the data service.

    This endpoint verifies that the service is healthy and can connect
    to the database. It also provides information about rate limiting
    configuration.

    Returns:
        dict: Health status information

    Raises:
        HTTPException: 503 if service is unhealthy
    """
    try:
        # Test database connection
        client = await get_supabase_client()

        # Test connection by querying a simple table
        today_table = get_daily_table_name("flash_point")
        result = (
            client.table(today_table).select("id", count="exact").limit(1).execute()
        )

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "rate_limit": {
                "requests_per_minute": RATE_LIMIT_REQUESTS,
                "window_seconds": RATE_LIMIT_WINDOW,
            },
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
