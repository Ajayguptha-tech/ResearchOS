from __future__ import annotations

import re
from typing import Any


# ===========================================================================
# VERIFIED CANONICAL DATASET REGISTRY
# Only legitimate, verified datasets with direct, canonical URLs and exact tasks.
# ===========================================================================

VERIFIED_REGISTRY: list[dict[str, Any]] = [
    # --- Computer Vision / Digit Recognition ---
    {
        "id": "mnist",
        "name": "MNIST Handwritten Digit Database",
        "aliases": ["mnist", "mnist handwritten digits", "mnist database", "handwritten digits"],
        "source": "Yann LeCun, Corinna Cortes, Christopher Burges (Courant Institute / OpenML)",
        "url": "https://yann.lecun.com/exdb/mnist/",
        "purpose": "60,000 training and 10,000 testing 28x28 grayscale images of handwritten digits 0-9.",
        "task": "Handwritten digit recognition / multi-class classification",
        "data_type": "images",
        "target_variable": "Digit class (0-9)",
        "domain": "computer_vision",
        "platform": "independent",
        "exact_keywords": ["mnist", "handwritten digit", "handwritten digits", "digit recognition", "digit classification"],
        "negative_keywords": ["fashion", "usps", "svhn"],
        "why_matched": "Contains benchmark 28x28 grayscale handwritten digits (0-9), directly satisfying the requested handwritten digit recognition task.",
    },
    {
        "id": "usps",
        "name": "USPS Handwritten Digit Dataset",
        "aliases": ["usps", "usps digits", "usps handwritten", "usps dataset"],
        "source": "US Postal Service / J.J. Hull (CEDAR) / Kaggle",
        "url": "https://www.kaggle.com/datasets/bistaumanga/usps-dataset",
        "purpose": "9,298 16x16 grayscale images of handwritten digits scanned from envelopes by the US Postal Service.",
        "task": "Handwritten digit recognition",
        "data_type": "images",
        "target_variable": "Digit class (0-9)",
        "domain": "computer_vision",
        "platform": "kaggle",
        "exact_keywords": ["usps", "usps digits", "usps handwritten", "handwritten digit recognition"],
        "negative_keywords": ["fashion", "mnist"],
        "why_matched": "Contains real-world envelope-scanned handwritten digits (0-9), directly satisfying the requested digit recognition task.",
    },
    {
        "id": "fashion_mnist",
        "name": "Fashion-MNIST",
        "aliases": ["fashion-mnist", "fashion mnist", "zalando fashion"],
        "source": "Zalando Research",
        "url": "https://github.com/zalandoresearch/fashion-mnist",
        "purpose": "70,000 28x28 grayscale images across 10 fashion article categories as a drop-in replacement for MNIST.",
        "task": "Fashion product classification / computer vision benchmarking",
        "data_type": "images",
        "target_variable": "Article category (T-shirt, Trouser, Pullover, Dress, Coat, Sandal, Shirt, Sneaker, Bag, Ankle boot)",
        "domain": "computer_vision",
        "platform": "github",
        "exact_keywords": ["fashion-mnist", "fashion mnist", "zalando", "fashion classification"],
        "negative_keywords": [],
        "why_matched": "Contains 10-class fashion article images specifically designed for fashion product classification benchmarks.",
    },
    {
        "id": "cifar10",
        "name": "CIFAR-10",
        "aliases": ["cifar-10", "cifar10", "cifar 10"],
        "source": "Alex Krizhevsky, Vinod Nair, Geoffrey Hinton (University of Toronto)",
        "url": "https://www.cs.toronto.edu/~kriz/cifar.html",
        "purpose": "60,000 32x32 color images across 10 distinct object classes with 6,000 images per class.",
        "task": "Natural object classification / visual representation learning",
        "data_type": "images",
        "target_variable": "Object class (airplane, automobile, bird, cat, deer, dog, frog, horse, ship, truck)",
        "domain": "computer_vision",
        "platform": "independent",
        "exact_keywords": ["cifar-10", "cifar10", "cifar 10"],
        "negative_keywords": ["cifar-100", "cifar100"],
        "why_matched": "Standard 10-class 32x32 color image benchmark directly matching the requested CIFAR-10 visual classification task.",
    },
    {
        "id": "cifar100",
        "name": "CIFAR-100",
        "aliases": ["cifar-100", "cifar100", "cifar 100"],
        "source": "Alex Krizhevsky, Vinod Nair, Geoffrey Hinton (University of Toronto)",
        "url": "https://www.cs.toronto.edu/~kriz/cifar.html",
        "purpose": "60,000 32x32 color images in 100 fine-grained classes grouped into 20 superclasses.",
        "task": "Fine-grained visual categorization",
        "data_type": "images",
        "target_variable": "Fine class (100 categories) and coarse class (20 superclasses)",
        "domain": "computer_vision",
        "platform": "independent",
        "exact_keywords": ["cifar-100", "cifar100", "cifar 100", "fine-grained object classification"],
        "negative_keywords": [],
        "why_matched": "100-class fine-grained image dataset directly matching the requested CIFAR-100 categorization benchmark.",
    },
    {
        "id": "imagenet",
        "name": "ImageNet (ILSVRC)",
        "aliases": ["imagenet", "ilsvrc"],
        "source": "Stanford University / ImageNet",
        "url": "https://www.image-net.org/",
        "purpose": "Over 14 million annotated images organized according to WordNet hierarchy with 1,000 fine-grained object categories in the standard challenge.",
        "task": "Large-scale visual object recognition and transfer learning",
        "data_type": "images",
        "target_variable": "1,000 synset object categories",
        "domain": "computer_vision",
        "platform": "stanford",
        "exact_keywords": ["imagenet", "ilsvrc", "large-scale image recognition"],
        "negative_keywords": ["mnist", "cifar", "fashion"],
        "why_matched": "Benchmark large-scale 1,000-class dataset directly matching the requested ImageNet computer vision task.",
    },
    {
        "id": "coco",
        "name": "Microsoft COCO (Common Objects in Context)",
        "aliases": ["coco", "ms coco", "microsoft coco", "coco dataset"],
        "source": "Microsoft COCO Consortium",
        "url": "https://cocodataset.org/",
        "purpose": "330,000 images with 1.5 million object instances across 80 object categories labeled with instance segmentations and captions.",
        "task": "Object detection, instance segmentation, and image captioning",
        "data_type": "images",
        "target_variable": "Object bounding boxes, polygon masks, and natural captions",
        "domain": "computer_vision",
        "platform": "microsoft",
        "exact_keywords": ["coco", "ms coco", "microsoft coco", "coco object detection", "instance segmentation"],
        "negative_keywords": [],
        "why_matched": "Directly matches the requested multi-object detection and instance segmentation criteria across 80 common categories.",
    },

    # --- Tabular / Classic Benchmarks (UCI) ---
    {
        "id": "uci_iris",
        "name": "Iris Dataset",
        "aliases": ["iris", "uci iris", "iris flower", "fisher's iris", "iris dataset"],
        "source": "UCI Machine Learning Repository / R.A. Fisher",
        "url": "https://archive.ics.uci.edu/dataset/53/iris",
        "purpose": "150 instances with 4 continuous physiological attributes (sepal length/width, petal length/width) across 3 iris flower species.",
        "task": "Multi-class classification / pattern recognition benchmark",
        "data_type": "tabular",
        "target_variable": "Iris species (Setosa, Versicolour, Virginica)",
        "domain": "botanical / tabular",
        "platform": "uci",
        "exact_keywords": ["iris", "uci iris", "iris flower", "iris dataset"],
        "negative_keywords": ["wine", "cancer", "abalone", "diabetes"],
        "why_matched": "Exact canonical Fisher Iris classification dataset from the UCI Machine Learning Repository.",
    },
    {
        "id": "uci_wine_quality",
        "name": "Wine Quality Dataset",
        "aliases": ["wine quality", "uci wine quality", "wine dataset", "cortez wine"],
        "source": "UCI Machine Learning Repository / P. Cortez",
        "url": "https://archive.ics.uci.edu/dataset/186/wine+quality",
        "purpose": "4,898 white and 1,599 red wine instances evaluated across 11 physicochemical inputs with sensory quality scores.",
        "task": "Classification and regression / physicochemical sensory modeling",
        "data_type": "tabular",
        "target_variable": "Wine sensory quality score (0-10)",
        "domain": "tabular",
        "platform": "uci",
        "exact_keywords": ["wine quality", "uci wine", "wine dataset"],
        "negative_keywords": ["iris", "cancer"],
        "why_matched": "Exact physicochemical wine quality dataset from the UCI Machine Learning Repository.",
    },
    {
        "id": "uci_breast_cancer",
        "name": "Breast Cancer Wisconsin (Diagnostic)",
        "aliases": ["breast cancer wisconsin", "wdbc", "uci breast cancer"],
        "source": "UCI Machine Learning Repository / W.N. Street",
        "url": "https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic",
        "purpose": "569 instances with 30 real-valued features computed from digitized FNA images of breast masses.",
        "task": "Binary classification (malignant vs benign diagnosis)",
        "data_type": "tabular",
        "target_variable": "Diagnosis (M = malignant, B = benign)",
        "domain": "healthcare / tabular",
        "platform": "uci",
        "exact_keywords": ["breast cancer wisconsin", "wdbc", "uci breast cancer", "breast cancer diagnosis"],
        "negative_keywords": ["iris", "wine"],
        "why_matched": "Exact UCI Breast Cancer Wisconsin (Diagnostic) benchmark dataset for malignant vs. benign classification.",
    },

    # --- Finance / Fraud Detection ---
    {
        "id": "kaggle_credit_card_fraud",
        "name": "Credit Card Fraud Detection Dataset",
        "aliases": ["credit card fraud", "credit card fraud detection", "fraud detection dataset", "kaggle credit card fraud", "card fraud"],
        "source": "Kaggle / Machine Learning Group (ULB)",
        "url": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
        "purpose": "284,807 transactions made by European cardholders in September 2013, with 492 frauds (highly unbalanced 0.172% positive class).",
        "task": "Credit card fraud detection / extreme class imbalance classification",
        "data_type": "tabular",
        "target_variable": "Class (1 for fraudulent transaction, 0 for genuine)",
        "domain": "finance / cybersecurity",
        "platform": "kaggle",
        "exact_keywords": ["credit card fraud", "fraud detection", "card fraud", "transaction fraud", "financial fraud"],
        "negative_keywords": ["stock", "market", "yahoo finance", "crypto"],
        "why_matched": "Contains real European cardholder transactions with fraud/non-fraud labels and directly matches the requested fraud-detection task.",
    },

    # --- Medical Imaging / COVID-19 ---
    {
        "id": "covid19_radiography",
        "name": "COVID-19 Radiography Database",
        "aliases": ["covid-19 radiography database", "covid-19 chest x-ray", "covid x-ray", "covid-19 radiography", "covid chest xray", "covid chest x-ray"],
        "source": "Kaggle / Qatar University & University of Dhaka",
        "url": "https://www.kaggle.com/datasets/tawsifurrahman/covid19-radiography-database",
        "purpose": "Winner of the COVID-19 Dataset Award with 3,616 COVID-19 positive cases, 10,192 Normal, 6,012 Lung Opacity, and 1,345 Viral Pneumonia chest X-ray images.",
        "task": "COVID-19 detection and pulmonary disease classification from chest radiographs",
        "data_type": "images",
        "target_variable": "Disease category (COVID-19, Normal, Lung Opacity, Viral Pneumonia)",
        "domain": "medical_imaging / healthcare",
        "platform": "kaggle",
        "exact_keywords": ["covid-19 chest x-ray", "covid-19 radiography", "covid x-ray", "covid chest x-ray", "covid-19 xray", "covid chest xray", "covid-19 dataset", "covid radiography"],
        "negative_keywords": [],
        "why_matched": "Specifically contains labeled COVID-19 positive chest X-rays along with normal and viral pneumonia controls.",
    },
    {
        "id": "covid19_cohen_collection",
        "name": "COVID-19 Image Data Collection",
        "aliases": ["covid-chestxray-dataset", "cohen covid dataset", "ieee8023 covid"],
        "source": "Joseph Paul Cohen / GitHub",
        "url": "https://github.com/ieee8023/covid-chestxray-dataset",
        "purpose": "Open database of COVID-19, MERS, SARS, and ARDS chest X-ray and CT images for clinical AI research.",
        "task": "COVID-19 medical image detection and differential diagnosis",
        "data_type": "images",
        "target_variable": "Pathology diagnosis (COVID-19, SARS, Streptococcus, etc.)",
        "domain": "medical_imaging / healthcare",
        "platform": "github",
        "exact_keywords": ["covid-19 image data collection", "cohen covid", "ieee8023 covid", "covid chest x-ray dataset"],
        "negative_keywords": [],
        "why_matched": "Open research collection of confirmed COVID-19 chest radiographs directly satisfying COVID-19 image analysis.",
    },
    {
        "id": "chexpert",
        "name": "CheXpert Dataset",
        "aliases": ["chexpert", "stanford chexpert"],
        "source": "Stanford ML Group",
        "url": "https://stanfordmlgroup.github.io/competitions/chexpert/",
        "purpose": "224,316 chest radiographs of 65,240 patients with expert radiologist annotations for 14 common chest observations.",
        "task": "Chest pathology classification and radiology interpretation",
        "data_type": "images",
        "target_variable": "14 chest pathologies (Atelectasis, Cardiomegaly, Consolidation, Edema, Pleural Effusion, etc.)",
        "domain": "medical_imaging / healthcare",
        "platform": "stanford",
        "exact_keywords": ["chexpert", "chest pathology", "chest radiographs interpretation"],
        "negative_keywords": ["covid"],
        "why_matched": "Large-scale chest radiograph dataset with 14 pathology labels for general radiology interpretation benchmarking.",
    },
    {
        "id": "mimic_iii",
        "name": "MIMIC-III Clinical Database",
        "aliases": ["mimic-iii", "mimic 3", "mimic clinical", "physionet mimic"],
        "source": "PhysioNet / MIT Lab for Computational Physiology",
        "url": "https://physionet.org/content/mimiciii/",
        "purpose": "De-identified clinical data from 40,000+ ICU patients including vital signs, medications, and laboratory results.",
        "task": "ICU patient outcome prediction, mortality risk modeling, and clinical NLP",
        "data_type": "tabular / EHR / clinical notes",
        "target_variable": "In-hospital mortality, length of stay, and readmission",
        "domain": "healthcare / clinical",
        "platform": "physionet",
        "exact_keywords": ["mimic-iii", "mimic 3", "icu patient", "critical care data", "clinical notes"],
        "negative_keywords": ["x-ray", "radiograph"],
        "why_matched": "Standard critical-care EHR benchmark containing high-resolution physiological records from ICU stays.",
    },

    # --- Agriculture / Plant Pathology ---
    {
        "id": "plantvillage",
        "name": "PlantVillage Dataset",
        "aliases": ["plantvillage", "plant village", "plant disease dataset", "leaf disease dataset"],
        "source": "Penn State University / EPFL / Kaggle",
        "url": "https://www.kaggle.com/datasets/emmarex/plantdisease",
        "purpose": "54,303 healthy and infected plant leaf images categorized across 38 crop-disease pairs for deep learning classification.",
        "task": "Foliar crop disease classification and agricultural diagnostics",
        "data_type": "images",
        "target_variable": "Crop and disease label (38 classes across apple, tomato, grape, potato, corn, etc.)",
        "domain": "agriculture",
        "platform": "kaggle",
        "exact_keywords": ["plantvillage", "plant village", "plant disease", "leaf disease", "foliar disease", "crop disease", "plant pathology"],
        "negative_keywords": [],
        "why_matched": "Contains 54,303 labeled healthy and diseased crop leaves across 38 crop-disease pairs for agricultural diagnostics.",
    },
    {
        "id": "plantdoc",
        "name": "PlantDoc Dataset",
        "aliases": ["plantdoc", "plant doc"],
        "source": "IIT Mandi / GitHub",
        "url": "https://github.com/pratikkayal/PlantDoc-Dataset",
        "purpose": "2,598 real-world field images across 13 plant species and 17 diseases annotated with bounding boxes for object detection.",
        "task": "Field plant disease detection and lesion localization",
        "data_type": "images",
        "target_variable": "Disease bounding box and class",
        "domain": "agriculture",
        "platform": "github",
        "exact_keywords": ["plantdoc", "plant doc", "field plant disease"],
        "negative_keywords": [],
        "why_matched": "Contains real-world in-field leaf images with disease bounding boxes for lesion localization under natural lighting.",
    },

    # --- Graph Neural Networks & Network Science ---
    {
        "id": "cora",
        "name": "Cora Citation Network",
        "aliases": ["cora", "cora dataset", "cora citation", "cora graph"],
        "source": "Automated Learning Group / Papers with Code",
        "url": "https://paperswithcode.com/dataset/cora",
        "purpose": "2,708 machine learning papers categorized into 7 classes with 5,429 citation links.",
        "task": "Graph node classification and link prediction",
        "data_type": "graph",
        "target_variable": "Paper research topic (7 categories: Case_Based, Genetic_Algorithms, Neural_Networks, Probabilistic_Methods, Reinforcement_Learning, Rule_Learning, Theory)",
        "domain": "graph_machine_learning",
        "platform": "papers with code",
        "exact_keywords": [
            "cora", "cora dataset", "cora citation", "cora graph",
            "citation network", "citation networks",
            "graph neural network", "graph neural networks", "gnn", "gnns",
            "graph node classification", "node classification",
        ],
        "negative_keywords": [],
        "why_matched": "Standard citation network benchmark directly satisfying semi-supervised node classification in graph neural networks.",
    },
    {
        "id": "citeseer",
        "name": "CiteSeer Dataset",
        "aliases": ["citeseer", "citeseer dataset", "citeseer graph"],
        "source": "CiteSeerX / Papers with Code",
        "url": "https://paperswithcode.com/dataset/citeseer",
        "purpose": "3,327 scientific papers classified into 6 categories with 4,732 citation edges and a dictionary of 3,703 unique words.",
        "task": "Graph convolutional network benchmarking and community detection",
        "data_type": "graph",
        "target_variable": "Scientific discipline (6 classes: Agents, AI, DB, IR, ML, HCI)",
        "domain": "graph_machine_learning",
        "platform": "papers with code",
        "exact_keywords": [
            "citeseer", "citeseer dataset", "citeseer citation",
            "citation network", "citation networks",
            "graph convolutional network", "graph convolutional networks",
            "graph neural network", "graph neural networks", "gnn", "gnns",
        ],
        "negative_keywords": [],
        "why_matched": "Canonical academic citation graph benchmark matching semi-supervised node classification and community detection.",
    },
    {
        "id": "ogb",
        "name": "Open Graph Benchmark (OGB)",
        "aliases": ["ogb", "open graph benchmark", "ogbn-arxiv", "ogbg-molhiv"],
        "source": "Stanford OGB Team",
        "url": "https://ogb.stanford.edu/",
        "purpose": "Curated collection of realistic, diverse, and challenging benchmark datasets for graph representation learning across node, link, and graph-level tasks.",
        "task": "Graph-level, link-level, and node-level graph neural network evaluation",
        "data_type": "graph",
        "target_variable": "Node properties, edge presence, and molecular graph properties",
        "domain": "graph_machine_learning",
        "platform": "stanford",
        "exact_keywords": [
            "open graph benchmark", "ogb", "ogbn-arxiv",
            "graph representation learning",
            "graph neural network", "graph neural networks", "gnn", "gnns",
        ],
        "negative_keywords": [],
        "why_matched": "Comprehensive large-scale graph benchmark suite developed by Stanford for realistic GNN evaluation.",
    },

    # --- NLP & Reading Comprehension ---
    {
        "id": "glue",
        "name": "GLUE Benchmark",
        "aliases": ["glue", "glue benchmark"],
        "source": "NYU / Hugging Face",
        "url": "https://huggingface.co/datasets/glue",
        "purpose": "General Language Understanding Evaluation benchmark covering 9 English natural language understanding tasks.",
        "task": "NLU evaluation, sentence classification, and natural language inference",
        "data_type": "text",
        "target_variable": "Task-dependent (entailment, sentiment, semantic equivalence, linguistic acceptability)",
        "domain": "nlp",
        "platform": "hugging face",
        "exact_keywords": ["glue", "glue benchmark", "general language understanding"],
        "negative_keywords": [],
        "why_matched": "Multi-task NLU benchmark covering 9 foundational language understanding tasks.",
    },
    {
        "id": "squad",
        "name": "SQuAD (Stanford Question Answering Dataset)",
        "aliases": ["squad", "squad v1.1", "squad 2.0", "squad dataset"],
        "source": "Stanford NLP Group",
        "url": "https://rajpurkar.github.io/SQuAD-explorer/",
        "purpose": "100,000+ reading comprehension question-answer pairs created on 500+ Wikipedia articles.",
        "task": "Extractive question answering and machine reading comprehension",
        "data_type": "text",
        "target_variable": "Answer text span indices within context paragraph",
        "domain": "nlp",
        "platform": "stanford",
        "exact_keywords": ["squad", "reading comprehension", "question answering", "qa dataset", "extractive qa"],
        "negative_keywords": [],
        "why_matched": "Exact reading comprehension benchmark containing Wikipedia articles with validated question-answer spans.",
    },

    # --- Cybersecurity & Network Intrusion ---
    {
        "id": "nsl_kdd",
        "name": "NSL-KDD Dataset",
        "aliases": ["nsl-kdd", "nsl kdd", "nsl kdd dataset"],
        "source": "University of New Brunswick (UNB)",
        "url": "https://www.unb.ca/cic/datasets/nsl.html",
        "purpose": "Network intrusion detection dataset solving inherent statistical flaws of KDD'99 with selective traffic records.",
        "task": "Intrusion detection system evaluation and cyber attack classification",
        "data_type": "network traffic / tabular",
        "target_variable": "Traffic type (Normal or 4 attack categories: DoS, Probe, R2L, U2R)",
        "domain": "cybersecurity",
        "platform": "unb",
        "exact_keywords": ["nsl-kdd", "nsl kdd", "network intrusion", "intrusion detection", "kdd intrusion"],
        "negative_keywords": [],
        "why_matched": "Canonical intrusion detection benchmark with labeled normal and multi-category cyber attack connection records.",
    },
    {
        "id": "cicids_2017",
        "name": "CICIDS 2017 Dataset",
        "aliases": ["cicids 2017", "cicids2017", "cicids"],
        "source": "Canadian Institute for Cybersecurity",
        "url": "https://www.unb.ca/cic/datasets/ids-2017.html",
        "purpose": "Realistic benign background network traffic and modern cyber attack profiles captured over 5 days.",
        "task": "Network security analysis and anomaly detection",
        "data_type": "PCAP / flow tabular",
        "target_variable": "Label (Benign or Attack types like Brute Force, DoS, Botnet, Infiltration)",
        "domain": "cybersecurity",
        "platform": "unb",
        "exact_keywords": ["cicids 2017", "cicids2017", "cicids", "network attack dataset"],
        "negative_keywords": [],
        "why_matched": "Full-packet and bidirectional flow cyber security dataset containing realistic benign traffic and modern attack profiles.",
    },

    # --- Code & Software Engineering ---
    {
        "id": "humaneval",
        "name": "HumanEval Benchmark",
        "aliases": ["humaneval", "human-eval"],
        "source": "OpenAI",
        "url": "https://github.com/openai/human-eval",
        "purpose": "164 hand-crafted Python programming problems with unit tests to evaluate functional correctness of code generation models.",
        "task": "Code generation evaluation and programming reasoning benchmarks",
        "data_type": "code / text",
        "target_variable": "Functional unit test pass rate (pass@k)",
        "domain": "code / software_engineering",
        "platform": "github",
        "exact_keywords": ["humaneval", "human-eval", "code generation", "program synthesis benchmark"],
        "negative_keywords": [],
        "why_matched": "164 hand-crafted programming problems with unit tests specifically evaluating functional correctness of code generation models.",
    },
    {
        "id": "codesearchnet",
        "name": "CodeSearchNet",
        "aliases": ["codesearchnet", "code search net"],
        "source": "GitHub / Microsoft Research",
        "url": "https://github.com/github/CodeSearchNet",
        "purpose": "2 million (comment, code) pairs and semantic code search benchmark across 6 programming languages.",
        "task": "Semantic code retrieval and code documentation generation",
        "data_type": "code / text",
        "target_variable": "Relevance of code snippet to natural language query",
        "domain": "code / software_engineering",
        "platform": "github",
        "exact_keywords": ["codesearchnet", "code search net", "semantic code search", "code retrieval"],
        "negative_keywords": [],
        "why_matched": "2 million code-comment pairs across 6 programming languages directly evaluating semantic code search.",
    },

    # --- Scholarly / Bibliometrics ---
    {
        "id": "s2orc",
        "name": "Semantic Scholar Open Research Corpus (S2ORC)",
        "aliases": ["s2orc", "semantic scholar corpus", "semantic scholar"],
        "source": "Allen Institute for AI (AI2)",
        "url": "https://github.com/allenai/s2orc",
        "purpose": "81.1 million English academic papers with rich citation graph and 8.1 million full text parse trees.",
        "task": "Scholarly document processing, citation graph mining, and academic text retrieval",
        "data_type": "text / graph",
        "target_variable": "Citation link and paper metadata",
        "domain": "scholarly / bibliometrics",
        "platform": "ai2",
        "exact_keywords": ["s2orc", "semantic scholar", "academic paper corpus", "scholarly citation dataset"],
        "negative_keywords": [],
        "why_matched": "Full-text open academic corpus with parsed citation graph for scholarly literature modeling.",
    },
]


