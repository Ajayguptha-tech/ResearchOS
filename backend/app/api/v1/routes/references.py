from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import Project, Reference
from app.schemas.references import (
    ReferenceCreate,
    ReferenceResponse,
    ReferenceUpdate,
)

router = APIRouter()


def _get_reference(db: Session, ref_id: int, user_id: int) -> Reference:
    ref = (
        db.query(Reference)
        .filter(Reference.id == ref_id, Reference.owner_id == user_id)
        .first()
    )
    if not ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference not found",
        )
    return ref


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


@router.get(
    "/project/{project_id}",
    response_model=list[ReferenceResponse],
)
def list_references(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> list[ReferenceResponse]:
    _verify_project(db, project_id, user_id)
    refs = (
        db.query(Reference)
        .filter(
            Reference.project_id == project_id,
            Reference.owner_id == user_id,
        )
        .order_by(Reference.created_at.desc())
        .all()
    )
    return refs


@router.post(
    "/project/{project_id}",
    response_model=ReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reference(
    project_id: int,
    payload: ReferenceCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReferenceResponse:
    _verify_project(db, project_id, user_id)
    ref = Reference(
        project_id=project_id,
        owner_id=user_id,
        title=payload.title,
        url=payload.url,
        authors=payload.authors,
        year=payload.year,
        notes=payload.notes,
        reference_type=payload.reference_type,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


@router.get(
    "/{ref_id}",
    response_model=ReferenceResponse,
)
def get_reference(
    ref_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReferenceResponse:
    return _get_reference(db, ref_id, user_id)


@router.patch(
    "/{ref_id}",
    response_model=ReferenceResponse,
)
def update_reference(
    ref_id: int,
    payload: ReferenceUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReferenceResponse:
    ref = _get_reference(db, ref_id, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ref, field, value)
    db.commit()
    db.refresh(ref)
    return ref


@router.delete(
    "/{ref_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference(
    ref_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> None:
    ref = _get_reference(db, ref_id, user_id)
    db.delete(ref)
    db.commit()
