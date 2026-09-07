"""Test the universal answering agent with diverse question types."""
import requests
import json

BASE = "http://127.0.0.1:8000"
results = []

def test(label, fn):
    try:
        fn()
        results.append((label, "PASS"))
        print(f"  [PASS] {label}")
    except Exception as e:
        results.append((label, f"FAIL: {e}"))
        print(f"  [FAIL] {label}: {e}")

# --- Setup ---
r = requests.post(f"{BASE}/api/v1/auth/register", json={
    "email": "universal@test.com", "password": "Test12345678", "name": "Universal Tester"
})
if r.status_code in (200, 201):
    token = r.json()["access_token"]
else:
    r = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": "universal@test.com", "password": "Test12345678"
    })
    token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Create project
r = requests.post(f"{BASE}/api/v1/projects/", json={
    "title": "AI in Healthcare", "domain": "Machine Learning"
}, headers=h)
project_id = r.json()["id"]

# Upload a document
import io
txt_content = b"This paper explores the use of deep learning for medical image classification. The authors used a CNN architecture trained on 50,000 chest X-ray images achieving 94% accuracy. The methodology involved transfer learning from ResNet-50. Key limitations include the small dataset size and lack of diversity in patient demographics."
files = {"file": ("research_paper.txt", io.BytesIO(txt_content), "text/plain")}
r = requests.post(f"{BASE}/api/v1/papers/upload?project_id={project_id}", files=files, headers=h)
doc = r.json()

# Add a reference
r = requests.post(f"{BASE}/api/v1/references/project/{project_id}", json={
    "title": "Deep Learning for Medical Imaging", "authors": "Smith et al.", "year": 2023
}, headers=h)

print("\n=== UNIVERSAL ASSISTANT TESTS ===\n")

# --- General Knowledge ---
def test_general():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "What is the speed of light?"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert len(data["reply"]) > 50, f"Reply too short: {data['reply']}"
    print(f"    Reply length: {len(data['reply'])} chars")
test("General knowledge question", test_general)

def test_python():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "How do I create a Python function?"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "python" in data["reply"].lower() or "function" in data["reply"].lower()
test("Python/programming question", test_python)

def test_ml():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "What is the difference between supervised and unsupervised learning?"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["reply"]) > 50
test("Machine learning question", test_ml)

# --- Project-specific ---
def test_projects():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "What projects do I have?"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "AI in Healthcare" in data["reply"], f"Expected project name in reply: {data['reply'][:200]}"
test("Workspace project list", test_projects)

def test_current_project():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What is my current project about?",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "AI in Healthcare" in data["reply"] or "healthcare" in data["reply"].lower()
test("Current project info", test_current_project)

# --- Document-aware ---
def test_doc_summary():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "Summarize my uploaded paper",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["reply"]) > 50
    # Should mention content from the actual document
    reply_lower = data["reply"].lower()
    assert any(kw in reply_lower for kw in ["deep learning", "medical", "cnn", "chest", "94%"]), \
        f"Reply doesn't reference document content: {data['reply'][:300]}"
test("Document summary question", test_doc_summary)

def test_doc_methodology():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What methodology is used in the uploaded paper?",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    reply_lower = data["reply"].lower()
    assert any(kw in reply_lower for kw in ["methodology", "method", "cnn", "resnet", "transfer"]), \
        f"Reply doesn't mention methodology: {data['reply'][:300]}"
test("Document methodology question", test_doc_methodology)

def test_doc_limitations():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What are the limitations?",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    reply_lower = data["reply"].lower()
    assert any(kw in reply_lower for kw in ["limitation", "dataset size", "diversity"]), \
        f"Reply doesn't mention limitations: {data['reply'][:300]}"
test("Document limitations question", test_doc_limitations)

# --- References ---
def test_references():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "Show me my references",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "Deep Learning for Medical Imaging" in data["reply"]
test("References question", test_references)

# --- Evidence ---
def test_evidence():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What evidence sessions do I have?",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["reply"]) > 20
test("Evidence sessions question", test_evidence)

# --- Research methodology ---
def test_methodology():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "How do I write a literature review?"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "literature review" in data["reply"].lower()
test("Research methodology question", test_methodology)

# --- Empty workspace context ---
def test_researchos():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "What is ResearchOS?"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "researchos" in data["reply"].lower()
test("What is ResearchOS", test_researchos)

# --- Follow-up question ---
def test_followup():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What about the second one?",
        "project_id": project_id
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["reply"]) > 20
test("Follow-up question", test_followup)

# --- Empty question ---
def test_empty():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": ""}, headers=h)
    assert r.status_code in [400, 422], f"Expected 400/422, got {r.status_code}"
test("Empty question returns error", test_empty)

# --- Source field ---
def test_source():
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={"message": "Hello"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "source" in data, "Response missing 'source' field"
    assert len(data["source"]) > 0
test("Source field present in response", test_source)

# --- Summary ---
print(f"\n{'='*50}")
passed = sum(1 for _, s in results if s == "PASS")
failed = sum(1 for _, s in results if s != "PASS")
print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
if failed:
    print("\nFailed tests:")
    for label, status in results:
        if status != "PASS":
            print(f"  {label}: {status}")
