from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReferenceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=1024)
    authors: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None
    reference_type: str = "paper"


class ReferenceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    url: str | None = None
    authors: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    notes: str | None = None
    reference_type: str | None = None


class ReferenceResponse(BaseModel):
    id: int
    project_id: int
    owner_id: int
    title: str
    url: str | None
    authors: str | None
    year: int | None
    notes: str | None
    reference_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
