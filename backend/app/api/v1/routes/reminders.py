from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import UserReminder
from app.schemas.reminders import (
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)

router = APIRouter()


def _get_reminder(
    db: Session, reminder_id: int, user_id: int
) -> UserReminder:
    reminder = (
        db.query(UserReminder)
        .filter(
            UserReminder.id == reminder_id,
            UserReminder.user_id == user_id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )
    return reminder


@router.post(
    "/",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reminder(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReminderResponse:
    reminder = UserReminder(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        reminder_datetime=payload.reminder_datetime,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/", response_model=list[ReminderResponse])
def list_reminders(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> list[ReminderResponse]:
    return (
        db.query(UserReminder)
        .filter(UserReminder.user_id == user_id)
        .order_by(UserReminder.reminder_datetime.asc())
        .all()
    )


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReminderResponse:
    return _get_reminder(db, reminder_id, user_id)


@router.patch("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReminderResponse:
    reminder = _get_reminder(db, reminder_id, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    reminder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete(
    "/{reminder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> None:
    reminder = _get_reminder(db, reminder_id, user_id)
    db.delete(reminder)
    db.commit()


@router.post(
    "/{reminder_id}/complete",
    response_model=ReminderResponse,
)
def complete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReminderResponse:
    reminder = _get_reminder(db, reminder_id, user_id)
    reminder.status = "completed"
    reminder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(reminder)
    return reminder
