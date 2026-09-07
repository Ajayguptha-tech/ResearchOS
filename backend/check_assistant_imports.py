"""Verify all backend imports still work after assistant rewrite."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

results = []
def check(label, expr):
    try:
        exec(expr)
        results.append((label, "OK"))
    except Exception as e:
        results.append((label, f"FAIL: {e}"))

check("assistant route", "from app.api.v1.routes.assistant import router, _build_workspace_context, _fallback_answer, _call_llm")
check("main app", "from app.main import app")
check("all routes", "from app.api.v1.routes import assistant, auth, papers, projects, research, references, research_papers, reminders, followups, notifications, communications, law, supervisor")
check("config", "from app.core.config import settings")
check("models", "from app.db.models import Project, ResearchDocument, Reference, AnalysisResult, ResearchPaper, User")
check("schemas", "from app.schemas.assistant import AssistantMessageRequest, AssistantMessageResponse")

for label, status in results:
    symbol = "+" if status == "OK" else "X"
    print(f"  [{symbol}] {label}: {status}")

# Count routes
from app.main import app
route_count = len(app.routes)
print(f"\nTotal routes: {route_count}")

failed = sum(1 for _, s in results if s != "OK")
print(f"\nImport check: {len(results) - failed}/{len(results)} passed")

with open("import_check_result.txt", "w", encoding="utf-8") as f:
    for label, status in results:
        f.write(f"[{status}] {label}\n")
    f.write(f"\nTotal routes: {route_count}\n")
    f.write(f"Import check: {len(results) - failed}/{len(results)} passed\n")
    if failed:
        f.write("FAILED\n")
    else:
        f.write("ALL OK\n")

if failed > 0:
    sys.exit(1)
