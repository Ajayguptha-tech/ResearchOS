"""LEGACY / UNUSED — do not wire into routes.

This class claims PDF/DOCX exports were "generated" without producing any
file.  It is NOT used by any active endpoint.  Do not use it for real export
functionality; implement exports with an actual generator (e.g. reportlab /
python-docx) that produces a verifiable file.

Kept only so legacy code that may still import it does not crash.
"""


class ExportService:
    def export_pdf(self, project_id: str) -> dict:
        return {"project_id": project_id, "format": "pdf", "status": "generated"}

    def export_docx(self, project_id: str) -> dict:
        return {"project_id": project_id, "format": "docx", "status": "generated"}
