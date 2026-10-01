"""Final Master End-to-End Audit Verification Script for ResearchOS."""
import sys
import json
import requests

API = "http://127.0.0.1:8000"
WEB = "http://localhost:3000"

results = []

def test(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
        print(f"  [PASS] {name}")
    except AssertionError as e:
        results.append((name, "FAIL", str(e)))
        print(f"  [FAIL] {name}: {e}")
    except Exception as e:
        results.append((name, "ERROR", str(e)[:200]))
        print(f"  [ERROR] {name}: {e}")

print("\n" + "="*60)
print("RESEARCHOS FINAL MASTER AUDIT VERIFICATION")
print("="*60 + "\n")

# 1. Backend Health
def test_backend_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
test("Backend /health endpoint", test_backend_health)

def test_dependencies():
    r = requests.get(f"{API}/health/dependencies")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in ("ok", "ready")
    assert data["checks"]["database"]["status"] == "ok"
test("Backend /health/dependencies (DB & storage)", test_dependencies)

# 2. Authentication - Register & Login & Me
token = ""
user_email = "audit_master_final@example.com"
user_pass = "MasterSecurePass123!"

def test_register():
    global token
    r = requests.post(f"{API}/api/v1/auth/register", json={
        "name": "Audit Master User",
        "email": user_email,
        "password": user_pass,
    })
    # If already registered from previous run, login instead
    if r.status_code == 201:
        token = r.json()["access_token"]
    else:
        r2 = requests.post(f"{API}/api/v1/auth/login", json={
            "email": user_email,
            "password": user_pass,
        })
        assert r2.status_code == 200, f"Login failed: {r2.text}"
        token = r2.json()["access_token"]
    assert len(token) > 20
test("Auth: Register or Login", test_register)

def test_auth_me():
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API}/api/v1/auth/me", headers=headers)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
    me = r.json()
    assert me["email"] == user_email
    assert me["name"] == "Audit Master User"
    assert "role" in me
test("Auth: GET /api/v1/auth/me", test_auth_me)

# 3. Projects
headers = {}
project_id = 0

def test_create_project():
    global headers, project_id
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API}/api/v1/projects/", json={
        "title": "Quantum Neural Computing",
        "domain": "Computer Science & Physics",
        "description": "Exploration of quantum variational circuits for deep learning",
    }, headers=headers)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
    project_id = r.json()["id"]
    assert project_id > 0
test("Projects: Create project", test_create_project)

def test_list_projects():
    r = requests.get(f"{API}/api/v1/projects/", headers=headers)
    assert r.status_code == 200
    projects = r.json()
    assert any(p["id"] == project_id for p in projects)
test("Projects: List projects", test_list_projects)

# 4. Document upload & extraction
doc_id = 0
def test_upload_doc():
    global doc_id
    content = b"Title: Quantum Deep Learning Foundations\nAuthors: Jane Doe et al.\n\nAbstract: We investigate quantum convolutional circuits.\nMethodology: Parameterized quantum gates simulated on classical hardware.\nResults: Achieved 94% accuracy on synthetic benchmark."
    files = {"file": ("quantum_foundations.txt", content, "text/plain")}
    r = requests.post(f"{API}/api/v1/papers/upload?project_id={project_id}", files=files, headers=headers)
    assert r.status_code == 201, f"Status {r.status_code}: {r.text}"
    doc_id = r.json()["id"]
    assert doc_id > 0
    assert r.json()["extracted_characters"] > 50
test("Documents: Upload & extract text", test_upload_doc)

def test_list_project_docs():
    r = requests.get(f"{API}/api/v1/papers/documents/project/{project_id}", headers=headers)
    assert r.status_code == 200
    docs = r.json()
    assert any(d["id"] == doc_id for d in docs)
test("Documents: List project documents", test_list_project_docs)

# 5. Local analysis
def test_local_analysis():
    r = requests.post(
        f"{API}/api/v1/research/analyze-local?idea=quantum+variational+algorithms&project_id={project_id}",
        headers=headers,
    )
    assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
    analysis = r.json()
    assert "methodology" in analysis or "evidence_backed" in analysis or "research_gaps" in analysis
