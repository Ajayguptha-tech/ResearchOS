"""Test Evidence Sessions CRUD end-to-end."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import requests

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  PASS  {name}")
        passed += 1
    except Exception as e:
        msg = str(e) if str(e).strip() else repr(e)
        print(f"  FAIL  {name}: {msg[:300]}")
        failed += 1

print("\n=== EVIDENCE SESSION TESTS ===\n")

# Auth
r = requests.post(f"{BASE}/api/v1/auth/register", json={"name": "ES Tester", "email": "es_test3@test.com", "password": "TestPass123!"})
token = r.json()["access_token"] if r.status_code == 200 else requests.post(f"{BASE}/api/v1/auth/login", json={"email": "es_test3@test.com", "password": "TestPass123!"}).json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Create project
r = requests.post(f"{BASE}/api/v1/projects", json={"title": "ES Test Project", "domain": "Testing"}, headers=h)
pid = r.json()["id"]

# Create a reference to attach later
r = requests.post(f"{BASE}/api/v1/references/project/{pid}", json={"title": "Test Ref", "url": "https://example.com", "authors": "Author A", "year": 2024}, headers=h)
ref_id = r.json()["id"]

print(f"Setup: project #{pid}, reference #{ref_id}\n")
print("Running tests...\n")

# --- CREATE ---
def test_create():
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/project/{pid}", json={
        "title": "Session 1",
        "description": "Test session",
        "notes": "Some notes",
        "session_date": "2025-01-15T10:00:00",
    }, headers=h)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data["title"] == "Session 1"
    assert data["project_id"] == pid
    assert data["status"] == "active"
test("CREATE evidence session", test_create)

# --- LIST ---
sessions_id = None
def test_list():
    global sessions_id
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/project/{pid}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    sessions_id = data[0]["id"]
    assert data[0]["title"] == "Session 1"
test("LIST evidence sessions", test_list)

# --- GET ---
def test_get():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/{sessions_id}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == sessions_id
    assert data["description"] == "Test session"
    assert data["notes"] == "Some notes"
    assert isinstance(data["items"], list)
test("GET evidence session detail", test_get)

# --- UPDATE ---
def test_update():
    r = requests.patch(f"{BASE}/api/v1/evidence-sessions/{sessions_id}", json={
        "title": "Updated Session",
        "status": "completed",
    }, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Updated Session"
    assert data["status"] == "completed"
test("UPDATE evidence session", test_update)

# --- ADD ITEM (reference) ---
item_id = None
def test_add_item():
    global item_id
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/{sessions_id}/items", json={
        "item_type": "reference",
        "item_id": ref_id,
        "note": "Important reference",
    }, headers=h)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data["item_type"] == "reference"
    assert data["item_id"] == ref_id
    assert data["title"] == "Test Ref"
    assert data["url"] == "https://example.com"
    item_id = data["id"]
test("ADD item (reference) to session", test_add_item)

# --- VERIFY ITEM IN SESSION ---
def test_item_in_session():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/{sessions_id}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test Ref"
test("VERIFY item appears in session detail", test_item_in_session)

# --- DUPLICATE ITEM ---
def test_duplicate_item():
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/{sessions_id}/items", json={
        "item_type": "reference",
        "item_id": ref_id,
    }, headers=h)
    assert r.status_code == 409, f"Expected 409, got {r.status_code}"
test("PREVENT duplicate item", test_duplicate_item)

# --- REMOVE ITEM ---
def test_remove_item():
    r = requests.delete(f"{BASE}/api/v1/evidence-sessions/{sessions_id}/items/{item_id}", headers=h)
    assert r.status_code == 204
    # Verify removed
    r2 = requests.get(f"{BASE}/api/v1/evidence-sessions/{sessions_id}", headers=h)
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 0
test("REMOVE item from session", test_remove_item)

# --- VERIFY ORIGINAL REFERENCE INTACT ---
def test_ref_intact():
    r = requests.get(f"{BASE}/api/v1/references/{ref_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["title"] == "Test Ref"
test("VERIFY original reference still exists", test_ref_intact)

# --- CREATE SECOND SESSION ---
session2_id = None
def test_create_second():
    global session2_id
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/project/{pid}", json={"title": "Session 2"}, headers=h)
    assert r.status_code == 201
    session2_id = r.json()["id"]
test("CREATE second session", test_create_second)

# --- LIST TWO ---
def test_list_two():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/project/{pid}", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 2
test("LIST shows two sessions", test_list_two)

# --- DELETE SESSION ---
def test_delete():
    global sessions_id
    r = requests.delete(f"{BASE}/api/v1/evidence-sessions/{sessions_id}", headers=h)
    assert r.status_code == 204
    # Verify deleted
    r2 = requests.get(f"{BASE}/api/v1/evidence-sessions/{sessions_id}", headers=h)
    assert r2.status_code == 404
test("DELETE evidence session", test_delete)

# --- PROJECT INTACT ---
def test_project_intact():
    r = requests.get(f"{BASE}/api/v1/projects/{pid}", headers=h)
    assert r.status_code == 200
    assert r.json()["title"] == "ES Test Project"
test("VERIFY project still intact after session deletion", test_project_intact)

# --- REFERENCE INTACT ---
def test_ref_still():
    r = requests.get(f"{BASE}/api/v1/references/{ref_id}", headers=h)
    assert r.status_code == 200
test("VERIFY reference still intact after session deletion", test_ref_still)

# --- CROSS-USER ISOLATION ---
def test_cross_user():
    r = requests.post(f"{BASE}/api/v1/auth/register", json={"name": "Other", "email": "es_other3@test.com", "password": "OtherPass123!"})
    token2 = r.json()["access_token"] if r.status_code == 200 else requests.post(f"{BASE}/api/v1/auth/login", json={"email": "es_other3@test.com", "password": "OtherPass123!"}).json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}
    # Can't list sessions from another user's project
    r2 = requests.get(f"{BASE}/api/v1/evidence-sessions/project/{pid}", headers=h2)
    assert r2.status_code == 404
    # Can't get session by ID
    r3 = requests.get(f"{BASE}/api/v1/evidence-sessions/{session2_id}", headers=h2)
    assert r3.status_code == 404
test("BLOCK cross-user session access", test_cross_user)

# --- NOT FOUND ---
def test_not_found():
    r = requests.get(f"{BASE}/api/v1/evidence-sessions/99999", headers=h)
    assert r.status_code == 404
test("404 for nonexistent session", test_not_found)

# --- LIST ON EMPTY PROJECT ---
def test_empty_project():
    r = requests.post(f"{BASE}/api/v1/projects", json={"title": "Empty", "domain": "None"}, headers=h)
    eid = r.json()["id"]
    r2 = requests.get(f"{BASE}/api/v1/evidence-sessions/project/{eid}", headers=h)
    assert r2.status_code == 200
    assert len(r2.json()) == 0
test("LIST on empty project returns empty array", test_empty_project)

# --- Summary ---
print(f"\n{'='*40}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print(f"{'='*40}")
sys.exit(1 if failed > 0 else 0)
