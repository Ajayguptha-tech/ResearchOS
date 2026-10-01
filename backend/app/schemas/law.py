from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["fact", "source", "inference", "suggestion"]


class LawProjectCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    legal_question: str = Field(..., min_length=10)
    jurisdiction: str | None = Field(default=None, max_length=128)


class LawProjectResponse(BaseModel):
    id: int
    title: str
    legal_question: str
    jurisdiction: str | None
    disclaimer: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LawSourceCreate(BaseModel):
    label: str = Field(..., min_length=3, max_length=255)
    source_url: str = Field(..., min_length=8, max_length=1024)
    source_type: SourceType
    excerpt: str | None = None


class LawSourceResponse(LawSourceCreate):
    id: int
    project_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
