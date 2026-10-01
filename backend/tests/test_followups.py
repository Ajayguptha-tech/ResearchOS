from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.services.reminder_service import execute_due_reminders
from conftest import TestingSessionLocal

client = TestClient(app)


def register(email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "name": "Researcher"},
    )
    assert response.status_code in {200, 201}
    return response.json()["access_token"]


def test_followup_lifecycle_and_owner_isolation() -> None:
    token = register("followup-owner@example.com")
    other_token = register("followup-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    followup = client.post(
        "/api/v1/followups/",
        headers=headers,
        json={"title": "Review top papers", "message": "Review the highest-ranked papers."},
    )
    assert followup.status_code == 201
    followup_id = followup.json()["id"]

    foreign = client.get(f"/api/v1/followups/{followup_id}", headers={"Authorization": f"Bearer {other_token}"})
    snoozed = client.post(f"/api/v1/followups/{followup_id}/snooze?hours=24", headers=headers)
    completed = client.post(f"/api/v1/followups/{followup_id}/complete", headers=headers)

    assert foreign.status_code == 404
    assert snoozed.json()["status"] == "snoozed"
    assert completed.json()["status"] == "completed"


def test_preferences_and_consent_gate_voice() -> None:
    token = register("preferences@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    preferences = client.get("/api/v1/followups/preferences/me", headers=headers)
    assert preferences.status_code == 200
    assert preferences.json()["in_app_enabled"] is True

    forbidden = client.patch(
        "/api/v1/followups/preferences/me",
        headers=headers,
        json={"voice_enabled": True},
    )
    allowed = client.patch(
        "/api/v1/followups/preferences/me",
        headers=headers,
        json={"phone_consent": True, "voice_enabled": True},
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200


def test_due_in_app_reminder_creates_notification_and_log() -> None:
    token = register("reminder@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    followup = client.post(
        "/api/v1/followups/",
        headers=headers,
        json={"title": "Continue analysis", "message": "Review the latest research findings."},
    ).json()
    reminder = client.post(
        f"/api/v1/followups/{followup['id']}/reminders",
        headers=headers,
        json={"followup_id": followup["id"], "channel": "in_app", "remind_at": (datetime.utcnow() - timedelta(minutes=1)).isoformat()},
    )
    assert reminder.status_code == 201

    db = TestingSessionLocal()
    assert execute_due_reminders(db) == 1
    db.close()

    notifications = client.get("/api/v1/notifications/", headers=headers)
    history = client.get("/api/v1/communications/history", headers=headers)
    assert notifications.status_code == 200
    assert len(notifications.json()) == 1
    assert history.json()[0]["type"] == "in_app"
