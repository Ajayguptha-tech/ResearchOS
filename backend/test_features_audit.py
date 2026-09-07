"""Feature-specific tests for Literature Search and Paper Writing Agent."""
import sys
import os
import subprocess
import time
import requests

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
print("FEATURE AUDIT: Literature Search + Paper Writing Agent")
print("=" * 60)

# Start server
print("\nStarting server...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
)
for i in range(30):
    try:
        r = requests.get(f"{BASE}/health", timeout=2)
        if r.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(1)

# Register and get token
EMAIL = f"feature_{int(time.time())}@test.com"
r = requests.post(f"{BASE}/api/v1/auth/register", json={
    "email": EMAIL, "password": "TestPass123!", "name": "Feature Tester"
}, timeout=10)
TOKEN = r.json().get("access_token")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Create project
r = requests.post(f"{BASE}/api/v1/projects/", json={
    "title": "Feature Test Project", "domain": "Computer Science"
}, headers=HEADERS, timeout=10)
PROJECT_ID = r.json()["id"]

# Upload a document
import io
content = b"This research paper examines machine learning methods for healthcare diagnosis. " * 200
files = {"file": ("healthcare_ml.txt", io.BytesIO(content), "text/plain")}
r = requests.post(f"{BASE}/api/v1/papers/upload?project_id={PROJECT_ID}",
    files=files, headers=HEADERS, timeout=30)
DOC_ID = r.json()["id"]

# ---- LITERATURE SEARCH ----
print("\n--- 1. Literature Search (20-year window) ---")

def test_literature_search():
    r = requests.post(f"{BASE}/api/v1/research/search-literature?idea=machine+learning+healthcare&max_results=30&page=1&per_page=10",
        headers=HEADERS, timeout=120)
    assert r.status_code == 200, f"Status: {r.status_code}"
    data = r.json()
    assert "results" in data
    assert "total" in data
    assert "page" in data
    assert "total_pages" in data
    # Check year range is dynamic (20-year window)
    current_year = 2026
    for paper in data["results"]:
        year = paper.get("year")
        if year:
            assert 2006 <= year <= current_year, f"Year {year} outside 20-year window"
    return True

test("Literature search with pagination", test_literature_search)

def test_literature_search_more_than_10():
    r = requests.post(f"{BASE}/api/v1/research/search-literature?idea=machine+learning+healthcare&max_results=50&page=1&per_page=50",
        headers=HEADERS, timeout=120)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 10, f"Expected more than 10 papers, got {data['total']}"
    return True

test("More than 10 papers accessible", test_literature_search_more_than_10)

def test_paper_scoring():
    r = requests.post(f"{BASE}/api/v1/research/search-literature?idea=machine+learning+healthcare&max_results=10&page=1&per_page=10",
        headers=HEADERS, timeout=120)
    assert r.status_code == 200
    data = r.json()
    for paper in data["results"]:
        score = paper.get("relevance_score")
        assert score is not None, "Score missing"
        assert 0 <= score <= 100, f"Score {score} out of range"
        explanation = paper.get("score_explanation")
        assert explanation is not None, "Score explanation missing"
        assert "citation_impact" in explanation
        assert "recency" in explanation
        assert "topic_relevance" in explanation
    return True

test("Paper scoring has explanation", test_paper_scoring)

def test_citation_data():
    r = requests.post(f"{BASE}/api/v1/research/search-literature?idea=machine+learning+healthcare&max_results=5&page=1&per_page=5",
        headers=HEADERS, timeout=120)
    assert r.status_code == 200
    data = r.json()
    found_citations = False
    for paper in data["results"]:
        if paper.get("citation_count", 0) > 0:
            found_citations = True
    assert found_citations, "No papers with citation data found"
    return True

test("Citation count present in results", test_citation_data)

# ---- PAPER WRITING AGENT ----
print("\n--- 2. Paper Writing Agent ---")

