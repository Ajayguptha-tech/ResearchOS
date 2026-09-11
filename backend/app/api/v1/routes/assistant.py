"""Research Assistant — Main Workspace Answering Agent.

Provides a context-aware research assistant that can answer questions about
the user's workspace, projects, documents, references, analyses, and general
research methodology.

When an LLM (Ollama) is available, sends the full workspace context to it for
grounded answers.  When no LLM is available, uses a deterministic fallback
that extracts relevant information from the workspace context.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.security import get_current_user as _get_user
from app.db.models import (
    AnalysisResult,
    EvidenceSession,
    EvidenceSessionItem,
    Project,
    Reference,
    ResearchDocument,
    ResearchPaper,
)
from app.schemas.assistant import AssistantMessageRequest, AssistantMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Workspace context builder
# ---------------------------------------------------------------------------


def _build_workspace_context(
    db: Session,
    user_id: int,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Gather all relevant workspace data for the authenticated user.

    Returns a structured dict that can be serialized into a context string
    for the LLM or used directly for fallback answering.
    """
    # --- Projects ---
    projects = db.query(Project).filter(Project.owner_id == user_id).all()
    project_list = []
    current_project = None

    for p in projects:
        doc_count = (
            db.query(ResearchDocument)
            .filter(ResearchDocument.project_id == p.id, ResearchDocument.owner_id == user_id)
            .count()
        )
        ref_count = (
            db.query(Reference)
            .filter(Reference.project_id == p.id, Reference.owner_id == user_id)
            .count()
        )
        analysis_count = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.project_id == p.id, AnalysisResult.owner_id == user_id)
            .count()
        )
        entry = {
            "id": p.id,
            "title": p.title,
            "domain": p.domain,
            "description": p.description or "",
            "status": p.status,
            "document_count": doc_count,
            "reference_count": ref_count,
            "analysis_count": analysis_count,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }
        project_list.append(entry)
        if project_id and p.id == project_id:
            current_project = entry

    # If project_id specified but not found, try to find it anyway
    if project_id and not current_project:
        p = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
        if p:
            current_project = {
                "id": p.id,
                "title": p.title,
                "domain": p.domain,
                "description": p.description or "",
                "status": p.status,
            }

    # --- Workspace-level documents (no project) ---
    workspace_docs = (
        db.query(ResearchDocument)
        .filter(
            ResearchDocument.owner_id == user_id,
            ResearchDocument.project_id.is_(None),
        )
        .all()
    )

    # --- Project-scoped documents ---
    project_docs = []
    if project_id:
        project_docs = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.project_id == project_id,
                ResearchDocument.owner_id == user_id,
            )
            .all()
        )

    # Build document summaries (with extracted content snippets)
    def _doc_summary(doc: ResearchDocument, include_text: bool = True) -> dict:
        summary: dict[str, Any] = {
            "id": doc.id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "project_id": doc.project_id,
            "created_at": doc.created_at.isoformat() if doc.created_at else "",
        }
        if include_text and doc.extracted_text:
            text = doc.extracted_text
            summary["text_preview"] = text[:500]
            summary["text_length"] = len(text)
        else:
            summary["text_preview"] = ""
            summary["text_length"] = len(doc.extracted_text) if doc.extracted_text else 0
        return summary

    workspace_doc_summaries = [_doc_summary(d) for d in workspace_docs[:20]]
    project_doc_summaries = [_doc_summary(d) for d in project_docs[:20]]

    # --- Full extracted text for documents (for answering) ---
    # Always include workspace-level documents AND project documents
    # so the assistant can answer questions about any uploaded document
    document_contents = []
    seen_filenames: set[str] = set()
    for doc in project_docs[:10]:
        if doc.extracted_text:
            text = doc.extracted_text[:8000]
            document_contents.append({
                "filename": doc.filename,
                "content_type": doc.content_type,
                "text": text,
            })
            seen_filenames.add(doc.filename)
    for doc in workspace_docs[:10]:
        if doc.extracted_text and doc.filename not in seen_filenames:
            text = doc.extracted_text[:8000]
            document_contents.append({
                "filename": doc.filename,
                "content_type": doc.content_type,
                "text": text,
            })

    # --- References ---
    references = []
    ref_query = db.query(Reference).filter(Reference.owner_id == user_id)
    if project_id:
        ref_query = ref_query.filter(Reference.project_id == project_id)
    for r in ref_query.order_by(Reference.created_at.desc()).limit(30).all():
        references.append({
            "id": r.id,
            "title": r.title,
            "url": r.url or "",
            "authors": r.authors or "",
            "year": r.year,
            "notes": r.notes or "",
            "type": r.reference_type,
            "project_id": r.project_id,
        })

    # --- Research Papers (user-written) ---
    papers = []
    paper_query = db.query(ResearchPaper).filter(ResearchPaper.owner_id == user_id)
    if project_id:
        paper_query = paper_query.filter(ResearchPaper.project_id == project_id)
    for rp in paper_query.order_by(ResearchPaper.updated_at.desc()).limit(10).all():
        papers.append({
            "id": rp.id,
            "title": rp.title,
            "word_count": rp.word_count,
            "status": rp.status,
            "project_id": rp.project_id,
        })

    # --- Saved Analyses ---
    analyses = []
    analysis_query = db.query(AnalysisResult).filter(AnalysisResult.owner_id == user_id)
    if project_id:
        analysis_query = analysis_query.filter(AnalysisResult.project_id == project_id)
    for ar in analysis_query.order_by(AnalysisResult.created_at.desc()).limit(10).all():
        # Parse the result JSON for key info
        result_data = {}
        try:
            result_data = json.loads(ar.result_json) if ar.result_json else {}
        except (json.JSONDecodeError, TypeError):
            pass
        analyses.append({
            "id": ar.id,
            "project_id": ar.project_id,
            "analysis_type": ar.analysis_type,
            "research_idea": ar.research_idea,
            "created_at": ar.created_at.isoformat() if ar.created_at else "",
            "has_gaps": bool(result_data.get("research_gaps", {}).get("gaps")),
            "gap_count": len(result_data.get("research_gaps", {}).get("gaps", [])),
            "dataset_count": len(result_data.get("datasets", {}).get("recommendations", [])),
        })

    # --- Evidence Sessions ---
    evidence_sessions: list[dict[str, Any]] = []
    es_query = db.query(EvidenceSession).filter(EvidenceSession.owner_id == user_id)
    if project_id:
        es_query = es_query.filter(EvidenceSession.project_id == project_id)
    for es in es_query.order_by(EvidenceSession.created_at.desc()).limit(20).all():
        items = []
        for item in db.query(EvidenceSessionItem).filter(
            EvidenceSessionItem.session_id == es.id
        ).all():
            items.append({
                "type": item.item_type,
                "id": item.item_id,
                "note": item.note or "",
            })
        evidence_sessions.append({
            "id": es.id,
            "title": es.title,
            "description": es.description or "",
            "notes": es.notes or "",
            "status": es.status,
            "item_count": len(items),
            "items": items,
            "created_at": es.created_at.isoformat() if es.created_at else "",
        })

    return {
        "user_id": user_id,
        "current_project_id": project_id,
        "current_project": current_project,
        "projects": project_list,
        "workspace_documents": workspace_doc_summaries,
        "project_documents": project_doc_summaries,
        "document_contents": document_contents,
        "references": references,
        "papers": papers,
        "analyses": analyses,
        "evidence_sessions": evidence_sessions,
    }


