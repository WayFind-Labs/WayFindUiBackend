from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class MessageRequest(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    media_id: str | None = None
    form_data: dict[str, Any] | None = None


class AgentEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    content: str | None = None
    fields: list[str] | None = None
    results: list[dict[str, Any]] | None = None
    record_id: str | None = None
    media_id: str | None = None
    case_reference: str | None = None
    confidence_tier: str | None = None
    evidence: dict[str, Any] | None = None