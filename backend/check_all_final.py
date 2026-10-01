import sys, traceback, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
results = []
def check(label, expr):
    try:
        exec(expr)
        results.append((label, "OK"))
    except Exception as e:
        results.append((label, f"FAIL: {e}"))

check("evidence sessions route", "from app.api.v1.routes.evidence_sessions import router")
from app.main import app
results.append(("main app", "OK"))
check("all routes", "from app.api.v1.routes import assistant, auth, communications, evidence_sessions, followups, law, notifications, papers, projects, references, reminders, research, research_papers, supervisor")
check("models", "from app.db.models import EvidenceSession, EvidenceSessionItem, Project, Reference, AnalysisResult, ResearchDocument")
check("schemas", "from app.schemas.evidence_sessions import EvidenceSessionCreate, EvidenceSessionResponse, EvidenceSessionUpdate, EvidenceSessionItemCreate, EvidenceSessionItemResponse")

for label, status in results:
    symbol = "+" if status == "OK" else "X"
    print(f"  [{symbol}] {label}: {status}")

print(f"\nRoutes: {len(app.routes)}")
failed = sum(1 for _, s in results if s != "OK")
print(f"Import check: {len(results) - failed}/{len(results)} passed")
if failed > 0:
    sys.exit(1)
print("\nALL OK")
