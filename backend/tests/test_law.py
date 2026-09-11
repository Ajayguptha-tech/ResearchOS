"""Verify that Legal Research routes are completely unmounted and removed from ResearchOS."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register(email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "name": "Researcher"},
    )
    assert response.status_code in {200, 201}
    return response.json()["access_token"]


def test_law_routes_are_removed_from_researchos() -> None:
    token = register("law-check@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # /api/v1/law routes must not be exposed
    assert client.get("/api/v1/law/projects", headers=headers).status_code == 404
    assert client.post(
        "/api/v1/law/projects",
        headers=headers,
        json={"title": "Test", "legal_question": "Question here"},
    ).status_code == 404
