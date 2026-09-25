# Shelter Backend — Architecture & Context

**Repository**: `e:\React\Shelter\ShelterAppUiBackend`  
**Date**: 2026-09-25  
**Role**: API Gateway — sits between the Next.js PWA and the WayFindMCPClient agent layer

---

## What Is This Repository?

`ShelterAppUiBackend` is the **public-facing FastAPI backend** for the Wayfind application.

It is the **only service** that the Next.js PWA (`ShelterApp ui`) communicates with. It acts as:
- The public API gateway
- The authentication and session authority
- The image/file intake and safety scan layer
- The rate limiter and request validator
- The SSE event stream broker to the frontend
- The internal caller of `WayFindMCPClient`

**It does NOT contain any AI logic, LangGraph, or MCP code.**

---

## Full System Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                        Next.js PWA                               │
│                      (ShelterApp ui)                             │
│                                                                  │
│  User Chat | Child Submission | Image Upload | Results           │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │  HTTPS + SSE
                           │  POST /api/sessions
                           │  POST /api/sessions/{id}/messages
                           │  GET  /api/sessions/{id}/events   <- SSE
                           │  POST /api/sessions/{id}/images
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   ShelterAppUiBackend                            │
│                       FastAPI                                    │
│                                                                  │
│  /api/sessions          <- Create / resume session               │
│  /api/sessions/{id}/messages  <- User sends a message           │
│  /api/sessions/{id}/events    <- SSE event stream               │
│  /api/sessions/{id}/images    <- Image upload endpoint          │
│                                                                  │
│  ┌──────────────┐  ┌──────────┐  ┌───────────┐  ┌───────────┐  │
│  │     Auth     │  │ Sessions │  │ Validation│  │Rate Limit │  │
│  └──────────────┘  └──────────┘  └───────────┘  └───────────┘  │
│  ┌──────────────┐  ┌──────────┐                                  │
│  │ Image Intake │  │  CORS    │                                  │
│  │ Safety Scan  │  │          │                                  │
│  └──────────────┘  └──────────┘                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           │  Internal HTTP (Docker network)
                           │  POST /internal/sessions/{id}/events
                           │  X-Internal-Key: <shared secret>
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    WayFindMCPClient                               │
│                   Internal Agent API                             │
│                                                                  │
│  LangGraph | MCP Client | LLM (Gemini)                          │
│  Intent detection | Follow-up loop | Search pipeline            │
│                                                                  │
│                          │                                       │
│                    MCP protocol (SSE)                            │
│                          │                                       │
│                   FastMCP Server                                 │
│  search_child_records   submit_found_child_report               │
│  image_match_candidates  search_support                         │
│  get_guidance            get_case_status                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      PostgreSQL          RAG          Image/Vector
                                       (Qdrant)
                  ┌────────┘
                  ▼
             Support/Location
```

---

## Responsibility Boundaries

### ShelterAppUiBackend owns:
- **All public HTTP/SSE endpoints** (the browser never talks to anything else)
- **Authentication** — anonymous JWT session tokens initially; account auth in future
- **Session lifecycle** — create, resume, store in Redis
- **Request validation** — reject malformed, oversized, or abusive requests
- **Rate limiting** — per session, per IP
- **CORS** — only allow the Next.js PWA origin
- **Image upload intake** — receive multipart file, run safety scan, store, get `media_id`
- **Event brokering** — receive agent events from `WayFindMCPClient`, stream to frontend via SSE
- **Internal API call** — call `WayFindMCPClient` with `session_id` + event payload

### ShelterAppUiBackend does NOT own:
- Any AI, LLM, or agent logic
- LangGraph, MCP, or tool orchestration
- Database reads/writes (PostgreSQL, Qdrant)
- RAG queries
- Matching or confidence scoring

---

## API Contract — Frontend to ShelterAppUiBackend

### Create / resume session
```
POST /api/sessions
Response: { "session_id": "uuid", "token": "jwt" }
```

### Send a message
```
POST /api/sessions/{session_id}/messages
Authorization: Bearer <token>
Content-Type: application/json
{ "content": "I found a girl near Saddar" }
```

### Upload an image
```
POST /api/sessions/{session_id}/images
Authorization: Bearer <token>
Content-Type: multipart/form-data
file: <image bytes>

Response: { "media_id": "internal-id" }
```

### Stream agent events (SSE)
```
GET /api/sessions/{session_id}/events
Authorization: Bearer <token>

Stream:
  data: {"type": "assistant_message", "content": "How old is she approximately?"}
  data: {"type": "request_information", "fields": ["age", "clothing"]}
  data: {"type": "search_results", "results": [...]}
  data: {"type": "submission_complete", "record_id": "..."}
```

---

## API Contract — ShelterAppUiBackend to WayFindMCPClient (internal)

```
POST /internal/sessions/{session_id}/events
X-Internal-Key: <shared secret>
Content-Type: application/json
{
    "event": {
        "type": "user_message",
        "content": "I found a girl near Saddar",
        "media_id": null,
        "form_data": null
    }
}

