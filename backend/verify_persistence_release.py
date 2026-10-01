"""Persistence audit script: create temporary record, verify, restart, verify, cleanup."""
import requests
import sys

BASE = "http://127.0.0.1:8000"

mode = sys.argv[1] if len(sys.argv) > 1 else "create"

if mode == "create":
    # 1. Register temporary user
    r = requests.post(f"{BASE}/api/v1/auth/register", json={
        "email": "persist_check@example.com", "password": "PassCheck123!", "name": "Persist Checker"
    })
    if r.status_code in (200, 201):
        token = r.json()["access_token"]
    else:
        r = requests.post(f"{BASE}/api/v1/auth/login", json={
            "email": "persist_check@example.com", "password": "PassCheck123!"
        })
        token = r.json()["access_token"]
    
    h = {"Authorization": f"Bearer {token}"}
    # Create temporary project
    r = requests.post(f"{BASE}/api/v1/projects/", json={
        "title": "TEMPORARY_PERSISTENCE_CHECK_XYZ",
        "domain": "Audit",
        "description": "Will be deleted after restart check"
    }, headers=h)
    assert r.status_code in (200, 201), f"Create failed: {r.text}"
    p_id = r.json()["id"]
    with open("temp_persist_id.txt", "w") as f:
        f.write(f"{token}\n{p_id}")
    print(f"Created temporary project #{p_id}")

elif mode == "verify_and_cleanup":
    with open("temp_persist_id.txt", "r") as f:
        lines = f.read().strip().splitlines()
        token = lines[0]
        p_id = int(lines[1])
    
    h = {"Authorization": f"Bearer {token}"}
    # Verify it persists after restart
    r = requests.get(f"{BASE}/api/v1/projects/", headers=h)
    assert r.status_code == 200, f"List failed: {r.text}"
    projects = r.json()
    found = any(p["id"] == p_id and p["title"] == "TEMPORARY_PERSISTENCE_CHECK_XYZ" for p in projects)
    assert found, f"Project #{p_id} NOT found after restart!"
    print(f"Verified project #{p_id} persisted across service restart!")
    
    # Clean up ONLY this record
    r_del = requests.delete(f"{BASE}/api/v1/projects/{p_id}", headers=h)
    assert r_del.status_code in (200, 204), f"Delete failed: {r_del.text}"
    print(f"Cleaned up temporary project #{p_id}")
    
    # Confirm deletion
    r_check = requests.get(f"{BASE}/api/v1/projects/", headers=h)
    still_there = any(p["id"] == p_id for p in r_check.json())
    assert not still_there, f"Project #{p_id} was NOT deleted!"
    print(f"Confirmed temporary project #{p_id} is cleanly removed.")
