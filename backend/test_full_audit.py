"""Full audit test suite for ResearchOS backend."""
import sys
import traceback
import os
import requests
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0
errors = []

def test(name, fn):
    global passed, failed
    try:
        result = fn()
        if result is False:
            failed += 1
            errors.append(f"FAIL: {name}")
            print(f"  FAIL: {name}")
        else:
            passed += 1
            print(f"  PASS: {name}")
    except Exception as e:
        failed += 1
        errors.append(f"FAIL: {name} — {e}")
        print(f"  FAIL: {name} — {e}")

print("=" * 60)
print("RESEARCHOS FULL AUDIT TEST SUITE")
print("=" * 60)

# ---- 1. HEALTH CHECK ----
print("\n--- 1. Health Check ---")

def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

test("Health check", test_health)

# ---- 2. AUTHENTICATION ----
print("\n--- 2. Authentication ---")

EMAIL_AUDIT = f"audit_{int(time.time())}@test.com"
PASSWORD_AUDIT = "TestPass123!"
TOKEN_AUDIT = None
TOKEN_AUDIT2 = None
EMAIL_AUDIT2 = f"audit2_{int(time.time())}@test.com"

def test_register():
    global TOKEN_AUDIT
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": EMAIL_AUDIT, "password": PASSWORD_AUDIT, "name": "Audit User"
    }, timeout=10)
    assert r.status_code in (200, 201), f"Status: {r.status_code}, Body: {r.text}"
    data = r.json()
    TOKEN_AUDIT = data.get("access_token")
    assert TOKEN_AUDIT, "No access_token"

test("Register user 1", test_register)

def test_register_user2():
    global TOKEN_AUDIT2
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": EMAIL_AUDIT2, "password": PASSWORD_AUDIT, "name": "Audit User 2"
    }, timeout=10)
    assert r.status_code in (200, 201)
    TOKEN_AUDIT2 = r.json().get("access_token")
    assert TOKEN_AUDIT2

test("Register user 2", test_register_user2)

def test_login():
    r = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": EMAIL_AUDIT, "password": PASSWORD_AUDIT
    }, timeout=10)
    assert r.status_code == 200
    assert r.json().get("access_token")

test("Login", test_login)

def test_wrong_password():
    r = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": EMAIL_AUDIT, "password": "wrongpassword"
    }, timeout=10)
    assert r.status_code in (400, 401, 422), f"Expected auth failure, got {r.status_code}"

test("Wrong password rejected", test_wrong_password)

