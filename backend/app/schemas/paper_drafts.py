from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaperDraftCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    instruction: str | None = None
    source_document_ids: list[int] = Field(default_factory=list)
    source_paper_ids: list[int] = Field(default_factory=list)


class PaperDraftUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None


class PaperDraftVersionResponse(BaseModel):
    id: int
    draft_id: int
    version_number: int
    title: str
    content: str
    word_count: int
    instruction: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperDraftResponse(BaseModel):
    id: int
    project_id: int
    owner_id: int
    title: str
    instruction: str | None
    content: str
    word_count: int
    status: str
    source_document_ids: list[int] = Field(default_factory=list)
    source_paper_ids: list[int] = Field(default_factory=list)
    current_version: int
    draft_classification: str = "AI-Generated Research Paper Draft / Reference"
    is_published: bool = False
    created_at: datetime
    updated_at: datetime
    versions: list[PaperDraftVersionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, draft):
        import json
        doc_ids = []
        paper_ids = []
        try:
            val = json.loads(draft.source_document_ids) if draft.source_document_ids else []
            doc_ids = val if isinstance(val, list) else []
        except (json.JSONDecodeError, TypeError):
            doc_ids = []
        try:
            val_p = json.loads(draft.source_paper_ids) if draft.source_paper_ids else []
            paper_ids = val_p if isinstance(val_p, list) else []
        except (json.JSONDecodeError, TypeError):
            paper_ids = []

        return cls(
            id=draft.id,
            project_id=draft.project_id,
            owner_id=draft.owner_id,
            title=draft.title,
            instruction=draft.instruction,
            content=draft.content,
            word_count=draft.word_count,
            status=draft.status,
            source_document_ids=doc_ids,
            source_paper_ids=paper_ids,
            current_version=draft.current_version,
            draft_classification="AI-Generated Research Paper Draft / Reference",
            is_published=False,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            versions=[
                PaperDraftVersionResponse.model_validate(v)
                for v in getattr(draft, 'versions', [])
            ],
        )
