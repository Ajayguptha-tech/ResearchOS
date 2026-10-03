import pytest
from ai.agents.dataset_recommendation_agent import DatasetRecommendationAgent
from ai.agents.experiment_planning_agent import ExperimentPlanningAgent
from ai.agents.literature_search_agent import LiteratureSearchAgent
from ai.agents.paper_analyzer_agent import PaperAnalyzerAgent
from ai.agents.paper_writing_agent import PaperWritingAgent, DRAFT_DISCLAIMER_HEADER
from ai.agents.research_gap_agent import ResearchGapAgent
from ai.agents.research_planner_agent import ResearchPlannerAgent
from ai.agents.roadmap_generator_agent import RoadmapGeneratorAgent
from ai.agents.survey_agent import SurveyAgent


def test_research_planner_agent():
    agent = ResearchPlannerAgent()
    plan = agent.plan("Self-Supervised Learning for Graph Neural Networks")
    assert plan["idea"] == "Self-Supervised Learning for Graph Neural Networks"
    assert len(plan["steps"]) >= 4
    assert plan["status"] == "ready"


def test_paper_analyzer_agent():
    agent = PaperAnalyzerAgent()
    sample_papers = [
        {
            "id": 1,
            "title": "Contrastive Learning on Graphs",
            "abstract": "We propose a novel contrastive loss. Our approach achieves 92% accuracy on benchmarks. However, scalability is a limitation for very large graphs.",
            "authors": ["A. Author", "B. Coauthor"],
            "year": 2024,
            "venue": "NeurIPS",
            "citation_count": 45,
            "doi": "10.1000/graph.1",
            "source": "Semantic Scholar",
        },
        {
            "id": 2,
            "title": "Graph Convolutional Networks for Molecule Generation",
            "abstract": "This study introduces a deep learning framework. Experiments show significant improvement over baselines.",
            "authors": ["C. Chemist"],
            "year": 2023,
            "venue": "ICLR",
            "citation_count": 80,
            "doi": "10.1000/mol.1",
            "source": "Crossref",
        },
    ]
    analysis = agent.analyze(sample_papers)
    assert analysis["papers_processed"] == 2
    assert "method_distribution" in analysis
    assert len(analysis["papers"]) == 2
    assert "Graph" in str(analysis["papers"][0]["methods"]) or "Learning" in str(analysis["papers"][0]["methods"])


def test_research_gap_agent():
    agent = ResearchGapAgent()
    analysis = {
        "papers": [
            {
                "id": 1,
                "title": "Study A",
                "limitations": ["Scalability is limited on large networks."],
                "findings": ["Achieved 90% accuracy."],
            }
        ]
    }
    gaps = agent.analyze("Graph Neural Networks", [{"title": "Study A"}], analysis)
    assert "gaps" in gaps
    assert len(gaps["gaps"]) >= 1


def test_dataset_recommendation_agent():
    agent = DatasetRecommendationAgent()
    recommendations = agent.recommend("Graph Neural Networks", [{"title": "Study A"}])
    assert "recommendations" in recommendations
    assert len(recommendations["recommendations"]) >= 1


def test_experiment_planning_agent():
    agent = ExperimentPlanningAgent()
    gaps = {"gaps": [{"title": "Scalability limitation"}]}
    datasets = {"recommendations": [{"name": "Cora Graph Dataset"}]}
    plan = agent.plan("Graph Neural Networks", gaps, datasets, [{"title": "Study A"}])
    assert "experiments" in plan
    assert len(plan["experiments"]) >= 1


def test_roadmap_generator_agent():
    agent = RoadmapGeneratorAgent()
    # Test safe execution with and without analysis dict
    roadmap_default = agent.generate("Federated Learning on Edge Devices")
    assert roadmap_default["idea"] == "Federated Learning on Edge Devices"
    assert len(roadmap_default["milestones"]) >= 5
    assert roadmap_default["status"] == "ready"

    # Test with analysis dict
    analysis = {
        "papers_processed": 2,
        "papers": [{"title": "Edge FL", "methods": ["Federated Learning"]}],
    }
    roadmap_with_analysis = agent.generate("Federated Learning on Edge Devices", analysis=analysis)
    assert roadmap_with_analysis["papers_referenced"] == 2
    assert len(roadmap_with_analysis["milestones"]) >= 5


def test_paper_writing_agent_disclaimer_and_provenance():
    agent = PaperWritingAgent()
    sources = [
        {
            "type": "paper",
            "title": "Foundations of Graph Transformers",
            "authors": ["E. Expert", "F. Colleague"],
            "year": 2024,
            "venue": "IEEE Transactions on Neural Networks",
            "doi": "10.1109/TNN.2024.01",
            "source": "Semantic Scholar",
            "abstract": "We evaluate graph transformers across 10 benchmarks. Our approach outperforms standard GCNs by 14%. However, quadratic complexity remains an open challenge.",
        },
        {
            "type": "document",
            "filename": "laboratory_notes.txt",
            "id": 42,
            "content": "Empirical testing showed 4.2x speedup with sparse attention on Cora dataset.",
        },
        {
            "type": "reference",
            "title": "Attention Is All You Need",
            "authors": "Vaswani et al.",
            "year": 2017,
            "url": "https://arxiv.org/abs/1706.03762",
        },
    ]

    draft = agent.generate(
        title="Scalable Graph Transformers for Large Heterogeneous Networks",
        instruction="Focus on computational efficiency and benchmarking.",
        sources=sources,
    )

    content = draft["content"]
    # Priority 7: MUST start with clear AI-Generated Research Paper Draft / Reference disclaimer
    assert content.startswith("> **AI-Generated Research Paper Draft / Reference**")
    assert "NOT an already published or peer-reviewed academic paper" in content

    # Priority 3: Citation accuracy and provenance
    assert "## References" in content
    assert "[1]" in content
    assert "[2]" in content
    assert "[3]" in content
    assert "Foundations of Graph Transformers" in content
    assert "laboratory_notes.txt" in content
    assert "Provenance: Semantic Scholar" in content or "Provenance: User Document Upload" in content


def test_survey_agent():
    agent = SurveyAgent()
    sample_papers = [
        {
            "id": 1,
            "title": "A Survey of Graph Representation Learning",
            "authors": ["H. Hamilton", "R. Ying", "J. Leskovec"],
            "year": 2020,
            "venue": "IEEE Data Eng. Bull.",
            "abstract": "This survey provides a taxonomy of graph embedding methods, including shallow encoders, autoencoders, and graph neural networks.",
            "citation_count": 1200,
            "source": "Semantic Scholar",
        },
        {
            "id": 2,
            "title": "Self-Supervised Learning on Graphs: Contrastive and Generative Approaches",
            "authors": ["Y. Liu", "T. Safavi"],
            "year": 2022,
            "venue": "KDD",
            "abstract": "We conduct a comparative study on self-supervised graph methods. Key finding: contrastive methods excel on node classification.",
            "citation_count": 350,
            "source": "Crossref",
        },
    ]

    survey = agent.survey_papers("Graph Representation Learning", sample_papers)
    assert survey["topic"] == "Graph Representation Learning"
    assert survey["papers_surveyed"] == 2
    assert "taxonomy" in survey
    assert "comparative_matrix" in survey
    assert len(survey["comparative_matrix"]) == 2
    assert "synthesis" in survey
    assert "# Literature Survey: Graph Representation Learning" in survey["synthesis"]
    assert survey["evidence_backed"] is False  # Requires >= 3 papers for evidence_backed