class DatasetRecommendationAgent:
    """Agent that recommends ONLY exact-matching verified datasets for a research query.

    Optimization Objective:
        EXACT RELEVANCE
        NOT: semantic similarity alone
        NOT: same general domain or task
        NOT: "related datasets"
        NOT: generic fallback platforms/homepages (UCI/Kaggle/HuggingFace portals)
    """

    def __init__(self) -> None:
        self.name = "Dataset Recommendation Agent"
        self._registry = VERIFIED_REGISTRY

    def _extract_requested_count(self, query: str) -> int | None:
        """Extract explicit requested dataset count if specified by the user."""
        match = re.search(r"\b(?:exactly|top|give me|recommend)?\s*(\d+)\s*datasets?\b", query, re.IGNORECASE)
        if match:
            try:
                count = int(match.group(1))
                if 1 <= count <= 50:
                    return count
            except ValueError:
                pass
        return None

    def _extract_requested_platform(self, query: str) -> str | None:
        """Extract explicit requested repository/platform filter if present."""
        q = query.lower()
        if "uci" in q:
            return "uci"
        if "kaggle" in q:
            return "kaggle"
        if "hugging face" in q or "huggingface" in q:
            return "hugging face"
        if "physionet" in q:
            return "physionet"
        if "stanford" in q:
            return "stanford"
        if "github" in q:
            return "github"
        return None

    def recommend(
        self,
        idea: str,
        papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Recommend exact-matching verified datasets for the given research idea.

        Guarantees:
        1. Exact dataset name matching takes highest precedence.
        2. Related, similarly named, or alternative datasets are NOT returned unless requested.
        3. Never returns generic fallback repository cards (UCI/Kaggle/Hugging Face portals).
        4. If N datasets are requested and only K < N exist, returns only K without substituting unrelated datasets.
        5. If no exact dataset can be verified, returns an empty list and an explicit message.
        """
        idea_clean = idea.strip()
        idea_lower = idea_clean.lower()
        requested_count = self._extract_requested_count(idea_lower)
        requested_platform = self._extract_requested_platform(idea_lower)

        matched_datasets: list[dict[str, Any]] = []
        matched_ids: set[str] = set()

        # -------------------------------------------------------------------
        # TIER 1: EXACT DATASET NAME / ALIAS MATCHING
        # -------------------------------------------------------------------
        for ds in self._registry:
            # Check negative keywords first
            # e.g., if ds is MNIST and negative_keywords has "fashion", skip if "fashion" is in query
            if any(nk in idea_lower for nk in ds["negative_keywords"]):
                continue

            # Platform filter check if requested
            if requested_platform and ds["platform"] != requested_platform and requested_platform not in ds["source"].lower():
                continue

            # Check exact aliases
            name_matched = False
            for alias in ds["aliases"]:
                # Word-boundary matching for aliases to avoid partial token collisions
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, idea_lower):
                    name_matched = True
                    break

            if name_matched and ds["id"] not in matched_ids:
                matched_ids.add(ds["id"])
                matched_datasets.append({
                    "name": ds["name"],
                    "purpose": ds["purpose"],
                    "source": ds["source"],
                    "use": ds["use"] if "use" in ds else ds["task"],
                    "url": ds["url"],
                    "matching_criteria": f"Exact dataset name/alias match for '{idea_clean}'",
                    "why_matched": ds["why_matched"],
                })

        # -------------------------------------------------------------------
        # TIER 2: EXACT TASK / DIRECT SPECIFIC OBJECTIVE MATCHING
        # (Only if Tier 1 did not find explicit dataset names, or to satisfy exact task)
        # -------------------------------------------------------------------
        if not matched_datasets:
            for ds in self._registry:
                if ds["id"] in matched_ids:
                    continue

                if any(nk in idea_lower for nk in ds["negative_keywords"]):
                    continue

                if requested_platform and ds["platform"] != requested_platform and requested_platform not in ds["source"].lower():
                    continue

                # Check exact task keywords
                task_matched = False
                matched_kw = ""
                for kw in ds["exact_keywords"]:
                    pattern = r"\b" + re.escape(kw) + r"(?:s|es)?\b"
                    if re.search(pattern, idea_lower):
                        task_matched = True
                        matched_kw = kw
                        break

                if task_matched:
                    matched_ids.add(ds["id"])
                    matched_datasets.append({
                        "name": ds["name"],
                        "purpose": ds["purpose"],
                        "source": ds["source"],
                        "use": ds["use"] if "use" in ds else ds["task"],
                        "url": ds["url"],
                        "matching_criteria": f"Directly satisfies exact task criteria: '{matched_kw}'",
                        "why_matched": ds["why_matched"],
                    })

        # -------------------------------------------------------------------
        # TIER 3: LITERATURE-REFERENCED EXACT DATASETS
        # If papers were analyzed and explicitly reference a verified benchmark
        # -------------------------------------------------------------------
        if papers and len(matched_datasets) == 0:
            for paper in papers:
                title = str(paper.get("title", "")).lower()
                abstract = str(paper.get("abstract", "") or paper.get("content", "")).lower()
                combined_paper_text = f"{title} {abstract}"

                for ds in self._registry:
                    if ds["id"] in matched_ids:
                        continue

                    # If the paper specifically names this dataset and the paper topic matches
                    for alias in ds["aliases"]:
                        if len(alias) >= 4 and re.search(r"\b" + re.escape(alias) + r"\b", combined_paper_text):
                            # Ensure the paper's dataset actually belongs to the user's idea domain
                            if any(kw in idea_lower for kw in ds["exact_keywords"]):
                                matched_ids.add(ds["id"])
                                matched_datasets.append({
                                    "name": ds["name"],
                                    "purpose": ds["purpose"],
                                    "source": ds["source"],
                                    "use": ds["use"] if "use" in ds else ds["task"],
                                    "url": ds["url"],
                                    "matching_criteria": f"Explicit benchmark identified in analyzed literature paper '{paper.get('title', 'Study')}'",
                                    "why_matched": ds["why_matched"],
                                })

        # -------------------------------------------------------------------
        # DEDUPLICATION & RESULT COUNT ENFORCEMENT
        # -------------------------------------------------------------------
        seen_keys: set[str] = set()
        unique_results: list[dict[str, Any]] = []

        for ds in matched_datasets:
            canonical_key = f"{ds['name'].strip().lower()}|{ds.get('url', '').strip().lower()}"
            if canonical_key not in seen_keys:
                seen_keys.add(canonical_key)
                unique_results.append(ds)

        total_verified = len(unique_results)

        # Truncate strictly to requested count N if user specified one
        message: str
        if total_verified == 0:
            message = "No exact dataset matching the requested criteria could be verified."
            final_recommendations = []
        elif requested_count is not None and requested_count < total_verified:
            final_recommendations = unique_results[:requested_count]
            message = f"Returned top {requested_count} exact-matching verified datasets."
        elif requested_count is not None and requested_count > total_verified:
            final_recommendations = unique_results
            message = f"Only {total_verified} exact match(es) could be verified; no unrelated datasets were substituted."
        else:
            final_recommendations = unique_results
            message = f"Successfully verified {total_verified} exact matching dataset(s)."

        # CRITICAL RULE: general_repositories MUST NOT contain generic fallback portals (UCI, Kaggle, HuggingFace)
        # unless user explicitly asks for repository portals
        general_repositories: list[dict[str, Any]] = []
        if any(w in idea_lower for w in ["repository portal", "data portal", "dataset repositories", "data archives"]):
            general_repositories = [
                {
                    "name": "UCI Machine Learning Repository",
                    "purpose": "Classic machine learning benchmark archive for classification, regression, and clustering datasets.",
                    "source": "UC Irvine",
                    "use": "Tabular model verification",
                    "url": "https://archive.ics.uci.edu/",
                },
                {
                    "name": "Kaggle Datasets",
                    "purpose": "Public data portal with community and competition datasets across diverse domains.",
                    "source": "Kaggle / Google",
                    "use": "Exploratory data analysis",
                    "url": "https://www.kaggle.com/datasets",
                },
            ]

        return {
            "research_idea": idea,
            "recommendations": final_recommendations,
            "general_repositories": general_repositories,
            "message": message,
            "status": "ready",
        }
