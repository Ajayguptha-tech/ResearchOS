import urllib.request, json, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
result_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_result.txt")

try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)
    data = json.loads(r.read())
    with open(result_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2))
    print("Backend healthy:", data)
except Exception as e:
    with open(result_file, "w", encoding="utf-8") as f:
        f.write(f"ERROR: {e}")
    print(f"Backend unreachable: {e}")
    sys.exit(1)
