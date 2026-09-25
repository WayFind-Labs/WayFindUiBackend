import time
from functools import lru_cache

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import get_settings


class RateLimiter:
    _key_prefix = "wayfind:rate:"

    def __init__(
        self,
        redis_url: str,
        message_limit: int,
        image_limit: int,
    ) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._message_limit = message_limit
        self._image_limit = image_limit

    async def _check(
        self,
        session_id: str,
        resource: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        window = int(time.time() // window_seconds)
        key = f"{self._key_prefix}{resource}:{session_id}:{window}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, window_seconds + 1)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many {resource} requests. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )

    async def check_message(self, session_id: str) -> None:
        await self._check(
            session_id,
            resource="messages",
            limit=self._message_limit,
            window_seconds=60,
        )

    async def check_image(self, session_id: str) -> None:
        await self._check(
            session_id,
            resource="images",
            limit=self._image_limit,
            window_seconds=60 * 60,
        )

    async def close(self) -> None:
        await self._redis.aclose()


@lru_cache
def get_rate_limiter() -> RateLimiter:
    settings = get_settings()
    return RateLimiter(
        redis_url=settings.redis_url,
        message_limit=settings.rate_limit_messages_per_minute,
        image_limit=settings.rate_limit_images_per_hour,
    )


async def check_message_rate(session_id: str) -> None:
    """Raise 429 if the session has exceeded its message rate limit."""
    await get_rate_limiter().check_message(session_id)


async def check_image_rate(session_id: str) -> None:
    """Raise 429 if the session has exceeded its image rate limit."""
    await get_rate_limiter().check_image(session_id)