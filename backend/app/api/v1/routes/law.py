from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import LawResearchProject, LawResearchSource
from app.schemas.law import LawProjectCreate, LawProjectResponse, LawSourceCreate, LawSourceResponse

router = APIRouter()


def get_project(db: Session, project_id: int, user_id: int) -> LawResearchProject:
    project = db.query(LawResearchProject).filter(LawResearchProject.id == project_id, LawResearchProject.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal research project not found")
    return project


@router.post("/projects", response_model=LawProjectResponse, status_code=status.HTTP_201_CREATED)
def create_law_project(payload: LawProjectCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    project = LawResearchProject(user_id=user_id, **payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[LawProjectResponse])
def list_law_projects(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return db.query(LawResearchProject).filter(LawResearchProject.user_id == user_id).order_by(LawResearchProject.id.desc()).all()


@router.post("/projects/{project_id}/sources", response_model=LawSourceResponse, status_code=status.HTTP_201_CREATED)
def add_law_source(project_id: int, payload: LawSourceCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    get_project(db, project_id, user_id)
    source = LawResearchSource(project_id=project_id, **payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/projects/{project_id}/sources", response_model=list[LawSourceResponse])
def list_law_sources(project_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    get_project(db, project_id, user_id)
    return db.query(LawResearchSource).filter(LawResearchSource.project_id == project_id).order_by(LawResearchSource.id.asc()).all()
