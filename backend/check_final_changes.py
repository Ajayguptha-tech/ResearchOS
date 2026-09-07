"""Check imports and run full API tests for the final changes."""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=== IMPORT CHECKS ===")
checks = [
    ("literature_search_agent", "from ai.agents.literature_search_agent import LiteratureSearchAgent"),
    ("assistant route", "from app.api.v1.routes.assistant import router"),
    ("evidence_sessions route", "from app.api.v1.routes.evidence_sessions import router"),
    ("main app", "from app.main import app"),
    ("models", "from app.db.models import EvidenceSession, EvidenceSessionItem"),
]

all_ok = True
for label, stmt in checks:
    try:
        exec(stmt)
        print(f"  OK  {label}")
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        all_ok = False

# Test the literature agent scoring
print("\n=== LITERATURE AGENT SCORING TEST ===")
try:
    from ai.agents.literature_search_agent import LiteratureSearchAgent
    agent = LiteratureSearchAgent()
    # Mock data with different citation counts
    test_papers = [
        {"title": "Deep learning for NLP", "authors": ["A"], "abstract": "deep learning natural language processing", "year": 2024, "url": "", "doi": "10.1/test1", "citation_count": 500, "venue": "ICML", "source": "Semantic Scholar", "citations_available": True},
        {"title": "A survey of ML methods", "authors": ["B"], "abstract": "machine learning survey methods", "year": 2019, "url": "", "doi": "10.1/test2", "citation_count": 1200, "venue": "JMLR", "source": "Semantic Scholar", "citations_available": True},
        {"title": "Recent advances in transformers", "authors": ["C"], "abstract": "transformer architecture deep learning", "year": 2023, "url": "", "doi": "10.1/test3", "citation_count": 50, "venue": "NeurIPS", "source": "Semantic Scholar", "citations_available": True},
    ]
    ranked = agent._rank_results("deep learning methods", test_papers)
    for p in ranked:
        score = p["relevance_score"]
        expl = p["score_explanation"]
        cite_count = p["citation_count"]
        print(f"  Score: {score:3d}/100 | Citations: {cite_count:5d} | "
              f"Impact: {expl['citation_impact']:6s} | "
              f"Recency: {expl['recency']:6s} | "
              f"Title: {p['title'][:40]}")
    print("  OK  Scoring model works")
except Exception as e:
    print(f"  FAIL Scoring model: {e}")
    all_ok = False

if all_ok:
    print("\nAll import checks passed.")
else:
    print("\nSome checks failed!")
    sys.exit(1)
