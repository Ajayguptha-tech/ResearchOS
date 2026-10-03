from datetime import datetime, timezone
import zoneinfo

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


def _canonical_timezone(tz_name: str | None) -> str:
    """Normalize timezone name, aliasing legacy/abbreviated names to canonical IANA."""
    if not tz_name or not tz_name.strip():
        return "Asia/Kolkata"
    cleaned = tz_name.strip()
    if cleaned in ("Asia/Calcutta", "IST"):
        return "Asia/Kolkata"
    try:
        zoneinfo.ZoneInfo(cleaned)
        return cleaned
    except Exception:
        return "Asia/Kolkata"


def _normalize_to_utc(dt: datetime | str, tz_name: str | None = None) -> datetime:
    """Normalize a datetime or string to UTC, interpreting naive datetimes in the specified timezone."""
    canonical_tz = _canonical_timezone(tz_name)
    try:
        target_tz = zoneinfo.ZoneInfo(canonical_tz)
    except Exception:
        target_tz = timezone.utc

    if isinstance(dt, str):
        clean_str = dt.strip()
        parsed = datetime.fromisoformat(clean_str)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=target_tz).astimezone(timezone.utc)
        return parsed.astimezone(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=target_tz)
    return dt.astimezone(timezone.utc)


@router.post(
    "",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
)
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
    tz_name = _canonical_timezone(payload.timezone)
    utc_dt = _normalize_to_utc(payload.reminder_datetime, tz_name)

    reminder = UserReminder(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        reminder_datetime=utc_dt.replace(tzinfo=None),
        timezone=tz_name,
        status="pending",
        email_sent=False,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("", response_model=list[ReminderResponse])
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
    now_utc = datetime.now(timezone.utc)

    if payload.timezone is not None:
        reminder.timezone = payload.timezone

    if payload.title is not None:
        reminder.title = payload.title

    if payload.description is not None:
        reminder.description = payload.description

    if payload.status is not None:
        reminder.status = payload.status

    if payload.reminder_datetime is not None:
        utc_dt = _normalize_to_utc(payload.reminder_datetime, reminder.timezone)
        reminder.reminder_datetime = utc_dt.replace(tzinfo=None)
        # If rescheduled to a future time, reset email status so it can trigger at the new time
        if utc_dt > now_utc and reminder.status in ("sent", "completed", "cancelled"):
            reminder.status = "pending"
            reminder.email_sent = False
            reminder.email_sent_at = None
            reminder.last_error = None

    reminder.updated_at = now_utc.replace(tzinfo=None)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.post(
    "/{reminder_id}/cancel",
    response_model=ReminderResponse,
)
def cancel_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReminderResponse:
    """Cancel a reminder so it will not dispatch any notifications."""
    reminder = _get_reminder(db, reminder_id, user_id)
    reminder.status = "cancelled"
    reminder.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
    reminder.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(reminder)
    return reminder



@router.post(
    "/{reminder_id}/send-now",
    response_model=ReminderResponse,
)
def send_reminder_email_now(
    reminder_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> ReminderResponse:
    """Trigger sending this reminder email immediately (useful for testing or on-demand dispatch)."""
    from app.services.reminder_agent import send_reminder_now

    return send_reminder_now(db, reminder_id, user_id)


@router.post(
    "/check-due",
)
def check_due_reminders(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> dict[str, int]:
    """Manually invoke the due-reminders scanner."""
    from app.services.reminder_agent import process_due_reminders

    processed = process_due_reminders(db)
    return {"processed": processed}
