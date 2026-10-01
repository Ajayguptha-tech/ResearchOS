import subprocess, time, sys
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
    stdout=open("server_stdout.log", "w"),
    stderr=open("server_stderr.log", "w"),
)
print(f"Started backend PID: {proc.pid}")
time.sleep(3)
print("Server starting...")