def test_create_and_generate_draft():
    # Create draft
    r = requests.post(f"{BASE}/api/v1/paper-drafts/project/{PROJECT_ID}", json={
        "title": "ML in Healthcare: A Review",
        "instruction": "Write an IEEE-style paper with abstract, introduction, and methodology",
        "source_document_ids": [DOC_ID],
        "source_paper_ids": [],
    }, headers=HEADERS, timeout=10)
    assert r.status_code in (200, 201)
    draft_id = r.json()["id"]

    # Generate (should use grounded template since no LLM)
    r2 = requests.post(f"{BASE}/api/v1/paper-drafts/{draft_id}/generate",
        headers=HEADERS, timeout=30)
    assert r2.status_code == 200
    data = r2.json()
    assert data["status"] == "success"
    content = data["draft"]["content"]
    assert len(content) > 100, "Generated content too short"
    assert "ML in Healthcare" in content or "ml in healthcare" in content.lower(), "Title not in draft"
    assert "# " in content, "No headings in draft"
    return True

test("Create and generate draft", test_create_and_generate_draft)

def test_draft_version_history():
    r = requests.post(f"{BASE}/api/v1/paper-drafts/project/{PROJECT_ID}", json={
        "title": "Version Test Draft",
    }, headers=HEADERS, timeout=10)
    draft_id = r.json()["id"]

    # Generate
    requests.post(f"{BASE}/api/v1/paper-drafts/{draft_id}/generate", headers=HEADERS, timeout=30)

    # Save (creates version)
    requests.patch(f"{BASE}/api/v1/paper-drafts/{draft_id}", json={
        "content": "Updated content for version test"
    }, headers=HEADERS, timeout=10)

    # List versions
    r3 = requests.get(f"{BASE}/api/v1/paper-drafts/{draft_id}/versions", headers=HEADERS, timeout=10)
    assert r3.status_code == 200
    versions = r3.json()
    assert len(versions) >= 2, f"Expected >= 2 versions, got {len(versions)}"
    return True

test("Draft version history preserved", test_draft_version_history)

def test_draft_source_grounding():
    """Verify the draft references actual source content."""
    r = requests.post(f"{BASE}/api/v1/paper-drafts/project/{PROJECT_ID}", json={
        "title": "Grounding Test",
        "instruction": "Focus on machine learning methods",
        "source_document_ids": [DOC_ID],
    }, headers=HEADERS, timeout=10)
    draft_id = r.json()["id"]

    r2 = requests.post(f"{BASE}/api/v1/paper-drafts/{draft_id}/generate",
        headers=HEADERS, timeout=30)
    assert r2.status_code == 200
    content = r2.json()["draft"]["content"]
    # The grounded template should mention the source
    assert "machine learning" in content.lower() or "healthcare" in content.lower(), \
        "Draft doesn't reference source content"
    return True

test("Draft grounded in source documents", test_draft_source_grounding)

# ---- ASSISTANT WITH NEW FEATURES ----
print("\n--- 3. Assistant with Workspace Context ---")

def test_assistant_evidence_sessions():
    # Create an evidence session
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/project/{PROJECT_ID}", json={
        "title": "Literature Review Session",
        "description": "Gathering evidence from recent papers"
    }, headers=HEADERS, timeout=10)
    assert r.status_code in (200, 201)

    # Ask assistant about evidence sessions
    r2 = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What evidence sessions do I have?",
        "project_id": PROJECT_ID
    }, headers=HEADERS, timeout=30)
    assert r2.status_code == 200
    reply = r2.json().get("reply", "").lower()
    assert "evidence session" in reply or "literature review session" in reply
    return True

test("Assistant knows about evidence sessions", test_assistant_evidence_sessions)

def test_assistant_document_content():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What methodology is discussed in my uploaded document?",
        "project_id": PROJECT_ID
    }, headers=HEADERS, timeout=30)
    assert r2.status_code == 200
    reply = r2.json().get("reply", "").lower()
    # Should reference the document content
    assert len(reply) > 50, "Reply too short"
    return True

test("Assistant uses document content", test_assistant_document_content)

def test_assistant_general_question():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "How do I write a good literature review?",
        "project_id": None
    }, headers=HEADERS, timeout=30)
    assert r.status_code == 200
    reply = r2.json().get("reply", "").lower()
    assert len(reply) > 50
    return True

test("Assistant answers general research questions", test_assistant_general_question)

# ---- CLEANUP ----
print("\n--- Cleanup ---")
requests.delete(f"{BASE}/api/v1/projects/{PROJECT_ID}", headers=HEADERS, timeout=10)

# Stop server
print("\nStopping server...")
server.terminate()
server.wait(timeout=5)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
if errors:
    print("\nFAILED TESTS:")
    for e in errors:
        print(f"  - {e}")
print()
sys.exit(0 if failed == 0 else 1)
