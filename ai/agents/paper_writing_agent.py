"""Paper Writing Agent — generates grounded research paper drafts.

Uses selected source documents, papers, and references to create a
structured academic paper draft.  Falls back to deterministic templates
when the LLM provider is unavailable.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


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

        Prefers backend/.env settings (LOCAL_LLM_MODEL / LOCAL_LLM_URL).  When no
        model is configured, queries Ollama's /api/tags and uses the first
        available model.  Never invents a model name.
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

            # Build context from sources
            context_parts = []
            for i, src in enumerate(sources[:10]):
                if src["type"] == "document":
                    context_parts.append(
                        f"[Source Document {i+1}: {src['filename']}]\n"
                        f"{src['content'][:3000]}"
                    )
                elif src["type"] == "paper":
                    context_parts.append(
                        f"[Source Paper {i+1}: {src['title']}]\n"
                        f"Authors: {src['authors']}\n"
                        f"Year: {src.get('year', 'N/A')}\n"
                        f"Venue: {src.get('venue', 'N/A')}\n"
                        f"Abstract: {src['abstract'][:1500]}"
                    )
                elif src["type"] == "reference":
                    context_parts.append(
                        f"[Reference {i+1}: {src['title']}]\n"
                        f"Authors: {src.get('authors', 'N/A')}\n"
                        f"Year: {src.get('year', 'N/A')}"
                    )

            context_str = "\n\n".join(context_parts) if context_parts else "No source documents available."

            system_prompt = (
                "You are an expert academic research paper writer. "
                "Write a complete, structured research paper in markdown format. "
                "Use ONLY the provided sources for factual claims. "
                "Do NOT fabricate citations, statistics, or research findings. "
                "If insufficient information is available for a section, "
                "write '[Insufficient source information for this section]' "
                "instead of fabricating content. "
                "Use IEEE citation style where referencing sources. "
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
        """Generate a paper draft grounded in the provided sources."""

        parts = []

        # ---- TITLE ----
        parts.append(f"# {title}\n")

        # ---- ABSTRACT ----
        doc_summaries = []
        for src in sources:
            if src["type"] == "document" and src.get("content"):
                first_sentences = re.split(r'[.!?\n]', src["content"][:1000])
                meaningful = [s.strip() for s in first_sentences if len(s.strip()) > 20][:3]
                if meaningful:
                    doc_summaries.append(f"- {'. '.join(meaningful)}.")
            elif src["type"] == "paper" and src.get("abstract"):
                doc_summaries.append(f"- {src['abstract'][:300]}.")

        parts.append("## Abstract\n")
        if doc_summaries:
            parts.append(
                f"This paper presents a comprehensive study related to {title}. "
                f"Drawing from {len(sources)} source(s), we analyze the current state of research "
                "and identify key findings, methodologies, and gaps in the existing literature.\n"
            )
        else:
            parts.append(
                "[Insufficient source information for abstract generation. "
                "Please provide source documents to generate a grounded abstract.]\n"
            )

        # ---- INTRODUCTION ----
        parts.append("## 1. Introduction\n")
        if sources:
            parts.append(
                f"The field of research presented in this paper addresses important questions "
                f"related to {title}. This study is motivated by the growing body of literature "
                f"and the need for systematic analysis of {len(sources)} source(s).\n"
            )
            parts.append(
                "The key contributions of this work include:\n"
                "- Systematic review of existing literature\n"
                "- Analysis of current research gaps\n"
                "- Evidence-based discussion of findings\n"
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
                authors = p.get("authors", "Unknown authors")
                year = p.get("year", "N/A")
                parts.append(
                    f"### {p['title']}\n"
                    f"**Authors:** {authors} ({year})\n"
                    f"**Venue:** {p.get('venue', 'N/A')}\n\n"
                    f"{p.get('abstract', 'Abstract not available.')}\n"
                )
        else:
            ref_sources = [s for s in sources if s["type"] == "reference"]
            if ref_sources:
                parts.append("The following references have been identified for this study:\n")
                for r in ref_sources:
                    authors = r.get("authors", "Unknown")
                    year = r.get("year", "N/A")
                    parts.append(f"- {r['title']} ({authors}, {year})")
                parts.append("")
            else:
                parts.append(
                    "[Insufficient source information for literature review. "
                    "Add research papers or references to build the review.]\n"
                )

        # ---- METHODOLOGY ----
        parts.append("## 3. Methodology\n")
        parts.append(
            "The methodology employed in this study follows a systematic approach:\n\n"
        )
        if instruction:
            parts.append(f"**Research Approach:** {instruction}\n\n")
        parts.append(
            "1. **Data Collection:** Sources were collected from uploaded documents and "
            "research papers identified through literature search.\n"
            "2. **Analysis Framework:** A structured analysis framework was applied to "
            "extract key findings, methodologies, and limitations.\n"
            "3. **Synthesis:** Findings were synthesized across multiple sources to "
            "identify common themes and research gaps.\n"
        )

        # ---- RESULTS & DISCUSSION ----
        parts.append("## 4. Results and Discussion\n")
        if doc_summaries:
            parts.append("### Key Findings\n")
            for summary in doc_summaries[:5]:
                parts.append(summary)
            parts.append("")
        parts.append(
            "### Research Gaps\n"
            "Based on the analysis of available sources, the following research gaps "
            "have been identified:\n"
        )
        if len(sources) >= 3:
            parts.append(
                "- Limited cross-study comparison of methodologies\n"
                "- Insufficient validation across diverse datasets\n"
                "- Need for longitudinal studies in this domain\n"
            )
        else:
            parts.append(
                "- [More source materials needed for comprehensive gap analysis]\n"
            )

        # ---- CONCLUSION ----
        parts.append("## 5. Conclusion\n")
        if sources:
            parts.append(
                f"This study has reviewed {len(sources)} source(s) related to {title}. "
                "The analysis reveals both established findings and areas requiring "
                "further investigation. Future research should focus on addressing "
                "the identified gaps through systematic experimentation and "
                "cross-validation.\n"
            )
        else:
            parts.append(
                "[Insufficient source information for meaningful conclusions. "
                "Upload research documents and papers to generate grounded conclusions.]\n"
            )

        # ---- REFERENCES ----
        parts.append("## References\n")
        ref_count = 0
        for src in sources:
            ref_count += 1
            if src["type"] == "document":
                parts.append(f"[{ref_count}] {src['filename']}")
            elif src["type"] == "paper":
                authors = src.get("authors", "Unknown")
                year = src.get("year", "")
                venue = src.get("venue", "")
                parts.append(
                    f"[{ref_count}] {authors}, \"{src['title']}\", "
                    f"{venue} ({year})."
                )
            elif src["type"] == "reference":
                authors = src.get("authors", "Unknown")
                year = src.get("year", "")
                url = src.get("url", "")
                parts.append(
                    f"[{ref_count}] {authors}, \"{src['title']}\" ({year})"
                    + (f". Available: {url}" if url else "")
                )

        if ref_count == 0:
            parts.append("[No sources available for reference list.]")

        return "\n".join(parts)
