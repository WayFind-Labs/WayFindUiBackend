from types import SimpleNamespace

import pytest

from app.auth import create_session_token, verify_session_token
from app.routes.sessions import create_session


@pytest.mark.asyncio
async def test_create_session_returns_session_and_token(monkeypatch) -> None:
    session_id = "session-123"

    class FakeStore:
        async def create(self) -> str:
            return session_id

    monkeypatch.setattr(
        "app.routes.sessions.create_session_token", lambda value: f"token-{value}"
    )
    response = await create_session(SimpleNamespace(state=SimpleNamespace(session_store=FakeStore())))

    assert response.session_id == session_id
    assert response.token == "token-session-123"


def test_session_token_round_trip() -> None:
    session_id = "session-456"
    token = create_session_token(session_id, expiry_hours=1)

    assert verify_session_token(token) == session_id