"""Start backend server, run tests, stop server."""
import subprocess
import sys
import time
import os
import requests

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("Starting backend server...")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for server to be ready
ready = False
for i in range(30):
    try:
        r = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if r.status_code == 200:
            ready = True
            print(f"Server ready after {i+1} seconds")
            break
    except Exception:
        pass
    time.sleep(1)

if not ready:
    print("ERROR: Server did not start in time")
    server.terminate()
    sys.exit(1)

# Run tests
print("\nRunning full audit tests...\n")
result = subprocess.run(
    [sys.executable, "test_full_audit.py"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
)

# Stop server
print("\nStopping server...")
server.terminate()
server.wait(timeout=5)
print("Server stopped.")

sys.exit(result.returncode)
