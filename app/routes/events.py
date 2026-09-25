from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.routes.messages import get_current_session
from services.event_broker import EventBroker

router = APIRouter()


def get_event_broker(request: Request) -> EventBroker:
    return request.app.state.event_broker


@router.get("/sessions/{session_id}/events")
async def stream_events(
    session_id: str,
    current_session: str = Depends(get_current_session),
    broker: EventBroker = Depends(get_event_broker),
) -> StreamingResponse:
    if session_id != current_session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not match the access token.",
        )

    async def generate() -> AsyncGenerator[str, None]:
        async for event in broker.consume(session_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )