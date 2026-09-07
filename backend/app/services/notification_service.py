"""LEGACY / UNUSED — do not wire into routes.

This class reports email/alerts as "queued"/"sent" WITHOUT actually sending
anything, which would violate the project rule that delivery status must be
truthful.  It is NOT used by any active endpoint: real email goes through
``app/services/email_service.py`` (status sent/logged/failed) and supervisor
notifications are written directly to the database in
``app/api/v1/routes/supervisor.py``.

Kept only so legacy code that may still import it does not crash.
"""


class NotificationService:
    def send_email(self, to: str, subject: str, body: str) -> dict:
        return {"to": to, "subject": subject, "status": "queued"}

    def send_supervisor_alert(self, project_id: str, message: str) -> dict:
        return {"project_id": project_id, "message": message, "status": "sent"}
