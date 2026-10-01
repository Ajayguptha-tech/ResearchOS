import requests
import json

BASE_BACKEND = "http://127.0.0.1:8000"
BASE_FRONTEND = "http://localhost:3000"

def run_live_e2e():
    results = {}
    print("--- 1. Testing Pre-login & Route Endpoints ---")
    # Test /law on frontend
    r_law = requests.get(f"{BASE_FRONTEND}/law")
    print(f"GET /law status: {r_law.status_code}")
    assert r_law.status_code == 404, f"Expected 404 for /law, got {r_law.status_code}"
    results["frontend_law_404"] = "PASS"

    # Test /login on frontend
    r_login = requests.get(f"{BASE_FRONTEND}/login")
    print(f"GET /login status: {r_login.status_code}")
    assert r_login.status_code == 200, f"Expected 200 for /login, got {r_login.status_code}"
    # Verify no workspace navigation links in login HTML
    assert "Legal research" not in r_login.text, "Found 'Legal research' in login HTML!"
    assert "workspace-sidebar" not in r_login.text, "Found sidebar in login HTML!"
    results["frontend_login_pristine"] = "PASS"

    # Test /law and /assistant on backend
    r_be_law = requests.get(f"{BASE_BACKEND}/api/v1/law/projects")
    print(f"GET /api/v1/law/projects: {r_be_law.status_code}")
    assert r_be_law.status_code == 404, f"Expected 404 for /api/v1/law, got {r_be_law.status_code}"
    
    r_be_asst = requests.post(f"{BASE_BACKEND}/api/v1/assistant/chat", json={"message": "hi"})
    print(f"POST /api/v1/assistant/chat: {r_be_asst.status_code}")
    assert r_be_asst.status_code == 404, f"Expected 404 for /api/v1/assistant, got {r_be_asst.status_code}"
    results["backend_unmounted_routes_404"] = "PASS"

    print("\n--- 2. Testing Authentication & User Setup ---")
    email = "live_e2e_researcher@researchos.io"
    password = "SecurePassword123!"
    
    # Try register or login
    reg_res = requests.post(f"{BASE_BACKEND}/api/v1/auth/register", json={
        "email": email, "password": password, "name": "Live E2E Tester"
    })
    if reg_res.status_code == 200:
        token = reg_res.json()["access_token"]
    else:
        login_res = requests.post(f"{BASE_BACKEND}/api/v1/auth/login", json={
            "email": email, "password": password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    results["auth_flow"] = "PASS"
    print("Authenticated successfully.")

    print("\n--- 3. Testing Strict Document Scope Isolation ---")
    # Create Project A
    p_a_res = requests.post(f"{BASE_BACKEND}/api/v1/projects/", headers=headers, json={
        "title": "Quantum Encryption Project A", "domain": "Quantum Computing"
    })
    assert p_a_res.status_code == 200
    p_a = p_a_res.json()
    p_a_id = p_a["id"]

    # Create Project B
    p_b_res = requests.post(f"{BASE_BACKEND}/api/v1/projects/", headers=headers, json={
        "title": "Bioinformatics Project B", "domain": "Genomics"
    })
    assert p_b_res.status_code == 200
    p_b = p_b_res.json()
    p_b_id = p_b["id"]

    # Upload Doc 1 to Project A
    files_a = {"file": ("quantum_protocol.txt", b"This paper evaluates quantum key distribution (QKD) protocols. Key finding: decoy-state BB84 achieves 10 Mbps secret key rate over 50 km fiber. Methodology: numerical simulation with channel loss 0.2 dB/km.", "text/plain")}
    doc_a_res = requests.post(f"{BASE_BACKEND}/api/v1/papers/upload?project_id={p_a_id}", headers=headers, files=files_a)
    assert doc_a_res.status_code == 201, f"Upload A failed: {doc_a_res.text}"
    doc_a = doc_a_res.json()
    assert doc_a["project_id"] == p_a_id

    # Upload Doc 2 to Main Workspace (project_id is None)
    files_global = {"file": ("global_survey.txt", b"A global survey of artificial intelligence trends in 2026. Key finding: transformer efficiency improved 4x through sparse attention. Methodology: empirical benchmarking across 20 models.", "text/plain")}
    doc_global_res = requests.post(f"{BASE_BACKEND}/api/v1/papers/upload", headers=headers, files=files_global)
    assert doc_global_res.status_code == 201, f"Upload Global failed: {doc_global_res.text}"
    doc_global = doc_global_res.json()
    assert doc_global["project_id"] is None

    # Verify Project A documents: contains Doc A, NOT Doc Global
    docs_a = requests.get(f"{BASE_BACKEND}/api/v1/papers/documents/project/{p_a_id}", headers=headers).json()
    doc_a_ids = [d["id"] for d in docs_a]
    assert doc_a["id"] in doc_a_ids, "Project A doc missing from Project A!"
    assert doc_global["id"] not in doc_a_ids, "Global doc leaked into Project A!"

    # Verify Project B documents: contains NEITHER Doc A nor Doc Global
    docs_b = requests.get(f"{BASE_BACKEND}/api/v1/papers/documents/project/{p_b_id}", headers=headers).json()
    doc_b_ids = [d["id"] for d in docs_b]
    assert doc_a["id"] not in doc_b_ids, "Project A doc leaked into Project B!"
    assert doc_global["id"] not in doc_b_ids, "Global doc leaked into Project B!"

    # Verify Main Workspace documents: contains Doc Global, NOT Doc A
    docs_main = requests.get(f"{BASE_BACKEND}/api/v1/papers/documents", headers=headers).json()
    doc_main_ids = [d["id"] for d in docs_main]
    assert doc_global["id"] in doc_main_ids, "Global doc missing from Main Workspace!"
    assert doc_a["id"] not in doc_main_ids, "Project A doc leaked into Main Workspace!"
    print("Document scope isolation verified across Project A, Project B, and Main Workspace!")
    results["document_scope_isolation"] = "PASS"

    print("\n--- 4. Testing One-Click Summarize Documents Endpoint ---")
    # Summarize Project A (no prompt provided!)
    sum_a_res = requests.post(f"{BASE_BACKEND}/api/v1/research/summarize-documents?project_id={p_a_id}", headers=headers)
    assert sum_a_res.status_code == 200, f"Summarize failed: {sum_a_res.text}"
    sum_a = sum_a_res.json()
    print(f"Project A summary count: {len(sum_a['summaries'])}")
    assert len(sum_a["summaries"]) == 1
    item_a = sum_a["summaries"][0]
    print(f"Title: {item_a['title']}")
    print(f"Summary: {item_a['summary']}")
    print(f"Key Findings: {item_a['key_findings']}")
    print(f"Methodology: {item_a['methodology']}")
    assert item_a["document_id"] == doc_a["id"]
    assert "decoy-state" in item_a["summary"] or "QKD" in item_a["summary"] or "quantum" in item_a["summary"].lower()

    # Summarize Main Workspace
    sum_main_res = requests.post(f"{BASE_BACKEND}/api/v1/research/summarize-documents", headers=headers)
    assert sum_main_res.status_code == 200
    sum_main = sum_main_res.json()
    print(f"Main workspace summary count: {len(sum_main['summaries'])}")
    main_doc_ids_summarized = [s["document_id"] for s in sum_main["summaries"]]
    assert doc_global["id"] in main_doc_ids_summarized
    assert doc_a["id"] not in main_doc_ids_summarized
    print("One-click summarize documents verified for both Project A and Main Workspace!")
    results["summarize_documents_grounded"] = "PASS"

    print("\n--- 5. Testing Paper Writing Agent Scoping & Anti-Hallucination ---")
    draft_res = requests.post(f"{BASE_BACKEND}/api/v1/paper-drafts/project/{p_a_id}", headers=headers, json={
        "title": "Quantum Protocol Investigation",
        "instruction": "Synthesize the current findings"
    })
    assert draft_res.status_code == 201, f"Draft create failed: {draft_res.text}"
    draft = draft_res.json()
    gen_res = requests.post(f"{BASE_BACKEND}/api/v1/paper-drafts/{draft['id']}/generate", headers=headers)
    assert gen_res.status_code == 200, f"Draft generate failed: {gen_res.text}"
    gen_data = gen_res.json()
    content = gen_data["draft"]["content"]
    print("Generated Draft snippet:\n", content[:300], "...")
    assert "quantum" in content.lower() or "qkd" in content.lower() or "decoy" in content.lower()
    assert "No specific gaps were documented" in content or "gaps identified" in content.lower() or "limitations" in content.lower()
    # Ensure source documents scoped strictly to Project A
    assert gen_data["draft"]["source_document_ids"] == [doc_a["id"]]
    print("Paper writing agent scoping & anti-hallucination verified!")
    results["paper_writing_agent_scoping"] = "PASS"

    print("\n--- 6. Testing Literature Search Citation Provenance ---")
    lit_res = requests.get(f"{BASE_BACKEND}/api/v1/research/literature/search?query=quantum+key+distribution&page=1&per_page=5", headers=headers)
    assert lit_res.status_code == 200
    lit_data = lit_res.json()
    assert "results" in lit_data
    if len(lit_data["results"]) > 0:
        first_p = lit_data["results"][0]
        print(f"Paper: {first_p['title']}")
        print(f"Citations: {first_p.get('citation_count')}")
        print(f"Citation Source: {first_p.get('citation_source')}")
        print(f"Google Scholar Verified: {first_p.get('google_scholar_verified')}")
        print(f"Google Scholar Citations: {first_p.get('google_scholar_citations')}")
        assert first_p.get("citation_source") in ["Semantic Scholar", "Crossref", "Semantic Scholar / Crossref"]
        assert first_p.get("google_scholar_verified") is False
        assert first_p.get("google_scholar_citations") is None
    print("Literature search citation provenance verified!")
    results["literature_citation_provenance"] = "PASS"

    print("\n--- Summary of Live E2E Results ---")
    for k, v in results.items():
        print(f"  {k}: {v}")
    
    assert all(v == "PASS" for v in results.values()), "Some tests did not pass!"
    print("\nALL LIVE E2E INTEGRATION CHECKS PASSED!")

if __name__ == "__main__":
    run_live_e2e()
