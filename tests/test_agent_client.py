import httpx
import pytest

from services.agent_client import AgentClient, AgentClientError


@pytest.mark.asyncio
async def test_agent_client_forwards_key_and_parses_events() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["key"] = request.headers["X-Internal-Key"]
        captured["json"] = request.read().decode()
        return httpx.Response(
            200,
            json=[{"type": "assistant_message", "content": "Hello"}],
        )

    client = AgentClient("http://agent.test", "secret")
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="http://agent.test",
        headers={"X-Internal-Key": "secret"},
        transport=httpx.MockTransport(handler),
    )

    events = await client.send_event("session-1", {"type": "user_message"})
    await client.close()

    assert captured["key"] == "secret"
    assert events[0].type == "assistant_message"


@pytest.mark.asyncio
async def test_agent_client_timeout_is_safe_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = AgentClient("http://agent.test", "secret")
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(AgentClientError):
        await client.send_event("session-1", {"type": "user_message"})
    await client.close()