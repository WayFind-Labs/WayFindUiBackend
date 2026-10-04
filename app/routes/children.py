"""
app/routes/children.py
Public endpoints for searching missing child candidates and submitting found child reports.
"""

from fastapi import APIRouter, Depends, Request
from schemas.child import (
    CandidateSearchResult,
    FoundChildReport,
    FoundChildSubmissionResult,
    SearchChildrenRequest,
)
from services.child_repository import ChildRepository

router = APIRouter(prefix="/children", tags=["Children"])


def get_child_repository(request: Request) -> ChildRepository:
    return request.app.state.child_repository


@router.post("/search", response_model=CandidateSearchResult)
async def search_children(
    body: SearchChildrenRequest,
    repo: ChildRepository = Depends(get_child_repository),
) -> CandidateSearchResult:
    """Search for matching candidate records using temporal windowing and attribute scoring."""
    return await repo.search_candidates(
        criteria=body.criteria,
        max_results=body.max_results,
    )


@router.post("/found", response_model=FoundChildSubmissionResult)
async def submit_found_child(
    body: FoundChildReport,
    repo: ChildRepository = Depends(get_child_repository),
) -> FoundChildSubmissionResult:
    """Submit a report for a found unaccompanied child."""
    return await repo.submit_found_child(report=body)
