import redis.asyncio as aioredis
from redis.asyncio import Redis

from finrag_core.core.config import get_settings
from finrag_core.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        logger.info("redis_connected", url=settings.redis_url)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("redis_closed")
