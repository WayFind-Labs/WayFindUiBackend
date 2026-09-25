# WayFind UI Backend

Public FastAPI gateway between the WayFind Next.js PWA and the internal
WayFindMCPClient agent service.

## Architecture

```text
Next.js PWA -- HTTPS/SSE --> this gateway -- internal HTTP --> WayFindMCPClient
                                  |
                                  +-- sessions, JWT auth, validation, rate limits
                                  +-- image intake and event streaming
```

The browser communicates only with this service. AI, LangGraph, MCP
orchestration, and database access remain inside `WayFindMCPClient`.

## Development setup

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```powershell
Copy-Item .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`. Redis and the internal
agent service must be running before the session and message endpoints are
used.

## Project guidance

Architecture boundaries and API contracts are documented in
`skills/context.md`. The phased delivery checklist is in
`skills/implementation_plan.md`.