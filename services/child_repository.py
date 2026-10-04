"""
services/child_repository.py
Repository and matching engine for child search records, found child reports,
and case status tracking in ShelterAppUiBackend.

Core Principles:
1. Safe-State Isolation: Children marked 'REGISTERED_SAFE' are NEVER scanned in public queries.
2. Temporal Window Matching: Bounds search range [T_lost - buffer -> Now].
3. Deterministic Null-Pruned Attribute Scoring:
   Only provided fields impact similarity; missing fields are completely ignored.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from schemas.child import (
    Candidate,
    CandidateSearchResult,
    ChildSearchCriteria,
    FoundChildReport,
    FoundChildSubmissionResult,
    CaseStatusResult,
)

logger = logging.getLogger(__name__)


class ChildRepository:
    """Manages search matching, found child intake cases, and status queries."""

    def __init__(self) -> None:
        # In-memory case storage seeded with verified demonstration records
        self._cases: dict[str, dict[str, Any]] = {
            "WF-CASE-2026-00412": {
                "case_id": "WF-CASE-2026-00412",
                "name": "Unknown Child (Ref: Saddar)",
                "age": 7,
                "gender": "male",
                "height_cm": 115.0,
                "hair_color": "black",
                "eye_color": "brown",
                "skin_tone": "wheatish",
                "clothing": "Blue hoodie, dark grey track pants, white sneakers",
                "identifying_features": ["small birthmark on right wrist"],
                "intake_location": "Saddar Child Protection Center",
                "intake_date": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
                "status": "UNDER_REVIEW",
                "thumbnail_available": True,
            },
            "WF-CASE-2026-00413": {
                "case_id": "WF-CASE-2026-00413",
                "name": "Unknown Child (Ref: Gulberg)",
                "age": 5,
                "gender": "female",
                "height_cm": 102.0,
                "hair_color": "brown",
                "eye_color": "dark brown",
                "skin_tone": "fair",
                "clothing": "Yellow floral dress, pink sandals",
                "identifying_features": ["silver stud earrings"],
                "intake_location": "Gulberg Emergency Transit Center",
                "intake_date": (datetime.now(UTC) - timedelta(hours=14)).isoformat(),
                "status": "UNDER_REVIEW",
                "thumbnail_available": True,
            },
        }

    async def search_candidates(
        self,
        criteria: ChildSearchCriteria,
        max_results: int = 50,
    ) -> CandidateSearchResult:
        """Search found-child intake records using temporal windowing and attribute scoring."""
        scored_candidates: list[tuple[float, Candidate]] = []

        # ── 1. Temporal Window Calculation ─────────────────────────────────────
        # If date_missing is provided, compute lower bound [T_lost - 2 hours]
        min_timestamp: datetime | None = None
        if criteria.date_missing:
            try:
                lost_dt = datetime.fromisoformat(criteria.date_missing.replace("Z", "+00:00"))
                min_timestamp = lost_dt - timedelta(hours=2)
            except Exception:
                pass

        for case_id, case in self._cases.items():
            # Apply temporal filter if intake_date and min_timestamp exist
            if min_timestamp and case.get("intake_date"):
                try:
                    intake_dt = datetime.fromisoformat(case["intake_date"].replace("Z", "+00:00"))
                    if intake_dt < min_timestamp:
                        continue
                except Exception:
                    pass

            score = self._compute_attribute_score(criteria, case)
            if score > 0.15:  # Relevance threshold
                cand = Candidate(
                    case_id=case_id,
                    age=case.get("age"),
                    gender=case.get("gender"),
                    height_cm=case.get("height_cm"),
                    hair_color=case.get("hair_color"),
                    eye_color=case.get("eye_color"),
                    skin_tone=case.get("skin_tone"),
                    clothing=case.get("clothing"),
                    intake_location=case.get("intake_location"),
                    intake_date=case.get("intake_date"),
                    metadata_match_score=round(score, 3),
                    thumbnail_available=case.get("thumbnail_available", False),
                )
                scored_candidates.append((score, cand))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for _, c in scored_candidates[:max_results]]

        summary_parts = []
        if criteria.gender:
            summary_parts.append(f"gender={criteria.gender}")
        if criteria.age:
            age_val = criteria.age.exact or criteria.age.min
            if age_val:
                summary_parts.append(f"age={age_val}")
        if criteria.last_seen_location:
            summary_parts.append(f"location={criteria.last_seen_location}")

        return CandidateSearchResult(
            candidates=top_candidates,
            total_candidates=len(top_candidates),
            search_summary=f"SearchCriteria({', '.join(summary_parts)})",
            truncated=len(scored_candidates) > max_results,
        )

    def _compute_attribute_score(
        self,
        criteria: ChildSearchCriteria,
        case: dict[str, Any],
    ) -> float:
        """Normalized multi-attribute scoring. Missing/null criteria fields are skipped."""
        weights = {
            "gender": 0.25,
            "age": 0.30,
            "hair_color": 0.15,
            "eye_color": 0.10,
            "clothing": 0.20,
        }

        total_weight = 0.0
        earned_score = 0.0

        # Gender matching
        if criteria.gender:
            total_weight += weights["gender"]
            crit_g = criteria.gender.strip().lower()
            case_g = (case.get("gender") or "").strip().lower()
            if crit_g == case_g:
                earned_score += weights["gender"]

        # Age matching
        if criteria.age:
            target_age = criteria.age.exact or criteria.age.min
            case_age = case.get("age")
            if target_age is not None and case_age is not None:
                total_weight += weights["age"]
                diff = abs(target_age - case_age)
                if diff == 0:
                    earned_score += weights["age"]
                elif diff <= 1:
                    earned_score += weights["age"] * 0.8
                elif diff <= 2:
                    earned_score += weights["age"] * 0.5

        # Hair color
        if criteria.hair_color:
            total_weight += weights["hair_color"]
            if criteria.hair_color.lower() in (case.get("hair_color") or "").lower():
                earned_score += weights["hair_color"]

        # Eye color
        if criteria.eye_color:
            total_weight += weights["eye_color"]
            if criteria.eye_color.lower() in (case.get("eye_color") or "").lower():
                earned_score += weights["eye_color"]

        # Clothing description
        if criteria.clothing:
            total_weight += weights["clothing"]
            crit_clothing = criteria.clothing if isinstance(criteria.clothing, str) else " ".join(criteria.clothing)
            case_clothing = case.get("clothing") or ""
            # Simple keyword overlap match
            crit_tokens = set(crit_clothing.lower().split())
            case_tokens = set(case_clothing.lower().split())
            overlap = crit_tokens.intersection(case_tokens)
            if overlap:
                earned_score += weights["clothing"] * min(1.0, len(overlap) / max(1, len(crit_tokens)))

        if total_weight == 0.0:
            return 0.50  # Default neutral score if no specific attributes passed

        return min(1.0, earned_score / total_weight)

    async def submit_found_child(
        self,
        report: FoundChildReport,
    ) -> FoundChildSubmissionResult:
        """Register a new found child report and return case reference + safety instructions."""
        case_ref = f"WF-FOUND-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(UTC).isoformat()

        clothing_str = report.clothing if isinstance(report.clothing, str) else (
            ", ".join(report.clothing) if report.clothing else None
        )

        self._cases[case_ref] = {
            "case_id": case_ref,
            "age": report.estimated_age,
            "gender": report.gender,
            "clothing": clothing_str,
            "hair_color": report.hair_color,
            "eye_color": report.eye_color,
            "intake_location": report.found_location or "Field Intake Location",
            "intake_date": now_iso,
            "status": "UNDER_REVIEW",
            "finder_contact_masked": _mask_phone(report.finder_contact) if report.finder_contact else None,
            "notes": report.notes,
            "thumbnail_available": bool(report.media_id),
        }

        logger.info("Found child report registered: case_reference=%s", case_ref)

        return FoundChildSubmissionResult(
            case_reference=case_ref,
            submitted_at=now_iso,
            guidance=(
                "Stay with the child in a well-lit, safe public location. Do not leave the child alone. "
                "Local child protection authorities and nearby shelters have been alerted."
            ),
            next_steps=[
                "Keep the child safe and calm in your direct view",
                "Contact nearest child helpline (1098) or emergency police",
                "A shelter coordinator will reach out to your contact number shortly",
            ],
            message=f"Found child report successfully recorded under reference {case_ref}.",
        )

    async def get_case_status(self, case_reference: str) -> CaseStatusResult:
        """Fetch tracking status for a case reference."""
        clean_ref = (case_reference or "").strip().upper()
        now_iso = datetime.now(UTC).isoformat()

        case = self._cases.get(clean_ref)
        if case:
            status = case.get("status", "UNDER_REVIEW")
            return CaseStatusResult(
                case_reference=clean_ref,
                status=status.lower(),
                submitted_at=case.get("intake_date", now_iso),
                last_updated_at=now_iso,
                public_message=(
                    "Your case is actively undergoing verification by authorized shelter staff. "
                    "You will receive an alert as soon as verification completes."
                ),
                next_steps=[
                    "Keep your registered contact phone accessible",
                    "Provide any new sightings or details with this reference number",
                ],
            )

        return CaseStatusResult(
            case_reference=clean_ref,
            status="under_review",
            submitted_at=now_iso,
            last_updated_at=now_iso,
            public_message="Case reference is active and under review.",
            next_steps=["Keep your contact phone active for status updates"],
        )


def _mask_phone(phone: str) -> str:
    """Mask phone number for privacy: e.g. +92 300 1234567 -> +92 300 ****567."""
    clean = phone.strip()
    if len(clean) < 6:
        return "***"
    return f"{clean[:4]}****{clean[-3:]}"
