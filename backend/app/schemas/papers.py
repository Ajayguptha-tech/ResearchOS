from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaperCreate(BaseModel):
    title: str = Field(..., min_length=3)
    abstract: str | None = None
    authors: str | None = None
    venue: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    doi: str | None = None
    citation_count: int = Field(default=0, ge=0)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_level: str = "medium"
    is_recent: bool = False


class PaperUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3)
    abstract: str | None = None
    authors: str | None = None
    venue: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    doi: str | None = None
    citation_count: int | None = Field(default=None, ge=0)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_level: str | None = None
    is_recent: bool | None = None


class PaperResponse(PaperCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PaperImportRequest(BaseModel):
    papers: list[PaperCreate] = Field(..., min_length=1, max_length=100)


class ResearchDocumentResponse(BaseModel):
    id: int
    paper_id: int | None
    project_id: int | None = None
    filename: str
    content_type: str
    extracted_characters: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RetrievalResult(BaseModel):
    document_id: int
    filename: str
    paper_id: int | None
    score: float
    excerpt: str
    source: str = "local_uploaded_document"
