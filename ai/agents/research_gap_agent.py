from __future__ import annotations


class ResearchGapAgent:
    def __init__(self) -> None:
        self.name = "Research Gap Analysis Agent"

    def analyze(
        self,
        idea: str,
        papers: list[dict],
        paper_analysis: dict,
    ) -> dict:

        gaps: list[dict] = []
        methods = paper_analysis.get("method_distribution", {})

        if not papers:
            gaps.append({
                "title": "Insufficient literature evidence",
                "description": (
                    "No papers were successfully retrieved, so research gaps "
                    "cannot yet be considered evidence-backed."
                ),
                "importance": "high",
            })
            return {
                "research_idea": idea,
                "gaps": gaps,
                "papers_compared": 0,
                "methods_observed": methods,
                "status": "insufficient_evidence",
            }

        # Analyze actual content for gap identification
        all_methods = set()
        all_findings = []
        all_limitations = []
        all_objectives = []

        for paper in papers:
            for m in paper.get("methods", []):
                all_methods.add(m)
            for f in paper.get("findings", []):
                if not f.startswith("No specific findings"):
                    all_findings.append(f)
            for lim in paper.get("limitations", []):
                if not lim.startswith("No explicit limitations"):
                    all_limitations.append(lim)
            for obj in paper.get("objectives", []):
                if not obj.startswith("Objective not explicitly"):
                    all_objectives.append(obj)

        # Gap 1: Method diversity analysis
        if len(all_methods) > 1:
            method_list = ", ".join(sorted(all_methods)[:5])
            gaps.append({
                "title": "Limited comparative evaluation across methods",
                "description": (
                    f"The documents reference multiple methods ({method_list}), "
                    "but there may be limited direct comparison between them. "
                    "A systematic comparative evaluation could reveal which "
                    "approaches perform best for this research area."
                ),
                "importance": "high",
            })
        elif len(all_methods) == 1:
            method_name = list(all_methods)[0]
            gaps.append({
                "title": "Single-method dependency identified",
                "description": (
                    f"All documents primarily use {method_name}. "
                    "There is an opportunity to explore alternative methodologies "
                    "and compare against this dominant approach."
                ),
                "importance": "high",
            })

        # Gap 2: Analysis of limitations from actual content
        if all_limitations:
            limitation_summary = all_limitations[0][:150]
            gaps.append({
                "title": "Addressing identified limitations",
                "description": (
                    f"The documents acknowledge specific limitations: \"{limitation_summary}...\". "
                    "Addressing these limitations presents a clear research opportunity."
                ),
                "importance": "high",
            })
        else:
            gaps.append({
                "title": "Limited limitation analysis",
                "description": (
                    "The analyzed documents do not explicitly state their limitations. "
                    "A deeper critical analysis could uncover implicit constraints "
                    "and areas for improvement."
                ),
                "importance": "medium",
            })

        # Gap 3: Dataset and evaluation gaps
        paper_count = len(papers)
        has_dataset_mention = any(
            "dataset" in str(p.get("abstract", "")).lower()
            for p in papers
        )
        if not has_dataset_mention:
            gaps.append({
                "title": "Limited dataset and evaluation support",
                "description": (
                    "The analyzed content does not reference specific datasets or "
                    "evaluation benchmarks. Identifying and recommending appropriate "
                    "datasets would strengthen the research methodology."
                ),
                "importance": "medium",
            })

        # Gap 4: Integration gap
        if paper_count >= 2:
            gaps.append({
                "title": "Cross-document integration opportunity",
                "description": (
                    f"With {paper_count} documents analyzed, there is an opportunity to "
                    "synthesize findings across sources, identify consensus points, "
                    "and highlight contradictions that could lead to new insights."
                ),
                "importance": "medium",
            })

        # Gap 5: Research novelty
        if all_objectives:
            objectives_text = " | ".join(all_objectives[:3])
            gaps.append({
                "title": "Novel contribution opportunity",
                "description": (
                    f"The existing objectives ({objectives_text[:200]}) "
                    "define the current scope. There may be opportunities to "
                    "extend this work with novel contributions not yet explored."
                ),
                "importance": "medium",
            })

        # Gap 6: Evaluation completeness
        findings_count = len(all_findings)
        if findings_count < paper_count:
            gaps.append({
                "title": "Incomplete empirical evidence",
                "description": (
                    f"Only {findings_count} of {paper_count} documents contain "
                    "explicit research findings. Additional empirical evidence "
                    "and experimental validation would strengthen conclusions."
                ),
                "importance": "medium",
            })

        return {
            "research_idea": idea,
            "gaps": gaps,
            "papers_compared": len(papers),
            "methods_observed": methods,
            "findings_count": findings_count,
            "limitations_found": len(all_limitations),
            "status": "ready",
        }
