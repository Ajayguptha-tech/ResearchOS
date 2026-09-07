import sys, traceback
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
try:
    from app.api.v1.routes import assistant
    from app.main import app
    from app.schemas.assistant import AssistantMessageRequest, AssistantMessageResponse
    print("ALL IMPORTS OK")
    print(f"Routes: {len(app.routes)}")
except Exception:
    traceback.print_exc()
    sys.exit(1)
