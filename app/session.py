from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import Redis


class SessionStore:
    _key_prefix = "wayfind:session:"

    def __init__(self, redis_url: str, ttl_seconds: int = 24 * 60 * 60) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    async def create(self) -> str:
        session_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        await self._redis.hset(
            self._key(session_id),
            mapping={"created_at": timestamp, "last_active": timestamp},
        )
        await self._redis.expire(self._key(session_id), self._ttl_seconds)
        return session_id

    async def exists(self, session_id: str) -> bool:
        return bool(await self._redis.exists(self._key(session_id)))

    async def touch(self, session_id: str) -> None:
        await self._redis.hset(
            self._key(session_id),
            mapping={"last_active": datetime.now(timezone.utc).isoformat()},
        )
        await self._redis.expire(self._key(session_id), self._ttl_seconds)

    async def close(self) -> None:
        await self._redis.aclose()