# Shelter Backend — Implementation Plan

**Repository**: `e:\React\Shelter\ShelterAppUiBackend`  
**Date**: 2026-09-25  
**Scope**: Public API gateway — FastAPI between Next.js PWA and WayFindMCPClient

> [!IMPORTANT]
> Read `skills/context.md` first. It contains the full architecture, responsibility boundaries,
> API contracts, and deployment model. This plan focuses only on implementation phases.

---

## Background

`ShelterAppUiBackend` is the **public-facing API gateway** for Wayfind. It:
- Accepts requests from the Next.js PWA over HTTPS + SSE
- Handles auth, sessions, validation, rate limiting, and image intake
- Forwards processed events to `WayFindMCPClient` (internal only)
- Streams agent events back to the frontend via SSE

It contains **no AI logic**. All intelligence lives in `WayFindMCPClient`.

---

## Architecture Overview

```text
Next.js PWA
    |  HTTPS + SSE
    v
ShelterAppUiBackend (this repo) - port 8001
    |  Internal HTTP
    v
WayFindMCPClient - port 8000 (never exposed publicly)
    |
    v
MCP Server + Databases
```

---

## Target Directory Structure

```text
ShelterAppUiBackend/
├── skills/
│   ├── context.md                           DONE
│   └── implementation_plan.md              THIS FILE
├── pyproject.toml                           Phase 1
├── .env.example                             Phase 1
├── .gitignore                               Phase 1
├── README.md                                Phase 1
|
├── app/
│   ├── __init__.py                          Phase 2
│   ├── main.py                              Phase 2
│   ├── config.py                            Phase 2
│   ├── auth.py                              Phase 3
│   ├── session.py                           Phase 3
│   ├── rate_limit.py                        Phase 4
│   └── routes/
│       ├── __init__.py                      Phase 2
│       ├── sessions.py                      Phase 3
│       ├── messages.py                      Phase 5
│       ├── events.py                        Phase 6
│       └── images.py                        Phase 7
|
├── services/
│   ├── __init__.py                          Phase 2
│   ├── agent_client.py                      Phase 5
│   ├── image_service.py                     Phase 7
│   └── event_broker.py                      Phase 6
|
├── schemas/
│   ├── __init__.py                          Phase 2
│   ├── session.py                           Phase 3
│   ├── message.py                           Phase 5
│   └── image.py                             Phase 7
|
└── tests/
    ├── __init__.py                          Phase 8
    ├── test_sessions.py
    ├── test_messages.py
    ├── test_images.py
    └── test_agent_client.py
```

---

## Phase 1 — Project Setup

### Tasks

- [ ] Initialize Python project with `pyproject.toml` (Python 3.12+)
- [ ] Configure **uv** as package manager (consistent with `WayFindMCPClient`)
- [ ] Define dependencies:
  - `fastapi` + `uvicorn[standard]`
  - `pydantic` v2 + `pydantic-settings`
  - `redis[asyncio]`
  - `httpx` (async HTTP client for internal calls)
  - `PyJWT` (JWT session tokens)
  - `python-multipart` (image upload)
  - `python-dotenv`
  - `slowapi` (rate limiting)
  - `pytest` + `pytest-asyncio` + `httpx` (testing)
- [ ] Create `.env.example`:
  ```env
  SECRET_KEY=changeme-jwt-secret
  CORS_ORIGINS=["http://localhost:3000"]
  HOST=0.0.0.0
  PORT=8001
  REDIS_URL=redis://localhost:6379
  RATE_LIMIT_MESSAGES_PER_MINUTE=20
  RATE_LIMIT_IMAGES_PER_HOUR=10
  AGENT_SERVICE_URL=http://localhost:8000
  SHELTER_BACKEND_API_KEY=changeme-dev-secret
  MAX_IMAGE_SIZE_MB=10
  ALLOWED_IMAGE_TYPES=["image/jpeg","image/png","image/webp"]
  IMAGE_SAFETY_SCAN_URL=http://localhost:9000
  IMAGE_STORAGE_URL=http://localhost:9001
  JWT_ALGORITHM=HS256
  JWT_SESSION_EXPIRY_HOURS=24
  ```
- [ ] Create `.gitignore` (Python defaults + `.env`)
- [ ] Create `README.md` with architecture overview and dev setup

---

## Phase 2 — App Factory & Schemas Foundation

