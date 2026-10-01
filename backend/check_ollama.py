import urllib.request, json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
try:
    r = urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3)
    data = json.loads(r.read())
    models = [m['name'] for m in data.get('models', [])]
    with open('ollama_result.txt', 'w', encoding='utf-8') as f:
        f.write(f"Ollama running. Models: {', '.join(models) if models else 'none'}\n")
    print(f"Ollama running. Models: {models}")
except Exception as e:
    with open('ollama_result.txt', 'w', encoding='utf-8') as f:
        f.write(f"Ollama NOT running: {e}\n")
    print(f"Ollama NOT running: {e}")
