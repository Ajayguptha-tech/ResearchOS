"""Paper Writing Agent — generates grounded research paper drafts.

Uses selected source documents, papers, and references to create a
structured academic paper draft. Falls back to deterministic templates
when the LLM provider is unavailable.

All drafts are clearly labeled as "AI-Generated Research Paper Draft / Reference".
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

DRAFT_DISCLAIMER_HEADER = (
    "> **AI-Generated Research Paper Draft / Reference**\n"
    "> *Notice: This document is an AI-generated draft intended for research scoping, reference, "
    "and literature synthesis. It is NOT an already published or peer-reviewed academic paper.*\n\n"
)


class PaperWritingAgent:
    def __init__(self) -> None:
        self.name = "Paper Writing Agent"

    def generate(
        self,
        title: str,
        instruction: str,
        sources: list[dict],
    ) -> dict:
        """Generate a structured research paper draft.

        Args:
            title: The paper title.
            instruction: User instructions (tone, style, sections, etc.).
            sources: List of source contexts (documents, papers, references).

        Returns:
            dict with ``content`` key containing the generated paper.
        """

        # Try LLM first
        llm_content = self._try_llm(title, instruction, sources)
        if llm_content:
            return {"content": llm_content, "method": "llm"}

        # Fallback: deterministic grounded draft
        content = self._generate_grounded_draft(title, instruction, sources)
        return {"content": content, "method": "grounded_template"}

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model() -> tuple[str, str] | None:
        """Return (model, base_url) for the local LLM, or None.

        Prefers backend/.env settings (LOCAL_LLM_MODEL / LOCAL_LLM_URL). When no
        model is configured, queries Ollama's /api/tags and uses the first
        available model. Never invents a model name.
        """
        import os

        try:
            from app.core.config import settings

            base_url = settings.local_llm_url
            configured = (settings.local_llm_model or "").strip()
        except Exception:
            base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            configured = os.environ.get("OLLAMA_MODEL", "").strip()

        if configured:
            return configured, base_url

        try:
            import httpx

            tags_response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
            if tags_response.status_code == 200:
                models = (tags_response.json() or {}).get("models") or []
                available = [
                    model.get("name")
                    for model in models
                    if isinstance(model, dict) and model.get("name")
                ]
                if available:
                    return available[0], base_url
        except Exception:
            pass
        return None

    def _try_llm(
        self, title: str, instruction: str, sources: list[dict]
    ) -> str | None:
        try:
            import httpx
            import json

            resolved = self._resolve_model()
            if resolved is None:
                logger.warning(
                    "[PaperWritingAgent] No LOCAL_LLM_MODEL configured and Ollama "
                    "reported no models; using the grounded template instead."
                )
                return None
            ollama_url, model = resolved

            # Build context from sources with citation numbers
            context_parts = []
            for i, src in enumerate(sources[:10], start=1):
                if src["type"] == "document":
                    context_parts.append(
                        f"[Source Document [{i}]: {src['filename']}]\n"
                        f"{src['content'][:3000]}"
                    )
                elif src["type"] == "paper":
                    prov = src.get("source", "Academic Literature")
                    context_parts.append(
                        f"[Source Paper [{i}]: {src['title']}]\n"
                        f"Authors: {src['authors']}\n"
                        f"Year: {src.get('year', 'N/A')}\n"
                        f"Venue: {src.get('venue', 'N/A')}\n"
                        f"Provenance: {prov}\n"
                        f"Abstract: {src['abstract'][:1500]}"
                    )
                elif src["type"] == "reference":
                    context_parts.append(
                        f"[Reference [{i}]: {src['title']}]\n"
                        f"Authors: {src.get('authors', 'N/A')}\n"
                        f"Year: {src.get('year', 'N/A')}"
                    )

            context_str = "\n\n".join(context_parts) if context_parts else "No source documents available."

            system_prompt = (
                "You are an expert academic research paper writer. "
                "Write a complete, structured research paper in markdown format. "
                "You MUST begin your response with this EXACT notice:\n"
                "> **AI-Generated Research Paper Draft / Reference**\n"
                "> *Notice: This document is an AI-generated draft intended for research scoping, reference, "
                "and literature synthesis. It is NOT an already published or peer-reviewed academic paper.*\n\n"
                "Use ONLY the provided sources for factual claims. "
                "Do NOT fabricate citations, statistics, or research findings. "
                "If insufficient information is available for a section, "
                "write '[Insufficient source information for this section]' "
                "instead of fabricating content. "
                "Use numbered IEEE citation style (e.g., [1], [2]) corresponding strictly to the provided sources. "
                "Include proper academic structure: abstract, introduction, "
                "literature review, methodology, results/discussion, conclusion, "
                "and references."
            )

            user_msg = (
                f"Title: {title}\n\n"
                f"Instructions: {instruction}\n\n"
                f"Sources:\n{context_str}\n\n"
                "Write the complete research paper now."
            )

            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                        ],
                        "stream": False,
                    },
                )

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if content.strip():
                    if not content.strip().startswith("> **AI-Generated Research Paper Draft / Reference**"):
                        content = DRAFT_DISCLAIMER_HEADER + content
                    return content

        except Exception as exc:
            logger.warning("[PaperWritingAgent] LLM unavailable: %s", exc)

        return None

    # ------------------------------------------------------------------
    # Grounded template fallback
    # ------------------------------------------------------------------

    def _generate_grounded_draft(
        self, title: str, instruction: str, sources: list[dict]
    ) -> str:
        """Generate a paper draft grounded in the provided sources with IEEE citations."""

        parts = []

        # ---- MANDATORY AI-GENERATED DRAFT DISCLAIMER ----
        parts.append(DRAFT_DISCLAIMER_HEADER)

        # ---- TITLE ----
        parts.append(f"# {title}\n")

        # ---- ABSTRACT ----
        doc_summaries = []
        for i, src in enumerate(sources, start=1):
            if src["type"] == "document" and src.get("content"):
                first_sentences = re.split(r'[.!?\n]', src["content"][:1000])
                meaningful = [s.strip() for s in first_sentences if len(s.strip()) > 20][:2]
                if meaningful:
                    doc_summaries.append(f"- [{i}] {'. '.join(meaningful)}.")
            elif src["type"] == "paper" and src.get("abstract"):
                doc_summaries.append(f"- [{i}] {src['abstract'][:250]}...")

        parts.append("## Abstract\n")
        if doc_summaries:
            cite_range = f"[1–{len(sources)}]" if len(sources) > 1 else "[1]"
            parts.append(
                f"This paper presents an evidence-backed study related to {title}. "
                f"Synthesizing {len(sources)} source(s) {cite_range}, we analyze the current state of research "
                "and identify key findings, methodologies, and open challenges in the literature.\n"
            )
        else:
            parts.append(
                "[Insufficient source information for abstract generation. "
                "Please provide source documents to generate a grounded abstract.]\n"
            )

        # ---- INTRODUCTION ----
        parts.append("## 1. Introduction\n")
        if sources:
            cite_range = f"[1–{len(sources)}]" if len(sources) > 1 else "[1]"
            parts.append(
                f"The field of research presented in this paper addresses foundational questions "
                f"related to {title}. This work is grounded in systematic analysis of {len(sources)} "
                f"source(s) {cite_range}.\n"
            )
            parts.append(
                "The key contributions of this work include:\n"
                f"- Evidence-grounded synthesis of existing literature {cite_range}\n"
                "- Comparative analysis of current methodologies and experimental baselines\n"
                "- Identification of critical research gaps and directions for future inquiry\n"
            )
        else:
            parts.append(
                "[Insufficient source information for introduction. "
                "Upload documents or add papers to provide grounding.]\n"
            )

        # ---- LITERATURE REVIEW ----
        parts.append("## 2. Literature Review\n")
        papers_in_sources = [s for s in sources if s["type"] == "paper"]
        if papers_in_sources:
            for p in papers_in_sources:
                idx = sources.index(p) + 1
                authors = p.get("authors", "Unknown authors")
                year = p.get("year", "N/A")
                venue = p.get("venue", "N/A")
                prov = p.get("source", "Academic Literature")
                parts.append(
                    f"### [{idx}] {p['title']}\n"
                    f"**Authors:** {authors} ({year}) [{idx}]\n"
                    f"**Venue:** {venue} | **Provenance:** {prov}\n\n"
                    f"{p.get('abstract', 'Abstract not available.')}\n"
                )
        else:
            ref_sources = [s for s in sources if s["type"] == "reference"]
            if ref_sources:
                parts.append("The following references have been identified for this study:\n")
                for r in ref_sources:
                    idx = sources.index(r) + 1
                    authors = r.get("authors", "Unknown")
                    year = r.get("year", "N/A")
                    parts.append(f"- [{idx}] {r['title']} ({authors}, {year})")
                parts.append("")
            else:
                parts.append(
                    "[Insufficient source information for literature review. "
                    "Add research papers or references to build the review.]\n"
                )

        # ---- METHODOLOGY ----
        parts.append("## 3. Methodology & Architecture\n")
        if sources:
            parts.append(
                f"Our methodology investigates the problem domain through empirical analysis "
                f"informed by the surveyed sources [1–{len(sources)}]. "
                "The system architecture integrates data preprocessing, baseline model comparison, "
                "and ablation testing under standardized evaluation metrics.\n"
            )
        else:
            parts.append("[Insufficient source information for methodology.]\n")

        # ---- RESULTS AND DISCUSSION ----
        parts.append("## 4. Results and Discussion\n")
        if doc_summaries:
            parts.append("### Key Findings from Grounded Sources\n")
            for summary in doc_summaries[:5]:
                parts.append(summary)
            parts.append("")

        parts.append(
            "### Research Gaps & Limitations\n"
            "Based on the grounded analysis of available sources, the following research gaps "
            "have been identified:\n"
        )
        extracted_gaps = []
        for i, src in enumerate(sources, start=1):
            content = src.get("content", "") or src.get("abstract", "")
            for line in content.split("\n"):
                lower = line.lower()
                if any(w in lower for w in ["limitation", "future work", "open challenge", "gap", "lack of", "remains to be"]):
                    cleaned = line.strip()
                    if 20 < len(cleaned) < 250:
                        extracted_gaps.append(f"- [{i}] {cleaned}")
                        if len(extracted_gaps) >= 3:
                            break
            if len(extracted_gaps) >= 3:
                break

        if extracted_gaps:
            for g in extracted_gaps:
                parts.append(f"{g}\n")
        else:
            parts.append(
                "- [No explicit research gaps documented in the provided source texts. Additional domain literature required.]\n"
            )

        # ---- CONCLUSION ----
        parts.append("## 5. Conclusion\n")
        if sources:
            parts.append(
                f"This study has presented an evidence-backed synthesis of {len(sources)} source(s) "
                f"related to {title}. The analysis establishes current benchmarks while highlighting "
                "crucial avenues for future experimental validation.\n"
            )
        else:
            parts.append(
                "[Insufficient source information for meaningful conclusions. "
                "Upload research documents and papers to generate grounded conclusions.]\n"
            )

        # ---- REFERENCES (Full Provenance) ----
        parts.append("## References\n")
        ref_count = 0
        for i, src in enumerate(sources, start=1):
            ref_count += 1
            if src["type"] == "document":
                doc_id = src.get("id") or src.get("document_id") or "doc"
                parts.append(f"[{i}] \"{src['filename']}\", Uploaded Research Document, ID: {doc_id} [Provenance: Local Upload].")
            elif src["type"] == "paper":
                authors = src.get("authors", "Unknown")
                year = src.get("year", "")
                venue = src.get("venue", "")
                doi = src.get("doi", "")
                doi_str = f" DOI: {doi}." if doi else ""
                prov = src.get("source", "Semantic Scholar / Crossref")
                parts.append(
                    f"[{i}] {authors}, \"{src['title']}\", "
                    f"{venue} ({year}).{doi_str} [Provenance: {prov}]."
                )
            elif src["type"] == "reference":
                authors = src.get("authors", "Unknown")
                year = src.get("year", "")
                url = src.get("url", "")
                parts.append(
                    f"[{i}] {authors}, \"{src['title']}\" ({year})"
                    + (f". Available: {url}" if url else "")
                    + " [Provenance: Project Reference]."
                )

        if ref_count == 0:
            parts.append("[No sources available for reference list.]")

        return "\n".join(parts)
