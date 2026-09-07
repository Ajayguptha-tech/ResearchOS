from __future__ import annotations


class ExperimentPlanningAgent:
    def __init__(self) -> None:
        self.name = "Experiment Planning Agent"

    def plan(
        self,
        idea: str,
        gaps: dict,
        datasets: dict,
        papers: list[dict],
    ) -> dict:

        experiments = []

        # Analyze the actual content to generate relevant experiments
        all_methods = set()
        all_findings = []
        for paper in papers:
            for m in paper.get("methods", []):
                all_methods.add(m)
            for f in paper.get("findings", []):
                if not f.startswith("No specific findings"):
                    all_findings.append(f)

        # Experiment 1: Baseline comparison (always relevant)
        experiments.append({
            "name": "Baseline literature comparison",
            "objective": (
                "Compare the proposed approach against existing methods "
                f"identified in the {len(papers)} analyzed document(s)."
            ),
            "metrics": [
                "Precision",
                "Recall",
                "F1-Score",
                "Top-k relevance",
            ],
        })

        # Experiment 2: Method-specific experiments based on actual methods found
        if all_methods:
            method_list = ", ".join(sorted(all_methods)[:3])
            experiments.append({
                "name": f"Evaluation of {method_list} approaches",
                "objective": (
                    f"Systematically evaluate {len(all_methods)} identified methodology/type "
                    f"({method_list}) using standardized benchmarks."
                ),
                "metrics": [
                    "Accuracy",
                    "Computational efficiency",
                    "Scalability",
                    "Reproducibility score",
                ],
            })

        # Experiment 3: Research gap evaluation
        gap_count = len(gaps.get("gaps", []))
        if gap_count > 0:
            top_gap = gaps["gaps"][0].get("title", "identified research gap")
            experiments.append({
                "name": "Gap-addressing prototype evaluation",
                "objective": (
                    f"Develop and evaluate a prototype addressing: \"{top_gap}\". "
                    "Measure improvement over existing approaches."
                ),
                "metrics": [
                    "Gap coverage score",
                    "Improvement over baseline",
                    "Expert relevance rating",
                    "Novel contribution assessment",
                ],
            })

        # Experiment 4: Dataset adequacy experiment
        dataset_count = len(datasets.get("recommendations", []))
        if dataset_count > 0:
            datasets_list = [d.get("name", "") for d in datasets.get("recommendations", [])[:3]]
            experiments.append({
                "name": "Dataset cross-validation",
                "objective": (
                    f"Evaluate the approach across {dataset_count} candidate dataset(s) "
                    f"({', '.join(datasets_list)}) to ensure generalizability."
                ),
                "metrics": [
                    "Cross-dataset consistency",
                    "Domain transferability",
                    "Data quality assessment",
                    "Performance variance",
                ],
            })

        # Experiment 5: Scalability and robustness
        experiments.append({
            "name": "Scalability and robustness testing",
            "objective": (
                "Evaluate how the approach performs with increasing data sizes, "
                "noisy inputs, and edge cases."
            ),
            "metrics": [
                "Response time vs data size",
                "Error rate under noise",
                "Memory consumption",
                "Graceful degradation",
            ],
        })

        # Experiment 6: User study / expert evaluation (if applicable)
        if len(papers) >= 3:
            experiments.append({
                "name": "Expert evaluation study",
                "objective": (
                    "Conduct expert evaluation of the research outputs "
                    "(gaps, recommendations, roadmap) against manual analysis."
                ),
                "metrics": [
                    "Expert agreement score",
                    "Time savings",
                    "Usefulness rating",
                    "Coverage completeness",
                ],
            })

        return {
            "research_idea": idea,
            "baseline": (
                "Manual literature review and keyword-based "
                "research planning without AI assistance."
            ),
            "proposed_system": (
                f"AI-assisted research workflow using {len(all_methods)} "
                f"identified methodology types across {len(papers)} documents."
            ),
            "experiments": experiments,
            "datasets_available": dataset_count,
            "papers_available": len(papers),
            "gaps_identified": gap_count,
            "methods_identified": sorted(all_methods),
            "status": "ready",
        }
