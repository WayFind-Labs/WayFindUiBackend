"""
app/routes/guardians.py
Guardian endpoints for pre-registering children in safe status (REGISTERED_SAFE)
and retrieving registered profiles.
"""

from fastapi import APIRouter, Depends, Request
from schemas.child import (
    ChildRegistrationRequest,
    ChildRegistrationResponse,
    RegisteredChildSummary,
)
from services.guardian_repository import GuardianRepository

router = APIRouter(prefix="/guardians", tags=["Guardians"])


def get_guardian_repository(request: Request) -> GuardianRepository:
    return request.app.state.guardian_repository


@router.post("/register-child", response_model=ChildRegistrationResponse)
async def register_child(
    body: ChildRegistrationRequest,
    repo: GuardianRepository = Depends(get_guardian_repository),
) -> ChildRegistrationResponse:
    """Pre-register a child proactively with baseline physical and guardian details."""
    return await repo.register_child(request=body)


@router.get("/{guardian_id}/children", response_model=list[RegisteredChildSummary])
async def list_registered_children(
    guardian_id: str,
    repo: GuardianRepository = Depends(get_guardian_repository),
) -> list[RegisteredChildSummary]:
    """List all registered children under a guardian profile."""
    return await repo.list_registered_children(guardian_id=guardian_id)
