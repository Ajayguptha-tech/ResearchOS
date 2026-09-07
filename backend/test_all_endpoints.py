"""Test all ResearchOS endpoints."""
import sys, os, json, requests
os.chdir(os.path.dirname(os.path.abspath(__file__)))

BASE = "http://127.0.0.1:8000"
results = []

def test(label, fn):
    try:
        fn()
        results.append((label, "PASS"))
    except Exception as e:
        results.append((label, f"FAIL: {e}"))

# Health
test("health check", lambda: (
    (r := requests.get(f"{BASE}/health")) and r.status_code == 200 or (_ for _ in ()).throw(Exception(f"status {r.status_code}"))
))

# Auth - register
def register():
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": "test_papers_new@example.com",
        "password": "TestPass123!",
        "name": "Paper Test User"
    })
    return r.status_code == 200
test("register", register)

# Auth - login
def login():
    r = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": "test_papers_new@example.com",
        "password": "TestPass123!"
    })
    return r.status_code == 200
test("login", login)

# Get token
login_resp = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "test_papers_new@example.com",
    "password": "TestPass123!"
})
token = login_resp.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

# Create project
def create_project():
    r = requests.post(f"{BASE}/api/v1/projects/", json={
        "title": "Test Paper Project",
        "domain": "Computer Science"
    }, headers=headers)
    return r.status_code == 200
test("create project", create_project)

# List projects
def list_projects():
    r = requests.get(f"{BASE}/api/v1/projects/", headers=headers)
    return r.status_code == 200 and len(r.json()) > 0
test("list projects", list_projects)

# Get project ID
projects_resp = requests.get(f"{BASE}/api/v1/projects/", headers=headers)
project_id = projects_resp.json()[0]["id"]

# Create paper (evidence)
def create_paper():
    r = requests.post(f"{BASE}/api/v1/papers/", json={
        "title": "Deep Learning for NLP",
        "abstract": "A survey of methods",
        "year": 2023,
        "citation_count": 150
    }, headers=headers)
    return r.status_code == 200 and r.json()["id"] > 0
test("create paper", create_paper)

# List papers
def list_papers():
    r = requests.get(f"{BASE}/api/v1/papers/", headers=headers)
    return r.status_code == 200 and len(r.json()) > 0
test("list papers", list_papers)

# Mark paper as recent
def mark_recent():
    papers_resp = requests.get(f"{BASE}/api/v1/papers/", headers=headers)
    pid = papers_resp.json()[0]["id"]
    r = requests.patch(f"{BASE}/api/v1/papers/{pid}", json={"is_recent": True}, headers=headers)
    return r.status_code == 200 and r.json().get("is_recent") == True
test("mark paper recent", mark_recent)

# Unmark paper as recent
def unmark_recent():
    papers_resp = requests.get(f"{BASE}/api/v1/papers/", headers=headers)
    pid = papers_resp.json()[0]["id"]
    r = requests.patch(f"{BASE}/api/v1/papers/{pid}", json={"is_recent": False}, headers=headers)
    return r.status_code == 200 and r.json().get("is_recent") == False
test("unmark paper recent", unmark_recent)

# Create draft
def create_draft():
    r = requests.post(f"{BASE}/api/v1/paper-drafts/project/{project_id}", json={
        "title": "Test Paper Draft",
        "instruction": "Write an IEEE paper on AI",
        "source_document_ids": [],
        "source_paper_ids": []
    }, headers=headers)
    return r.status_code == 201 and r.json()["id"] > 0
test("create draft", create_draft)

# List drafts
def list_drafts():
    r = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=headers)
    return r.status_code == 200 and len(r.json()) > 0
test("list drafts", list_drafts)

# Get draft
def get_draft():
    drafts_resp = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=headers)
    did = drafts_resp.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/paper-drafts/{did}", headers=headers)
    return r.status_code == 200 and r.json()["title"] == "Test Paper Draft"
test("get draft", get_draft)

# Generate draft content
def generate_draft():
    drafts_resp = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=headers)
    did = drafts_resp.json()[0]["id"]
    r = requests.post(f"{BASE}/api/v1/paper-drafts/{did}/generate", headers=headers)
    return r.status_code == 200 and r.json().get("status") == "success"
test("generate draft", generate_draft)

# Update draft
def update_draft():
    drafts_resp = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=headers)
    did = drafts_resp.json()[0]["id"]
    r = requests.patch(f"{BASE}/api/v1/paper-drafts/{did}", json={
        "content": "Updated content here"
    }, headers=headers)
    return r.status_code == 200 and r.json()["content"] == "Updated content here"
test("update draft", update_draft)

# List draft versions
def list_versions():
    drafts_resp = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=headers)
    did = drafts_resp.json()[0]["id"]
    r = requests.get(f"{BASE}/api/v1/paper-drafts/{did}/versions", headers=headers)
    return r.status_code == 200 and len(r.json()) > 0
test("list draft versions", list_versions)

# Search literature endpoint
def search_literature():
    r = requests.post(f"{BASE}/api/v1/research/search-literature?idea=machine+learning&max_results=5&page=1&per_page=5", headers=headers)
    return r.status_code == 200
test("search literature endpoint", search_literature)

# Existing tests
def list_references():
    r = requests.get(f"{BASE}/api/v1/references/project/{project_id}", headers=headers)
    return r.status_code == 200
test("list references", list_references)

def create_reference():
    r = requests.post(f"{BASE}/api/v1/references/project/{project_id}", json={
        "title": "Test Reference",
        "url": "https://example.com"
    }, headers=headers)
    return r.status_code == 200
test("create reference", create_reference)

def list_evidence():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/project/{project_id}", headers=headers)
    return r.status_code == 200
test("list evidence sessions", list_evidence)

def list_reminders():
    r = requests.get(f"{BASE}/api/v1/reminders/", headers=headers)
    return r.status_code == 200
test("list reminders", list_reminders)

# Delete draft
def delete_draft():
    drafts_resp = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=headers)
    did = drafts_resp.json()[0]["id"]
    r = requests.delete(f"{BASE}/api/v1/paper-drafts/{did}", headers=headers)
    return r.status_code == 204
test("delete draft", delete_draft)

# Delete paper
def delete_paper():
    papers_resp = requests.get(f"{BASE}/api/v1/papers/", headers=headers)
    pid = papers_resp.json()[0]["id"]
    r = requests.delete(f"{BASE}/api/v1/papers/{pid}", headers=headers)
    return r.status_code == 204
test("delete paper", delete_paper)

# Cross-user security
def cross_user_block():
    r2 = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": "test_other@example.com",
        "password": "OtherPass123!",
        "name": "Other User"
    })
    t2 = requests.post(f"{BASE}/api/v1/auth/login", json={
        "email": "test_other@example.com",
        "password": "OtherPass123!"
    }).json().get("access_token", "")
    h2 = {"Authorization": f"Bearer {t2}"}
    r = requests.get(f"{BASE}/api/v1/paper-drafts/project/{project_id}", headers=h2)
    return r.status_code in (404, 403)
test("cross-user draft access blocked", cross_user_block)

# Report
with open("test_all_result.txt", "w", encoding="utf-8") as f:
    for label, status in results:
        f.write(f"{status:6s} | {label}\n")
    passed = sum(1 for _, s in results if s == "PASS")
    f.write(f"\n{passed}/{len(results)} tests passed\n")
    for label, status in results:
        if status != "PASS":
            f.write(f"  FAILED: {label} -> {status}\n")