Response: JSON array of agent events
[
    { "type": "assistant_message", "content": "..." },
    { "type": "request_information", "fields": ["age"] }
]
```

---

## Agent Event Types

The following event types flow from `WayFindMCPClient` → `ShelterAppUiBackend` → Frontend:

| Event Type | Direction | Description |
|-----------|-----------|-------------|
| `assistant_message` | Agent → UI | A conversational message from the agent |
| `request_information` | Agent → UI | Agent needs more info; frontend renders a form |
| `request_image` | Agent → UI | Agent is asking the user to upload a photo |
| `search_started` | Agent → UI | Signal that a search is running (show spinner) |
| `search_results` | Agent → UI | Candidate results (safe, no PII) |
| `submission_complete` | Agent → UI | Report submitted; includes `record_id` |
| `review_pending` | Agent → UI | Possible match found; under human review |
| `error` | Agent → UI | Something failed; safe user-facing message |

---

## Authentication Model

### Phase 1 (current): Anonymous sessions
- Frontend creates a session on first load → gets `session_id` + `JWT`
- JWT encodes `session_id` + expiry only (no user identity)
- All endpoints are session-scoped, not user-scoped

### Future: Account-based auth
- User provides name, email, and password within the chat prompt
- Backend detects this intent and creates a Wayfind account in-conversation
- Account links to sessions and enables:
  - Notifications when a matching child is found
  - Case status updates
  - Report history

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.12+) |
| Package manager | uv |
| Session store | Redis |
| Auth tokens | PyJWT |
| Image safety scan | Stub → real scan service |
| Image storage | Stub → object storage (S3/GCS) |
| Rate limiting | slowapi or custom middleware |
| SSE streaming | FastAPI `StreamingResponse` with `text/event-stream` |
| Internal HTTP client | httpx (async) |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio |

---

## Directory Structure Target

```text
ShelterAppUiBackend/
├── skills/
│   ├── context.md                           THIS FILE
│   └── implementation_plan.md              Implementation phases
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
|
├── app/
│   ├── __init__.py
│   ├── main.py                              <- FastAPI app factory + SSE + CORS
│   ├── config.py                            <- Pydantic Settings
│   ├── auth.py                              <- JWT session token logic
│   ├── session.py                           <- Redis session store
│   ├── rate_limit.py                        <- Per-session/IP rate limiter
│   └── routes/
│       ├── __init__.py
│       ├── sessions.py                      <- POST /api/sessions
│       ├── messages.py                      <- POST /api/sessions/{id}/messages
│       ├── events.py                        <- GET /api/sessions/{id}/events (SSE)
│       └── images.py                        <- POST /api/sessions/{id}/images
|
├── services/
│   ├── __init__.py
│   ├── agent_client.py                      <- Internal httpx client -> WayFindMCPClient
│   ├── image_service.py                     <- Safety scan + storage
│   └── event_broker.py                      <- Fan-out agent events to SSE stream
|
├── schemas/
│   ├── __init__.py
│   ├── session.py                           <- SessionCreate, SessionResponse
│   ├── message.py                           <- MessageRequest, AgentEvent
│   └── image.py                             <- ImageUploadResponse
|
└── tests/
    ├── __init__.py
    ├── test_sessions.py
    ├── test_messages.py
    ├── test_images.py
    └── test_agent_client.py
```

---

## Environment Variables

```env
# Server
SECRET_KEY=changeme-jwt-secret
CORS_ORIGINS=["http://localhost:3000"]
HOST=0.0.0.0
PORT=8001

# Redis
REDIS_URL=redis://localhost:6379

# Rate limiting
RATE_LIMIT_MESSAGES_PER_MINUTE=20
RATE_LIMIT_IMAGES_PER_HOUR=10

# Internal agent service (WayFindMCPClient)
AGENT_SERVICE_URL=http://localhost:8000
SHELTER_BACKEND_API_KEY=changeme-dev-secret

# Image intake
MAX_IMAGE_SIZE_MB=10
ALLOWED_IMAGE_TYPES=["image/jpeg", "image/png", "image/webp"]
IMAGE_SAFETY_SCAN_URL=http://localhost:9000  # stub initially
IMAGE_STORAGE_URL=http://localhost:9001      # stub initially

# JWT
JWT_ALGORITHM=HS256
JWT_SESSION_EXPIRY_HOURS=24
```

---

## Security Principles

1. **The browser never calls `WayFindMCPClient` directly** — all traffic goes through this service
2. **The internal API key is never exposed to the frontend** — it lives only in server env
3. **Images are scanned before storage** — `media_id` is only returned after a clean scan
4. **No PII is logged** — session IDs only in logs; no user content
5. **JWT is session-scoped** — no user identity until account feature is implemented
6. **Rate limiting prevents abuse** — applied before forwarding to agent service
7. **All errors return safe messages** — no stack traces, no internal URLs

---

## Deployment (Docker Compose)

```yaml
services:
  shelter-ui:
    build: ./ShelterApp ui
    ports: ["3000:3000"]

  shelter-backend:
    build: ./ShelterAppUiBackend
    ports: ["8001:8001"]
    environment:
      AGENT_SERVICE_URL: http://wayfind-agent:8000
      REDIS_URL: redis://redis:6379
    depends_on: [redis, wayfind-agent]

  wayfind-agent:
    build: ./WayFindMCPClient
    ports: ["8000:8000"]   # internal only; not exposed publicly
    environment:
      SHELTER_BACKEND_API_KEY: changeme-dev-secret
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

---

## Key Principle

> **Frontend talks to Shelter Backend.**  
> **Shelter Backend talks to LangGraph (WayFindMCPClient).**  
> **LangGraph talks to MCP.**  
> **MCP talks to your actual capabilities/data.**  
>
> Each layer has one job. The frontend never knows that LangGraph or MCP exist.
