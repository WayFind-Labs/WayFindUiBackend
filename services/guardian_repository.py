"""
services/guardian_repository.py
Manages child pre-registration (REGISTERED_SAFE) and guardian profiles.

Key Security Rules:
- Registered children are tagged with status 'REGISTERED_SAFE'
- Pre-registered children are completely excluded from public missing child searches
- Guardian contact numbers are masked and never exposed to the public
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from schemas.child import (
    ChildRegistrationRequest,
    ChildRegistrationResponse,
    RegisteredChildSummary,
)

logger = logging.getLogger(__name__)


class GuardianRepository:
    """Manages guardian profiles and safe child pre-registrations."""

    def __init__(self) -> None:
        # Pre-seeded demonstration registered children
        self._guardians: dict[str, dict[str, Any]] = {
            "demo-guardian-1": {
                "id": "demo-guardian-1",
                "name": "Sarah Khan",
                "phone_masked": "+92 300 ****123",
                "children": [
                    {
                        "id": "child-demo-1",
                        "name": "Zaid Khan",
                        "age": 7,
                        "gender": "male",
                        "hair_color": "black",
                        "eye_color": "dark brown",
                        "status": "REGISTERED_SAFE",
                        "registered_at": "2026-08-12T10:00:00Z",
                    },
                    {
                        "id": "child-demo-2",
                        "name": "Amina Khan",
                        "age": 4,
                        "gender": "female",
                        "hair_color": "brown",
                        "eye_color": "brown",
                        "status": "REGISTERED_SAFE",
                        "registered_at": "2026-08-12T10:05:00Z",
                    },
                ],
            }
        }

    async def register_child(
        self,
        request: ChildRegistrationRequest,
    ) -> ChildRegistrationResponse:
        """Register a new child under a guardian profile in REGISTERED_SAFE status."""
        child_id = f"WF-CHILD-{uuid.uuid4().hex[:8].upper()}"
        guardian_id = f"WF-GUARD-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(UTC).isoformat()

        child_record = {
            "id": child_id,
            "guardian_id": guardian_id,
            "name": request.child_name.strip(),
            "dob": request.dob,
            "age": request.age,
            "gender": request.gender,
            "hair_color": request.hair_color,
            "eye_color": request.eye_color,
            "skin_tone": request.skin_tone,
            "height_cm": request.height_cm,
            "identifying_features": request.identifying_features,
            "medical_notes": request.medical_notes,
            "emergency_contact": request.emergency_contact,
            "baseline_photo_media_id": request.baseline_photo_media_id,
            "status": "REGISTERED_SAFE",
            "registered_at": now_iso,
        }

        masked_phone = _mask_phone(request.guardian_phone)
        self._guardians[guardian_id] = {
            "id": guardian_id,
            "name": request.guardian_name.strip(),
            "phone_masked": masked_phone,
            "children": [child_record],
        }

        logger.info(
            "Child registered successfully: child_id=%s, guardian_id=%s, status=REGISTERED_SAFE",
            child_id,
            guardian_id,
        )

        return ChildRegistrationResponse(
            success=True,
            child_id=child_id,
            guardian_id=guardian_id,
            child_name=request.child_name.strip(),
            status="REGISTERED_SAFE",
            registered_at=now_iso,
            message=f"{request.child_name} has been successfully pre-registered as safe on Wayfind.",
        )

    async def list_registered_children(
        self,
        guardian_id: str,
    ) -> list[RegisteredChildSummary]:
        """List all pre-registered children for a given guardian."""
        guardian = self._guardians.get(guardian_id)
        if not guardian:
            # Fallback to demo profile for seamless frontend onboarding
            guardian = self._guardians.get("demo-guardian-1", {})

        children = guardian.get("children", [])
        return [
            RegisteredChildSummary(
                id=c["id"],
                name=c["name"],
                age=c.get("age"),
                gender=c.get("gender"),
                status=c.get("status", "REGISTERED_SAFE"),
                registered_at=c.get("registered_at", datetime.now(UTC).isoformat()),
            )
            for c in children
        ]


def _mask_phone(phone: str) -> str:
    clean = phone.strip()
    if len(clean) < 6:
        return "***"
    return f"{clean[:4]}****{clean[-3:]}"