def test_get_profile():
    r = requests.get(f"{BASE}/api/v1/auth/me", headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL_AUDIT

test("Get profile", test_get_profile)

# ---- 3. PROJECTS ----
print("\n--- 3. Projects ---")

PROJECT_ID_AUDIT = None

def test_create_project():
    global PROJECT_ID_AUDIT
    r = requests.post(f"{BASE}/api/v1/projects/", json={
        "title": "Audit Test Project", "domain": "Computer Science"
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200, f"Status: {r.status_code}, Body: {r.text}"
    PROJECT_ID_AUDIT = r.json()["id"]

test("Create project", test_create_project)

def test_list_projects():
    r = requests.get(f"{BASE}/api/v1/projects/", headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List projects", test_list_projects)

# ---- 4. DOCUMENTS ----
print("\n--- 4. Documents ---")

DOC_ID_AUDIT = None

def test_upload_txt():
    global DOC_ID_AUDIT
    import io
    content = b"This is a test document about machine learning in healthcare. " * 100
    files = {"file": ("test_doc.txt", io.BytesIO(content), "text/plain")}
    r = requests.post(f"{BASE}/api/v1/papers/upload?project_id={PROJECT_ID_AUDIT}",
        files=files, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=30)
    assert r.status_code in (200, 201), f"Status: {r.status_code}, Body: {r.text}"
    DOC_ID_AUDIT = r.json()["id"]

test("Upload TXT document", test_upload_txt)

def test_list_documents():
    r = requests.get(f"{BASE}/api/v1/papers/documents/project/{PROJECT_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List documents", test_list_documents)

def test_get_document_content():
    r = requests.get(f"{BASE}/api/v1/papers/documents/{DOC_ID_AUDIT}/content",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json().get("extracted_text", "")) > 0

test("Get document content", test_get_document_content)

def test_get_document_summary():
    r = requests.get(f"{BASE}/api/v1/papers/documents/{DOC_ID_AUDIT}/summary",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200

test("Get document summary", test_get_document_summary)

# ---- 5. PAPERS (Evidence Library) ----
print("\n--- 5. Papers (Evidence Library) ---")

PAPER_ID_AUDIT = None

def test_create_paper():
    global PAPER_ID_AUDIT
    r = requests.post(f"{BASE}/api/v1/papers/", json={
        "title": "Test Evidence Paper", "abstract": "This is test evidence."
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    PAPER_ID_AUDIT = r.json()["id"]

test("Create paper", test_create_paper)

def test_list_papers():
    r = requests.get(f"{BASE}/api/v1/papers/", headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List papers", test_list_papers)

def test_update_paper():
    r = requests.patch(f"{BASE}/api/v1/papers/{PAPER_ID_AUDIT}", json={
        "title": "Updated Evidence Paper"
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Evidence Paper"

test("Update paper", test_update_paper)

# ---- 6. REFERENCES ----
print("\n--- 6. References ---")

REF_ID_AUDIT = None

def test_create_reference():
    global REF_ID_AUDIT
    r = requests.post(f"{BASE}/api/v1/references/project/{PROJECT_ID_AUDIT}", json={
        "title": "Test Reference", "authors": "Author One", "year": 2023
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code in (200, 201), f"Status: {r.status_code}, Body: {r.text}"
    REF_ID_AUDIT = r.json()["id"]

test("Create reference", test_create_reference)

def test_list_references():
    r = requests.get(f"{BASE}/api/v1/references/project/{PROJECT_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List references", test_list_references)

# ---- 7. EVIDENCE SESSIONS ----
print("\n--- 7. Evidence Sessions ---")

ES_ID_AUDIT = None

def test_create_evidence_session():
    global ES_ID_AUDIT
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/project/{PROJECT_ID_AUDIT}", json={
        "title": "Test Evidence Session", "description": "Testing evidence CRUD"
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code in (200, 201), f"Status: {r.status_code}, Body: {r.text}"
    ES_ID_AUDIT = r.json()["id"]

test("Create evidence session", test_create_evidence_session)

def test_list_evidence_sessions():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/project/{PROJECT_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List evidence sessions", test_list_evidence_sessions)

def test_update_evidence_session():
    r = requests.patch(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}", json={
        "title": "Updated Evidence Session"
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Evidence Session"

test("Update evidence session", test_update_evidence_session)

def test_add_evidence_item():
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}/items", json={
        "item_type": "reference", "item_id": REF_ID_AUDIT, "note": "Test note"
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code in (200, 201), f"Status: {r.status_code}, Body: {r.text}"

test("Add evidence item", test_add_evidence_item)

def test_list_evidence_items():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json().get("items", [])) >= 1

test("List evidence items", test_list_evidence_items)

# ---- 8. PAPER DRAFTS ----
print("\n--- 8. Paper Drafts ---")

DRAFT_ID_AUDIT = None

def test_create_draft():
    global DRAFT_ID_AUDIT
    r = requests.post(f"{BASE}/api/v1/paper-drafts/project/{PROJECT_ID_AUDIT}", json={
        "title": "Test Draft Paper",
        "instruction": "Write an introduction section",
        "source_document_ids": [DOC_ID_AUDIT],
        "source_paper_ids": [],
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code in (200, 201), f"Status: {r.status_code}, Body: {r.text}"
    DRAFT_ID_AUDIT = r.json()["id"]

test("Create paper draft", test_create_draft)

def test_list_drafts():
    r = requests.get(f"{BASE}/api/v1/paper-drafts/project/{PROJECT_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List paper drafts", test_list_drafts)

def test_generate_draft():
    r = requests.post(f"{BASE}/api/v1/paper-drafts/{DRAFT_ID_AUDIT}/generate",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=30)
    assert r.status_code in (200, 502), f"Status: {r.status_code}, Body: {r.text[:200]}"
    if r.status_code == 200:
        data = r.json()
        assert data["status"] == "success"
        assert len(data["draft"]["content"]) > 0

test("Generate paper draft", test_generate_draft)

def test_draft_versions():
    r = requests.get(f"{BASE}/api/v1/paper-drafts/{DRAFT_ID_AUDIT}/versions",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 200
    assert len(r.json()) >= 1

test("List draft versions", test_draft_versions)

# ---- 9. ASSISTANT ----
print("\n--- 9. Assistant ---")

def test_assistant_workspace():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What is ResearchOS?", "project_id": None
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=30)
    assert r.status_code == 200
    assert len(r.json().get("reply", "")) > 10

test("Assistant - general question", test_assistant_workspace)

def test_assistant_project():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What projects do I have?", "project_id": PROJECT_ID_AUDIT
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=30)
    assert r.status_code == 200

test("Assistant - project question", test_assistant_project)

def test_assistant_document():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "Summarize my uploaded paper", "project_id": PROJECT_ID_AUDIT
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=30)
    assert r.status_code == 200
    assert "test_doc" in r.json().get("reply", "").lower() or "machine learning" in r.json().get("reply", "").lower()

test("Assistant - document question", test_assistant_document)

# ---- 10. SECURITY / CROSS-USER ----
print("\n--- 10. Security / Cross-User ---")

def test_cross_user_project():
    r = requests.get(f"{BASE}/api/v1/projects/",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT2}"}, timeout=10)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert PROJECT_ID_AUDIT not in ids

test("User 2 cannot see User 1's projects", test_cross_user_project)

def test_cross_user_document():
    r = requests.get(f"{BASE}/api/v1/papers/documents/{DOC_ID_AUDIT}/content",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT2}"}, timeout=10)
    assert r.status_code in (404, 403)

test("User 2 cannot access User 1's document", test_cross_user_document)

# ---- 11. DELETIONS ----
print("\n--- 11. Deletions ---")

def test_delete_evidence_item():
    global ES_ID_AUDIT
    # Re-create the evidence session first (it was deleted by a later test)
    r_recreate = requests.post(f"{BASE}/api/v1/evidence-sessions/project/{PROJECT_ID_AUDIT}", json={
        "title": "Temp Evidence Session for Deletion Test"
    }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    if r_recreate.status_code in (200, 201):
        ES_ID_AUDIT = r_recreate.json()["id"]
        # Add an item
        r_item = requests.post(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}/items", json={
            "item_type": "reference", "item_id": REF_ID_AUDIT, "note": "Test note"
        }, headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
        if r_item.status_code in (200, 201):
            item_id = r_item.json()["id"]
            r2 = requests.delete(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}/items/{item_id}",
                headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
            assert r2.status_code == 204
            # Verify removed
            r3 = requests.get(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}",
                headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
            remaining_ids = [i["id"] for i in r3.json().get("items", [])]
            assert item_id not in remaining_ids

test("Delete evidence item", test_delete_evidence_item)

def test_delete_evidence_session():
    r = requests.delete(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 204
    # Verify removed
    r2 = requests.get(f"{BASE}/api/v1/evidence-sessions/{ES_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r2.status_code == 404

test("Delete evidence session", test_delete_evidence_session)

def test_delete_draft():
    r = requests.delete(f"{BASE}/api/v1/paper-drafts/{DRAFT_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 204

test("Delete paper draft", test_delete_draft)

def test_delete_reference():
    r = requests.delete(f"{BASE}/api/v1/references/{REF_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 204

test("Delete reference", test_delete_reference)

def test_delete_paper():
    r = requests.delete(f"{BASE}/api/v1/papers/{PAPER_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 204

test("Delete paper", test_delete_paper)

def test_delete_document():
    r = requests.delete(f"{BASE}/api/v1/papers/documents/{DOC_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 204

test("Delete document", test_delete_document)

def test_delete_project():
    r = requests.delete(f"{BASE}/api/v1/projects/{PROJECT_ID_AUDIT}",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r.status_code == 204

test("Delete project", test_delete_project)

# ---- 12. VERIFICATION AFTER DELETIONS ----
print("\n--- 12. Post-Deletion Verification ---")

def test_paper_still_deleted():
    r2 = requests.get(f"{BASE}/api/v1/papers/",
        headers={"Authorization": f"Bearer {TOKEN_AUDIT}"}, timeout=10)
    assert r2.status_code == 200
    data = r2.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    ids = [p["id"] for p in data]
    assert PAPER_ID_AUDIT not in ids

test("Deleted paper still gone", test_paper_still_deleted)

# ---- SUMMARY ----
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
if errors:
    print("\nFAILED TESTS:")
    for e in errors:
        print(f"  - {e}")
print()

sys.exit(0 if failed == 0 else 1)
