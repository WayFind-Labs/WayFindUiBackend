import logging
import time
from functools import lru_cache
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class RateLimiter:
    _key_prefix = "wayfind:rate:"

    def __init__(
        self,
        redis_url: str,
        message_limit: int,
        image_limit: int,
    ) -> None:
        self._message_limit = message_limit
        self._image_limit = image_limit
        self._redis = None
        self._memory_counts: dict[str, list[float]] = {}

        if redis_url and not redis_url.startswith("memory"):
            try:
                from redis.asyncio import Redis
                self._redis = Redis.from_url(redis_url, decode_responses=True)
            except Exception as exc:
                logger.warning("Redis rate limiter init failed (%s), using in-memory", exc)
                self._redis = None

    async def _check(
        self,
        session_id: str,
        resource: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        if self._redis:
            try:
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
                return
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning("Redis error in rate limiter (%s), switching to in-memory", exc)
                self._redis = None

        # In-memory sliding window check
        now = time.time()
        mem_key = f"{resource}:{session_id}"
        timestamps = [t for t in self._memory_counts.get(mem_key, []) if now - t < window_seconds]
        if len(timestamps) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many {resource} requests. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )
        timestamps.append(now)
        self._memory_counts[mem_key] = timestamps

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
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass


@lru_cache
def get_rate_limiter() -> RateLimiter:
    from app.config import get_settings
    settings = get_settings()
    return RateLimiter(
        redis_url=settings.redis_url,
        message_limit=settings.rate_limit_messages_per_minute,
        image_limit=settings.rate_limit_images_per_hour,
    )