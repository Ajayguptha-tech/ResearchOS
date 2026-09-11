"""Routes for paper drafts — CRUD + Paper Writing Agent."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import Paper, PaperDraft, PaperDraftVersion, Project, ResearchDocument, Reference
from app.schemas.paper_drafts import (
    PaperDraftCreate,
    PaperDraftResponse,
    PaperDraftUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_draft_for_user(db: Session, draft_id: int, user_id: int) -> PaperDraft:
    draft = (
        db.query(PaperDraft)
        .filter(PaperDraft.id == draft_id, PaperDraft.owner_id == user_id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return draft


def _get_project_for_user(db: Session, project_id: int, user_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/project/{project_id}", response_model=list[PaperDraftResponse])
def list_drafts(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """List all drafts for a project."""
    _get_project_for_user(db, project_id, user_id)
    drafts = (
        db.query(PaperDraft)
        .filter(PaperDraft.project_id == project_id, PaperDraft.owner_id == user_id)
        .order_by(PaperDraft.updated_at.desc())
        .all()
    )
    return [PaperDraftResponse.from_model(d) for d in drafts]


@router.post("/project/{project_id}", response_model=PaperDraftResponse, status_code=status.HTTP_201_CREATED)
def create_draft(
    project_id: int,
    payload: PaperDraftCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Create a new paper draft."""
    _get_project_for_user(db, project_id, user_id)
    draft = PaperDraft(
        project_id=project_id,
        owner_id=user_id,
        title=payload.title,
        instruction=payload.instruction,
        source_document_ids=json.dumps(payload.source_document_ids),
        source_paper_ids=json.dumps(payload.source_paper_ids),
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return PaperDraftResponse.from_model(draft)


@router.get("/{draft_id}", response_model=PaperDraftResponse)
def get_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Get a draft by ID with version history."""
    draft = _get_draft_for_user(db, draft_id, user_id)
    return PaperDraftResponse.from_model(draft)


@router.patch("/{draft_id}", response_model=PaperDraftResponse)
def update_draft(
    draft_id: int,
    payload: PaperDraftUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Update draft content (save new version)."""
    from datetime import datetime

    draft = _get_draft_for_user(db, draft_id, user_id)
    if payload.title is not None:
        draft.title = payload.title
    if payload.content is not None:
        draft.content = payload.content
        draft.word_count = len(payload.content.split()) if payload.content.strip() else 0
    # Create a version snapshot
    draft.current_version += 1
    version = PaperDraftVersion(
        draft_id=draft.id,
        version_number=draft.current_version,
        title=draft.title,
        content=draft.content,
        word_count=draft.word_count,
        instruction=draft.instruction,
    )
    db.add(version)
    draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)
    return PaperDraftResponse.from_model(draft)


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Delete a draft and its version history."""
    draft = _get_draft_for_user(db, draft_id, user_id)
    db.delete(draft)
    db.commit()


@router.post("/{draft_id}/generate")
def generate_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Generate / regenerate paper content using the Paper Writing Agent."""
    from datetime import datetime

    draft = _get_draft_for_user(db, draft_id, user_id)

    # Gather source documents
    try:
        raw_docs = json.loads(draft.source_document_ids) if draft.source_document_ids else []
        doc_ids = raw_docs if isinstance(raw_docs, list) else []
    except (json.JSONDecodeError, TypeError):
        doc_ids = []

    try:
        raw_papers = json.loads(draft.source_paper_ids) if draft.source_paper_ids else []
        paper_ids = raw_papers if isinstance(raw_papers, list) else []
    except (json.JSONDecodeError, TypeError):
        paper_ids = []

    source_contexts = []

    # Fetch document content - strictly scoped to this project
    if doc_ids:
        docs = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.id.in_(doc_ids),
                ResearchDocument.owner_id == user_id,
                ResearchDocument.project_id == draft.project_id,
            )
            .all()
        )
    else:
        # Use all documents belonging to this project if none explicitly selected
        docs = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.owner_id == user_id,
                ResearchDocument.project_id == draft.project_id,
            )
            .all()
        )

    # Persist the actual scoped source document IDs used
    draft.source_document_ids = json.dumps([doc.id for doc in docs])

    for doc in docs:
        source_contexts.append({
            "type": "document",
            "filename": doc.filename,
            "content": doc.extracted_text[:6000],
        })

    # Fetch paper metadata
    for pid in paper_ids:
        paper = (
            db.query(Paper)
            .filter(Paper.id == pid, Paper.owner_id == user_id)
            .first()
        )
        if paper:
            source_contexts.append({
                "type": "paper",
                "title": paper.title,
                "abstract": paper.abstract or "",
                "authors": paper.authors or "",
                "year": paper.year,
                "venue": paper.venue or "",
            })

    # Fetch project references
    refs = (
        db.query(Reference)
        .filter(
            Reference.project_id == draft.project_id,
            Reference.owner_id == user_id,
        )
        .all()
    )
    for ref in refs[:20]:
        source_contexts.append({
            "type": "reference",
            "title": ref.title,
            "url": ref.url or "",
            "authors": ref.authors or "",
            "year": ref.year,
        })

    # Try to generate using the Paper Writing Agent
    try:
        from ai.agents.paper_writing_agent import PaperWritingAgent

        agent = PaperWritingAgent()
        result = agent.generate(
            title=draft.title,
            instruction=draft.instruction or "",
            sources=source_contexts,
        )

        content = result.get("content", "")
        draft.content = content
        draft.word_count = len(content.split()) if content.strip() else 0
        draft.current_version += 1

        # Save version snapshot
        version = PaperDraftVersion(
            draft_id=draft.id,
            version_number=draft.current_version,
            title=draft.title,
            content=content,
            word_count=draft.word_count,
            instruction=draft.instruction,
        )
        db.add(version)
        draft.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(draft)

        return {
            "status": "success",
            "draft": PaperDraftResponse.from_model(draft).model_dump(),
            "message": f"Draft generated ({draft.word_count} words, version {draft.current_version})",
        }

    except Exception as exc:
        logger.error("[PaperDraft] Generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paper generation failed: {exc}",
        ) from exc


@router.get("/{draft_id}/versions", response_model=list[dict])
def list_versions(
    draft_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """List all version snapshots for a draft."""
    draft = _get_draft_for_user(db, draft_id, user_id)
    versions = (
        db.query(PaperDraftVersion)
        .filter(PaperDraftVersion.draft_id == draft.id)
        .order_by(PaperDraftVersion.version_number.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "title": v.title,
            "content": v.content[:200] + ("..." if len(v.content) > 200 else ""),
            "word_count": v.word_count,
            "created_at": v.created_at.isoformat() if v.created_at else "",
        }
        for v in versions
    ]
