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


def test_paper_crud_import_and_search() -> None:
    token = register("papers@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    imported = client.post(
        "/api/v1/papers/import",
        headers=headers,
        json={
            "papers": [
                {"title": "Causal Discovery in Biology", "abstract": "A study of causal graphs."},
                {"title": "Graph Learning Methods", "abstract": "Methods for graph representation."},
            ]
        },
    )
    assert imported.status_code == 200
    assert len(imported.json()) == 2

    search = client.get("/api/v1/papers/search?q=graph", headers=headers)
    assert search.status_code == 200
    assert [paper["title"] for paper in search.json()] == ["Graph Learning Methods", "Causal Discovery in Biology"]

    paper_id = imported.json()[0]["id"]
    updated = client.patch(
        f"/api/v1/papers/{paper_id}",
        headers=headers,
        json={"evidence_level": "high"},
    )
    assert updated.status_code == 200
    assert updated.json()["evidence_level"] == "high"

    deleted = client.delete(f"/api/v1/papers/{paper_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/papers/{paper_id}", headers=headers).status_code == 404


def test_papers_are_private_and_search_requires_query() -> None:
    owner_token = register("paper-owner@example.com")
    other_token = register("paper-other@example.com")
    created = client.post(
        "/api/v1/papers/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Private Evidence", "abstract": "Protected research record."},
    )
    paper_id = created.json()["id"]

    foreign = client.get(
        f"/api/v1/papers/{paper_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    empty_search = client.get(
        "/api/v1/papers/search?q=",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert foreign.status_code == 404
    assert empty_search.status_code == 422


def test_local_document_upload_and_retrieval_are_owner_scoped() -> None:
    owner_token = register("documents-owner@example.com")
    other_token = register("documents-other@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    uploaded = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        files={"file": ("research-notes.md", b"Graph neural networks improve molecule property prediction.", "text/markdown")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["extracted_characters"] > 0

    retrieved = client.get("/api/v1/papers/retrieve?q=molecule", headers=headers)
    foreign_documents = client.get("/api/v1/papers/documents", headers={"Authorization": f"Bearer {other_token}"})

    assert retrieved.status_code == 200
    assert retrieved.json()[0]["source"] == "local_uploaded_document"
    assert "molecule" in retrieved.json()[0]["excerpt"].lower()
    assert foreign_documents.json() == []
