"""
schemas/child.py
Pydantic models for child search criteria, found child reports,
guardian registrations, and candidate results in ShelterAppUiBackend.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AgeRange(BaseModel):
    exact: int | None = Field(default=None, ge=0, le=18)
    min: int | None = Field(default=None, ge=0, le=18)
    max: int | None = Field(default=None, ge=0, le=18)


class HeightRange(BaseModel):
    min: float | None = Field(default=None, ge=30.0, le=220.0)
    max: float | None = Field(default=None, ge=30.0, le=220.0)


class ChildSearchCriteria(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    age: AgeRange | None = None
    gender: str | None = None
    height_cm: float | None = None
    height_range: HeightRange | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    skin_tone: str | None = None
    clothing: str | list[str] | None = None
    identifying_features: list[str] | None = None
    last_seen_location: str | None = None
    date_missing: str | None = None
    media_id: str | None = None


class SearchChildrenRequest(BaseModel):
    criteria: ChildSearchCriteria
    max_results: int = 50


class Candidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    case_id: str
    age: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    skin_tone: str | None = None
    clothing: str | None = None
    intake_location: str | None = None
    intake_date: str | None = None
    metadata_match_score: float = 0.0
    thumbnail_available: bool = False
    details: dict[str, Any] | None = None


class CandidateSearchResult(BaseModel):
    candidates: list[Candidate] = Field(default_factory=list)
    total_candidates: int = 0
    search_summary: str = ""
    truncated: bool = False


class FoundChildReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    estimated_age: int | None = Field(default=None, ge=0, le=18)
    gender: str | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    clothing: str | list[str] | None = None
    found_location: str | None = None
    current_custody: str | None = None
    identifying_features: list[str] | None = None
    finder_contact: str | None = None
    media_id: str | None = None
    notes: str | None = None


class FoundChildSubmissionResult(BaseModel):
    case_reference: str
    submitted_at: str
    guidance: str
    next_steps: list[str] = Field(default_factory=list)
    message: str = ""


class CaseStatusResult(BaseModel):
    case_reference: str
    status: str
    submitted_at: str
    last_updated_at: str
    public_message: str
    next_steps: list[str] = Field(default_factory=list)


class ChildRegistrationRequest(BaseModel):
    guardian_name: str
    guardian_phone: str
    guardian_national_id: str | None = None
    child_name: str
    dob: str | None = None
    age: int | None = None
    gender: str | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    skin_tone: str | None = None
    height_cm: float | None = None
    identifying_features: list[str] | None = None
    medical_notes: str | None = None
    emergency_contact: str | None = None
    baseline_photo_media_id: str | None = None


class RegisteredChildSummary(BaseModel):
    id: str
    name: str
    age: int | None = None
    gender: str | None = None
    status: str = "REGISTERED_SAFE"
    registered_at: str


class ChildRegistrationResponse(BaseModel):
    success: bool
    child_id: str
    guardian_id: str
    child_name: str
    status: str = "REGISTERED_SAFE"
    registered_at: str
    message: str
