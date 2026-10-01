from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class DeliveryResult:
    status: str
    provider: str
    detail: str
    external_id: str | None = None


class InAppProvider:
    name = "in_app"

    def send(self, user_id: int, title: str, message: str) -> DeliveryResult:
        return DeliveryResult("sent", self.name, f"In-app notification queued for user {user_id}")


class DevelopmentEmailProvider:
    name = "console"

    def send(self, recipient: str, subject: str, body: str) -> DeliveryResult:
        logger.info("[Email] Development email for %s: %s\n%s", recipient, subject, body)
        return DeliveryResult("logged", self.name, "Email rendered to backend logs")


class DevelopmentVoiceProvider:
    name = "mock"

    def send(self, phone_number: str, message: str) -> DeliveryResult:
        logger.info("[Voice] Mock call for %s: %s", phone_number, message)
        return DeliveryResult("logged", self.name, "Voice call recorded in development logs")


def followup_message(title: str, message: str, due_at: datetime | None) -> str:
    due = due_at.astimezone(timezone.utc).isoformat() if due_at else "not scheduled"
    return f"{title}: {message}\nFollow-up time: {due}\nNext step: Open the ResearchOS workspace."
