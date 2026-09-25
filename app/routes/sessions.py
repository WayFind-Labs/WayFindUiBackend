from fastapi import APIRouter, Request

from app.auth import create_session_token
from schemas.session import SessionResponse

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: Request) -> SessionResponse:
    session_id = await request.app.state.session_store.create()
    token = create_session_token(session_id)
    return SessionResponse(session_id=session_id, token=token)