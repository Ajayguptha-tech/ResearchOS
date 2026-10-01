import sys, traceback, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
try:
    from app.api.v1.routes import evidence_sessions
    from app.db.models import EvidenceSession, EvidenceSessionItem
    from app.schemas.evidence_sessions import EvidenceSessionCreate, EvidenceSessionResponse, EvidenceSessionUpdate, EvidenceSessionItemCreate, EvidenceSessionItemResponse
    from app.main import app
    print(f"ALL IMPORTS OK. Routes: {len(app.routes)}")
except Exception:
    traceback.print_exc()
    sys.exit(1)
