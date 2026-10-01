"""LEGACY / UNUSED — do not wire into routes.

This class returns a HARDCODED fake paper ("paper-001") and is NOT used by
any active endpoint.  Real retrieval over the user's uploaded documents is
implemented in ``app/services/document_service.py`` (DocumentService.retrieve)
and exposed by ``/api/v1/papers/retrieve``.

Kept only so legacy code that may still import it does not crash.
"""


class RetrievalService:
    def semantic_search(self, query: str, limit: int = 10) -> list[dict]:
        return [
            {
                "paper_id": "paper-001",
                "title": f"Relevant paper for: {query}",
                "score": 0.92,
                "citation_count": 145,
                "summary": "Evidence-backed literature snippet generated from semantic retrieval.",
            }
        ][:limit]
