class ResearchPlannerAgent:
    def __init__(self) -> None:
        self.name = "Research Planner Agent"

    def plan(self, idea: str) -> dict:
        idea_clean = idea.strip()
        lower = idea_clean.lower()

        # Domain-aware intelligence generation
        if any(kw in lower for kw in ["plant", "leaf", "crop", "agriculture", "botanical", "farming", "foliar"]):
            problem_understanding = (
                f"Automated visual diagnosis of foliar pathologies from leaf imagery addresses critical crop yield risks. "
                f"By substituting traditional, error-prone manual crop scouting with deep learning computer vision pipelines, "
                f"this research targets rapid, automated pathogen identification under diverse real-world agricultural conditions."
            )
            objectives = [
                "Develop and benchmark deep convolutional neural networks and vision transformer architectures for multi-class foliar disease classification.",
                "Mitigate visual noise, complex outdoor background clutter, and variable lighting through robust data augmentation and leaf segmentation.",
                "Optimize model parameter complexity and inference latency for deployment on edge-constrained agricultural mobile devices."
            ]
            research_questions = [
                "How do modern convolutional backbones (e.g., EfficientNet, ResNet) compare with Vision Transformers (ViT, Swin) in capturing fine-grained lesion textures versus global leaf context?",
                "To what degree can transfer learning and self-supervised pre-training bridge the domain gap between controlled laboratory benchmarks and uncontrolled field images?",
                "What attention-guided or feature-fusion mechanisms best isolate early-stage subtle disease spots without false positives from natural leaf variegation or dirt?",
                "Can quantization and model distillation reduce compute requirements for offline edge inference without significant classification degradation?"
            ]
            model_recommendations = [
                {"name": "Convolutional Neural Networks (ResNet-50 / EfficientNet-B4)", "rationale": "High-inductive bias for localized texture extraction, fine-grained lesion identification, and transfer learning from pre-trained ImageNet weights."},
                {"name": "Vision Transformers (ViT-Base / Swin Transformer)", "rationale": "Captures long-range spatial dependencies and subtle foliar color transitions across entire leaf surfaces with self-attention."},
                {"name": "Lightweight Edge Architectures (MobileNetV3 / YOLOv8-Nano)", "rationale": "Enables sub-50ms inference on resource-constrained mobile hardware for offline in-field diagnosis by agricultural workers."}
            ]
            methodology_recommendations = [
                {"stage": "Data Preprocessing & Augmentation", "details": "Color jitter, random rotation, affine transformations, and background illumination normalization to simulate real-world farm conditions."},
                {"stage": "Transfer Learning & Class Balancing", "details": "Progressive unfreezing of backbone layers combined with class-balanced focal loss to address rare pathogen classes."},
                {"stage": "Interpretability & Field Validation", "details": "Grad-CAM/saliency map generation to verify predictions ground on actual foliar lesions, followed by cross-species field validation."}
            ]
            expected_challenges = [
                "Severe class imbalance between widespread pathologies and rare, localized crop diseases.",
                "Domain shift between clean laboratory training datasets (uniform background) and uncontrolled field conditions (complex soil, weeds, direct sunlight).",
                "Visual symptom ambiguity where multiple diseases or nutrient deficiencies produce overlapping chlorosis and necrosis."
            ]
            potential_novelty = (
                "A lightweight, attention-augmented deep learning framework combining fine-grained lesion feature extraction with mobile edge deployability, "
                "validated across field-captured imagery with explainable visual attention heatmaps."
            )
            future_work = [
                "Integration of multi-spectral imagery and ambient sensor telemetry (humidity, temperature) for predictive disease progression forecasting.",
                "Few-shot and zero-shot learning frameworks to detect novel and mutating plant pathogen variants with minimal labeled reference samples."
            ]

        elif any(kw in lower for kw in ["vision", "image", "detection", "segmentation", "video", "cnn"]):
            problem_understanding = (
                f"The investigation of '{idea_clean}' focuses on developing robust visual representation and classification models. "
                f"Key priorities include feature discriminability, spatial localization accuracy, and resilience against visual noise and occlusions."
            )
            objectives = [
                f"Design an effective visual feature extraction pipeline tailored to '{idea_clean}'.",
                "Evaluate comparative performance across convolutional and transformer-based visual architectures.",
                "Quantify generalization performance across varying illumination, scale, and background conditions."
            ]
            research_questions = [
                "What architectural inductive biases yield the optimal tradeoff between spatial fidelity and feature abstraction for this domain?",
                "How can data scarcity or labeling noise be mitigated using self-supervised pre-training or synthetic augmentation?",
                "What are the latency-accuracy tradeoffs across deployment platforms?"
            ]
            model_recommendations = [
                {"name": "Deep CNN Backbones (ResNet, EfficientNet)", "rationale": "Robust spatial hierarchy and well-established transfer learning benchmarks."},
                {"name": "Vision Transformers (ViT, Swin)", "rationale": "Global receptive field and attention-driven feature prioritization."},
                {"name": "Lightweight Mobile Networks (MobileNet, ShuffleNet)", "rationale": "Optimized FLOPs for real-time edge or client-side execution."}
            ]
            methodology_recommendations = [
                {"stage": "Image Preprocessing & Augmentation", "details": "Geometric normalization, photometric augmentations, and cutmix/mixup regularizations."},
                {"stage": "Supervised & Semi-supervised Training", "details": "Multi-stage transfer learning with cosine annealing learning rate schedules."},
                {"stage": "Benchmark Evaluation & Saliency Analysis", "details": "Precision-recall curves, mAP evaluation, and feature attribution inspection."}
            ]
            expected_challenges = [
                "High computational cost during high-resolution feature extraction.",
                "Susceptibility to domain shifts between training and production environments."
            ]
            potential_novelty = f"An optimized architectural framework for {idea_clean} demonstrating superior accuracy-to-compute ratio."
            future_work = [
                "Extending the model to multi-modal visual-textual understanding.",
                "Implementing active learning for efficient continuous human-in-the-loop annotation."
            ]

        elif any(kw in lower for kw in ["nlp", "language", "text", "speech", "llm", "transformer", "dialogue"]):
            problem_understanding = (
                f"The research problem '{idea_clean}' addresses computational linguistic modeling and semantic representation. "
                f"Core challenges involve context retention, factual consistency, domain adaptation, and computational efficiency."
            )
            objectives = [
                f"Formulate a structured natural language processing methodology for '{idea_clean}'.",
                "Benchmark pre-trained language model representations against specialized domain-adapted baselines.",
                "Evaluate model interpretability, factual grounding, and robustness against out-of-distribution inputs."
            ]
            research_questions = [
                "How does fine-tuning compare with retrieval-augmented generation for domain fidelity?",
                "What attention heads or representations carry the highest predictive utility for this task?",
                "How can hallucinations and catastrophic forgetting be prevented during continuous domain adaptation?"
            ]
            model_recommendations = [
                {"name": "Pre-trained Transformer Encoders (RoBERTa / DeBERTa)", "rationale": "State-of-the-art bidirectional context modeling for classification and extraction."},
                {"name": "Autoregressive LLMs with LoRA / PEFT", "rationale": "Parameter-efficient adaptation of generative capabilities with minimal parameter drift."},
                {"name": "Retrieval-Augmented Ensembles", "rationale": "Grounding model outputs directly against external verified knowledge corpora."}
            ]
            methodology_recommendations = [
                {"stage": "Text Preprocessing & Tokenization", "details": "Subword tokenization, sequence truncation, and domain vocabulary alignment."},
                {"stage": "Parameter-Efficient Fine-Tuning", "details": "Low-Rank Adaptation (LoRA) and prompt tuning on curated domain datasets."},
                {"stage": "Evaluation & Grounding Audit", "details": "BLEU/ROUGE/F1 metrics paired with automated factual consistency verification."}
            ]
            expected_challenges = [
                "Context length constraints and memory quadratic scaling with sequence length.",
                "Handling domain-specific jargon and ambiguous linguistic constructions."
            ]
            potential_novelty = f"A parameter-efficient adaptation strategy tailored to {idea_clean} with verifiable factual grounding."
            future_work = [
                "Cross-lingual generalization across resource-scarce languages.",
                "Investigation of self-correction mechanisms during generation."
            ]

        else:
            problem_understanding = (
                f"The investigation into '{idea_clean}' addresses critical theoretical and practical objectives in modern computing. "
                f"This research analyzes current paradigms, identifies empirical bottlenecks, and designs an evidence-backed solution."
            )
            objectives = [
                f"Establish an analytical problem formulation and formal baseline for '{idea_clean}'.",
                "Identify and resolve core methodological bottlenecks through empirical evaluation and systematic comparative studies.",
                "Synthesize experimental findings into a validated architectural framework and deployment roadmap."
            ]
            research_questions = [
                f"What are the primary performance and scaling constraints inherent in current approaches to '{idea_clean}'?",
                "How can the proposed methodology improve efficiency, accuracy, or robustness over state-of-the-art baselines?",
                "What empirical metrics best capture real-world operational viability for this solution?"
            ]
            model_recommendations = [
                {"name": "Domain-Specific Deep Learning / Algorithmic Models", "rationale": "High expressive capacity tuned to the operational characteristics of the target domain."},
                {"name": "Ensemble & Hybrid Architectures", "rationale": "Combines inductive strengths of multiple model families to maximize variance reduction and predictive stability."},
                {"name": "Optimized Baseline Implementations", "rationale": "Standardized canonical benchmarks for statistically rigorous performance comparison."}
            ]
            methodology_recommendations = [
                {"stage": "Problem Scoping & Data Synthesis", "details": "Formal specification of operational constraints, target metrics, and data curation."},
                {"stage": "Iterative Modeling & Optimization", "details": "Systematic hyperparameter tuning, cross-validation, and ablation studies."},
                {"stage": "Statistical Verification & Stress Testing", "details": "Significance testing, edge-case failure mode analysis, and reproducibility validation."}
            ]
            expected_challenges = [
                "Balancing computational complexity with model expressiveness.",
                "Data distribution shift between evaluation benchmarks and production deployment."
            ]
            potential_novelty = f"A novel methodological framework addressing fundamental limitations in current approaches to '{idea_clean}'."
            future_work = [
                "Expanding scalability testing to enterprise-scale distributed environments.",
                "Exploring semi-autonomous adaptive parameter tuning."
            ]

        return {
            "idea": idea_clean,
            "objectives": objectives,
            "status": "ready",
            "problem_understanding": problem_understanding,
            "research_questions": research_questions,
            "model_recommendations": model_recommendations,
            "methodology_recommendations": methodology_recommendations,
            "expected_challenges": expected_challenges,
            "potential_novelty": potential_novelty,
            "future_work": future_work,
        }

