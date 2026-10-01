import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
# Make sure ai module is importable
sys.path.insert(0, os.getcwd())

results = []
checks = [
    ("paper_drafts route", "from app.api.v1.routes.paper_drafts import router"),
    ("paper_drafts schema", "from app.schemas.paper_drafts import PaperDraftCreate, PaperDraftResponse"),
    ("paper_writing_agent", "from ai.agents.paper_writing_agent import PaperWritingAgent"),
    ("PaperDraft model", "from app.db.models import PaperDraft, PaperDraftVersion"),
    ("main app", "from app.main import app"),
]

for label, expr in checks:
    try:
        exec(expr)
        results.append((label, "OK"))
    except Exception as e:
        results.append((label, f"FAIL: {e}"))

with open("check_new_result.txt", "w", encoding="utf-8") as f:
    for label, status in results:
        f.write(f"{label}: {status}\n")
    f.write(f"\nTotal: {sum(1 for _, s in results if s == 'OK')}/{len(results)} passed\n")
