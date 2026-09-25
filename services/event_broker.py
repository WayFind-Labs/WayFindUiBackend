import asyncio
from collections.abc import AsyncGenerator

from schemas.message import AgentEvent


class EventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[AgentEvent | None]] = {}
        self._lock = asyncio.Lock()

    async def _get_queue(self, session_id: str) -> asyncio.Queue[AgentEvent | None]:
        async with self._lock:
            return self._queues.setdefault(session_id, asyncio.Queue())

    async def push(self, session_id: str, event: AgentEvent) -> None:
        queue = await self._get_queue(session_id)
        await queue.put(event)

    async def consume(self, session_id: str) -> AsyncGenerator[AgentEvent, None]:
        queue = await self._get_queue(session_id)
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            queue = self._queues.get(session_id)
        if queue is not None:
            await queue.put(None)

    async def close(self) -> None:
        async with self._lock:
            session_ids = list(self._queues)
        for session_id in session_ids:
            await self.close_session(session_id)