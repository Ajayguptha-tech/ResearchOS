from fastapi.testclient import TestClient

from app.db.models import User
from app.main import app
from conftest import TestingSessionLocal

client = TestClient(app)


def register(email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "name": "Researcher"},
    )
    assert response.status_code in {200, 201}
    return response.json()["access_token"]


def promote(token: str) -> None:
    user_id = int(client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"])
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    assert user is not None
    user.role = "supervisor"
    db.commit()
    db.close()


def test_supervisor_review_creates_owner_notification() -> None:
    owner_token = register("review-owner@example.com")
    supervisor_token = register("review-supervisor@example.com")
    promote(supervisor_token)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    supervisor_headers = {"Authorization": f"Bearer {supervisor_token}"}

    project = client.post(
        "/api/v1/projects/",
        headers=owner_headers,
        json={"title": "Reviewable Project", "domain": "Physics"},
    ).json()
    review = client.post(
        f"/api/v1/supervisor/projects/{project['id']}/feedback",
        headers=supervisor_headers,
        json={"decision": "approved", "message": "The methodology is clear."},
    )

    assert review.status_code == 200
    notifications = client.get("/api/v1/notifications/", headers=owner_headers)
    assert notifications.status_code == 200
    assert len(notifications.json()) == 1
    notification_id = notifications.json()[0]["id"]

    marked_read = client.patch(f"/api/v1/notifications/{notification_id}/read", headers=owner_headers)
    assert marked_read.status_code == 200
    assert marked_read.json()["read_at"] is not None


def test_review_and_notifications_are_authorized() -> None:
    owner_token = register("auth-owner@example.com")
    researcher_token = register("auth-researcher@example.com")
    project = client.post(
        "/api/v1/projects/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Authorization Project", "domain": "Chemistry"},
    ).json()

    forbidden_review = client.post(
        f"/api/v1/supervisor/projects/{project['id']}/feedback",
        headers={"Authorization": f"Bearer {researcher_token}"},
        json={"decision": "rejected", "message": "Needs more evidence."},
    )
    unauthenticated_notifications = client.get("/api/v1/notifications/")

    assert forbidden_review.status_code == 403
    assert unauthenticated_notifications.status_code == 401