### `app/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    secret_key: str
    cors_origins: List[str] = ["http://localhost:3000"]
    host: str = "0.0.0.0"
    port: int = 8001
    redis_url: str = "redis://localhost:6379"
    rate_limit_messages_per_minute: int = 20
    rate_limit_images_per_hour: int = 10
    agent_service_url: str = "http://localhost:8000"
    shelter_backend_api_key: str
    max_image_size_mb: int = 10
    allowed_image_types: List[str] = ["image/jpeg", "image/png", "image/webp"]
    image_safety_scan_url: str = ""
    image_storage_url: str = ""
    jwt_algorithm: str = "HS256"
    jwt_session_expiry_hours: int = 24

    class Config:
        env_file = ".env"
```

### `app/main.py`

- FastAPI app factory
- CORS middleware (allow frontend origin only — never the agent service origin)
- Global exception handlers (no stack traces to client)
- Mount `/api` router
- Mount rate limiter
- Lifespan: startup → init Redis session store; shutdown → close Redis

### `schemas/` — shared Pydantic models

```python
# schemas/session.py
class SessionResponse(BaseModel):
    session_id: str
    token: str

# schemas/message.py
class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class AgentEvent(BaseModel):
    type: str
    content: str | None = None
    fields: list[str] | None = None
    results: list[dict] | None = None
    record_id: str | None = None
    media_id: str | None = None

# schemas/image.py
class ImageUploadResponse(BaseModel):
    media_id: str
    message: str = "Image received and stored."
```

---

## Phase 3 — Sessions & Auth

### `app/auth.py`

```python
# JWT session token (no user identity yet — session-scoped only)

def create_session_token(session_id: str, expiry_hours: int) -> str:
    """Create JWT encoding only session_id + expiry."""
    ...

def verify_session_token(token: str) -> str:
    """Verify token and return session_id. Raise 401 if invalid."""
    ...
```

### `app/session.py`

```python
# Redis-backed session store
# Stores: { session_id: { "created_at": ..., "last_active": ... } }
# No agent state stored here — WayFindMCPClient owns agent state

class SessionStore:
    async def create(self) -> str:           # returns session_id
    async def exists(self, session_id) -> bool:
    async def touch(self, session_id) -> None:  # update last_active
    async def close(self) -> None:
```

### `app/routes/sessions.py`

```python
# POST /api/sessions
# Creates a new anonymous session and returns JWT

@router.post("/sessions")
async def create_session() -> SessionResponse:
    session_id = await session_store.create()
    token = create_session_token(session_id)
    return SessionResponse(session_id=session_id, token=token)
```

---

## Phase 4 — Rate Limiting

### `app/rate_limit.py`

```python
# Per-session rate limits using slowapi or a custom Redis counter

# Messages: RATE_LIMIT_MESSAGES_PER_MINUTE per session
# Images:   RATE_LIMIT_IMAGES_PER_HOUR per session

async def check_message_rate(session_id: str) -> None:
    """Raise 429 if session has exceeded message rate limit."""
    ...

async def check_image_rate(session_id: str) -> None:
    """Raise 429 if session has exceeded image rate limit."""
    ...
```

---

## Phase 5 — Message Endpoint & Agent Client

### `services/agent_client.py`

```python
# Internal async HTTP client to WayFindMCPClient

class AgentClient:
    def __init__(self, base_url: str, api_key: str):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Internal-Key": api_key},
            timeout=60.0
        )

    async def send_event(
        self,
        session_id: str,
        event: dict
    ) -> list[AgentEvent]:
        """POST /internal/sessions/{session_id}/events"""
        ...

    async def close(self) -> None:
        await self._client.aclose()
```

### `app/routes/messages.py`

```python
# POST /api/sessions/{session_id}/messages
# Auth: Bearer JWT
# Body: { "content": "string" }

@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: MessageRequest,
    current_session: str = Depends(verify_session_token),
    agent_client: AgentClient = Depends(get_agent_client),
) -> list[AgentEvent]:
    # 1. Verify session_id matches JWT session
    # 2. Check rate limit
    # 3. Forward to agent client
    # 4. Return agent events
    # 5. Update session last_active
    ...
```

---

## Phase 6 — SSE Event Stream

### `services/event_broker.py`

```python
# Manages in-memory SSE queues per session
# Agent events are pushed here; clients consume via GET /events

class EventBroker:
    async def push(self, session_id: str, event: AgentEvent) -> None:
    async def consume(self, session_id: str) -> AsyncGenerator[AgentEvent, None]:
    async def close_session(self, session_id: str) -> None:
```

### `app/routes/events.py`

```python
# GET /api/sessions/{session_id}/events
# Auth: Bearer JWT
# Returns: text/event-stream

@router.get("/sessions/{session_id}/events")
async def stream_events(
    session_id: str,
    current_session: str = Depends(verify_session_token),
    broker: EventBroker = Depends(get_event_broker),
) -> StreamingResponse:
    async def generate():
        async for event in broker.consume(session_id):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Alternative**: In v1 you can skip SSE and return events directly from `POST /messages`. Add SSE later when the frontend is ready to consume it. Start simple.

