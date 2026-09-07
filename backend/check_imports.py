"""Quick import check for all ResearchOS backend modules."""
import sys
sys.path.insert(0, ".")

errors = []

modules = [
    ("app.db.base", "Base"),
    ("app.db.models", "User"),
    ("app.db.models", "Project"),
    ("app.db.models", "ResearchDocument"),
    ("app.db.models", "ResearchPaper"),
    ("app.db.models", "AnalysisResult"),
    ("app.db.models", "EmailVerification"),
    ("app.db.models", "PasswordResetToken"),
    ("app.db.models", "UserReminder"),
    ("app.db.session", "engine"),
    ("app.db.migrations", "upgrade_sqlite_schema"),
    ("app.core.config", "settings"),
    ("app.core.security", "hash_password"),
    ("app.services.document_service", "DocumentService"),
    ("app.services.otp_service", "create_password_reset_token"),
    ("app.services.email_service", "send_email"),
    ("ai.agents.paper_analyzer_agent", "PaperAnalyzerAgent"),
    ("ai.agents.research_gap_agent", "ResearchGapAgent"),
    ("ai.agents.dataset_recommendation_agent", "DatasetRecommendationAgent"),
    ("ai.agents.experiment_planning_agent", "ExperimentPlanningAgent"),
    ("ai.agents.roadmap_generator_agent", "RoadmapGeneratorAgent"),
    ("ai.agents.literature_search_agent", "LiteratureSearchAgent"),
    ("ai.agents.research_planner_agent", "ResearchPlannerAgent"),
    ("app.services.agent_orchestrator", "AgentOrchestrator"),
]

for module_path, attr_name in modules:
    try:
        mod = __import__(module_path, fromlist=[attr_name])
        getattr(mod, attr_name)
        print(f"  OK  {module_path}.{attr_name}")
    except Exception as e:
        print(f"  FAIL  {module_path}.{attr_name}: {e}")
        errors.append(f"{module_path}.{attr_name}: {e}")

# Check FastAPI app can be built
try:
    from app.main import app
    print(f"  OK  FastAPI app built ({len(app.routes)} routes)")
except Exception as e:
    print(f"  FAIL  FastAPI app: {e}")
    errors.append(f"FastAPI app: {e}")

print()
if errors:
    print(f"RESULT: {len(errors)} failures")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("RESULT: ALL IMPORTS OK")
