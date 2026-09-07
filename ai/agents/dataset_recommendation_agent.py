from __future__ import annotations


class DatasetRecommendationAgent:
    def __init__(self) -> None:
        self.name = "Dataset Recommendation Agent"

    def recommend(
        self,
        idea: str,
        papers: list[dict],
    ) -> dict:

        idea_lower = idea.lower()

        recommendations = []

        # Keyword-based recommendations with real URLs
        keyword_datasets = [
            {
                "keywords": ["research", "literature", "paper", "citation", "academic"],
                "datasets": [
                    {
                        "name": "Semantic Scholar Corpus",
                        "purpose": "Research-paper metadata and abstracts for literature retrieval and recommendation experiments.",
                        "source": "Semantic Scholar",
                        "use": "Literature retrieval and ranking",
                        "url": "https://www.semanticscholar.org/product/datasets",
                    },
                    {
                        "name": "OpenAlex",
                        "purpose": "Open scholarly metadata for papers, authors, concepts, institutions, and citations. Covers 250M+ works.",
                        "source": "OpenAlex",
                        "use": "Research discovery and knowledge graph construction",
                        "url": "https://openalex.org/",
                    },
                    {
                        "name": "arXiv Dataset",
                        "purpose": "Open research-paper metadata and full text for computer science, physics, and mathematics.",
                        "source": "arXiv / Kaggle",
                        "use": "AI and computer science literature retrieval",
                        "url": "https://www.kaggle.com/datasets/Cornell-University/arxiv",
                    },
                ],
            },
            {
                "keywords": ["machine learning", "deep learning", "neural", "classification", "prediction"],
                "datasets": [
                    {
                        "name": "UCI Machine Learning Repository",
                        "purpose": "Classic ML benchmark datasets for classification, regression, and clustering.",
                        "source": "UCI",
                        "use": "Model evaluation and benchmarking",
                        "url": "https://archive.ics.uci.edu/",
                    },
                    {
                        "name": "Kaggle Datasets",
                        "purpose": "Community-contributed datasets across all domains for ML experiments.",
                        "source": "Kaggle",
                        "use": "Experimentation and prototyping",
                        "url": "https://www.kaggle.com/datasets",
                    },
                    {
                        "name": "Hugging Face Datasets",
                        "purpose": "Curated NLP, CV, and multimodal datasets with easy loading APIs.",
                        "source": "Hugging Face",
                        "use": "Training and evaluating ML models",
                        "url": "https://huggingface.co/datasets",
                    },
                ],
            },
            {
                "keywords": ["nlp", "natural language", "text", "sentiment", "language model"],
                "datasets": [
                    {
                        "name": "GLUE Benchmark",
                        "purpose": "Standard NLP benchmark covering 9 tasks for evaluating language understanding.",
                        "source": "NYU / Hugging Face",
                        "use": "NLP model evaluation",
                        "url": "https://huggingface.co/datasets/glue",
                    },
                    {
                        "name": "Common Crawl",
                        "purpose": "Petabytes of web-crawled text data for large-scale language model training.",
                        "source": "Common Crawl Foundation",
                        "use": "Language model pretraining",
                        "url": "https://commoncrawl.org/",
                    },
                    {
                        "name": "SQuAD",
                        "purpose": "Reading comprehension dataset with 100K+ question-answer pairs from Wikipedia.",
                        "source": "Stanford NLP",
                        "use": "Question answering research",
                        "url": "https://rajpurkar.github.io/SQuAD-explorer/",
                    },
                ],
            },
            {
                "keywords": ["computer vision", "image", "object detection", "segmentation"],
                "datasets": [
                    {
                        "name": "ImageNet",
                        "purpose": "14M+ labeled images across 21K categories for visual recognition.",
                        "source": "Stanford / ImageNet",
                        "use": "Image classification and transfer learning",
                        "url": "https://www.image-net.org/",
                    },
                    {
                        "name": "COCO",
                        "purpose": "330K images with 80 object categories for detection, segmentation, and captioning.",
                        "source": "Microsoft COCO",
                        "use": "Object detection and image segmentation",
                        "url": "https://cocodataset.org/",
                    },
                ],
            },
            {
                "keywords": ["cybersecurity", "security", "intrusion", "malware", "network"],
                "datasets": [
                    {
                        "name": "NSL-KDD",
                        "purpose": "Network intrusion detection benchmark dataset with labeled normal and attack traffic.",
                        "source": "UNB",
                        "use": "Intrusion detection system evaluation",
                        "url": "https://www.unb.ca/cic/datasets/nsl.html",
                    },
                    {
                        "name": "CICIDS 2017",
                        "purpose": "Intrusion detection dataset with benign and attack traffic patterns.",
                        "source": "Canadian Institute for Cybersecurity",
                        "use": "Network security research",
                        "url": "https://www.unb.ca/cic/datasets/ids-2017.html",
                    },
                ],
            },
            {
                "keywords": ["health", "medical", "clinical", "disease", "patient"],
                "datasets": [
                    {
                        "name": "MIMIC-III",
                        "purpose": "De-identified clinical data from 40K+ ICU patients including vital signs and lab results.",
                        "source": "MIT Lab for Computational Physiology",
                        "use": "Clinical research and health informatics",
                        "url": "https://physionet.org/content/mimiciii/",
                    },
                ],
            },
            {
                "keywords": ["iot", "internet of things", "sensor", "smart"],
                "datasets": [
                    {
                        "name": "BoT-IoT",
                        "purpose": "Botnet detection dataset for IoT network traffic.",
                        "source": "UNSW Canberra",
                        "use": "IoT security research",
                        "url": "https://research.unsw.edu.au/projects/bot-iot-dataset",
                    },
                ],
            },
        ]

        for entry in keyword_datasets:
            if any(kw in idea_lower for kw in entry["keywords"]):
                recommendations.extend(entry["datasets"])

        # Always add a general-purpose dataset
        if not recommendations:
            recommendations.extend([
                {
                    "name": "Kaggle Datasets",
                    "purpose": "Community-contributed datasets across all domains for ML experiments and research.",
                    "source": "Kaggle",
                    "use": "General research and experimentation",
                    "url": "https://www.kaggle.com/datasets",
                },
                {
                    "name": "Hugging Face Datasets",
                    "purpose": "Curated NLP, CV, and multimodal datasets with easy loading APIs.",
                    "source": "Hugging Face",
                    "use": "Training and evaluating ML models",
                    "url": "https://huggingface.co/datasets",
                },
            ])

        # Deduplicate by name
        seen_names = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec["name"] not in seen_names:
                seen_names.add(rec["name"])
                unique_recommendations.append(rec)

        return {
            "research_idea": idea,
            "recommendations": unique_recommendations,
            "status": "ready",
        }
