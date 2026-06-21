from redis.asyncio import Redis

from app.core.config import settings

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def hit_rate_limit(*, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)

    ttl = await redis_client.ttl(key)
    retry_after = ttl if ttl and ttl > 0 else window_seconds
    return current > limit, retry_after


async def reset_rate_limit(key: str) -> None:
    await redis_client.delete(key)
