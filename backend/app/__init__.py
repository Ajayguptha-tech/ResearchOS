"""ResearchOS backend package.

The repository keeps shared AI agents at the project root.  Make that root
available when the documented ``cd backend && uvicorn app.main:app`` command
is used, without requiring callers to set PYTHONPATH manually.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure all models are imported so Base.metadata.create_all() registers them.
import app.db.models  # noqa: F401, E402
