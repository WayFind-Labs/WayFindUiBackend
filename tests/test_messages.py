from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.messages import send_message
from schemas.message import AgentEvent, MessageRequest


class FakeAgentClient:
    def __init__(self) -> None:
        self.calls = []

    async def send_event(self, session_id: str, event: dict) -> list[AgentEvent]:
        self.calls.append((session_id, event))
        return [AgentEvent(type="assistant_message", content="Received")]


class FakeLimiter:
    async def check_message(self, _session_id: str) -> None:
        return None


class FakeStore:
    def __init__(self) -> None:
        self.touched = []

    async def touch(self, session_id: str) -> None:
        self.touched.append(session_id)


class FakeBroker:
    async def push(self, session_id: str, event: AgentEvent) -> None:
        pass


@pytest.mark.asyncio
async def test_message_forwards_media_id_and_touches_session() -> None:
    agent = FakeAgentClient()
    store = FakeStore()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                rate_limiter=FakeLimiter(),
                session_store=store,
                event_broker=FakeBroker(),
            )
        )
    )

    events = await send_message(
        "session-123",
        MessageRequest(content="Found a child", media_id="media-1"),
        request,
        current_session="session-123",
        agent_client=agent,
    )

    assert events[0].type == "assistant_message"
    assert agent.calls == [
        (
            "session-123",
            {"type": "user_message", "content": "Found a child", "media_id": "media-1"},
        )
    ]
    assert store.touched == ["session-123"]


@pytest.mark.asyncio
async def test_message_rejects_different_session() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(HTTPException) as error:
        await send_message(
            "session-123",
            MessageRequest(content="Hello"),
            request,
            current_session="session-999",
            agent_client=FakeAgentClient(),
        )

    assert error.value.status_code == 403