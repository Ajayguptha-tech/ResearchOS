"""Routes for per-project research paper editing.

Users write and save their research paper content within a project workspace.
Each project can have one research paper (the user's own writing, NOT imported papers).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import Project, ResearchPaper
from app.schemas.research_papers import (
    ResearchPaperCreate,
    ResearchPaperResponse,
    ResearchPaperUpdate,
)

router = APIRouter()


def _get_paper_for_user(
    db: Session, paper_id: int, user_id: int
) -> ResearchPaper:
    paper = (
        db.query(ResearchPaper)
        .filter(
            ResearchPaper.id == paper_id,
            ResearchPaper.owner_id == user_id,
        )
        .first()
    )
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research paper not found",
        )
    return paper


def _get_project_for_user(
    db: Session, project_id: int, user_id: int
) -> Project:
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@router.get(
    "/project/{project_id}",
    response_model=ResearchPaperResponse | None,
)
def get_project_paper(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ResearchPaper | None:
    """Get the research paper for a project, or null if none exists yet."""
    _get_project_for_user(db, project_id, user_id)
    paper = (
        db.query(ResearchPaper)
        .filter(
            ResearchPaper.project_id == project_id,
            ResearchPaper.owner_id == user_id,
        )
        .first()
    )
    return paper


@router.post(
    "/project/{project_id}",
    response_model=ResearchPaperResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_or_update_project_paper(
    project_id: int,
    payload: ResearchPaperCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ResearchPaper:
    """Create a new research paper for the project, or update the existing one."""
    _get_project_for_user(db, project_id, user_id)

    existing = (
        db.query(ResearchPaper)
        .filter(
            ResearchPaper.project_id == project_id,
            ResearchPaper.owner_id == user_id,
        )
        .first()
    )

    if existing:
        existing.title = payload.title
        existing.content = payload.content
        existing.word_count = len(payload.content.split()) if payload.content.strip() else 0
        db.commit()
        db.refresh(existing)
        return existing

    paper = ResearchPaper(
        project_id=project_id,
        owner_id=user_id,
        title=payload.title,
        content=payload.content,
        word_count=len(payload.content.split()) if payload.content.strip() else 0,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.patch(
    "/{paper_id}",
    response_model=ResearchPaperResponse,
)
def update_research_paper(
    paper_id: int,
    payload: ResearchPaperUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ResearchPaper:
    """Update a research paper by ID (for autosave)."""
    paper = _get_paper_for_user(db, paper_id, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)
    if payload.content is not None:
        paper.word_count = len(payload.content.split()) if payload.content.strip() else 0
    from datetime import datetime
    paper.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(paper)
    return paper
