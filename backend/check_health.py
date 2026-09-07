import urllib.request, json, sys
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)
    data = json.loads(r.read())
    with open("health_result.txt", "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2))
    print("Backend healthy:", data)
except Exception as e:
    with open("health_result.txt", "w", encoding="utf-8") as f:
        f.write(f"ERROR: {e}")
    print(f"Backend unreachable: {e}")
    sys.exit(1)
