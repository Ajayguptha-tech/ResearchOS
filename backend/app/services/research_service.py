"""LEGACY / UNUSED — do not wire into routes.

This class returns HARDCODED placeholder results (including a fake
``proj_demo_001`` project id) and is NOT used by any active endpoint.
Real project CRUD lives in ``app/db/repositories/project_repository.py``
(routes/projects.py) and the real research workflow runs through
``app/services/agent_orchestrator.py`` + the ``ai/agents/*`` implementations.

Kept only so legacy code that may still import it does not crash.
"""


class ResearchService:
    def __init__(self) -> None:
        self.active_workflows = []

    def create_project(self, title: str, user_id: str) -> dict:
        return {
            "project_id": "proj_demo_001",
            "title": title,
            "user_id": user_id,
            "status": "draft",
        }

    def generate_research_plan(self, idea: str) -> dict:
        return {
            "idea": idea,
            "status": "planned",
            "evidence_required": True,
            "agents": [
                "Research Planner Agent",
                "Literature Search Agent",
                "Semantic Retrieval Agent",
                "Gap Analysis Agent",
                "Roadmap Generator Agent",
            ],
        }
