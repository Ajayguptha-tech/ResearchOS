"""LEGACY / UNUSED — do not wire into routes.

This class returns HARDCODED placeholder sources and is NOT used by any
active endpoint.  The real literature search implementation is
``ai/agents/literature_search_agent.py`` (Semantic Scholar + Crossref),
invoked via ``app/services/agent_orchestrator.py`` and
``app/api/v1/routes/research.py``.

Kept only so legacy code that may still import it does not crash.
"""


class LiteratureService:
    def __init__(self) -> None:
        self.sources = [
            {"id": "lit_1", "title": "Evidence-backed semantic retrieval result", "score": 0.95},
            {"id": "lit_2", "title": "Related method and benchmark study", "score": 0.88},
        ]

    def get_top_sources(self, query: str) -> list[dict]:
        return [{**item, "query": query} for item in self.sources]
