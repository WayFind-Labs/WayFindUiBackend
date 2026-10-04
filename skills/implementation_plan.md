# Shelter Backend — Phased Implementation Plan

**Repository**: `e:\React\Shelter\ShelterAppUiBackend`  
**Status**: Comprehensive Deterministic-First & Crisis Response Plan  

---

## Phase Overview

```text
Phase 1: Schemas & Data Models (PostgreSQL & PostGIS)
   ↓
Phase 2: Temporal Window Engine & Dynamic Query Builder
   ↓
Phase 3: Normalized Weighted Scoring & Tolerance Decays
   ↓
Phase 4: Guardian Pre-Registration & 1-Click SOS Broadcast
   ↓
Phase 5: Structured Search & Intake APIs (Null-Tolerant)
   ↓
Phase 6: Staff Human-in-the-Loop Review Queue
   ↓
Phase 7: Two-Phase Notification & Masked Communication Gateway
   ↓
Phase 8: Empathetic De-escalation Crisis AI Companion
   ↓
Phase 9: Cascaded Biometric Face Matcher (Post-MVP Extensibility)
```

---

## Detailed Phase Breakdown

### Phase 1: Database Schemas & Status Lifecycle
* Models: `Guardian`, `Child` (`REGISTERED_SAFE`, `REPORTED_MISSING`, `FOUND`), `SOSBeacon`, `IntakeCase`, `MatchScore`, `AuditLog`.
* PostGIS spatial indexing for locations.

### Phase 2: Temporal Window Engine & Query Builder
* Dynamic time-window bounding ($[\text{Lost Time} - \text{buffer}] \le \text{Intake Time} \le [\text{Now} + \text{buffer}]$).
* Parameterized SQL builder omitting `null` attributes.

### Phase 3: Weighted Scoring & Mathematical Decays
* Linear age decay ($\pm 0 \to 1.0, \pm 1 \to 0.85, \pm 2 \to 0.60, \pm 3 \to 0.20$).
* Height decay window ($\pm 5\text{ cm} \to 1.0, \pm 15\text{ cm} \to 0.0$).
* Denominator normalization for missing user inputs.

### Phase 4: Guardian Pre-Registration & 1-Click SOS APIs
* `POST /api/children/register`: Pre-registration (defaults to `REGISTERED_SAFE`).
* `POST /api/cases/sos`: 1-Click SOS trigger, captures `last_seen_time`, flips status to `REPORTED_MISSING`, emits `child.sos.activated.v1`.

### Phase 5: Structured Search & Intake Endpoints
* `POST /api/search/match`: Evaluates active missing/found cases within the temporal window.

### Phase 6: Staff Review Queue & HITL Approvals
* `GET /api/review/queue`: Staff queue for uncertain ($0.50 \le S < 0.80$) and high ($S \ge 0.80$) matches.
* `POST /api/review/{id}/decision`: Staff `CONFIRM` or `REJECT` action with tamper-evident audit logs.

### Phase 7: Two-Phase Notification & Communication Gateway
* **Phase 1 Alert:** Immediate SMS/Push to guardian on potential match detection.
* **Phase 2 Alert:** Verified shelter address / Twilio masked call/SMS bridge connecting finder and guardian.

### Phase 8: Empathetic De-escalation Crisis AI Companion
* Conversational edge adapter using a fast LLM (Gemini Flash Lite) to deliver trauma-informed reassurance, breathing prompts, immediate safety instructions, and gentle background slot extraction.

### Phase 9: Cascaded Biometric Face Matcher (Post-MVP)
* InsightFace 512-D vector comparison executed strictly on the Top-3 to Top-5 shortlisted candidates.
