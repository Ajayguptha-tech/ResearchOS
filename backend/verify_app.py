"""Verify the FastAPI app loads correctly with all routes."""
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
routes = [r.path for r in app.routes if hasattr(r, "path")]
print(f"{len(routes)} routes loaded")
for r in sorted(routes):
    print(f"  {r}")

# Verify the literature agent works
from ai.agents.literature_search_agent import LiteratureSearchAgent
agent = LiteratureSearchAgent()
print("\nLiterature agent OK")
print(f"Current year: {__import__('datetime').datetime.now().year}")
print(f"Year window: {__import__('datetime').datetime.now().year - 20} - {__import__('datetime').datetime.now().year}")
