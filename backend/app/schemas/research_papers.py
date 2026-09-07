from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResearchPaperCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="")


class ResearchPaperUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None


class ResearchPaperResponse(BaseModel):
    id: int
    project_id: int
    owner_id: int
    title: str
    content: str
    word_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
