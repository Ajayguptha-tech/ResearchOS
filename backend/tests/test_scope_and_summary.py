"""Tests for strict document scope isolation, one-click document summarization,
and verification that law and assistant routes are removed from user-facing API.
"""

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


def test_main_workspace_and_project_document_isolation() -> None:
    token = register("isolation-test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Project A and Project B
    resp_a = client.post("/api/v1/projects/", headers=headers, json={"title": "Project A", "domain": "AI"})
    assert resp_a.status_code in {200, 201}
    proj_a_id = resp_a.json()["id"]

    resp_b = client.post("/api/v1/projects/", headers=headers, json={"title": "Project B", "domain": "Biology"})
    assert resp_b.status_code in {200, 201}
    proj_b_id = resp_b.json()["id"]

    # 2. Upload paper-A.txt to Project A
    up_a = client.post(
        f"/api/v1/papers/upload?project_id={proj_a_id}",
        headers=headers,
        files={"file": ("paper-A.txt", b"Paper A describes neural networks and transformers. Results show improved accuracy.", "text/plain")},
    )
    assert up_a.status_code == 201
    doc_a_id = up_a.json()["id"]

    # 3. Upload paper-B.txt to Project B
    up_b = client.post(
        f"/api/v1/papers/upload?project_id={proj_b_id}",
        headers=headers,
        files={"file": ("paper-B.txt", b"Paper B analyzes protein folding using graph models. Results demonstrate rapid convergence.", "text/plain")},
    )
    assert up_b.status_code == 201
    doc_b_id = up_b.json()["id"]

    # 4. Upload global-paper.txt to Main Workspace (no project_id)
    up_global = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        files={"file": ("global-paper.txt", b"Global overview of scientific computing algorithms. Methodology includes benchmark evaluations.", "text/plain")},
    )
    assert up_global.status_code == 201
    doc_global_id = up_global.json()["id"]

    # VERIFY ISOLATION:

    # Global documents list: MUST contain only global-paper.txt, NOT paper-A or paper-B
    global_docs = client.get("/api/v1/papers/documents", headers=headers).json()
    global_ids = [d["id"] for d in global_docs]
    assert doc_global_id in global_ids
    assert doc_a_id not in global_ids
    assert doc_b_id not in global_ids

    # Project A documents list: MUST contain only paper-A.txt
    proj_a_docs = client.get(f"/api/v1/papers/documents/project/{proj_a_id}", headers=headers).json()
    proj_a_ids = [d["id"] for d in proj_a_docs]
    assert proj_a_ids == [doc_a_id]
    assert doc_b_id not in proj_a_ids
    assert doc_global_id not in proj_a_ids

    # Project B documents list: MUST contain only paper-B.txt
    proj_b_docs = client.get(f"/api/v1/papers/documents/project/{proj_b_id}", headers=headers).json()
    proj_b_ids = [d["id"] for d in proj_b_docs]
    assert proj_b_ids == [doc_b_id]
    assert doc_a_id not in proj_b_ids
    assert doc_global_id not in proj_b_ids


def test_summarize_documents_scoped_and_user_triggered() -> None:
    token = register("summary-test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create Project
    resp = client.post("/api/v1/projects/", headers=headers, json={"title": "NLP Project", "domain": "NLP"})
    assert resp.status_code in {200, 201}
    proj_id = resp.json()["id"]

    # Empty summary test: when no documents exist
    empty_summary = client.post(f"/api/v1/research/summarize-documents?project_id={proj_id}", headers=headers)
    assert empty_summary.status_code == 200
    assert empty_summary.json()["status"] == "empty"
    assert empty_summary.json()["count"] == 0

    # Upload document to project
    up_proj = client.post(
        f"/api/v1/papers/upload?project_id={proj_id}",
        headers=headers,
        files={"file": ("attention-study.txt", b"Attention is a deep learning mechanism. Our experiments show improved translation. Methodology: Transformer architecture optimization.", "text/plain")},
    )
    assert up_proj.status_code == 201

    # Upload global document
    up_global = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        files={"file": ("general-ai.txt", b"General artificial intelligence survey. Findings show progress in reasoning. Methodology: Literature review and benchmark analysis.", "text/plain")},
    )
    assert up_global.status_code == 201

    # Summarize Project Documents (NO text prompt required)
    proj_summary = client.post(f"/api/v1/research/summarize-documents?project_id={proj_id}", headers=headers)
    assert proj_summary.status_code == 200
    p_data = proj_summary.json()
    assert p_data["status"] == "success"
    assert p_data["count"] == 1
    assert p_data["summaries"][0]["filename"] == "attention-study.txt"
    assert "summary" in p_data["summaries"][0]
    assert "key_findings" in p_data["summaries"][0]
    assert "methodology" in p_data["summaries"][0]

    # Summarize Global Workspace Documents (NO text prompt required)
    global_summary = client.post("/api/v1/research/summarize-documents", headers=headers)
    assert global_summary.status_code == 200
    g_data = global_summary.json()
    assert g_data["status"] == "success"
    assert g_data["count"] == 1
    assert g_data["summaries"][0]["filename"] == "general-ai.txt"


def test_law_and_assistant_endpoints_are_unmounted() -> None:
    token = register("routes-check@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify law endpoints return 404 (unmounted)
    law_resp = client.get("/api/v1/law/projects", headers=headers)
    assert law_resp.status_code == 404

    # Verify assistant endpoints return 404 (unmounted)
    assistant_resp = client.post("/api/v1/assistant/chat", headers=headers, json={"message": "hello"})
    assert assistant_resp.status_code == 404


def test_paper_draft_scoping_and_generation() -> None:
    token = register("draft-scoping@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create project
    proj_resp = client.post("/api/v1/projects/", headers=headers, json={"title": "Draft Project", "domain": "CS"})
    proj_id = proj_resp.json()["id"]

    # Upload document to project
    doc_resp = client.post(
        f"/api/v1/papers/upload?project_id={proj_id}",
        headers=headers,
        files={"file": ("project-source.txt", b"Novel findings on distributed consensus algorithms. The proposed protocol achieves sub-second latency.", "text/plain")},
    )
    doc_id = doc_resp.json()["id"]

    # Upload global document (must NOT be used in project draft)
    client.post(
        "/api/v1/papers/upload",
        headers=headers,
        files={"file": ("unrelated-global.txt", b"Global unrelated material that must never leak into project draft.", "text/plain")},
    )

    # Create draft for project with doc_id
    draft_resp = client.post(
        f"/api/v1/paper-drafts/project/{proj_id}",
        headers=headers,
        json={
            "title": "A Study on Distributed Consensus",
            "instruction": "Focus on consensus latency.",
            "source_document_ids": [doc_id],
        },
    )
    assert draft_resp.status_code == 201
    draft_id = draft_resp.json()["id"]

    # Generate draft
    gen_resp = client.post(f"/api/v1/paper-drafts/{draft_id}/generate", headers=headers)
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["status"] == "success"
    content = gen_data["draft"]["content"]
    assert "A Study on Distributed Consensus" in content
    assert "project-source.txt" in content
    assert "unrelated-global.txt" not in content
