from __future__ import annotations


class RoadmapGeneratorAgent:
    def __init__(self) -> None:
        self.name = "Roadmap Generator Agent"

    def generate(
        self,
        idea: str,
        analysis: dict | None = None,
        gaps: dict | None = None,
        datasets: dict | None = None,
        experiments: dict | None = None,
    ) -> dict:

        analysis = analysis if isinstance(analysis, dict) else {}
        gaps = gaps if isinstance(gaps, dict) else {}
        datasets = datasets if isinstance(datasets, dict) else {}
        experiments = experiments if isinstance(experiments, dict) else {}

        papers_processed = analysis.get("papers_processed", 0)
        papers = analysis.get("papers", [])
        gap_count = len(gaps.get("gaps", []))
        dataset_count = len(datasets.get("recommendations", []))
        experiment_count = len(experiments.get("experiments", []))
        total_chars = sum(p.get("extracted_characters", 0) for p in papers)

        milestones = []

        # Step 1: Problem definition (always first)
        milestones.append({
            "step": 1,
            "title": "Define research question and objectives",
            "description": (
                f"Based on the analysis of {papers_processed} document(s), "
                "convert the research idea into a precise research question "
                "with measurable objectives and expected outcomes."
            ),
        })

        # Step 2: Literature review (content-aware)
        if papers_processed > 0:
            methods_found = set()
            for p in papers:
                for m in p.get("methods", []):
                    methods_found.add(m)
            method_str = ", ".join(sorted(methods_found)[:3]) if methods_found else "various"
            milestones.append({
                "step": 2,
                "title": "Evidence-backed literature review",
                "description": (
                    f"Review {papers_processed} document(s) ({total_chars:,} characters analyzed). "
                    f"Identified approaches: {method_str}. "
                    "Synthesize findings, compare methods, and document evidence."
                ),
            })
        else:
            milestones.append({
                "step": 2,
                "title": "Conduct comprehensive literature review",
                "description": (
                    "Search and analyze academic papers, conference proceedings, "
                    "and relevant publications using Semantic Scholar and Crossref."
                ),
            })

        # Step 3: Gap analysis
        if gap_count > 0:
            top_gaps = [g.get("title", "") for g in gaps.get("gaps", [])[:3]]
            milestones.append({
                "step": 3,
                "title": f"Identify and prioritize {gap_count} research gaps",
                "description": (
                    f"Analyzed gaps include: {'; '.join(top_gaps)}. "
                    "Prioritize gaps by importance and feasibility."
                ),
            })
        else:
            milestones.append({
                "step": 3,
                "title": "Identify research gaps",
                "description": (
                    "Analyze existing literature for unexplored areas, "
                    "methodological limitations, and open questions."
                ),
            })

        # Step 4: Dataset selection
        if dataset_count > 0:
            ds_names = [d.get("name", "") for d in datasets.get("recommendations", [])[:3]]
            milestones.append({
                "step": 4,
                "title": f"Evaluate {dataset_count} candidate datasets",
                "description": (
                    f"Consider datasets: {', '.join(ds_names)}. "
                    "Assess data quality, size, relevance, licensing, and accessibility."
                ),
            })
        else:
            milestones.append({
                "step": 4,
                "title": "Identify and evaluate datasets",
                "description": (
                    "Find appropriate datasets from Kaggle, UCI, Hugging Face, "
                    "or domain-specific repositories."
                ),
            })

        # Step 5: Methodology design
        all_methods = set()
        for p in papers:
            for m in p.get("methods", []):
                all_methods.add(m)
        if all_methods:
            milestones.append({
                "step": 5,
                "title": "Design methodology informed by existing approaches",
                "description": (
                    f"Incorporate insights from {len(all_methods)} identified method types. "
                    "Define system architecture, models, retrieval strategy, "
                    "evaluation protocol, and experimental design."
                ),
            })
        else:
            milestones.append({
                "step": 5,
                "title": "Design research methodology",
                "description": (
                    "Define system architecture, models, approach, "
                    "evaluation protocol, and experimental design."
                ),
            })

        # Step 6: Experiments
        if experiment_count > 0:
            exp_names = [e.get("name", "") for e in experiments.get("experiments", [])[:3]]
            milestones.append({
                "step": 6,
                "title": f"Execute {experiment_count} planned experiments",
                "description": (
                    f"Planned experiments: {'; '.join(exp_names)}. "
                    "Run experiments systematically and record all results."
                ),
            })
        else:
            milestones.append({
                "step": 6,
                "title": "Design and run experiments",
                "description": (
                    "Implement the proposed approach and run experiments "
                    "with appropriate baselines and evaluation metrics."
                ),
            })

        # Step 7: Evaluation
        milestones.append({
            "step": 7,
            "title": "Evaluate and analyze results",
            "description": (
                "Measure performance against baselines, analyze statistical "
                "significance, evaluate across datasets, and identify strengths/weaknesses."
            ),
        })

        # Step 8: Write-up
        milestones.append({
            "step": 8,
            "title": "Prepare research paper/report",
            "description": (
                f"Document literature ({papers_processed} sources), methodology, "
                f"experiments, results, limitations ({gap_count} gaps identified), "
                "and future work directions."
            ),
        })

        return {
            "idea": idea,
            "milestones": milestones,
            "analysis_summary": analysis.get("summary", ""),
            "papers_referenced": papers_processed,
            "gaps_identified": gap_count,
            "datasets_available": dataset_count,
            "experiments_planned": experiment_count,
            "status": "ready",
        }