---

## Phase 7 — Image Upload

### `services/image_service.py`

```python
class ImageService:
    async def validate(self, file: UploadFile) -> None:
        """Reject if: wrong mime type, too large, not a real image."""
        ...

    async def safety_scan(self, file_bytes: bytes, mime_type: str) -> bool:
        """Call external safety scan service. Returns True if safe."""
        # Stub: always returns True in dev
        ...

    async def store(self, file_bytes: bytes, mime_type: str) -> str:
        """Store in object storage. Returns media_id."""
        # Stub: generate UUID, return as media_id
        ...
```

### `app/routes/images.py`

```python
# POST /api/sessions/{session_id}/images
# Auth: Bearer JWT
# Content-Type: multipart/form-data

@router.post("/sessions/{session_id}/images")
async def upload_image(
    session_id: str,
    file: UploadFile,
    current_session: str = Depends(verify_session_token),
    image_service: ImageService = Depends(get_image_service),
) -> ImageUploadResponse:
    # 1. Check rate limit
    # 2. Validate file type + size
    # 3. Safety scan
    # 4. Store → get media_id
    # 5. Return media_id (frontend attaches this to next message)
    ...
```

**Frontend flow**:
1. User selects image → `POST /images` → receives `media_id`
2. User sends message → `POST /messages` with `content` + `media_id`
3. Backend attaches `media_id` to agent event payload

---

## Phase 8 — Tests

### `tests/test_sessions.py`
- `POST /api/sessions` → 200, returns `session_id` + `token`
- JWT is valid and decodes to correct `session_id`

### `tests/test_messages.py`
- `POST /api/sessions/{id}/messages` with valid JWT → forwards to agent client
- Invalid JWT → 401
- Rate limit exceeded → 429
- Agent client error → 500 with safe message

### `tests/test_images.py`
- Upload valid JPEG → 200 + `media_id`
- Upload oversized file → 413
- Upload invalid type → 422
- Safety scan failure → 400 with safe message

### `tests/test_agent_client.py`
- Correct `X-Internal-Key` header forwarded
- Agent response parsed into `AgentEvent` list correctly
- Timeout → safe error returned

---

## Implementation Order

| Phase | Description | Deliverable |
|-------|-------------|-------------|
| 1 | Project setup | `pyproject.toml`, `.env.example`, `.gitignore`, `README.md` |
| 2 | App factory + schemas | `app/main.py`, `app/config.py`, `schemas/` |
| 3 | Sessions + auth | `app/auth.py`, `app/session.py`, `app/routes/sessions.py` |
| 4 | Rate limiting | `app/rate_limit.py` |
| 5 | Message endpoint + agent client | `services/agent_client.py`, `app/routes/messages.py` |
| 6 | SSE event stream | `services/event_broker.py`, `app/routes/events.py` |
| 7 | Image upload | `services/image_service.py`, `app/routes/images.py` |
| 8 | Tests | `tests/` |

---

## What Happens in Each User Turn

```text
User types: "I found a girl around 7 near Saddar"

  1. POST /api/sessions/{id}/messages { "content": "..." }
  2. Verify JWT → get session_id
  3. Check rate limit → OK
  4. POST /internal/sessions/{id}/events (-> WayFindMCPClient)
     { "event": { "type": "user_message", "content": "...", "media_id": null } }
  5. WayFindMCPClient runs LangGraph → returns events:
     [{ "type": "request_information", "fields": ["age", "clothing"] }]
  6. Return events to frontend
  7. Frontend renders: "Could you tell me approximately how old she is and what she was wearing?"
```

---

## Relationship to WayFindMCPClient

```text
ShelterAppUiBackend                WayFindMCPClient
─────────────────────              ───────────────────────
Owns: sessions, auth,              Owns: agent state, LangGraph,
      rate limits, CORS,                 MCP client, LLM, tools,
      image intake                       matching pipeline

Knows about: session_id,           Knows about: conversation history,
             media_id,                          intent, criteria,
             user content                       follow-up state

Does NOT know: LangGraph,          Does NOT know: who the user is,
               MCP tools,                        auth tokens,
               agent state                       rate limits
```

---

## Open Questions / Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | SSE vs poll for events? | Start with direct return from `POST /messages`; add SSE in Phase 6 |
| 2 | Image storage initially? | Local filesystem stub → real object storage later |
| 3 | Image safety scan initially? | Stub (always safe) → real scan service later |
| 4 | Account creation? | Not in v1; future: detect intent in chat and create account in-conversation |
| 5 | JWT secret rotation? | Single secret from `.env` for now |