def _context_to_string(ctx: dict[str, Any]) -> str:
    """Serialize workspace context into a text block for the LLM prompt."""
    lines: list[str] = []

    lines.append("=== RESEARCHOS WORKSPACE CONTEXT ===")
    lines.append("")

    # Projects overview
    lines.append(f"TOTAL PROJECTS: {len(ctx['projects'])}")
    for p in ctx["projects"]:
        pid = p["id"]
        marker = " [CURRENT]" if ctx.get("current_project_id") == pid else ""
        lines.append(f"  - Project #{pid}: {p['title']} ({p['domain']}){marker}")
        lines.append(f"    Status: {p['status']} | Docs: {p['document_count']} | Refs: {p['reference_count']} | Analyses: {p['analysis_count']}")
        if p.get("description"):
            lines.append(f"    Description: {p['description']}")
    lines.append("")

    # Current project detail
    if ctx.get("current_project"):
        cp = ctx["current_project"]
        lines.append(f"=== CURRENT PROJECT: {cp['title']} ===")
        lines.append(f"Domain: {cp['domain']}")
        if cp.get("description"):
            lines.append(f"Description: {cp['description']}")
        lines.append("")

    # Project documents
    if ctx["project_documents"]:
        lines.append(f"PROJECT DOCUMENTS ({len(ctx['project_documents'])}):")
        for d in ctx["project_documents"]:
            lines.append(f"  - {d['filename']} ({d['content_type']}, {d['text_length']} chars)")
        lines.append("")

    # Document content
    if ctx["document_contents"]:
        lines.append("=== UPLOADED DOCUMENT CONTENT ===")
        for dc in ctx["document_contents"]:
            lines.append(f"\n--- Document: {dc['filename']} ({dc['content_type']}) ---")
            lines.append(dc["text"])
            lines.append(f"--- End of {dc['filename']} ---")
        lines.append("")

    # References
    if ctx["references"]:
        lines.append(f"REFERENCES ({len(ctx['references'])}):")
        for r in ctx["references"]:
            ref_str = f"  - \"{r['title']}\""
            if r["authors"]:
                ref_str += f" by {r['authors']}"
            if r["year"]:
                ref_str += f" ({r['year']})"
            if r["url"]:
                ref_str += f" [{r['url']}]"
            lines.append(ref_str)
            if r["notes"]:
                lines.append(f"    Notes: {r['notes']}")
        lines.append("")

    # Papers
    if ctx["papers"]:
        lines.append(f"RESEARCH PAPERS ({len(ctx['papers'])}):")
        for rp in ctx["papers"]:
            lines.append(f"  - \"{rp['title']}\" ({rp['word_count']} words, {rp['status']})")
        lines.append("")

    # Analyses
    if ctx["analyses"]:
        lines.append(f"SAVED ANALYSES ({len(ctx['analyses'])}):")
        for a in ctx["analyses"]:
            lines.append(f"  - Project #{a['project_id']}: \"{a['research_idea']}\" ({a['analysis_type']})")
            lines.append(f"    Gaps: {a['gap_count']} | Datasets: {a['dataset_count']} | Date: {a['created_at']}")
        lines.append("")

    # Workspace-level documents
    if ctx["workspace_documents"]:
        lines.append(f"WORKSPACE-LEVEL DOCUMENTS ({len(ctx['workspace_documents'])}):")
        for d in ctx["workspace_documents"]:
            lines.append(f"  - {d['filename']} ({d['content_type']}, {d['text_length']} chars)")
        lines.append("")

    # Evidence Sessions
    if ctx.get("evidence_sessions"):
        lines.append(f"EVIDENCE SESSIONS ({len(ctx['evidence_sessions'])}):")
        for es in ctx["evidence_sessions"]:
            lines.append(f"  - \"{es['title']}\" [{es['status']}]")
            if es.get("description"):
                lines.append(f"    Description: {es['description']}")
            if es.get("notes"):
                lines.append(f"    Notes: {es['notes']}")
            if es["items"]:
                lines.append(f"    Attached items: {es['item_count']}")
                for it in es["items"]:
                    lines.append(f"      - {it['type']} #{it['id']}{': ' + it['note'] if it['note'] else ''}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM integration
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are ResearchOS Assistant — a knowledgeable, helpful AI assistant with research intelligence.

You have access to the user's complete ResearchOS workspace including their projects,
uploaded documents (with extracted text), references, research papers, evidence sessions,
and past analyses.

CAPABILITIES — answer ALL safe questions:
- Research questions, literature review, methodology, citations
- Academic questions across all disciplines
- Technical/programming questions (code, debugging, architecture)
- General knowledge (science, math, engineering, CS, history, etc.)
- Writing, summarization, explanation, rewriting
- Project-specific questions using workspace data
- Document-specific questions using extracted content
- Questions about the user's ResearchOS workspace
- General-purpose helpful assistant responses

RULES:
1. Answer the user's actual question directly and helpfully.
2. When the user asks about their workspace/projects/documents, use the provided context.
3. When the user asks a general question unrelated to their workspace, answer it with your general knowledge.
4. When document content is available and relevant, ground your answer in it and cite the document.
5. Never fabricate information about the user's workspace, documents, or projects.
6. Never refuse to answer a safe, reasonable question.
7. Keep answers clear, well-structured, and appropriately detailed.
8. Use markdown formatting for readability.
9. For dataset questions, recommend real, well-known datasets and platforms.
10. Distinguish between document-derived information and general knowledge when both are used.
11. If information cannot be found in project sources, say so and provide general knowledge if possible.
12. Support follow-up questions by maintaining conversation context.
13. For code questions, provide working code examples when appropriate.
14. For math/science questions, show your reasoning clearly."""


_last_ollama_check_time: float = 0.0
_cached_ollama_model: str | None = None
_OLLAMA_CHECK_COOLDOWN: float = 10.0


def _resolve_ollama_model() -> str | None:
    """Return the local LLM model to use, or None when it cannot be determined.

    Uses LOCAL_LLM_MODEL when configured.  Otherwise asks Ollama for its
    available models (GET /api/tags) and uses the first one.  Returns None
    (never a made-up name) when Ollama is unreachable or has no models, so
    callers fall back to the deterministic answer path.
    """
    global _last_ollama_check_time, _cached_ollama_model
    if settings.local_llm_model and settings.local_llm_model.strip():
        return settings.local_llm_model.strip()
    import time
    now = time.time()
    if now - _last_ollama_check_time < _OLLAMA_CHECK_COOLDOWN:
        return _cached_ollama_model
    _last_ollama_check_time = now
    try:
        tags_response = httpx.get(
            f"{settings.local_llm_url}/api/tags",
            timeout=1.0,
        )
        if tags_response.status_code == 200:
            models = (tags_response.json() or {}).get("models") or []
            available = [
                model.get("name")
                for model in models
                if isinstance(model, dict) and model.get("name")
            ]
            if available:
                logger.info(
                    "[Assistant] No LOCAL_LLM_MODEL configured; using first available Ollama model: %s",
                    available[0],
                )
                _cached_ollama_model = available[0]
                return _cached_ollama_model
        logger.info(
            "[Assistant] Ollama reachable but reported no models. "
            "Set LOCAL_LLM_MODEL in backend/.env to pick an installed model."
        )
    except Exception as exc:
        logger.debug("[Assistant] Could not list Ollama models: %s", exc)
    _cached_ollama_model = None
    return None


def _call_llm(system_prompt: str, user_prompt: str) -> str | None:
    """Send a single-turn chat completion request to the local LLM provider.

    Returns the response text, or None if the LLM is unavailable.
    """
    if settings.ai_provider != "local":
        return None

    url = f"{settings.local_llm_url}/api/chat"
    model = _resolve_ollama_model()
    if model is None:
        return None

    try:
        response = httpx.post(
            url,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
            timeout=120.0,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("message", {}).get("content", "")
        else:
            logger.warning("[Assistant] LLM returned status %d: %s", response.status_code, response.text[:200])
            return None
    except httpx.ConnectError:
        logger.info("[Assistant] LLM not reachable at %s", settings.local_llm_url)
        return None
    except Exception as exc:
        logger.warning("[Assistant] LLM call failed: %s", exc)
        return None


def _call_llm_with_messages(messages: list[dict[str, str]]) -> str | None:
    """Send a multi-turn chat completion request to the local LLM provider.

    Supports conversation history for follow-up question context.
    Returns the response text, or None if the LLM is unavailable.
    """
    if settings.ai_provider != "local":
        return None

    url = f"{settings.local_llm_url}/api/chat"
    model = _resolve_ollama_model()
    if model is None:
        return None

    try:
        response = httpx.post(
            url,
            json={
                "model": model,
                "messages": messages,
                "stream": False,
            },
            timeout=120.0,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("message", {}).get("content", "")
        else:
            logger.warning("[Assistant] LLM returned status %d: %s", response.status_code, response.text[:200])
            return None
    except httpx.ConnectError:
        logger.info("[Assistant] LLM not reachable at %s", settings.local_llm_url)
        return None
    except Exception as exc:
        logger.warning("[Assistant] LLM call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Fallback answering (no LLM)
# ---------------------------------------------------------------------------

def _keyword_match(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in text (case-insensitive)."""
    lower = text.lower()
    return sum(1 for kw in keywords if kw in lower)


def _fallback_answer(message: str, ctx: dict[str, Any]) -> str:
    """Generate a grounded answer without an LLM.

    Uses keyword matching on the user question and the workspace context
    to extract relevant information and compose a structured answer.
    """
    lower_msg = message.lower().strip()
    parts: list[str] = []

    # --- Workspace overview questions ---
    overview_keywords = ["what do i have", "what projects", "my projects",
                         "overview", "what's in my workspace",
                         "workspace summary", "what have i done"]
    if _keyword_match(lower_msg, overview_keywords) > 0:
        if not ctx["projects"]:
            return (
                "**Your workspace is empty.**\n\n"
                "Here's how to get started with ResearchOS:\n"
                "1. **Create a project** — Click 'Create project' in the Projects section\n"
                "2. **Upload documents** — Add research papers, datasets, or notes to your project\n"
                "3. **Run AI Analysis** — Analyze your documents for gaps, datasets, and experiments\n"
                "4. **Add references** — Track papers and sources you've found\n\n"
                "I can help you with any of these steps!"
            )
        parts.append(f"## Your Workspace\n\nYou have **{len(ctx['projects'])} project(s)**:")
        for p in ctx["projects"]:
            marker = " *(current)*" if ctx.get("current_project_id") == p["id"] else ""
            parts.append(f"- **{p['title']}** ({p['domain']}){marker}")
            parts.append(f"  - {p['document_count']} document(s), {p['reference_count']} reference(s), {p['analysis_count']} analysis(es)")
        if ctx["workspace_documents"]:
            parts.append(f"\nYou also have **{len(ctx['workspace_documents'])} workspace-level document(s)** in your evidence library.")
        return "\n".join(parts)

    # --- Document questions ---
    doc_keywords = ["paper", "document", "uploaded", "file", "pdf", "docx",
                    "text", "extract", "content", "read"]
    doc_question_keywords = ["summarize", "about", "methodology", "findings",
                             "limitations", "conclusion", "result", "objective",
                             "problem", "approach", "dataset", "abstract",
                             "compare", "explain", "what does", "what is in"]
    is_doc_question = (
        _keyword_match(lower_msg, doc_keywords) > 0
        and _keyword_match(lower_msg, doc_question_keywords) > 0
    )

    all_docs = ctx["document_contents"]
    if is_doc_question and all_docs:
        # Try to find the most relevant document
        best_doc = None
        best_score = 0
        for doc in all_docs:
            score = _keyword_match(lower_msg, [doc["filename"].lower().replace(".", " ")])
            if score > best_score:
                best_score = score
                best_doc = doc
        # If no filename match, use the first document
        if not best_doc:
            best_doc = all_docs[0]

        doc_text = best_doc["text"]
        doc_name = best_doc["filename"]

        # --- Summarize ---
        if any(kw in lower_msg for kw in ["summarize", "summary", "overview of"]):
            # Extract first ~2000 chars as summary
            preview = doc_text[:2000]
            parts.append(f"## Summary of {doc_name}\n")
            parts.append(f"Based on the uploaded document **{doc_name}** ({best_doc['content_type']}):\n")
            parts.append(preview)
            if len(doc_text) > 2000:
                parts.append(f"\n\n*Showing first 2,000 of {len(doc_text):,} characters. The full document contains {len(doc_text):,} characters.*")
            return "\n".join(parts)

        # --- Methodology ---
        if any(kw in lower_msg for kw in ["methodology", "method", "approach", "technique", "algorithm"]):
            # Search for methodology-related sections
            method_text = _extract_section(doc_text, ["method", "approach", "technique", "algorithm", "procedure", "experiment design"])
            if method_text:
                parts.append(f"## Methodology — {doc_name}\n")
                parts.append(f"Based on **{doc_name}**:\n")
                parts.append(method_text)
            else:
                parts.append(f"## Methodology — {doc_name}\n")
                parts.append("I couldn't find a clear methodology section in the document. Here's what the document discusses:")
                parts.append(doc_text[:1500])
            return "\n".join(parts)

        # --- Limitations ---
        if any(kw in lower_msg for kw in ["limitation", "weakness", "shortcoming", "constraint"]):
            lim_text = _extract_section(doc_text, ["limitation", "weakness", "shortcoming", "constraint", "future work"])
            if lim_text:
                parts.append(f"## Limitations — {doc_name}\n")
                parts.append(f"Based on **{doc_name}**:\n")
                parts.append(lim_text)
            else:
                parts.append(f"## Limitations — {doc_name}\n")
                parts.append("I couldn't find an explicit limitations section. The document discusses:")
                parts.append(doc_text[:1500])
            return "\n".join(parts)

        # --- Research gaps ---
        if any(kw in lower_msg for kw in ["gap", "research gap", "missing", "open problem"]):
            gap_text = _extract_section(doc_text, ["gap", "open problem", "future work", "future direction", "research question"])
            if gap_text:
                parts.append(f"## Research Gaps — {doc_name}\n")
                parts.append(f"Based on **{doc_name}**:\n")
                parts.append(gap_text)
            else:
                parts.append(f"## Research Gaps — {doc_name}\n")
                parts.append("I couldn't find an explicit research gaps section. Here's what the document covers:")
                parts.append(doc_text[:1500])
            return "\n".join(parts)

        # --- Dataset ---
        if any(kw in lower_msg for kw in ["dataset", "data set", "data used", "corpus"]):
            data_text = _extract_section(doc_text, ["dataset", "data set", "data collection", "data source", "corpus", "evaluation data"])
            if data_text:
                parts.append(f"## Dataset Information — {doc_name}\n")
                parts.append(f"Based on **{doc_name}**:\n")
                parts.append(data_text)
            else:
                parts.append(f"## Dataset — {doc_name}\n")
                parts.append("I couldn't find explicit dataset information. The document mentions:")
                parts.append(doc_text[:1500])
            return "\n".join(parts)

        # --- Problem / objective ---
        if any(kw in lower_msg for kw in ["problem", "objective", "aim", "goal", "what is this about", "what does it"]):
            intro_text = _extract_section(doc_text, ["introduction", "abstract", "background", "problem", "objective", "aim"])
            if intro_text:
                parts.append(f"## Problem & Objectives — {doc_name}\n")
                parts.append(f"Based on **{doc_name}**:\n")
                parts.append(intro_text)
            else:
                parts.append(f"## About {doc_name}\n")
                parts.append(doc_text[:1500])
            return "\n".join(parts)

        # --- Generic document question ---
        parts.append(f"## Document: {doc_name}\n")
        parts.append(f"The document **{doc_name}** contains {len(doc_text):,} characters of extracted text.\n")
        parts.append("**First 2,000 characters:**\n")
        parts.append(doc_text[:2000])
        if len(doc_text) > 2000:
            parts.append(f"\n*Full document: {len(doc_text):,} characters available.*")
        parts.append(f"\n\n*Ask me specific questions like 'What methodology is used?' or 'What are the limitations?'*")
        return "\n".join(parts)

    # --- Evidence session questions ---
    evidence_keywords = ["evidence", "evidence session", "session", "gathering session"]
    if _keyword_match(lower_msg, evidence_keywords) > 0:
        evidence_sessions = ctx.get("evidence_sessions", [])
        if not evidence_sessions:
            parts.append("## Evidence Sessions\n")
            parts.append("You don't have any evidence sessions yet. Create one in your project workspace under the **Evidence Sessions** tab to start gathering and organizing evidence for your research.")
            return "\n".join(parts)
        parts.append(f"## Your Evidence Sessions ({len(evidence_sessions)})\n")
        for es in evidence_sessions:
            parts.append(f"- **{es['title']}** [{es['status']}]")
            if es["description"]:
                parts.append(f"  Description: {es['description']}")
            if es["notes"]:
                parts.append(f"  Notes: {es['notes']}")
            if es["items"]:
                parts.append(f"  Attached items: {es['item_count']}")
        return "\n".join(parts)

    # --- Reference questions ---
    ref_keywords = ["reference", "citation", "paper i added", "source", "bibliography"]
    if _keyword_match(lower_msg, ref_keywords) > 0:
        if not ctx["references"]:
            parts.append("## References\n")
            parts.append("You haven't added any references yet. You can add them from your project workspace under the **References** section.")
            return "\n".join(parts)
        parts.append(f"## Your References ({len(ctx['references'])})\n")
        for r in ctx["references"]:
            ref_line = f"- **{r['title']}**"
            if r["authors"]:
                ref_line += f" — {r['authors']}"
            if r["year"]:
                ref_line += f" ({r['year']})"
            if r["url"]:
                ref_line += f"\n  Link: {r['url']}"
            if r["notes"]:
                ref_line += f"\n  Notes: {r['notes']}"
            parts.append(ref_line)
        return "\n".join(parts)

    # --- Analysis questions ---
    analysis_keywords = ["analysis", "research gap", "gap analysis", "roadmap",
                         "dataset recommendation", "what did my analysis", "saved analysis",
                         "my analyses", "my analysis"]
    if _keyword_match(lower_msg, analysis_keywords) > 0:
        if not ctx["analyses"]:
            parts.append("## Saved Analyses\n")
            parts.append("You haven't run any analyses yet. To analyze your research:")
            parts.append("1. Open a project workspace")
            parts.append("2. Upload research documents")
            parts.append("3. Go to **AI Analysis** and enter a research idea")
            parts.append("4. The analysis will be saved automatically")
            return "\n".join(parts)
        parts.append(f"## Your Analyses ({len(ctx['analyses'])})\n")
        for a in ctx["analyses"]:
            parts.append(f"- **{a['research_idea']}** (Project #{a['project_id']})")
            parts.append(f"  - {a['gap_count']} research gap(s), {a['dataset_count']} dataset recommendation(s)")
            parts.append(f"  - Created: {a['created_at']}")
        return "\n".join(parts)

    # --- Project-specific questions ---
    project_keywords = ["project", "what is my project", "my research", "current project"]
    if _keyword_match(lower_msg, project_keywords) > 0 and ctx.get("current_project"):
        cp = ctx["current_project"]
        parts.append(f"## Current Project: {cp['title']}\n")
        parts.append(f"**Domain:** {cp['domain']}")
        if cp.get("description"):
            parts.append(f"**Description:** {cp['description']}")
        parts.append(f"**Status:** {cp['status']}")
        if ctx["project_documents"]:
            parts.append(f"\n**Documents ({len(ctx['project_documents'])}):**")
            for d in ctx["project_documents"]:
                parts.append(f"- {d['filename']} ({d['text_length']:,} chars)")
        if ctx["references"]:
            parts.append(f"\n**References ({len(ctx['references'])}):**")
            for r in ctx["references"][:5]:
                parts.append(f"- {r['title']}")
        if ctx["analyses"]:
            parts.append(f"\n**Analyses ({len(ctx['analyses'])}):**")
            for a in ctx["analyses"][:3]:
                parts.append(f"- {a['research_idea']}")
        return "\n".join(parts)

    # --- Research methodology / general questions ---
    methodology_keywords = ["how do i", "how to", "what is", "explain", "methodology",
                            "literature review", "research question", "hypothesis",
                            "experiment design", "data collection", "sampling",
                            "write a paper", "structure of", "citation", "plagiarism",
                            "peer review", "publication", "journal", "conference",
                            "qualitative", "quantitative", "mixed method",
                            "survey", "case study", "meta-analysis", "systematic review"]
    if _keyword_match(lower_msg, methodology_keywords) > 0:
        # General research methodology guidance
        guidance = _get_research_guidance(lower_msg)
        if guidance:
            return guidance

    # --- Dataset recommendation questions ---
    dataset_keywords = ["recommend dataset", "what dataset", "suggest dataset",
                        "where can i find data", "good dataset for"]
    if _keyword_match(lower_msg, dataset_keywords) > 0:
        return _get_dataset_guidance(lower_msg, ctx)

    # --- General knowledge / programming / technical questions ---
    # These keywords indicate the user wants a general answer, not workspace data
    general_keywords = [
        "python", "javascript", "java ", "code", "programming",
        "function", "class", "algorithm", "data structure",
        "html", "css", "react", "sql", "database",
        "machine learning", "neural network", "deep learning",
        "physics", "chemistry", "biology", "math",
        "equation", "formula", "theorem", "proof",
        "history", "geography", "economics", "philosophy",
        "write me", "help me write", "create a", "generate a",
        "define", "difference between", "compare", "pros and cons",
        "why does", "how does", "what causes", "what happens when",
        "explain simply", "in simple terms", "eli5",
        "translate", "summarize this", "rewrite",
    ]
    if _keyword_match(lower_msg, general_keywords) > 0:
        # Check if this is actually about project documents first
        is_about_docs = _keyword_match(lower_msg, ["my document", "uploaded", "my paper", "my project"])
        if not is_about_docs:
            return _get_general_guidance(lower_msg)

    # --- "What is ResearchOS" ---
    if any(kw in lower_msg for kw in ["what is researchos", "about researchos", "what does researchos do"]):
        return (
            "## About ResearchOS\n\n"
            "ResearchOS is an **AI-powered research intelligence platform** designed to "
            "help researchers, students, and academics streamline their research workflow.\n\n"
            "**Core features:**\n"
            "- **Project Management** — Create and manage multiple research projects\n"
            "- **Document Upload & Analysis** — Upload PDFs, DOCX, CSV, and more for AI-powered analysis\n"
            "- **Literature Search** — Find and analyze relevant research papers\n"
            "- **Research Gap Analysis** — Identify gaps in existing literature\n"
            "- **Dataset Recommendations** — Get suggestions for relevant datasets\n"
            "- **Experiment Planning** — Design experiments with proper methodology\n"
            "- **Research Roadmap** — Generate a step-by-step research plan\n"
            "- **Research Assistant** — Ask questions about your workspace and research\n"
            "- **References Management** — Track papers, sources, and citations\n"
            "- **Paper Editor** — Write and manage your research paper drafts\n\n"
            f"You currently have **{len(ctx['projects'])} project(s)** and "
            f"**{len(ctx['workspace_documents'])} document(s)** in your workspace."
        )

    # --- Fallback: try to match project names in the question ---
    for p in ctx["projects"]:
        if p["title"].lower() in lower_msg:
            parts.append(f"## Project: {p['title']}\n")
            parts.append(f"**Domain:** {p['domain']}")
            if p.get("description"):
                parts.append(f"**Description:** {p['description']}")
            parts.append(f"**Status:** {p['status']}")
            parts.append(f"**Documents:** {p['document_count']} | **References:** {p['reference_count']} | **Analyses:** {p['analysis_count']}")
            return "\n".join(parts)

    # --- Generic fallback ---
    # When the LLM is unavailable and no specific topic matched,
    # provide a helpful overview of capabilities.
    parts.append("## ResearchOS Assistant\n")
    parts.append("I can help you with a wide range of topics. Here are some examples:\n")
    parts.append("**About your workspace:**")
    parts.append("- \"What projects do I have?\"")
    parts.append("- \"What documents have I uploaded?\"")
    parts.append("- \"Show me my references\"")
    parts.append("- \"What analyses have I run?\"")
    parts.append("- \"What evidence sessions do I have?\"\n")
    parts.append("**About your documents:**")
    parts.append("- \"Summarize my uploaded paper\"")
    parts.append("- \"What methodology does my document use?\"")
    parts.append("- \"What are the limitations?\"")
    parts.append("- \"What datasets are mentioned?\"\n")
    parts.append("**Research guidance:**")
    parts.append("- \"How do I write a literature review?\"")
    parts.append("- \"How do I formulate a research question?\"")
    parts.append("- \"What is a systematic review?\"\n")
    parts.append("**General questions:**")
    parts.append("- \"Explain quantum computing\"")
    parts.append("- \"How does a neural network work?\"")
    parts.append("- \"Help me debug this Python code\"")
    parts.append("- \"What is the difference between TCP and UDP?\"\n")

    if ctx["projects"]:
        parts.append(f"*Tip: You have {len(ctx['projects'])} project(s). Open a project to work with its documents.*")
    else:
        parts.append("*Tip: Create a project first, then upload documents for me to analyze.*")

    return "\n".join(parts)


def _extract_section(text: str, section_keywords: list[str]) -> str:
    """Try to extract a relevant section from document text based on keywords.

    Looks for paragraph/section matches and returns surrounding context.
    """
    lower_text = text.lower()
    best_pos = -1
    best_kw = ""

    for kw in section_keywords:
        pos = lower_text.find(kw)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
            best_kw = kw

    if best_pos == -1:
        return ""

    # Extract a window around the keyword
    start = max(0, best_pos - 200)
    end = min(len(text), best_pos + 2000)
    excerpt = text[start:end].strip()

    # Try to find paragraph boundaries
    # Find the start of the paragraph containing the keyword
    para_start = excerpt.rfind("\n\n", 0, best_pos - start + 200)
    if para_start != -1:
        excerpt = excerpt[para_start:].strip()

    return excerpt


# --- Research methodology guidance ---

_RESEARCH_GUIDANCE: dict[tuple[str, ...], str] = {
    ("literature review",): (
        "## How to Write a Literature Review\n\n"
        "A literature review surveys existing research on your topic:\n\n"
        "1. **Define your scope** — What question are you answering?\n"
        "2. **Search systematically** — Use academic databases (Google Scholar, IEEE Xplore, ACM DL, PubMed)\n"
        "3. **Organize by theme** — Group papers by methodology, findings, or topic\n"
        "4. **Synthesize** — Don't just summarize; compare and contrast findings\n"
        "5. **Identify gaps** — What hasn't been studied?\n"
        "6. **Write it up** — Introduction → Thematic sections → Conclusion/Gaps\n\n"
        "**Tip:** Use ResearchOS to upload papers, run AI Analysis, and identify research gaps automatically."
    ),
    ("research question", "formulate", "define"): (
        "## Formulating a Research Question\n\n"
        "A good research question should be:\n"
        "- **Specific** — Narrow enough to be answerable\n"
        "- **Measurable** — Can be investigated with data\n"
        "- **Relevant** — Addresses a real gap or need\n"
        "- **Feasible** — Achievable with your resources\n\n"
        "**Frameworks:**\n"
        "- **PICO** (Population, Intervention, Comparison, Outcome) — for clinical research\n"
        "- **FINER** (Feasible, Interesting, Novel, Ethical, Relevant) — general criteria\n\n"
        "**Example:**\n"
        "- Too broad: \"How does AI help in education?\"\n"
        "- Better: \"How does AI-powered tutoring affect learning outcomes in undergraduate STEM courses?\""
    ),
    ("hypothesis",): (
        "## What is a Hypothesis?\n\n"
        "A hypothesis is a **testable prediction** about the relationship between variables.\n\n"
        "**Characteristics of a good hypothesis:**\n"
        "- Clear and specific\n"
        "- Testable through experiments or observation\n"
        "- Based on existing literature or theory\n"
        "- Includes independent and dependent variables\n\n"
        "**Example:**\n"
        "\"Students who use AI-assisted tutoring will score 15% higher on standardized tests than those using traditional methods.\""
    ),
    ("experiment", "design", "experimental design"): (
        "## Experiment Design\n\n"
        "A well-designed experiment includes:\n\n"
        "1. **Research Question** — What are you testing?\n"
        "2. **Hypothesis** — What do you expect?\n"
        "3. **Variables** — Independent, dependent, and controlled\n"
        "4. **Methodology** — How will you conduct the experiment?\n"
        "5. **Sample Size** — How many participants/samples?\n"
        "6. **Control Group** — Baseline for comparison\n"
        "7. **Metrics** — How will you measure results?\n"
        "8. **Analysis Plan** — Statistical tests you'll use\n\n"
        "**Common designs:** Randomized Controlled Trial, A/B Testing, Factorial Design, Pre-post Test"
    ),
    ("qualitative",): (
        "## Qualitative Research Methods\n\n"
        "Qualitative research explores **meanings, experiences, and phenomena**:\n\n"
        "- **Interviews** — One-on-one or group conversations\n"
        "- **Focus Groups** — Group discussions on a topic\n"
        "- **Observations** — Watching behavior in natural settings\n"
        "- **Case Studies** — In-depth study of a specific case\n"
        "- **Ethnography** — Immersive cultural study\n"
        "- **Grounded Theory** — Building theory from data\n\n"
        "**Analysis methods:** Thematic analysis, coding, narrative analysis, content analysis"
    ),
    ("quantitative",): (
        "## Quantitative Research Methods\n\n"
        "Quantitative research measures **numerical relationships**:\n\n"
        "- **Surveys/Questionnaires** — Structured data collection\n"
        "- **Experiments** — Controlled manipulation of variables\n"
        "- **Statistical Analysis** — Hypothesis testing, regression, ANOVA\n"
        "- **Correlational Studies** — Measuring relationships\n\n"
        "**Common statistical tests:** t-test, chi-square, ANOVA, regression analysis, Pearson correlation"
    ),
    ("systematic review", "meta-analysis"): (
        "## Systematic Review & Meta-Analysis\n\n"
        "**Systematic Review:** A rigorous, reproducible synthesis of all relevant studies.\n\n"
        "**Steps:**\n"
        "1. Define the review question (PICO framework)\n"
        "2. Develop a search strategy\n"
        "3. Set inclusion/exclusion criteria\n"
        "4. Screen studies (title/abstract → full text)\n"
        "5. Extract data\n"
        "6. Assess quality/risk of bias\n"
        "7. Synthesize results\n"
        "8. Report findings\n\n"
        "**Meta-Analysis:** Statistical combination of results from multiple studies to calculate an overall effect size."
    ),
    ("survey",): (
        "## Survey Design\n\n"
        "1. **Define objectives** — What do you want to learn?\n"
        "2. **Target population** — Who are your respondents?\n"
        "3. **Question types** — Multiple choice, Likert scale, open-ended\n"
        "4. **Sampling method** — Random, stratified, convenience\n"
        "5. **Sample size** — Use power analysis or rule of thumb (n ≥ 30 for statistical tests)\n"
        "6. **Pilot test** — Try with a small group first\n"
        "7. **Distribution** — Online (Google Forms, SurveyMonkey) or in-person\n"
        "8. **Analysis** — Descriptive statistics, cross-tabulation, regression"
    ),
    ("citation", "cite", "referencing", "reference style"): (
        "## How to Cite References\n\n"
        "Common citation styles:\n"
        "- **APA** — Social sciences (Author, Year)\n"
        "- **IEEE** — Engineering/CS [Number]\n"
        "- **MLA** — Humanities (Author Page)\n"
        "- **Chicago** — History/Law (Footnotes)\n\n"
        "**Tools:** Zotero, Mendeley, EndNote, BibTeX\n\n"
        "**Tip:** Use a reference manager to organize and auto-format citations."
    ),
    ("write paper", "write a paper", "paper structure", "paper format", "write research"): (
        "## Research Paper Structure\n\n"
        "1. **Title** — Concise and descriptive\n"
        "2. **Abstract** — 150-300 word summary (problem, method, results, conclusion)\n"
        "3. **Introduction** — Background, problem statement, objectives, contributions\n"
        "4. **Literature Review** — Existing work, comparison, gaps\n"
        "5. **Methodology** — Your approach, experimental setup, data collection\n"
        "6. **Results** — Findings with tables/figures\n"
        "7. **Discussion** — Interpret results, compare with existing work\n"
        "8. **Conclusion** — Summary, contributions, limitations, future work\n"
        "9. **References** — All cited works\n\n"
        "**Tip:** Use the ResearchOS Paper Editor to draft your paper within your project."
    ),
    ("peer review",): (
        "## Peer Review Process\n\n"
        "Peer review is expert evaluation of research before publication:\n\n"
        "1. **Submission** — Author submits paper to journal/conference\n"
        "2. **Editor screening** — Initial relevance check\n"
        "3. **Reviewer assignment** — 2-4 domain experts\n"
        "4. **Review** — Detailed evaluation of methodology, results, novelty\n"
        "5. **Decision** — Accept, minor revisions, major revisions, reject\n"
        "6. **Revision** — Author addresses feedback\n"
        "7. **Publication** — Accepted papers are published"
    ),
}


def _get_research_guidance(message: str) -> str | None:
    """Match a research methodology question against known guidance."""
    lower_msg = message.lower()

    for keywords, guidance in _RESEARCH_GUIDANCE.items():
        if any(kw in lower_msg for kw in keywords):
            return guidance

    return None


def _get_dataset_guidance(message: str, ctx: dict[str, Any]) -> str:
    """Provide dataset recommendation guidance."""
    parts = ["## Finding the Right Dataset\n"]

    # Check if we have any analyses with dataset recommendations
    if ctx["analyses"]:
        parts.append("**From your saved analyses, datasets have been recommended for:**\n")
        for a in ctx["analyses"]:
            if a["dataset_count"] > 0:
                parts.append(f"- {a['research_idea']} ({a['dataset_count']} recommendation(s))")
        parts.append("\nCheck your project's **AI Analysis** section for detailed dataset recommendations.\n")

    # General dataset sources
    parts.append("**Popular dataset sources:**\n")
    parts.append("| Source | URL | Specialty |")
    parts.append("|--------|-----|-----------|")
    parts.append("| Kaggle | https://kaggle.com/datasets | ML, Data Science, General |")
    parts.append("| UCI ML Repository | https://archive.ics.uci.edu/ml | Classical ML benchmarks |")
    parts.append("| Hugging Face | https://huggingface.co/datasets | NLP, Vision, LLMs |")
    parts.append("| Papers With Code | https://paperswithcode.com/datasets | Research benchmarks |")
    parts.append("| Google Dataset Search | https://datasetsearch.research.google.com | Cross-domain |")
    parts.append("| IEEE DataPort | https://ieee-dataport.org | Engineering, CS |")
    parts.append("| Data.gov | https://data.gov | US Government Open Data |")
    parts.append("| World Bank Open Data | https://data.worldbank.org | Economics, Development |")

    # Try to suggest based on project domain
    if ctx.get("current_project"):
        domain = ctx["current_project"]["domain"].lower()
        parts.append(f"\n**For your domain ({ctx['current_project']['domain']}), consider:**\n")
        if any(kw in domain for kw in ["nlp", "language", "text", "chatbot"]):
            parts.append("- Hugging Face Datasets (NLP tasks)")
            parts.append("- GLUE/SuperGLUE benchmarks")
            parts.append("- Common Crawl")
        elif any(kw in domain for kw in ["vision", "image", "cv", "visual"]):
            parts.append("- ImageNet")
            parts.append("- COCO (Common Objects in Context)")
            parts.append("- CIFAR-10/100")
        elif any(kw in domain for kw in ["health", "medical", "clinical"]):
            parts.append("- MIMIC-III/IV (clinical data)")
            parts.append("- PhysioNet")
            parts.append("- UK Biobank")
        elif any(kw in domain for kw in ["security", "cyber", "network"]):
            parts.append("- NSL-KDD (network intrusion)")
            parts.append("- CICIDS datasets")
            parts.append("- UNSW-NB15")
        else:
            parts.append("- Google Dataset Search for your specific topic")
            parts.append("- Papers With Code for research benchmarks")

    return "\n".join(parts)


def _get_general_guidance(message: str) -> str:
    """Provide helpful answers for general knowledge, technical, and programming questions.

    This is the fallback when the LLM is unavailable. It provides structured,
    useful answers for common question types.
    """
    parts: list[str] = []

    # --- Programming / Coding ---
    if any(kw in message for kw in ["python", "javascript", "java ", "code",
                                     "function", "class", "programming"]):
        parts.append("## Programming Help\n")
        parts.append("I'd be happy to help with programming. Here are some common topics:\n")
        parts.append("- **Python** — Functions, classes, decorators, generators, async/await, data structures")
        parts.append("- **JavaScript** — Closures, promises, async/await, DOM manipulation, frameworks")
        parts.append("- **Java** — OOP, generics, collections, streams, Spring Boot")
        parts.append("- **SQL** — Queries, joins, indexes, optimization")
        parts.append("- **Data Structures** — Arrays, linked lists, trees, graphs, hash maps")
        parts.append("- **Algorithms** — Sorting, searching, dynamic programming, graph algorithms")
        parts.append("\n*Note: When the LLM is available, I can provide specific code solutions. Without it, I can guide you to the right concepts.*")
        return "\n".join(parts)

    # --- Machine Learning / AI ---
    if any(kw in message for kw in ["machine learning", "neural network", "deep learning",
                                     "artificial intelligence", "ai ", "nlp", "computer vision"]):
        parts.append("## Machine Learning & AI\n")
        parts.append("Key concepts in ML/AI:\n")
        parts.append("- **Supervised Learning** — Classification, regression, decision trees, SVMs, random forests")
        parts.append("- **Unsupervised Learning** — Clustering (K-means, DBSCAN), dimensionality reduction (PCA, t-SNE)")
        parts.append("- **Deep Learning** — CNNs (vision), RNNs/LSTMs (sequences), Transformers (NLP, vision)")
        parts.append("- **NLP** — Tokenization, embeddings, attention, BERT, GPT, fine-tuning")
        parts.append("- **Evaluation** — Accuracy, precision, recall, F1, AUC-ROC, confusion matrix")
        parts.append("- **Optimization** — Gradient descent, Adam, learning rate scheduling, regularization")
        parts.append("\n*Upload relevant papers to your project, and I can help analyze specific ML approaches.*")
        return "\n".join(parts)

    # --- Math / Science ---
    if any(kw in message for kw in ["math", "equation", "formula", "theorem", "proof",
                                     "physics", "chemistry", "biology"]):
        parts.append("## Math & Science\n")
        parts.append("I can help with various math and science topics:\n")
        parts.append("- **Calculus** — Derivatives, integrals, series, differential equations")
        parts.append("- **Linear Algebra** — Vectors, matrices, eigenvalues, SVD")
        parts.append("- **Probability & Statistics** — Distributions, hypothesis testing, Bayesian inference")
        parts.append("- **Discrete Math** — Graph theory, combinatorics, logic")
        parts.append("- **Physics** — Mechanics, electromagnetism, quantum, thermodynamics")
        parts.append("- **Chemistry** — Organic, inorganic, physical, analytical")
        parts.append("- **Biology** — Molecular, cellular, ecology, genetics")
        parts.append("\n*Please ask a specific question and I'll do my best to help!*")
        return "\n".join(parts)

    # --- Writing / Summarization ---
    if any(kw in message for kw in ["write", "summarize", "rewrite", "explain simply",
                                     "translate", "help me write"]):
        parts.append("## Writing Assistance\n")
        parts.append("I can help with various writing tasks:\n")
        parts.append("- **Academic writing** — Papers, abstracts, literature reviews")
        parts.append("- **Technical writing** — Documentation, reports, READMEs")
        parts.append("- **General writing** — Essays, emails, summaries, explanations")
        parts.append("- **Editing** — Grammar, clarity, structure, tone")
        parts.append("\n*Note: For best results with writing tasks, please have the LLM provider (Ollama) running. I can provide structure and guidance without it.*")
        return "\n".join(parts)

    # --- General knowledge ---
    parts.append("## I Can Help!")
    parts.append("I'm the ResearchOS Assistant. I can answer questions on many topics:")
    parts.append("")
    parts.append("**Research & Academic:**")
    parts.append("- Literature review, methodology, citations, research gaps")
    parts.append("- Paper analysis, dataset recommendations, experiment design")
    parts.append("")
    parts.append("**Technical & Programming:**")
    parts.append("- Python, JavaScript, SQL, data structures, algorithms")
    parts.append("- Machine learning, AI, web development")
    parts.append("")
    parts.append("**General Knowledge:**")
    parts.append("- Math, science, engineering, writing, explanations")
    parts.append("")
    parts.append("**Workspace:**")
    parts.append("- Your projects, documents, references, analyses")
    parts.append("")
    parts.append("Please ask a specific question and I'll do my best to help!")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=AssistantMessageResponse,
)
def chat(
    payload: AssistantMessageRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> AssistantMessageResponse:
    message = payload.message.strip()
    project_id = getattr(payload, "project_id", None)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    # --- Step 1: Build workspace context ---
    try:
        ctx = _build_workspace_context(db, user_id, project_id)
    except Exception as exc:
        logger.error("[Assistant] Failed to build workspace context: %s", exc)
        ctx = {"projects": [], "workspace_documents": [], "project_documents": [],
               "document_contents": [], "references": [], "papers": [], "analyses": [],
               "current_project": None, "current_project_id": None}

    # --- Step 2: Try LLM ---
    llm_response = None
    if settings.ai_provider == "local":
        context_str = _context_to_string(ctx)
        # Build conversation messages with history for multi-turn support
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"{context_str}\n\n=== WORKSPACE CONTEXT LOADED ===\nPlease answer all questions using this context. When the user refers to 'my project', 'my documents', etc., use the information above."
            },
            {"role": "assistant", "content": "I've loaded your workspace context. I can see your projects, documents, references, analyses, and evidence sessions. How can I help you with your research?"},
        ]
        # Append conversation history if provided
        history = getattr(payload, "history", None) or []
        for turn in history[-10:]:  # keep last 10 turns for context window
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        # Add current message
        messages.append({"role": "user", "content": f"{context_str}\n\n=== USER QUESTION ===\n{message}\n\n=== ANSWER ===\n"})
        llm_response = _call_llm_with_messages(messages)

    if llm_response:
        # Determine sources
        sources = []
        if ctx["document_contents"]:
            sources = [dc["filename"] for dc in ctx["document_contents"][:5]]
        source_str = ", ".join(sources) if sources else "general knowledge"

        return AssistantMessageResponse(
            reply=llm_response,
            source=f"llm ({source_str})",
        )

    # --- Step 3: Fallback (deterministic, document-grounded) ---
    fallback_response = _fallback_answer(message, ctx)

    sources = []
    if ctx["document_contents"]:
        sources = [dc["filename"] for dc in ctx["document_contents"][:3]]
    source_str = ", ".join(sources) if sources else "workspace context"

    return AssistantMessageResponse(
        reply=fallback_response,
        source=f"workspace ({source_str})",
    )
