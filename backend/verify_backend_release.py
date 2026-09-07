"""Live backend audit for ResearchOS release verification."""
import requests
import sys

BASE = "http://127.0.0.1:8000"
results = []

import traceback

def record(name, status, detail=""):
    results.append((name, status, detail))
    print(f"  [{status}] {name}{f' — {detail}' if detail else ''}")

# 1. Health
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200 and r.json().get("status") == "ok"
    record("GET /health", "PASS", r.text[:60])
except Exception as e:
    record("GET /health", "FAIL", str(e))

# 2. Health Dependencies
try:
    r = requests.get(f"{BASE}/health/dependencies", timeout=5)
    assert r.status_code == 200 and r.json().get("status") == "ok"
    record("GET /health/dependencies", "PASS", str(r.json().get("checks", {})))
except Exception as e:
    record("GET /health/dependencies", "FAIL", str(e))

# 3. Authentication
user_email = "release_audit_user@example.com"
user_pass = "AuditPassword123!"
token = None
try:
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": user_email, "password": user_pass, "name": "Release Auditor"
    })
    if r.status_code in (200, 201):
        token = r.json()["access_token"]
    else:
        r = requests.post(f"{BASE}/api/v1/auth/login", json={
            "email": user_email, "password": user_pass
        })
        assert r.status_code == 200
        token = r.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{BASE}/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    record("Authentication (register/login/me)", "PASS", f"User #{me.json()['id']}")
except Exception as e:
    record("Authentication", "FAIL", str(e))

if not token:
    print("Cannot continue without token")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

# 4. Projects
project_id = None
try:
    r = requests.post(f"{BASE}/api/v1/projects/", json={
        "title": "Release Audit Quantum Project",
        "domain": "Quantum Computing",
        "description": "Validation project for release readiness"
    }, headers=headers)
    assert r.status_code in (200, 201)
    project_id = r.json()["id"]
    
    r_list = requests.get(f"{BASE}/api/v1/projects/", headers=headers)
    assert any(p["id"] == project_id for p in r_list.json())
    record("Projects (create/list)", "PASS", f"Project #{project_id}")
except Exception as e:
    record("Projects", "FAIL", str(e))

# 5. Literature Search
try:
    r = requests.post(f"{BASE}/api/v1/research/search-literature?idea=transformer+attention&max_results=5&page=1&per_page=5", headers=headers)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
    data = r.json()
    items = data.get("results", [])
    assert len(items) > 0, "No results returned"
    first = items[0]
    assert first.get("title") and (first.get("doi") or first.get("url") or first.get("year"))
    record("Literature (real provider search)", "PASS", f"{len(items)} papers found; provider={data.get('provider')}")
except Exception as e:
    traceback.print_exc()
    record("Literature", "FAIL", str(e))

# 6. Documents (upload & extraction)
doc_id = None
try:
    import io
    content = b"Graph Neural Networks in Quantum Chemistry. Methodology: Molecular graph embedding with message passing. Results: Achieved 0.012 eV MAE on QM9."
    files = {"file": ("release_test.txt", io.BytesIO(content), "text/plain")}
    r = requests.post(f"{BASE}/api/v1/papers/upload?project_id={project_id}", files=files, headers=headers)
    assert r.status_code == 201
    doc_data = r.json()
    doc_id = doc_data["id"]
    assert doc_data["extracted_characters"] > 0
    
    # Read document content
    r_doc = requests.get(f"{BASE}/api/v1/papers/documents/{doc_id}/content", headers=headers)
    assert r_doc.status_code == 200, f"Status {r_doc.status_code}: {r_doc.text}"
    assert "graph neural networks" in r_doc.json().get("extracted_text", "").lower()
    record("Documents (upload, extraction & retrieval)", "PASS", f"Doc #{doc_id}, chars={doc_data['extracted_characters']}")
except Exception as e:
    traceback.print_exc()
    record("Documents", "FAIL", str(e))

# 7. References
ref_id = None
try:
    r = requests.post(f"{BASE}/api/v1/references/project/{project_id}", json={
        "title": "Quantum Chemistry via GNN",
        "url": "https://arxiv.org/abs/1704.01212",
        "authors": "Gilmer et al.",
        "year": 2017
    }, headers=headers)
    assert r.status_code in (200, 201)
    ref_id = r.json()["id"]
    
    r_refs = requests.get(f"{BASE}/api/v1/references/project/{project_id}", headers=headers)
    assert any(ref["id"] == ref_id for ref in r_refs.json())
    record("References (create/list)", "PASS", f"Ref #{ref_id}")
except Exception as e:
    record("References", "FAIL", str(e))

# 8. Evidence Sessions
es_id = None
try:
    r = requests.post(f"{BASE}/api/v1/evidence-sessions/project/{project_id}", json={
        "title": "Benchmark Synthesis Session",
        "description": "Cross-validation of literature data",
        "notes": "Verified accuracy benchmarks"
    }, headers=headers)
    assert r.status_code in (200, 201)
    es_id = r.json()["id"]
    
    # Add reference item
    if ref_id:
        r_item = requests.post(f"{BASE}/api/v1/evidence-sessions/{es_id}/items", json={
            "item_type": "reference",
            "item_id": ref_id,
            "note": "Primary baseline citation"
        }, headers=headers)
        assert r_item.status_code in (200, 201)
    
    record("Evidence Sessions (create/item attach)", "PASS", f"Session #{es_id}")
except Exception as e:
    record("Evidence Sessions", "FAIL", str(e))

# 9. Paper Writing (Drafts)
draft_id = None
try:
    r = requests.post(f"{BASE}/api/v1/paper-drafts/project/{project_id}", json={
        "title": "Draft on Quantum Graph Learning",
        "instruction": "Summarize molecular graph representations",
        "document_ids": [doc_id] if doc_id else []
    }, headers=headers)
    assert r.status_code in (200, 201)
    draft_id = r.json()["id"]
    
    # Generate content
    r_gen = requests.post(f"{BASE}/api/v1/paper-drafts/{draft_id}/generate", headers=headers)
    assert r_gen.status_code == 200
    
    # Version list
    r_ver = requests.get(f"{BASE}/api/v1/paper-drafts/{draft_id}/versions", headers=headers)
    assert r_ver.status_code == 200
    record("Paper Writing (draft/generate/versions)", "PASS", f"Draft #{draft_id}")
except Exception as e:
    record("Paper Writing", "FAIL", str(e))

# 10. Assistants
try:
    r = requests.post(f"{BASE}/api/v1/assistant/chat", json={
        "message": "What is the methodology in the uploaded document?",
        "project_id": project_id
    }, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data and len(data["reply"]) > 20
    record("Assistant (project-grounded Q&A)", "PASS", f"Source={data.get('source')}, reply_len={len(data['reply'])}")
except Exception as e:
    record("Assistant", "FAIL", str(e))

print("\n" + "=" * 50)
fails = [name for name, status, _ in results if status == "FAIL"]
if fails:
    print(f"FAILED: {len(fails)} endpoints failed: {fails}")
    sys.exit(1)
else:
    print(f"ALL {len(results)} BACKEND CHECKS PASSED LIVE!")
