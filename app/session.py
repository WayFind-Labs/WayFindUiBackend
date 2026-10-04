import logging
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)


class SessionStore:
    _key_prefix = "wayfind:session:"

    def __init__(self, redis_url: str, ttl_seconds: int = 24 * 60 * 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._memory_store: dict[str, dict[str, str]] = {}
        self._redis = None

        if redis_url and not redis_url.startswith("memory"):
            try:
                from redis.asyncio import Redis
                self._redis = Redis.from_url(redis_url, decode_responses=True)
            except Exception as exc:
                logger.warning("Redis init failed (%s), using in-memory session store", exc)
                self._redis = None

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    async def create(self) -> str:
        session_id = str(uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        mapping = {"created_at": timestamp, "last_active": timestamp}

        if self._redis:
            try:
                await self._redis.hset(self._key(session_id), mapping=mapping)
                await self._redis.expire(self._key(session_id), self._ttl_seconds)
                return session_id
            except Exception as exc:
                logger.warning("Redis error on create (%s), switching to in-memory", exc)
                self._redis = None

        self._memory_store[session_id] = mapping
        return session_id

    async def exists(self, session_id: str) -> bool:
        if self._redis:
            try:
                return bool(await self._redis.exists(self._key(session_id)))
            except Exception:
                self._redis = None

        return session_id in self._memory_store

    async def touch(self, session_id: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        if self._redis:
            try:
                await self._redis.hset(self._key(session_id), mapping={"last_active": timestamp})
                await self._redis.expire(self._key(session_id), self._ttl_seconds)
                return
            except Exception:
                self._redis = None

        if session_id in self._memory_store:
            self._memory_store[session_id]["last_active"] = timestamp

    async def close(self) -> None:
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass