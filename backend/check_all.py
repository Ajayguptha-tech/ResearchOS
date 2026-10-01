import sys
sys.path.insert(0, ".")
errors = []
modules = [
    ("app.db.base", "Base"),
    ("app.db.models", "User"), ("app.db.models", "Project"), ("app.db.models", "ResearchDocument"),
    ("app.db.models", "ResearchPaper"), ("app.db.models", "AnalysisResult"), ("app.db.models", "Reference"),
    ("app.db.session", "engine"), ("app.db.migrations", "upgrade_sqlite_schema"),
    ("app.core.config", "settings"), ("app.core.security", "hash_password"),
    ("app.services.document_service", "DocumentService"),
    ("app.services.agent_orchestrator", "AgentOrchestrator"),
    ("ai.agents.paper_analyzer_agent", "PaperAnalyzerAgent"),
    ("ai.agents.dataset_recommendation_agent", "DatasetRecommendationAgent"),
    ("ai.agents.research_gap_agent", "ResearchGapAgent"),
]
for mod_path, attr in modules:
    try:
        mod = __import__(mod_path, fromlist=[attr])
        getattr(mod, attr)
        print(f"  OK  {mod_path}.{attr}")
    except Exception as e:
        print(f"  FAIL  {mod_path}.{attr}: {e}")
        errors.append(f"{mod_path}.{attr}: {e}")

try:
    from app.main import app
    route_count = len(app.routes)
    print(f"  OK  FastAPI app ({route_count} routes)")
except Exception as e:
    print(f"  FAIL  FastAPI app: {e}")
    errors.append(f"FastAPI app: {e}")

if errors:
    print(f"\nRESULT: {len(errors)} failures")
    sys.exit(1)
else:
    print("\nRESULT: ALL OK")
