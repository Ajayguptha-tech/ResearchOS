from fastapi.testclient import TestClient

from app.main import app
from conftest import TestingSessionLocal
client = TestClient(app)


def register(email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "name": email.split("@")[0]},
    )
    assert response.status_code in {200, 201}
    return response.json()["access_token"]


def test_projects_require_authentication() -> None:
    response = client.get("/api/v1/projects/")
    assert response.status_code == 401


def test_projects_are_scoped_to_authenticated_owner() -> None:
    first_token = register("first@example.com")
    second_token = register("second@example.com")

    created = client.post(
        "/api/v1/projects/",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"title": "Causal Inference", "domain": "Statistics"},
    )
    assert created.status_code == 200
    project_id = created.json()["id"]
    assert created.json()["user_id"] > 0

    first_projects = client.get(
        "/api/v1/projects/", headers={"Authorization": f"Bearer {first_token}"}
    )
    assert first_projects.status_code == 200
    assert [project["id"] for project in first_projects.json()] == [project_id]

    second_projects = client.get(
        "/api/v1/projects/", headers={"Authorization": f"Bearer {second_token}"}
    )
    assert second_projects.status_code == 200
    assert second_projects.json() == []

    forbidden_project = client.get(
        f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {second_token}"}
    )
    assert forbidden_project.status_code == 404


def test_login_returns_token_for_registered_user() -> None:
    register("login@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "strong-password"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_rejects_invalid_password() -> None:
    register("invalid@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "invalid@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_research_workflow_persists_ideas_and_plans() -> None:
    token = register("workflow@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "workflow@example.com"

    project = client.post(
        "/api/v1/projects/",
        headers=headers,
        json={"title": "Language Models", "domain": "Natural Language Processing"},
    ).json()
    project_id = project["id"]

    idea = client.post(
        f"/api/v1/projects/{project_id}/ideas",
        headers=headers,
        json={
            "title": "Evaluate transfer learning",
            "description": "Measure whether transfer learning improves low-resource translation.",
        },
    )
    assert idea.status_code == 200

    plan = client.post(
        f"/api/v1/projects/{project_id}/plan",
        headers=headers,
        json={"idea_id": idea.json()["id"]},
    )
    assert plan.status_code == 200
    assert len(plan.json()["steps"]) == 5

    reloaded = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["ideas"][0]["id"] == idea.json()["id"]
    assert reloaded.json()["plans"][0]["id"] == plan.json()["id"]


def test_missing_or_foreign_project_plan_is_not_accessible() -> None:
    owner_token = register("plan-owner@example.com")
    other_token = register("plan-other@example.com")
    project = client.post(
        "/api/v1/projects/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Private Plan", "domain": "Biology"},
    ).json()

    foreign_response = client.post(
        f"/api/v1/projects/{project['id']}/plan",
        headers={"Authorization": f"Bearer {other_token}"},
        json={},
    )
    missing_response = client.post(
        "/api/v1/projects/99999/plan",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={},
    )

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
