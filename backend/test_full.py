"""Full end-to-end ResearchOS API test suite."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)
client = TestClient(app)
tests = []

def test(name, fn):
    try:
        fn()
        tests.append((name, "PASS", ""))
    except AssertionError as e:
        tests.append((name, "FAIL", str(e)[:200]))
    except Exception as e:
        tests.append((name, "ERROR", str(e)[:200]))

# === AUTH ===
token = None
def test_register():
    global token
    r = client.post("/api/v1/auth/register", json={"email": "test@full.com", "password": "TestPass123", "name": "Test User"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    token = r.json()["access_token"]
test("Register", test_register)

def test_dup_email():
    r = client.post("/api/v1/auth/register", json={"email": "test@full.com", "password": "AnotherPass456", "name": "Test User 2"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
test("Duplicate email registration", test_dup_email)

def test_login():
    r = client.post("/api/v1/auth/login", json={"email": "test@full.com", "password": "TestPass123"})
    assert r.status_code == 200
test("Login", test_login)

def test_wrong_pw():
    r = client.post("/api/v1/auth/login", json={"email": "test@full.com", "password": "WrongPassword"})
    assert r.status_code == 401
test("Wrong password", test_wrong_pw)

def test_me():
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@full.com"
test("Get profile", test_me)

# === PROJECTS ===
project_id = None
def test_create_project():
    global project_id
    r = client.post("/api/v1/projects/", json={"title": "Test Project", "domain": "AI Research", "description": "A test research project"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    project_id = r.json()["id"]
test("Create project", test_create_project)

def test_list_projects():
    r = client.get("/api/v1/projects/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert any(p["title"] == "Test Project" for p in r.json())
test("List projects", test_list_projects)

def test_get_project():
    r = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["description"] == "A test research project"
test("Get project with description", test_get_project)

# === DOCUMENTS ===
doc_id = None
def test_upload_txt():
    global doc_id
    r = client.post(f"/api/v1/papers/upload?project_id={project_id}",
        files={"file": ("paper.txt", b"This paper presents a deep learning approach for network intrusion detection using CNN. Results show 95% accuracy.", "text/plain")},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    doc_id = r.json()["id"]
    assert r.json()["extracted_characters"] > 0
test("Upload TXT document", test_upload_txt)

def test_upload_pdf():
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text="Deep Learning for Security", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="Abstract: We propose a CNN-based IDS with 95% accuracy on NSL-KDD.", new_x="LMARGIN", new_y="NEXT")
    r = client.post(f"/api/v1/papers/upload?project_id={project_id}",
        files={"file": ("security.pdf", bytes(pdf.output()), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, f"PDF upload failed: {r.status_code} {r.text}"
    assert r.json()["extracted_characters"] > 0
test("Upload PDF", test_upload_pdf)

def test_upload_docx():
    from docx import Document
    from io import BytesIO
    doc = Document()
    doc.add_heading("ML Research", level=1)
    doc.add_paragraph("We use supervised learning for classification tasks.")
    buf = BytesIO()
    doc.save(buf)
    r = client.post(f"/api/v1/papers/upload?project_id={project_id}",
        files={"file": ("ml.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
test("Upload DOCX", test_upload_docx)

def test_list_project_docs():
    r = client.get(f"/api/v1/papers/documents/project/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 3
test("List project documents", test_list_project_docs)

def test_get_doc_content():
    r = client.get(f"/api/v1/papers/documents/{doc_id}/content", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "deep learning" in r.json()["extracted_text"].lower()
test("Get document content", test_get_doc_content)

def test_get_doc_summary():
    r = client.get(f"/api/v1/papers/documents/{doc_id}/summary", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "preview" in r.json()
test("Get document summary", test_get_doc_summary)

# === REFERENCES ===
ref_id = None
def test_create_ref():
    global ref_id
    r = client.post(f"/api/v1/references/project/{project_id}",
        json={"title": "Test Paper", "url": "https://example.com/paper", "authors": "Author One", "year": 2024},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    ref_id = r.json()["id"]
test("Create reference", test_create_ref)

def test_list_refs():
    r = client.get(f"/api/v1/references/project/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
test("List references", test_list_refs)

def test_get_ref():
    r = client.get(f"/api/v1/references/{ref_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["url"] == "https://example.com/paper"
test("Get reference", test_get_ref)

def test_delete_ref():
    r = client.delete(f"/api/v1/references/{ref_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
    r2 = client.get(f"/api/v1/references/{ref_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 404
test("Delete reference", test_delete_ref)

# === ANALYSIS ===
def test_analyze():
    r = client.post(f"/api/v1/research/analyze-local?idea=deep+learning+intrusion+detection&project_id={project_id}",
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    result = r.json()
    assert result["analysis"]["papers_processed"] >= 2
    assert len(result["datasets"]["recommendations"]) > 0
    # Check dataset URLs
    for ds in result["datasets"]["recommendations"]:
        assert ds.get("url", "").startswith("http"), f"Dataset URL missing: {ds['name']}"
test("AI Analysis with document content", test_analyze)

def test_save_analysis():
    r = client.post("/api/v1/research/save-analysis",
        json={"project_id": project_id, "research_idea": "deep learning", "document_ids": [doc_id], "result_json": "{}"},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
test("Save analysis", test_save_analysis)

def test_list_analyses():
    r = client.get(f"/api/v1/research/analyses/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
test("List analyses", test_list_analyses)

# === RESEARCH PAPER ===
def test_paper_editor():
    r = client.post(f"/api/v1/research-papers/project/{project_id}",
        json={"title": "My Paper", "content": "## Abstract\nThis is my paper content."},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    r2 = client.get(f"/api/v1/research-papers/project/{project_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["title"] == "My Paper"
test("Paper editor create and read", test_paper_editor)

# === REMINDERS ===
def test_reminders():
    r = client.post("/api/v1/reminders/", json={"title": "Review paper", "reminder_datetime": "2026-12-01T10:00:00"},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    r2 = client.get("/api/v1/reminders/", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert len(r2.json()) >= 1
test("Create and list reminders", test_reminders)

# === ASSISTANT ===
def test_assistant():
    r = client.post("/api/v1/assistant/chat", json={"message": "What can I do?", "project_id": project_id},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "ResearchOS" in r.json()["reply"]
test("Research Assistant", test_assistant)

# === DOCUMENT DELETE ===
def test_doc_delete():
    r = client.delete(f"/api/v1/papers/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
    r2 = client.get(f"/api/v1/papers/documents/{doc_id}/content", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 404
test("Delete document", test_doc_delete)

# === PROJECT DELETE ===
def test_project_delete():
    # Create a temp project to delete
    r = client.post("/api/v1/projects/", json={"title": "Delete Me", "domain": "Test"},
        headers={"Authorization": f"Bearer {token}"})
    temp_id = r.json()["id"]
    r2 = client.delete(f"/api/v1/projects/{temp_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 204
    r3 = client.get(f"/api/v1/projects/{temp_id}", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 404
test("Delete project", test_project_delete)

# === SECURITY: OWNERSHIP ===
def test_ownership():
    # Register a second user
    r = client.post("/api/v1/auth/register", json={"email": "other@test.com", "password": "OtherPass123", "name": "Other User"})
    other_token = r.json()["access_token"]
    # Try to access first user's project
    r2 = client.get(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert r2.status_code == 404, f"Expected 404, got {r2.status_code}"
    # Try to delete first user's document
    r3 = client.delete(f"/api/v1/papers/documents/{doc_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert r3.status_code == 404
test("Cross-user ownership protection", test_ownership)

# === HEALTH ===
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
test("Health check", test_health)

# Print results
print()
print("=" * 60)
print("RESEARCHOS FULL API TEST SUITE")
print("=" * 60)
passed = 0
failed = 0
for name, status, detail in tests:
    marker = "[PASS]" if status == "PASS" else "[FAIL]"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {marker} {name}{suffix}")
    if status == "PASS": passed += 1
    else: failed += 1

print(f"\nResults: {passed} passed, {failed} failed, {len(tests)} total")
if failed:
    print("OVERALL: FAIL")
    sys.exit(1)
else:
    print("OVERALL: ALL TESTS PASSED")
