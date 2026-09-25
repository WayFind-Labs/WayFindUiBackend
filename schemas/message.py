from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    media_id: str | None = None


class AgentEvent(BaseModel):
    type: str
    content: str | None = None
    fields: list[str] | None = None
    results: list[dict] | None = None
    record_id: str | None = None
    media_id: str | None = None