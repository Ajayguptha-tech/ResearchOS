from __future__ import annotations

import logging

from ai.agents.dataset_recommendation_agent import (
    DatasetRecommendationAgent,
)
from ai.agents.experiment_planning_agent import (
    ExperimentPlanningAgent,
)
from ai.agents.literature_search_agent import (
    LiteratureSearchAgent,
)
from ai.agents.paper_analyzer_agent import (
    PaperAnalyzerAgent,
)
from ai.agents.research_gap_agent import (
    ResearchGapAgent,
)
from ai.agents.research_planner_agent import (
    ResearchPlannerAgent,
)
from ai.agents.roadmap_generator_agent import (
    RoadmapGeneratorAgent,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self) -> None:
        self.planner = ResearchPlannerAgent()
        self.literature = LiteratureSearchAgent()
        self.paper_analyzer = PaperAnalyzerAgent()
        self.gap_analyzer = ResearchGapAgent()
        self.dataset_agent = DatasetRecommendationAgent()
        self.experiment_agent = ExperimentPlanningAgent()
        self.roadmap = RoadmapGeneratorAgent()

    def run_research_workflow(
        self,
        idea: str,
        papers: list[dict] | None = None,
        max_results: int = 30,
    ) -> dict:

        logger.info("[Research] Received idea: %s", idea)

        # Planning and literature are required for an evidence-backed response.
        plan = self.planner.plan(idea)

        if papers is None:
            logger.info("[Research] Searching literature providers")
            literature = self.literature.search(idea, max_results=max_results)
            papers = literature.get(
                "results",
                [],
            )
        else:
            literature = {
                "query": idea,
                "results": papers,
                "status": "success",
                "source": "local_uploaded_documents",
            }
        if not papers:
            message = literature.get("message", "Literature providers returned no usable papers.")
            logger.error("[Research] Literature search failed: %s", message)
            raise RuntimeError(message)
        logger.info("[Research] Unique ranked papers: %d", len(papers))

        # 3. Paper analysis
        logger.info("[Research] Running paper analysis")
        analysis = self.paper_analyzer.analyze(
            papers,
        )

        # 4. Research gap analysis
        gaps = self.gap_analyzer.analyze(
            idea,
            papers,
            analysis,
        )

        # 5. Dataset recommendation
        datasets = self.dataset_agent.recommend(
            idea,
            papers,
        )

        # 6. Experiment planning
        experiments = self.experiment_agent.plan(
            idea,
            gaps,
            datasets,
            papers,
        )

        # 7. Final roadmap
        roadmap = self.roadmap.generate(
            idea,
            analysis,
            gaps,
            datasets,
            experiments,
        )

        evidence_backed = len(papers) >= 3

        return {
            "plan": plan,
            "literature": literature,
            "analysis": analysis,
            "research_gaps": gaps,
            "datasets": datasets,
            "experiments": experiments,
            "roadmap": roadmap,
            "evidence_backed": evidence_backed,
            "ai_generated_opportunities": [
                gap["title"]
                for gap in gaps.get(
                    "gaps",
                    [],
                )
            ],
        }
