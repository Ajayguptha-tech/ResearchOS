from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Item schemas ---

class EvidenceSessionItemCreate(BaseModel):
    item_type: str = Field(..., pattern=r"^(reference|document)$")
    item_id: int = Field(..., gt=0)
    note: str | None = None


class EvidenceSessionItemResponse(BaseModel):
    id: int
    session_id: int
    item_type: str
    item_id: int
    note: str | None
    created_at: datetime

    # Enriched fields from the linked reference/document
    title: str | None = None
    url: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Session schemas ---

class EvidenceSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    notes: str | None = None
    session_date: datetime | None = None
    status: str = "active"


class EvidenceSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    notes: str | None = None
    session_date: datetime | None = None
    status: str | None = None


class EvidenceSessionResponse(BaseModel):
    id: int
    project_id: int
    owner_id: int
    title: str
    description: str | None
    notes: str | None
    session_date: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[EvidenceSessionItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
