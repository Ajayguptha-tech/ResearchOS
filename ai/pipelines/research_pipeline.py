from ai.agents.literature_search_agent import LiteratureSearchAgent
from ai.agents.paper_analyzer_agent import PaperAnalyzerAgent
from ai.agents.research_planner_agent import ResearchPlannerAgent


class ResearchPipeline:
    def __init__(self) -> None:
        self.planner = ResearchPlannerAgent()
        self.search = LiteratureSearchAgent()
        self.analyzer = PaperAnalyzerAgent()

    def execute(self, idea: str) -> dict:
        plan = self.planner.plan(idea)
        literature = self.search.search(idea)
        analysis = self.analyzer.analyze(literature.get("results", []))
        return {
            "plan": plan,
            "literature": literature,
            "analysis": analysis,
            "requires_evidence": True,
        }
