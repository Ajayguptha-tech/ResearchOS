"""Survey Agent — synthesizes comprehensive literature surveys from academic papers and documents.

Conducts domain reviews, extracts taxonomies of methods, organizes key findings,
and compiles evidence-backed literature survey reports with full citation provenance.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.agents.literature_search_agent import LiteratureSearchAgent
from ai.agents.paper_analyzer_agent import PaperAnalyzerAgent

logger = logging.getLogger(__name__)


class SurveyAgent:
    def __init__(
        self,
        search_agent: LiteratureSearchAgent | None = None,
        analyzer_agent: PaperAnalyzerAgent | None = None,
    ) -> None:
        self.name = "Survey Agent"
        self.search_agent = search_agent or LiteratureSearchAgent()
        self.analyzer_agent = analyzer_agent or PaperAnalyzerAgent()

    def survey_topic(self, topic: str, max_papers: int = 30) -> dict[str, Any]:
        """Conduct a comprehensive academic literature survey for a research topic."""
        topic = topic.strip()
        if not topic:
            return {
                "topic": topic,
                "status": "error",
                "message": "Topic cannot be empty",
                "papers_surveyed": 0,
                "taxonomy": {},
                "synthesis": "",
            }

        logger.info("[SurveyAgent] Conducting literature survey on %r", topic)
        search_result = self.search_agent.search(topic, max_results=max_papers)
        papers = search_result.get("results", [])

        return self.survey_papers(topic, papers, source_label=search_result.get("source", "Academic Literature"))

    def survey_papers(
        self, topic: str, papers: list[dict], source_label: str = "Uploaded Documents"
    ) -> dict[str, Any]:
        """Synthesize a structured literature survey report from a collection of papers."""
        analysis = self.analyzer_agent.analyze(papers)
        analyzed_papers = analysis.get("papers", [])
        method_distribution = analysis.get("method_distribution", {})

        # Extract taxonomy
        taxonomy = {}
        for method, count in sorted(method_distribution.items(), key=lambda x: -x[1]):
            taxonomy[method] = {
                "count": count,
                "papers": [
                    p["title"] for p in analyzed_papers if method in p.get("methods", [])
                ],
            }

        # Build comparative synthesis matrix
        matrix = []
        for i, p in enumerate(analyzed_papers, start=1):
            authors_str = (
                ", ".join(p["authors"][:2]) + (" et al." if len(p["authors"]) > 2 else "")
                if isinstance(p["authors"], list)
                else str(p.get("authors") or "Unknown")
            )
            matrix.append({
                "index": i,
                "title": p.get("title", "Untitled"),
                "authors": authors_str,
                "year": p.get("year"),
                "methods": p.get("methods", []),
                "findings": p.get("findings", [])[:2],
                "limitations": p.get("limitations", [])[:1],
                "citations": p.get("citation_count", 0),
                "doi": p.get("doi", ""),
                "provenance": p.get("citation_source") or p.get("source") or source_label,
            })

        # Synthesize literature survey summary
        paper_count = len(papers)
        top_methods = list(taxonomy.keys())[:3]
        methods_str = ", ".join(top_methods) if top_methods else "diverse computational approaches"

        synthesis_sections = [
            f"# Literature Survey: {topic}\n",
            f"**Survey Overview:** This survey synthesizes findings from {paper_count} research publications "
            f"sourced from {source_label}. The dominant methodologies identified across the corpus include {methods_str}.\n",
            "## Methodological Taxonomy\n",
        ]

        for method, info in list(taxonomy.items())[:6]:
            synthesis_sections.append(
                f"- **{method}** ({info['count']} paper{'s' if info['count'] > 1 else ''}): "
                f"Utilized in studies such as *{info['papers'][0]}*."
            )

        synthesis_sections.append("\n## Critical Gaps & Open Challenges\n")
        all_limitations = []
        for p in analyzed_papers:
            for lim in p.get("limitations", []):
                if not lim.startswith("No explicit limitations"):
                    all_limitations.append(f"- [{p['title'][:40]}...]: {lim}")
        if all_limitations:
            synthesis_sections.extend(all_limitations[:5])
        else:
            synthesis_sections.append(
                "- Limited explicit limitations documented in the retrieved abstracts; full-text review recommended."
            )

        return {
            "topic": topic,
            "status": "success" if papers else "warning",
            "papers_surveyed": paper_count,
            "source": source_label,
            "taxonomy": taxonomy,
            "comparative_matrix": matrix,
            "analysis": analysis,
            "synthesis": "\n".join(synthesis_sections),
            "evidence_backed": paper_count >= 3,
        }
