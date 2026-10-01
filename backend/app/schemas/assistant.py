from pydantic import BaseModel, Field
from typing import Literal


class AssistantMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    project_id: int | None = None
    history: list[dict[str, str]] | None = Field(
        default=None,
        description="Optional conversation history: list of {role, content} dicts",
    )


class AssistantMessageResponse(BaseModel):
    reply: str
    source: str = "static"
