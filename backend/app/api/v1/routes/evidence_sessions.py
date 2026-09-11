"""Evidence Session CRUD routes.

Provides full Create / Read / Update / Delete for evidence-gathering sessions
and the ability to attach / detach references and documents to sessions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import (
    EvidenceSession,
    EvidenceSessionItem,
    Project,
    Reference,
    ResearchDocument,
)
from app.schemas.evidence_sessions import (
    EvidenceSessionCreate,
    EvidenceSessionItemCreate,
    EvidenceSessionItemResponse,
    EvidenceSessionResponse,
    EvidenceSessionUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_project(db: Session, project_id: int, user_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _get_session(db: Session, session_id: int, user_id: int) -> EvidenceSession:
    sess = (
        db.query(EvidenceSession)
        .filter(
            EvidenceSession.id == session_id,
            EvidenceSession.owner_id == user_id,
        )
        .first()
    )
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence session not found",
        )
    return sess


def _enrich_item(
    db: Session, item: EvidenceSessionItem, user_id: int
) -> EvidenceSessionItemResponse:
    """Attach human-readable title/url from the linked reference or document."""
    resp = EvidenceSessionItemResponse.model_validate(item)
    if item.item_type == "reference":
        ref = (
            db.query(Reference)
            .filter(Reference.id == item.item_id, Reference.owner_id == user_id)
            .first()
        )
        if ref:
            resp.title = ref.title
            resp.url = ref.url
    elif item.item_type == "document":
        doc = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.id == item.item_id,
                ResearchDocument.owner_id == user_id,
            )
            .first()
        )
        if doc:
            resp.title = doc.filename
    return resp


def _enrich_session(
    db: Session, sess: EvidenceSession, user_id: int
) -> EvidenceSessionResponse:
    resp = EvidenceSessionResponse.model_validate(sess)
    resp.items = [_enrich_item(db, item, user_id) for item in sess.items]
    return resp


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get(
    "/project/{project_id}",
    response_model=list[EvidenceSessionResponse],
)
def list_sessions(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> list[EvidenceSessionResponse]:
    _verify_project(db, project_id, user_id)
    sessions = (
        db.query(EvidenceSession)
        .filter(
            EvidenceSession.project_id == project_id,
            EvidenceSession.owner_id == user_id,
        )
        .order_by(EvidenceSession.created_at.desc())
        .all()
    )
    return [_enrich_session(db, s, user_id) for s in sessions]


@router.post(
    "/project/{project_id}",
    response_model=EvidenceSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    project_id: int,
    payload: EvidenceSessionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> EvidenceSessionResponse:
    _verify_project(db, project_id, user_id)
    sess = EvidenceSession(
        project_id=project_id,
        owner_id=user_id,
        title=payload.title,
        description=payload.description,
        notes=payload.notes,
        session_date=payload.session_date,
        status=payload.status,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return _enrich_session(db, sess, user_id)


@router.get(
    "/{session_id}",
    response_model=EvidenceSessionResponse,
)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> EvidenceSessionResponse:
    sess = _get_session(db, session_id, user_id)
    return _enrich_session(db, sess, user_id)


@router.patch(
    "/{session_id}",
    response_model=EvidenceSessionResponse,
)
def update_session(
    session_id: int,
    payload: EvidenceSessionUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> EvidenceSessionResponse:
    sess = _get_session(db, session_id, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sess, field, value)
    db.commit()
    db.refresh(sess)
    return _enrich_session(db, sess, user_id)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> None:
    sess = _get_session(db, session_id, user_id)
    db.delete(sess)
    db.commit()


# ---------------------------------------------------------------------------
# Attach / detach items (references or documents)
# ---------------------------------------------------------------------------

@router.post(
    "/{session_id}/items",
    response_model=EvidenceSessionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_item(
    session_id: int,
    payload: EvidenceSessionItemCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> EvidenceSessionItemResponse:
    sess = _get_session(db, session_id, user_id)

    # Verify the linked resource exists and belongs to the user
    if payload.item_type == "reference":
        ref = (
            db.query(Reference)
            .filter(Reference.id == payload.item_id, Reference.owner_id == user_id)
            .first()
        )
        if not ref:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference not found",
            )
        # Must belong to the same project
        if ref.project_id != sess.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference does not belong to this project",
            )
    elif payload.item_type == "document":
        doc = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.id == payload.item_id,
                ResearchDocument.owner_id == user_id,
            )
            .first()
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        if doc.project_id != sess.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document does not belong to this project",
            )

    # Prevent duplicates
    existing = (
        db.query(EvidenceSessionItem)
        .filter(
            EvidenceSessionItem.session_id == session_id,
            EvidenceSessionItem.item_type == payload.item_type,
            EvidenceSessionItem.item_id == payload.item_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item already attached to this session",
        )

    item = EvidenceSessionItem(
        session_id=session_id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        note=payload.note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _enrich_item(db, item, user_id)


@router.delete(
    "/{session_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_item(
    session_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> None:
    sess = _get_session(db, session_id, user_id)
    item = (
        db.query(EvidenceSessionItem)
        .filter(
            EvidenceSessionItem.id == item_id,
            EvidenceSessionItem.session_id == session_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session item not found",
        )
    db.delete(item)
    db.commit()
