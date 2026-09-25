from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import verify_session_token
from schemas.message import AgentEvent, MessageRequest
from services.agent_client import AgentClient, AgentClientError

router = APIRouter()
bearer_scheme = HTTPBearer()


def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    return verify_session_token(credentials.credentials)


def get_agent_client(request: Request) -> AgentClient:
    return request.app.state.agent_client


@router.post("/sessions/{session_id}/messages", response_model=list[AgentEvent])
async def send_message(
    session_id: str,
    body: MessageRequest,
    request: Request,
    current_session: str = Depends(get_current_session),
    agent_client: AgentClient = Depends(get_agent_client),
) -> list[AgentEvent]:
    if session_id != current_session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session does not match the access token.",
        )

    await request.app.state.rate_limiter.check_message(session_id)
    try:
        events = await agent_client.send_event(
            session_id,
            {"type": "user_message", "content": body.content},
        )
    except AgentClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The agent service is temporarily unavailable.",
        ) from exc

    for event in events:
        await request.app.state.event_broker.push(session_id, event)
    await request.app.state.session_store.touch(session_id)
    return events