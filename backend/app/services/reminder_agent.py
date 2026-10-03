"""Reminder Agent service.

Handles:
- Detecting due user research reminders.
- Dispatching email reminders using the existing email provider (Resend API / SMTP / console).
- Atomic duplicate prevention (exactly ONE email sent per reminder).
- Enforcing delivery only to verified user email addresses.
- Formatting due times accurately in the user's specific timezone.
- Immediate manual testing ("send now") of reminders.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import zoneinfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User, UserReminder
from app.services.email_service import (
    reminder_email_body,
    reminder_email_html,
    send_email,
)

logger = logging.getLogger(__name__)


def _normalize_utc(dt: datetime) -> datetime:
    """Ensure datetime has timezone.utc."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def recover_stale_reminders(db: Session) -> int:
    """Recover reminders that were interrupted while in 'processing' state (e.g. server restart)."""
    stale_count = (
        db.query(UserReminder)
        .filter(
            UserReminder.status == "processing",
            UserReminder.email_sent.is_(False),
        )
        .update({
            "status": "pending",
            "last_error": "Recovered from interrupted processing state",
        })
    )
    if stale_count:
        db.commit()
        logger.info("[ReminderAgent] Recovered %d interrupted reminder(s) back to 'pending'", stale_count)
    return stale_count


def process_due_reminders(db: Session, now: datetime | None = None) -> int:
    """Process all pending reminders that are due and haven't had an email sent yet.

    Returns the number of reminders successfully processed.
    Guarantees exactly ONE email is sent via atomic status updates and email_sent checks.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    else:
        now = _normalize_utc(now)

    # First recover any stale processing reminders (e.g. from previous aborted workers)
    recover_stale_reminders(db)

    # Query all pending, unsent reminders (ordered earliest first)
    pending_reminders = (
        db.query(UserReminder)
        .filter(
            UserReminder.status == "pending",
            UserReminder.email_sent.is_(False),
        )
        .order_by(UserReminder.reminder_datetime.asc())
        .all()
    )

    processed_count = 0

    for reminder in pending_reminders:
        try:
            # Check if due (timezone-safe comparison in UTC)
            remind_time = _normalize_utc(reminder.reminder_datetime)
            if remind_time > now:
                # Future reminder — not due yet
                continue

            # Atomic claim to prevent duplicate sends across concurrent workers
            claimed = (
                db.query(UserReminder)
                .filter(
                    UserReminder.id == reminder.id,
                    UserReminder.status == "pending",
                    UserReminder.email_sent.is_(False),
                )
                .update({"status": "processing"})
            )
            db.commit()
            if not claimed:
                # Another worker already claimed this reminder
                continue

            # Refresh reminder instance
            db.refresh(reminder)

            user = db.query(User).filter(User.id == reminder.user_id).first()
            if not user:
                reminder.status = "failed"
                reminder.last_error = "User account not found"
                db.commit()
                continue

            if not user.email:
                reminder.status = "failed"
                reminder.last_error = "User has no email address configured"
                db.commit()
                continue

            # Strict requirement: Email is only sent to verified email addresses
            if not user.email_verified:
                reminder.status = "pending"
                reminder.last_error = "User email address is not verified; reminder delivery postponed"
                db.commit()
                logger.warning(
                    "[ReminderAgent] Skipping reminder %d: user %s email is not verified",
                    reminder.id,
                    user.email,
                )
                continue

            subject = f"ResearchOS Reminder: {reminder.title}"
            body = reminder_email_body(
                title=reminder.title,
                description=reminder.description,
                due_datetime=reminder.reminder_datetime,
                user_name=user.name,
                timezone_name=reminder.timezone,
            )
            html = reminder_email_html(
                title=reminder.title,
                description=reminder.description,
                due_datetime=reminder.reminder_datetime,
                user_name=user.name,
                timezone_name=reminder.timezone,
            )

            email_result = send_email(user.email, subject, body, html=html)
            email_status = email_result.get("status")

            if email_status in ("sent", "simulated", "logged"):
                reminder.email_sent = True
                reminder.status = "sent"
                reminder.email_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
                reminder.last_error = None
                db.commit()
                processed_count += 1
                logger.info(
                    "[ReminderAgent] Sent due reminder %d ('%s') to verified email %s (timezone: %s)",
                    reminder.id,
                    reminder.title,
                    user.email,
                    reminder.timezone,
                )
            else:
                reminder.status = "pending"
                reminder.last_error = email_result.get("detail", "Failed to send email")
                db.commit()
                logger.warning(
                    "[ReminderAgent] Failed to send reminder %d to %s: %s",
                    reminder.id,
                    user.email,
                    reminder.last_error,
                )
        except Exception as exc:
            logger.error("[ReminderAgent] Error processing reminder %s: %s", getattr(reminder, 'id', 'unknown'), exc)
            try:
                reminder.status = "pending"
                reminder.last_error = f"Processing exception: {exc}"
                db.commit()
            except Exception:
                db.rollback()

    return processed_count


def send_reminder_now(db: Session, reminder_id: int, user_id: int) -> UserReminder:
    """Send a reminder email immediately for manual testing or on-demand notification."""
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

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email not found",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send reminder: user email address is not verified",
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    is_future = reminder.reminder_datetime > now_utc

    subject = f"[Test Email] ResearchOS Reminder: {reminder.title}" if is_future else f"ResearchOS Reminder: {reminder.title}"
    body = reminder_email_body(
        title=reminder.title,
        description=reminder.description,
        due_datetime=reminder.reminder_datetime,
        user_name=user.name,
        timezone_name=reminder.timezone,
    )
    html = reminder_email_html(
        title=reminder.title,
        description=reminder.description,
        due_datetime=reminder.reminder_datetime,
        user_name=user.name,
        timezone_name=reminder.timezone,
    )

    email_result = send_email(user.email, subject, body, html=html)
    email_status = email_result.get("status")

    if email_status in ("sent", "simulated", "logged"):
        if is_future:
            # Test email sent successfully without prematurely disarming the scheduled reminder
            reminder.last_error = f"Test email sent successfully at {now_utc.strftime('%H:%M:%S UTC')}. Automatic reminder remains scheduled."
        else:
            reminder.email_sent = True
            reminder.status = "sent"
            reminder.email_sent_at = now_utc
            reminder.last_error = None
        db.commit()
        db.refresh(reminder)
        logger.info(
            "[ReminderAgent] Manually triggered test reminder %d ('%s') sent to %s (is_future=%s)",
            reminder.id,
            reminder.title,
            user.email,
            is_future,
        )
        return reminder
    else:
        error_detail = email_result.get("detail", "Failed to send email")
        reminder.last_error = error_detail
        db.commit()
        db.refresh(reminder)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email delivery failed: {error_detail}",
        )
