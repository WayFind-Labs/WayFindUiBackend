# Shelter Backend — Architecture & Context Reference

**Repository**: `e:\React\Shelter\ShelterAppUiBackend`  
**Architecture Model**: Deterministic-First Hybrid Architecture with Edge Empathetic AI  
**Role**: Core API Gateway, Registry, Temporal Matching Engine, Communication Gateway, and Alerting Service.

---

## 1. What Is This Repository?

`ShelterAppUiBackend` is the authoritative core backend for the Wayfind platform. It manages:

- **Guardian Pre-Registration & 1-Click SOS Broadcast**: Parents pre-register children (`REGISTERED_SAFE`). Tapping **1-Click SOS** transitions the record to `REPORTED_MISSING` and broadcasts an active emergency search beacon.
- **Temporal Time-Window Search (Zero DB-Wide Scans)**: Evaluates incoming reports only against active records within a temporal buffer $[\text{Lost Time} - \text{buffer}] \to [\text{Now}]$, avoiding expensive full-database scans.
- **Two-Phase Progressive Notification Pipeline**:
  - *Phase 1 (Immediate Acknowledgment)*: Notifies guardian that a potential match has been detected and is under priority verification.
  - *Phase 2 (Verified Match & Direction)*: Directs guardian to verified shelter location or opens a secure communication gateway.
- **Finder-Guardian Communication Gateway**: Provides masked VoIP/SMS bridging (via Twilio Voice/SMS proxy) or verified contact exchange between citizen finders and verified guardians.
- **Empathetic Crisis & De-escalation Companion**: Optional conversational edge adapter for trauma-informed calming, reassurance, and immediate safety checklists during emergency intake.
- **Human-in-the-Loop (HITL) Staff Verification**: Queue for authorized shelter/child protection staff to inspect side-by-side evidence before releasing private contact channels.

---

## 2. Core System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Next.js PWA Client                                │
│                             (ShelterApp ui)                                 │
│                                                                             │
│  [1-Click SOS Beacon]   [Structured Search Form]   [Crisis Support Bot]     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       │ HTTPS REST & WebSockets/SSE
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ShelterAppUiBackend                                │
│                              (FastAPI)                                      │
│                                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────────┐ │
│  │ Guardian Registry & SOS  │  │ Temporal Buffer Engine (Time Windowing)  │ │
│  └──────────────────────────┘  └──────────────────────────────────────────┘ │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────────┐ │
│  │ Communication Gateway    │  │ Deterministic Dynamic Query Builder      │ │
│  │ (Masked VoIP/SMS Bridge) │  │ (Null-Pruned SQL & Range Scorer)         │ │
│  └──────────────────────────┘  └──────────────────────────────────────────┘ │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────────┐ │
│  │ Empathetic Crisis LLM    │  │ Staff Review Queue & HITL Approvals      │ │
│  │ (De-escalation Adapter)  │  │                                          │ │
│  └──────────────────────────┘  └──────────────────────────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                   ▼                                       ▼
    ┌─────────────────────────────┐         ┌─────────────────────────────────┐
    │   PostgreSQL 16 + PostGIS   │         │    Encrypted Object Storage     │
    │   • Guardians & Children    │         │    (S3 / MinIO)                 │
    │   • Active SOS Missing Beacons│       │    • Pre-Registered Photos      │
    │   • Found Child Reports     │         │    • Intake Evidence Photos     │
    └─────────────────────────────┘         └─────────────────────────────────┘
                   │
                   ▼ (Top 3-5 Shortlisted Candidates Only)
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                Cascaded Biometric Face Matcher (InsightFace)            │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. End-to-End Workflows

### A. Guardian Pre-Registration & SOS Activation
1. **Pre-Registration:** Guardian registers child $\to$ Stored as `REGISTERED_SAFE`. Safe children are strictly excluded from missing search queries.
2. **1-Click SOS Beacon:** Guardian taps SOS $\to$ Enters approximate last-seen time (e.g. *"today at 2:00 PM"*) $\to$ Status flips to `REPORTED_MISSING` $\to$ Broadcasts `child.sos.activated.v1`.
3. **Temporal Window Search:** The search engine immediately queries found-child reports and shelter intake logs created between $[\text{Lost Time} - 2\text{ hours}]$ and $[\text{Current Time}]$.

### B. Found Child Report & Progressive Notification
1. A citizen or shelter reports a found child with attributes and location.
2. The engine evaluates active `REPORTED_MISSING` records within the temporal window.
3. If a high-confidence match is detected:
   - **Phase 1 Notification:** Guardian receives immediate SMS/Push: *"We have detected a potential match for [Child Name] at [Area]. Our team is verifying details now. We will send you an update shortly."*
   - **Staff Verification (HITL):** Shelter staff approves match in `/admin/review`.
   - **Phase 2 Notification & Gateway:**
     - *If at an authorized shelter:* Guardian receives official shelter address, reception desk number, and case passkey.
     - *If with a citizen finder:* System creates a masked communication bridge and instructs finder: *"The parents of [Child Name] have been alerted and are connecting now. Please stay in a safe, well-lit location."*

### C. Empathetic De-escalation AI Companion
- Accessible via chat for distraught parents or witnesses.
- Delivers steady reassurance, breathing pauses, and actionable immediate safety steps (e.g., alert store security, check nearby water bodies).
- Gathers missing clothing and location details smoothly in the background and submits them to the deterministic search engine.
