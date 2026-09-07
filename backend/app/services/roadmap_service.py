class RoadmapService:
    def build(self, idea: str) -> dict:
        return {
            "idea": idea,
            "plan": [
                "Define research questions",
                "Review relevant literature",
                "Design experiments",
                "Document evidence and gaps",
                "Prepare final plan",
            ],
            "status": "draft",
        }