test("Research: Run local document-grounded analysis", test_local_analysis)

# 6. References
ref_id = 0
def test_references():
    global ref_id
    r = requests.post(f"{API}/api/v1/references/project/{project_id}", json={
        "title": "Quantum Computation and Quantum Information",
        "url": "https://doi.org/10.1017/CBO9780511976666",
        "authors": "Nielsen and Chuang",
        "year": 2010,
        "notes": "Standard textbook",
        "reference_type": "book",
    }, headers=headers)
    assert r.status_code == 201, f"Status {r.status_code}: {r.text}"
    ref_id = r.json()["id"]
    r2 = requests.get(f"{API}/api/v1/references/project/{project_id}", headers=headers)
    assert r2.status_code == 200
    assert any(ref["id"] == ref_id for ref in r2.json())
test("References: Create & list project references", test_references)

# 7. Reminders
rem_id = 0
def test_reminders():
    global rem_id
    r = requests.post(f"{API}/api/v1/reminders/", json={
        "title": "Submit conference camera-ready",
        "description": "Ensure author feedback is addressed",
        "reminder_datetime": "2026-10-15T10:00:00",
    }, headers=headers)
    assert r.status_code in (200, 201), f"Status {r.status_code}: {r.text}"
    rem_id = r.json()["id"]
    r_list = requests.get(f"{API}/api/v1/reminders/", headers=headers)
    assert r_list.status_code == 200
    assert any(rem["id"] == rem_id for rem in r_list.json())
test("Reminders: Create & list reminders", test_reminders)

# 8. Paper Drafts
draft_id = 0
def test_paper_drafts():
    global draft_id
    r = requests.post(f"{API}/api/v1/paper-drafts/project/{project_id}", json={
        "title": "A Survey of Quantum Variational Optimization",
        "instruction": "Draft an introductory paper outline",
    }, headers=headers)
    assert r.status_code == 201, f"Status {r.status_code}: {r.text}"
    draft_id = r.json()["id"]
    r_gen = requests.post(f"{API}/api/v1/paper-drafts/{draft_id}/generate", headers=headers)
    assert r_gen.status_code == 200, f"Status {r_gen.status_code}: {r_gen.text}"
    r_ver = requests.get(f"{API}/api/v1/paper-drafts/{draft_id}/versions", headers=headers)
    assert r_ver.status_code == 200
test("Paper Drafts: Create, generate & list versions", test_paper_drafts)

# 9. Assistant Chat
def test_assistant():
    r = requests.post(f"{API}/api/v1/assistant/chat", json={
        "message": "What is ResearchOS?",
    }, headers=headers)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
    assert "reply" in r.json()
test("Assistant: Knowledge / workspace query", test_assistant)

# 10. Frontend Pages & SSR HTML
def test_frontend_home():
    r = requests.get(f"{WEB}/")
    assert r.status_code == 200
test("Frontend: Root page / returns 200", test_frontend_home)

def test_frontend_login():
    r = requests.get(f"{WEB}/login")
    assert r.status_code == 200
test("Frontend: /login page returns 200", test_frontend_login)

def test_frontend_dashboard():
    r = requests.get(f"{WEB}/dashboard")
    assert r.status_code == 200
test("Frontend: /dashboard page returns 200", test_frontend_dashboard)

def test_frontend_workspace_html():
    r = requests.get(f"{WEB}/workspace")
    assert r.status_code == 200
    html = r.text
    assert "ResearchOS" in html
    assert "<nav" in html
    assert "Workspace" in html
    assert "Projects" in html
    assert "Research Ideas" in html
    assert "Legal research" in html
test("Frontend: /workspace renders stable navigation shell in SSR HTML", test_frontend_workspace_html)

# Summary
passed_count = sum(1 for _, status, _ in results if status == "PASS")
failed_count = sum(1 for _, status, _ in results if status != "PASS")

print("\n" + "="*60)
print(f"RESULTS: {passed_count}/{len(results)} tests PASSED (failures: {failed_count})")
print("="*60)

if failed_count > 0:
    sys.exit(1)
sys.exit(0)
