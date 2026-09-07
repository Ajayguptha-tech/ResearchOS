import subprocess, time, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
print(f"Started backend PID: {proc.pid}")

# Wait for server to start
for i in range(10):
    time.sleep(1)
    if proc.poll() is not None:
        print(f"Server exited with code: {proc.returncode}")
        print(proc.stderr.read().decode())
        break
    print(f"Waiting... {i+1}s")

# Test health
import urllib.request
try:
    resp = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5)
    print(f"Health: {resp.read().decode()}")
except Exception as e:
    print(f"Health check failed: {e}")

# Keep running
print("Server running. PID:", proc.pid)
