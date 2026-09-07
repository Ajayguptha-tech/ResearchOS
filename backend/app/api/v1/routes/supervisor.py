from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_supervisor
from app.db.models import Notification, Project, SupervisorFeedback
from app.schemas.reviews import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.get("/dashboard")
def supervisor_dashboard(_: object = Depends(require_supervisor), db: Session = Depends(get_db)):
    return {
        "pending_reviews": db.query(SupervisorFeedback).filter(SupervisorFeedback.decision == "changes_requested").count(),
        "approved": db.query(SupervisorFeedback).filter(SupervisorFeedback.decision == "approved").count(),
        "rejected": db.query(SupervisorFeedback).filter(SupervisorFeedback.decision == "rejected").count(),
    }


@router.post("/projects/{project_id}/feedback", response_model=FeedbackResponse)
def submit_review(
    project_id: int,
    payload: FeedbackCreate,
    supervisor=Depends(require_supervisor),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    feedback = SupervisorFeedback(
        project_id=project_id,
        reviewer_id=supervisor.id,
        decision=payload.decision,
        message=payload.message,
    )
    notification = Notification(
        user_id=project.owner_id,
        type="supervisor_review",
        message=f"Your project received a {payload.decision} review: {payload.message}",
    )
    db.add_all([feedback, notification])
    db.commit()
    db.refresh(feedback)
    return feedback
