"""
app/routes/cases.py
Public tracking endpoint for case status and verification updates.
"""

from fastapi import APIRouter, Depends, Request
from schemas.child import CaseStatusResult
from services.child_repository import ChildRepository

router = APIRouter(prefix="/cases", tags=["Cases"])


def get_child_repository(request: Request) -> ChildRepository:
    return request.app.state.child_repository


@router.get("/{case_reference}", response_model=CaseStatusResult)
async def get_case_status(
    case_reference: str,
    repo: ChildRepository = Depends(get_child_repository),
) -> CaseStatusResult:
    """Retrieve public verification status and guidance for a given case reference."""
    return await repo.get_case_status(case_reference=case_reference)
