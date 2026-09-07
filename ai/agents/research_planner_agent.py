class ResearchPlannerAgent:
    def __init__(self) -> None:
        self.name = "Research Planner Agent"

    def plan(self, idea: str) -> dict:
        return {
            "idea": idea,
            "objectives": ["scope the problem", "find relevant literature", "turn evidence into roadmap"],
            "status": "ready",
        }
