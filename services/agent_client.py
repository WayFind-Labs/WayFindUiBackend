import httpx
from pydantic import ValidationError

from schemas.message import AgentEvent


class AgentClientError(Exception):
    """Raised when the internal agent service cannot handle an event."""


class AgentClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Internal-Key": api_key},
            timeout=60.0,
        )

    async def send_event(
        self,
        session_id: str,
        event: dict,
    ) -> list[AgentEvent]:
        try:
            response = await self._client.post(
                f"/internal/sessions/{session_id}/events",
                json={"event": event},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Agent response must be a list")
            return [AgentEvent.model_validate(item) for item in payload]
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            raise AgentClientError from exc

    async def close(self) -> None:
        await self._client.aclose()