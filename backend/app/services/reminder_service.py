from __future__ import annotations

from datetime import datetime
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.db.models import CommunicationLog, Notification, NotificationPreference, Reminder, User
from app.services.communication_providers import DevelopmentEmailProvider, DevelopmentVoiceProvider, InAppProvider, followup_message

logger = logging.getLogger(__name__)


def is_within_quiet_hours(
    preferences: NotificationPreference | None, now: datetime
) -> bool:
    """Return whether a notification must wait for the user's quiet period.

    Quiet-hour values are deliberately stored as ``HH:MM`` strings so old
    preference records stay compatible.  An invalid timezone or an incomplete
    quiet-hour range is treated as no quiet period rather than dropping a
    reminder forever.
    """
    if not preferences or not preferences.quiet_start or not preferences.quiet_end:
        return False
    try:
        local_time = now.replace(tzinfo=ZoneInfo("UTC")).astimezone(
            ZoneInfo(preferences.timezone or "UTC")
        ).time()
        start = datetime.strptime(preferences.quiet_start, "%H:%M").time()
        end = datetime.strptime(preferences.quiet_end, "%H:%M").time()
    except (ValueError, ZoneInfoNotFoundError):
        logger.warning("Ignoring invalid quiet-hour preference for user %s", preferences.user_id)
        return False

    if start == end:
        return False
    return start <= local_time < end if start < end else local_time >= start or local_time < end


def execute_due_reminders(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    due = (
        db.query(Reminder)
        .join(Reminder.followup)
        .filter(
            Reminder.enabled.is_(True),
            Reminder.remind_at <= now,
            Reminder.attempts < Reminder.max_reminders,
            Reminder.followup.has(status="pending"),
        )
        .all()
    )
    executed = 0
    for reminder in due:
        followup = reminder.followup
        user = db.query(User).filter(User.id == followup.user_id).first()
        if not user:
            reminder.last_error = "User no longer exists"
            reminder.attempts += 1
            db.commit()
            continue
        preferences = db.query(NotificationPreference).filter(NotificationPreference.user_id == user.id).first()
        if is_within_quiet_hours(preferences, now):
            logger.info("Deferring reminder %s during quiet hours", reminder.id)
            continue
        if reminder.channel == "in_app" and preferences and not preferences.in_app_enabled:
            reminder.last_error = "In-app notifications are disabled"
            reminder.attempts += 1
            db.commit()
            continue
        if reminder.channel == "voice" and (not preferences or not preferences.voice_enabled or not preferences.phone_consent or not user.phone_number):
            reminder.last_error = "Voice reminder requires phone number, consent, and enabled voice notifications"
            reminder.attempts += 1
            db.commit()
            continue
        message = followup_message(followup.title, followup.message, followup.due_at)
        if reminder.channel == "in_app":
            result = InAppProvider().send(user.id, followup.title, message)
            db.add(Notification(user_id=user.id, type="research_followup", message=message))
        elif reminder.channel == "email":
            if preferences and not preferences.email_enabled:
                reminder.last_error = "Email notifications are disabled"
                reminder.attempts += 1
                db.commit()
                continue
            result = DevelopmentEmailProvider().send(user.email, followup.title, message)
        else:
            result = DevelopmentVoiceProvider().send(user.phone_number, message)
        db.add(CommunicationLog(user_id=user.id, project_id=followup.project_id, communication_type=reminder.channel, provider=result.provider, status=result.status, failure_reason=None, consent_state="consented" if reminder.channel == "voice" else "not_required"))
        reminder.attempts += 1
        reminder.enabled = reminder.attempts < reminder.max_reminders
        reminder.last_error = None
        db.commit()
        executed += 1
        logger.info("[Reminder] Executed follow-up %s through %s", followup.id, reminder.channel)
    return executed
