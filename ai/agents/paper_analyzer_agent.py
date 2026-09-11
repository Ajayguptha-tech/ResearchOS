class PaperAnalyzerAgent:
    def __init__(self) -> None:
        self.name = "Paper Analyzer Agent"

    def analyze(self, papers: list[dict]) -> dict:
        analyzed_papers = []

        method_keywords = {
            "machine learning": "Machine Learning",
            "deep learning": "Deep Learning",
            "neural network": "Neural Networks",
            "artificial intelligence": "Artificial Intelligence",
            "large language model": "Large Language Models",
            "llm": "Large Language Models",
            "natural language processing": "Natural Language Processing",
            "nlp": "Natural Language Processing",
            "computer vision": "Computer Vision",
            "classification": "Classification",
            "clustering": "Clustering",
            "regression": "Regression",
            "simulation": "Simulation",
            "experiment": "Experimental Evaluation",
            "experimental": "Experimental Evaluation",
            "framework": "Framework-based Approach",
            "architecture": "System Architecture",
            "optimization": "Optimization",
            "algorithm": "Algorithmic Approach",
            "intrusion detection": "Intrusion Detection",
            "routing": "Routing Algorithm",
            "network security": "Network Security",
            "wireless": "Wireless Networking",
            "cloud computing": "Cloud Computing",
            "edge computing": "Edge Computing",
            "internet of things": "Internet of Things",
            "iot": "Internet of Things",
            "transformer": "Transformer Architecture",
            "bert": "BERT-based Model",
            "gpt": "GPT-based Model",
            "reinforcement learning": "Reinforcement Learning",
            "supervised": "Supervised Learning",
            "unsupervised": "Unsupervised Learning",
            "semi-supervised": "Semi-supervised Learning",
            "generative": "Generative Model",
            "benchmark": "Benchmark Evaluation",
            "dataset": "Dataset Analysis",
            "survey": "Survey/Survey Paper",
            "review": "Literature Review",
            "comparison": "Comparative Study",
        }

        limitation_keywords = [
            "limitation", "limitations", "future work", "future research",
            "challenge", "challenges", "lack of", "limited", "however",
            "drawback", "constraint", "shortcoming", "weakness",
        ]

        finding_keywords = [
            "results show", "results demonstrate", "results indicate",
            "we found", "findings show", "demonstrates", "achieves",
            "improves", "outperforms", "significant improvement",
            "evaluation shows", "experiments show", "our approach",
            "the proposed", "we propose", "we introduce",
        ]

        objective_keywords = [
            "objective", "aim", "goal", "purpose", "we aim",
            "this paper", "this study", "this work", "we present",
            "we introduce", "we propose", "our goal",
        ]

        for paper in papers:
            title = paper.get("title", "Untitled paper")
            abstract = paper.get("abstract") or ""
            authors = paper.get("authors", [])
            year = paper.get("year")
            url = paper.get("url", "")
            filename = paper.get("filename", "")
            extracted_chars = paper.get("extracted_characters", 0)

            text = f"{title} {abstract}".lower()

            # Detect methods from content
            methods = []
            for keyword, method in method_keywords.items():
                if keyword in text and method not in methods:
                    methods.append(method)
            if not methods:
                methods.append("Method not explicitly identified from available content")

            # Extract limitations from actual content
            limitations = []
            for keyword in limitation_keywords:
                sentence = self._extract_sentence(text, keyword)
                if sentence:
                    limitations.append(sentence)
            limitations = list(dict.fromkeys(limitations))[:3]

            # Extract findings from actual content
            findings = []
            for keyword in finding_keywords:
                sentence = self._extract_sentence(text, keyword)
                if sentence:
                    findings.append(sentence)
            findings = list(dict.fromkeys(findings))[:3]

            # Extract objectives from actual content
            objectives = []
            for keyword in objective_keywords:
                sentence = self._extract_sentence(text, keyword)
                if sentence:
                    objectives.append(sentence)
            objectives = list(dict.fromkeys(objectives))[:2]

            # Build document summary from actual content
            summary = self._build_document_summary(abstract, text, filename)

            # Research opportunity based on actual content
            if limitations:
                research_opportunity = (
                    f"Based on identified limitations ({limitations[0][:80]}...), "
                    "there is an opportunity to investigate improved approaches."
                )
            else:
                research_opportunity = (
                    "Further evaluation using additional datasets, "
                    "baselines, and experimental settings may reveal "
                    "new research opportunities."
                )

            analyzed_papers.append({
                "id": paper.get("id"),
                "document_id": paper.get("document_id") or paper.get("id"),
                "title": title,
                "authors": authors,
                "year": year,
                "url": url,
                "filename": filename,
                "extracted_characters": extracted_chars,
                "methods": methods,
                "findings": findings if findings else ["No specific findings extracted from available content."],
                "objectives": objectives if objectives else ["Objective not explicitly identified from available content."],
                "abstract_summary": summary,
                "limitations": limitations if limitations else ["No explicit limitations identified from available content."],
                "research_opportunity": research_opportunity,
            })

        # Aggregate statistics
        method_counts = {}
        for paper in analyzed_papers:
            for method in paper["methods"]:
                method_counts[method] = method_counts.get(method, 0) + 1

        key_findings = []

        if papers:
            key_findings.append(
                f"{len(papers)} research document(s) were retrieved and analyzed."
            )
        else:
            key_findings.append("No research documents were available for analysis.")

        if method_counts:
            most_common_method = max(method_counts, key=method_counts.get)
            key_findings.append(
                f"The most frequently identified approach or technology is {most_common_method}."
            )

        papers_with_findings = sum(
            1 for paper in analyzed_papers
            if not paper["findings"][0].startswith("No specific findings")
        )
        if papers_with_findings:
            key_findings.append(
                f"{papers_with_findings} document(s) contain extractable findings."
            )

        papers_with_limitations = sum(
            1 for paper in analyzed_papers
            if not paper["limitations"][0].startswith("No explicit limitations")
        )
        if papers_with_limitations:
            key_findings.append(
                f"{papers_with_limitations} document(s) contain possible limitations or research challenges."
            )

        # Content completeness assessment
        total_chars = sum(p.get("extracted_characters", 0) for p in papers)
        if total_chars > 10000:
            key_findings.append(
                f"Total content analyzed: {total_chars:,} characters across all documents."
            )
        elif total_chars > 0:
            key_findings.append(
                f"Limited content available ({total_chars:,} characters). Uploading full papers may improve analysis quality."
            )

        key_findings.append(
            "Research opportunities should be derived from the methods, "
            "findings, limitations, and evidence available across the documents."
        )

        return {
            "papers_processed": len(papers),
            "papers": analyzed_papers,
            "method_distribution": method_counts,
            "summary": (
                f"The analyzer inspected {len(papers)} document(s) "
                f"containing {total_chars:,} total characters "
                "and extracted methods, findings, objectives, abstract information, "
                "limitations, and possible research opportunities."
            ),
            "key_findings": key_findings,
        }

    def _build_document_summary(self, abstract: str, full_text: str, filename: str) -> str:
        """Build a meaningful summary from the actual document content."""
        if not abstract:
            return "No abstract or extracted content available."

        cleaned = " ".join(abstract.split())

        # Extract key sections if present
        sections = []
        text_lower = full_text.lower()

        # Try to identify document structure
        section_markers = [
            ("abstract", "Abstract"),
            ("introduction", "Introduction"),
            ("methodology", "Methodology"),
            ("method", "Method"),
            ("results", "Results"),
            ("conclusion", "Conclusion"),
            ("conclusions", "Conclusions"),
            ("discussion", "Discussion"),
            ("related work", "Related Work"),
            ("background", "Background"),
        ]

        found_sections = []
        for marker, label in section_markers:
            if f"[page" in text_lower and marker in text_lower:
                found_sections.append(label)

        if found_sections:
            sections.append(f"Document sections detected: {', '.join(found_sections)}")

        # Summarize the content
        if len(cleaned) > 600:
            # Try to find a good breaking point
            sentences = cleaned.replace(".", ".|").split("|")
            summary_parts = []
            char_count = 0
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if char_count + len(sentence) > 600:
                    break
                summary_parts.append(sentence)
                char_count += len(sentence)
            cleaned = " ".join(summary_parts)

        if sections:
            return f"{cleaned}\n\n{'  '.join(sections)}"

        return cleaned

    def _extract_sentence(self, text: str, keyword: str) -> str:
        """Extract a sentence containing the given keyword."""
        sentences = (
            text
            .replace("?", ".")
            .replace("!", ".")
            .split(".")
        )

        for sentence in sentences:
            sentence = sentence.strip()
            if keyword in sentence and len(sentence) > 20:
                sentence = sentence.capitalize()
                if len(sentence) > 300:
                    sentence = sentence[:300] + "..."
                return sentence

        return ""
