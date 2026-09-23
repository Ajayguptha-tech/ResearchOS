from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import NotificationPreference, Project, Reminder, ResearchFollowUp
from app.schemas.followups import FollowUpCreate, FollowUpResponse, FollowUpUpdate, PreferenceResponse, PreferenceUpdate, ReminderCreate, ReminderResponse

router = APIRouter()


def get_followup(db: Session, followup_id: int, user_id: int) -> ResearchFollowUp:
    followup = db.query(ResearchFollowUp).filter(ResearchFollowUp.id == followup_id, ResearchFollowUp.user_id == user_id).first()
    if not followup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    return followup


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_followup(payload: FollowUpCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    if payload.project_id is not None and not db.query(Project).filter(Project.id == payload.project_id, Project.owner_id == user_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    followup = ResearchFollowUp(user_id=user_id, **payload.model_dump())
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


@router.get("", response_model=list[FollowUpResponse])
@router.get("/", response_model=list[FollowUpResponse])
def list_followups(project_id: int | None = Query(default=None), db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    query = db.query(ResearchFollowUp).filter(ResearchFollowUp.user_id == user_id)
    if project_id is not None:
        query = query.filter(ResearchFollowUp.project_id == project_id)
    return query.order_by(ResearchFollowUp.due_at.asc(), ResearchFollowUp.id.asc()).all()


@router.get("/preferences/me", response_model=PreferenceResponse)
def get_preferences(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    preference = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not preference:
        preference = NotificationPreference(user_id=user_id)
        db.add(preference)
        db.commit()
        db.refresh(preference)
    return preference


@router.patch("/preferences/me", response_model=PreferenceResponse)
def update_preferences(payload: PreferenceUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    preference = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not preference:
        preference = NotificationPreference(user_id=user_id)
        db.add(preference)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(preference, field, value)
    if preference.voice_enabled and not preference.phone_consent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Voice notifications require explicit phone consent")
    db.commit()
    db.refresh(preference)
    return preference


@router.get("/{followup_id}", response_model=FollowUpResponse)
def read_followup(followup_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return get_followup(db, followup_id, user_id)


@router.patch("/{followup_id}", response_model=FollowUpResponse)
def update_followup(followup_id: int, payload: FollowUpUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    followup = get_followup(db, followup_id, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(followup, field, value)
    db.commit()
    db.refresh(followup)
    return followup


@router.delete("/{followup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_followup(followup_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    db.delete(get_followup(db, followup_id, user_id))
    db.commit()


@router.post("/{followup_id}/complete", response_model=FollowUpResponse)
def complete_followup(followup_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    followup = get_followup(db, followup_id, user_id)
    followup.status = "completed"
    followup.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(followup)
    return followup


@router.post("/{followup_id}/snooze", response_model=FollowUpResponse)
def snooze_followup(followup_id: int, hours: int = 24, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    if hours < 1 or hours > 720:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Snooze duration must be between 1 and 720 hours")
    followup = get_followup(db, followup_id, user_id)
    followup.status = "snoozed"
    followup.snoozed_until = datetime.utcnow() + timedelta(hours=hours)
    db.commit()
    db.refresh(followup)
    return followup


@router.post("/{followup_id}/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(followup_id: int, payload: ReminderCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    if payload.followup_id != followup_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Follow-up ID does not match request path")
    get_followup(db, followup_id, user_id)
    if payload.channel == "voice":
        preference = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
        if not preference or not preference.phone_consent or not preference.voice_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Phone reminders require explicit consent and voice notifications enabled")
    reminder = Reminder(**payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


