import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.repositories.project_repository import ProjectRepository
from app.db.models import AnalysisResult, ResearchDocument, ResearchIdea, ResearchPaper, ResearchPlan
from app.schemas.research import PlanCreateRequest, ProjectCreateRequest, ResearchIdeaRequest
from app.services.roadmap_service import RoadmapService

router = APIRouter()


@router.post("")
@router.post("/")
def create_project(payload: ProjectCreateRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    repo = ProjectRepository(db)
    project = repo.create(payload.title, payload.domain, owner_id=user_id, description=payload.description)
    return {"id": project.id, "title": project.title, "domain": project.domain, "description": getattr(project, 'description', None), "status": project.status, "user_id": user_id}


@router.get("")
@router.get("/")
def list_projects(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    projects = ProjectRepository(db).list_for_owner(user_id)
    result = []
    for project in projects:
        doc_count = db.query(ResearchDocument).filter(ResearchDocument.project_id == project.id, ResearchDocument.owner_id == user_id).count()
        result.append({
            "id": project.id,
            "title": project.title,
            "domain": project.domain,
            "description": getattr(project, 'description', None),
            "status": project.status,
            "document_count": doc_count,
        })
    return result


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    repo = ProjectRepository(db)
    project = repo.get_for_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    doc_count = db.query(ResearchDocument).filter(ResearchDocument.project_id == project.id, ResearchDocument.owner_id == user_id).count()
    analysis_count = db.query(AnalysisResult).filter(AnalysisResult.project_id == project.id, AnalysisResult.owner_id == user_id).count()
    return {
        "id": project.id,
        "title": project.title,
        "domain": project.domain,
        "description": getattr(project, 'description', None),
        "status": project.status,
        "document_count": doc_count,
        "analysis_count": analysis_count,
        "ideas": [
            {"id": idea.id, "title": idea.title, "description": idea.description, "status": idea.status}
            for idea in project.ideas
        ],
        "plans": [
            {"id": plan.id, "idea_id": plan.idea_id, "steps": plan.steps, "status": plan.status}
            for plan in project.plans
        ],
    }


@router.post("/{project_id}/ideas")
def create_idea(
    project_id: int,
    payload: ResearchIdeaRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    project = ProjectRepository(db).get_for_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    idea = ResearchIdea(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return {"id": idea.id, "title": idea.title, "description": idea.description, "status": idea.status}


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> None:
    """Delete a project and all its owned resources."""
    repo = ProjectRepository(db)
    project = repo.get_for_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Remove stored document files
    docs = db.query(ResearchDocument).filter(
        ResearchDocument.project_id == project_id,
        ResearchDocument.owner_id == user_id,
    ).all()
    for doc in docs:
        try:
            file_path = Path(doc.storage_path)
            if file_path.is_file():
                os.remove(file_path)
        except Exception:
            pass

    # Delete project (cascades through relationships where configured)
    db.delete(project)
    db.commit()


@router.post("/{project_id}/plan")
def generate_plan(
    project_id: int,
    payload: PlanCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    project = ProjectRepository(db).get_for_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    idea = db.query(ResearchIdea).filter(ResearchIdea.id == payload.idea_id, ResearchIdea.project_id == project_id).first() if payload.idea_id else None
    roadmap = RoadmapService().build(idea.description if idea else f"Research in {project.domain}")
    plan = ResearchPlan(project_id=project_id, idea_id=idea.id if idea else None, steps=roadmap["plan"])
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"id": plan.id, "project_id": project_id, "idea_id": plan.idea_id, "steps": plan.steps, "status": plan.status}
