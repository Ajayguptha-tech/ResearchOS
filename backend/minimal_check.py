"""Minimal import check."""
import sys
import traceback

try:
    from app.api.v1.routes import assistant
    with open("import_result.txt", "w") as f:
        f.write("OK\n")
except Exception:
    with open("import_result.txt", "w") as f:
        traceback.print_exc(file=f)
    sys.exit(1)
