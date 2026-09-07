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


def test_law_project_preserves_source_provenance_and_privacy() -> None:
    token = register("law-owner@example.com")
    other_token = register("law-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/law/projects",
        headers=headers,
        json={
            "title": "Data privacy matter",
            "legal_question": "What authorities address consent for this data processing?",
            "jurisdiction": "Example jurisdiction",
        },
    )
    assert created.status_code == 201
    project_id = created.json()["id"]
    assert "not legal advice" in created.json()["disclaimer"].lower()

    source = client.post(
        f"/api/v1/law/projects/{project_id}/sources",
        headers=headers,
        json={
            "label": "Published statute source",
            "source_url": "https://example.test/statute",
            "source_type": "source",
            "excerpt": "User-provided excerpt",
        },
    )
    foreign = client.get(
        "/api/v1/law/projects",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert source.status_code == 201
    assert source.json()["source_url"] == "https://example.test/statute"
    assert source.json()["source_type"] == "source"
    assert foreign.json() == []


def test_law_source_rejects_unclassified_result() -> None:
    token = register("law-validation@example.com")
    project = client.post(
        "/api/v1/law/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Validation matter", "legal_question": "Which source should be reviewed?"},
    ).json()
    response = client.post(
        f"/api/v1/law/projects/{project['id']}/sources",
        headers={"Authorization": f"Bearer {token}"},
        json={"label": "Unclassified authority", "source_url": "https://example.test/source", "source_type": "authority"},
    )
    assert response.status_code == 422
