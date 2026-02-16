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
Utility for MASX-HOTSPOTS Agentic AI System.
Common utilities used across agents, workflows, and services including:
- ID generation, text sanitization, URL validation
- Retry logic with exponential backoff
- Performance measurement and timing utilities
Usage: from app.core.utils import generate_run_id, retry_with_backoff, measure_execution_time
"""

import time
import uuid
import re
from ast import literal_eval
import httpx
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional, Union
from urllib.parse import urlparse
import json
import random

from .exceptions import ExternalServiceException


def generate_workflow_id() -> str:
    """
    Generate a unique run ID for workflow execution.
    Returns:
        str: Unique run ID in format 'YYYY-MM-DD-HHMMSS-UUID'
    """
    timestamp = time.strftime("%Y-%m-%d-%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}-{unique_id}"


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input by removing control characters and limiting length.
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (None for no limit)
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""

    # Remove control characters except newlines and tabs
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Normalize whitespace
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."

    return sanitized


def validate_url(url: str, timeout: int = 10) -> bool:
    """
    Validate URL format and optionally check accessibility.
    Args:
        url: URL to validate
        timeout: Timeout for accessibility check in seconds
    Returns:
        bool: True if URL is valid and accessible
    """
    try:
        # Basic URL format validation
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False

        # Check if URL is accessible
        with httpx.Client(timeout=timeout) as client:
            response = client.head(url, follow_redirects=True)
            return response.status_code < 400

    except Exception:
        return False


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = False,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for retrying functions with exponential backoff.
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
    Usage:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def api_call():
            # Function that may fail
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        raise ExternalServiceException(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            context={"last_error": str(e)},
                        )

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        delay += random.uniform(0, 5)
                    time.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator


# @contextmanager --Python decorator that lets you write your own with blocks.
@contextmanager
def measure_execution_time(operation_name: str = "operation"):
    """
    Context manager to measure execution time of operations.
    Args:
        operation_name: Name of the operation being measured
    Usage:
        with measure_execution_time("api_call"):
            # Code to measure
            result = api_call()
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"{operation_name} took {duration:.2f} seconds")


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback to default value.
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
    Returns:
        Parsed JSON object or default value
    """
    try:
        return safe_json_parse(json_str)
    except Exception as e:
        return e  # Catch and return ANY exception


def safe_json_parse(response: Union[str, Any]) -> Any:
    """
    Safely parses potentially malformed LLM output into a valid JSON object.
    Applies minimal intervention only when needed.
    """
    if not isinstance(response, str):
        return response

    # Quick parse attempt
    try:
        return json.loads(response)
    except Exception:
        pass  # Proceed with cleanup only if initial parse fails

    # Step 1: Remove any LLM intro text
    lines = response.strip().splitlines()
    json_lines = []
    capture = False
    for line in lines:
        if line.strip().startswith("[") or line.strip().startswith("{"):
            capture = True
        if capture:
            json_lines.append(line)

    raw = "\n".join(json_lines).strip()

    # Step 2: Try parsing again (raw may now be clean)
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Step 3: Clean known issues
    # Fix trailing commas
    raw = re.sub(r",\s*([\]}])", r"\1", raw)

    # Quote unquoted keys
    raw = re.sub(r"([{,]\s*)([a-zA-Z0-9_]+)(\s*):", r'\1"\2"\3:', raw)

    # Replace single quotes with double quotes (only if no double quotes exist)
    if '"' not in raw and "'" in raw:
        raw = raw.replace("'", '"')

    # Remove smart characters or bad escapes
    raw = raw.encode("utf-8", "ignore").decode("utf-8")

    # Step 4: Try parsing again
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Step 5: Last resort trimming
    if raw.count("{") > 0 and raw.count("}") > 0:
        last_curly = raw.rfind("}")
        raw_trimmed = raw[: last_curly + 1]
        try:
            return json.loads(raw_trimmed)
        except Exception:
            pass

    # Step 6: Literal eval fallback
    try:
        return literal_eval(raw)
    except Exception as e:
        print("Final parse failed. Input preview:\n", raw[:500])
        raise ValueError(f"Could not parse input as JSON or Python dict: {e}")


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Split a list into chunks of specified size.
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
    Returns:
        List of chunks
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]
