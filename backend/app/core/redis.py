import redis.asyncio as aioredis
from app.core.config import settings

_redis = None

async def get_redis() -> aioredis.Redis | None:
    """Returns a Redis client, or None if REDIS_URL is not configured."""
    global _redis
    if not settings.REDIS_URL:
        return None
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
