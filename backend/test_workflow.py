"""End-to-end API workflow test for ResearchOS."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")

import json
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine

# Ensure tables exist
Base.metadata.create_all(bind=engine)

client = TestClient(app)
tests = []

def test(name, fn):
    try:
        fn()
        tests.append((name, "PASS", ""))
    except AssertionError as e:
        tests.append((name, "FAIL", str(e)))
    except Exception as e:
        tests.append((name, "ERROR", str(e)[:200]))

# TEST 1: Register
token = None
def test_register():
    global token
    r = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "TestPass123",
        "name": "Test User",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    assert "access_token" in data
    token = data["access_token"]
test("Register new user", test_register)

# TEST 2: Get profile
def test_me():
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
test("Get user profile", test_me)

# TEST 3: Login
def test_login():
    r = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123",
    })
    assert r.status_code == 200
    assert "access_token" in r.json()
test("Login with credentials", test_login)

# TEST 4: Duplicate email registration
def test_dup_email():
    global token
    r = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "AnotherPass456",
        "name": "Test User Two",
    })
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    assert "access_token" in r.json()
test("Register second account with same email", test_dup_email)

# TEST 5: Wrong password
def test_wrong_password():
    r = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPassword",
    })
    assert r.status_code == 401
test("Login with wrong password fails", test_wrong_password)

# TEST 6: Create project
project_id = None
def test_create_project():
    global project_id
    r = client.post("/api/v1/projects/", json={
        "title": "Cybersecurity Research",
        "domain": "Network Security",
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    project_id = data["id"]
    assert data["title"] == "Cybersecurity Research"
test("Create research project", test_create_project)

# TEST 7: List projects
def test_list_projects():
    r = client.get("/api/v1/projects/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) >= 1
    assert any(p["title"] == "Cybersecurity Research" for p in projects)
test("List projects shows created project", test_list_projects)

# TEST 8: Upload TXT document
doc_id = None
def test_upload_txt():
    global doc_id
    r = client.post(
        f"/api/v1/papers/upload?project_id={project_id}",
        files={"file": ("research.txt", b"This paper presents a novel deep learning approach for network intrusion detection. The proposed method uses convolutional neural networks to classify network traffic patterns. Our experiments show 95% accuracy on the NSL-KDD benchmark dataset.", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    data = r.json()
    doc_id = data["id"]
    assert data["filename"] == "research.txt"
    assert data["extracted_characters"] > 0
test("Upload TXT document", test_upload_txt)

# TEST 9: List project documents
def test_list_project_docs():
    r = client.get(f"/api/v1/papers/documents/project/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) >= 1
    assert docs[0]["filename"] == "research.txt"
test("List project documents", test_list_project_docs)

# TEST 10: Run AI analysis
analysis_result = None
def test_analysis():
    global analysis_result
    r = client.post(
        f"/api/v1/research/analyze-local?idea=network+intrusion+detection+using+deep+learning&project_id={project_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    analysis_result = r.json()
    # Check analysis contains real content
    assert "analysis" in analysis_result
    assert analysis_result["analysis"]["papers_processed"] >= 1
    paper = analysis_result["analysis"]["papers"][0]
    assert "methods" in paper
    assert len(paper["methods"]) > 0
test("Run AI analysis on uploaded document", test_analysis)

# TEST 11: Save analysis
def test_save_analysis():
    r = client.post(
        "/api/v1/research/save-analysis",
        json={
            "project_id": project_id,
            "research_idea": "network intrusion detection using deep learning",
            "document_ids": [doc_id],
            "result_json": json.dumps(analysis_result),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    assert "id" in r.json()
test("Save analysis result", test_save_analysis)

# TEST 12: Load persisted analysis
def test_load_analyses():
    r = client.get(f"/api/v1/research/analyses/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    analyses = r.json()
    assert len(analyses) >= 1
    assert "result_json" in analyses[0]
test("Load persisted analyses", test_load_analyses)

# TEST 13: Dataset recommendations have URLs
def test_dataset_urls():
    recs = analysis_result.get("datasets", {}).get("recommendations", [])
    assert len(recs) > 0, "No dataset recommendations"
    for rec in recs:
        assert "url" in rec, f"Dataset '{rec.get('name')}' missing URL"
        url = rec["url"]
        assert url.startswith("http"), f"Dataset URL not clickable: {url}"
test("Dataset recommendations have real URLs", test_dataset_urls)

# TEST 14: Create second project
def test_second_project():
    r = client.post("/api/v1/projects/", json={
        "title": "ML Research",
        "domain": "Machine Learning",
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    p = r.json()
    assert p["title"] == "ML Research"
test("Create second project", test_second_project)

# TEST 15: Projects are isolated
def test_project_isolation():
    r = client.get(f"/api/v1/papers/documents/project/{project_id}", headers={"Authorization": f"Bearer {token}"})
    docs = r.json()
    # The first project should only have its own doc
    assert all(d.get("project_id") == project_id or d.get("project_id") is None for d in docs)
test("Project document isolation", test_project_isolation)

# TEST 16: Health check
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
test("Health check", test_health)

# Print results
print()
print("=" * 60)
print("RESEARCHOS END-TO-END API WORKFLOW TEST")
print("=" * 60)
passed = 0
failed = 0
for name, status, detail in tests:
    marker = "[PASS]" if status == "PASS" else "[FAIL]"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {marker} {name}{suffix}")
    if status == "PASS":
        passed += 1
    else:
        failed += 1

print()
print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
if failed:
    print("OVERALL: FAIL")
    sys.exit(1)
else:
    print("OVERALL: ALL TESTS PASSED")
