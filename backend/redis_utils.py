"""
Redis Connection Utility for Azure Container Apps.

Supports multiple connection methods:
1. REDIS_URL (full connection string)
2. REDIS_HOST + REDIS_PORT + REDIS_PASSWORD (Azure Redis Cache format)
3. Default localhost fallback for development

IMPORTANT: RQ requires raw binary Redis connections (decode_responses=False),
while our progress tracking uses string connections (decode_responses=True).
"""

import os
from typing import Optional
from redis import Redis
from rq import Queue
from dotenv import load_dotenv

load_dotenv()


def _get_redis_params():
    """Get Redis connection parameters from environment."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return {"url": redis_url}
    
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "password": os.getenv("REDIS_PASSWORD") or None,
        "ssl": os.getenv("REDIS_SSL", "false").lower() == "true"
    }


def get_redis_connection() -> Redis:
    """
    Get a Redis connection WITH decode_responses=True for string operations.
    Use this for reading/writing progress updates (JSON strings).
    
    Returns:
        Redis connection instance with string decoding
    """
    params = _get_redis_params()
    if "url" in params:
        return Redis.from_url(params["url"], decode_responses=True)
    
    return Redis(
        host=params["host"],
        port=params["port"],
        password=params["password"],
        ssl=params["ssl"],
        decode_responses=True
    )


def get_raw_redis_connection() -> Redis:
    """
    Get a Redis connection WITHOUT decode_responses for binary data.
    Use this for RQ (Redis Queue) which stores pickled Python objects.
    
    Returns:
        Redis connection instance without decoding (binary mode)
    """
    params = _get_redis_params()
    if "url" in params:
        return Redis.from_url(params["url"], decode_responses=False)
    
    return Redis(
        host=params["host"],
        port=params["port"],
        password=params["password"],
        ssl=params["ssl"],
        decode_responses=False
    )


def get_queue(name: str = "default") -> Queue:
    """
    Get an RQ Queue instance.
    
    IMPORTANT: Uses raw Redis connection (decode_responses=False)
    because RQ stores serialized Python objects.
    
    Args:
        name: Queue name (default: "default")
    
    Returns:
        RQ Queue instance
    """
    # RQ requires raw binary connection
    redis_conn = get_raw_redis_connection()
    return Queue(name, connection=redis_conn)


# Progress key helpers
def get_progress_key(job_id: str) -> str:
    """Get the Redis key for job progress."""
    return f"job:{job_id}:progress"


def get_result_key(job_id: str) -> str:
    """Get the Redis key for job result."""
    return f"job:{job_id}:result"

