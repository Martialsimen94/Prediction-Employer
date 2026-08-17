"""Redis client factory."""

from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    """Return a cached, process-wide Redis client."""
    return redis.Redis.from_url(get_settings().redis_dsn, decode_responses=True)
