import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import AnalysisResult, Project, ResearchDocument
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = AgentOrchestrator()


class AnalysisSaveRequest(BaseModel):
    project_id: int
    research_idea: str
    document_ids: list[int] = Field(default_factory=list)
    result_json: str


class AnalysisResultResponse(BaseModel):
    id: int
    project_id: int
    research_idea: str
    result_json: str
    created_at: str


@router.post("/analyze")
def analyze_research(
    idea: str,
    max_results: int = Query(default=30, ge=1, le=100),
    _: int = Depends(get_current_user),
):
    idea = idea.strip()
    if len(idea) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Research idea must contain at least 5 characters.")
    try:
        return orchestrator.run_research_workflow(idea, max_results=max_results)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/search-literature")
def search_literature(
    idea: str,
    max_results: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    _: int = Depends(get_current_user),
):
    """Dedicated literature search with pagination."""
    idea = idea.strip()
    if len(idea) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search query must contain at least 5 characters.")
    try:
        from ai.agents.literature_search_agent import LiteratureSearchAgent
        agent = LiteratureSearchAgent()
        result = agent.search(idea, max_results=max_results)
        all_papers = result.get("results", [])
        total = len(all_papers)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "query": idea,
            "results": all_papers[start:end],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page)),  # ceil division
            "status": result.get("status", "success"),
            "source": result.get("source", ""),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/literature/search")
def search_literature_get(
    query: str = Query(..., min_length=2),
    max_results: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_current_user),
):
    """GET endpoint for literature search."""
    return search_literature(idea=query, max_results=max_results, page=page, per_page=per_page, _=user_id)


@router.post("/analyze-local")
def analyze_local_research(
    idea: str,
    document_ids: list[int] | None = Query(default=None),
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Analyze real owner-scoped uploaded documents without provider access."""
    idea = idea.strip()
    if len(idea) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Research idea must contain at least 5 characters.")

    papers = DocumentService.analysis_papers(
        db,
        user_id,
        idea,
        document_ids,
        project_id=project_id,
    )
    if not papers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable uploaded documents matched the research idea.",
        )
    try:
        result = orchestrator.run_research_workflow(idea, papers=papers)
        # Attach document info for frontend display
        result["_documents_used"] = [
            {"id": p.get("document_id"), "filename": p.get("filename", "")}
            for p in papers if p.get("document_id")
        ]
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/summarize-documents")
def summarize_documents(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Summarize uploaded documents strictly for the current workspace context (project or global)."""
    if project_id is not None:
        project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        docs = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.owner_id == user_id,
                ResearchDocument.project_id == project_id,
            )
            .order_by(ResearchDocument.created_at.desc())
            .all()
        )
        scope_name = f"Project: {project.title}"
    else:
        docs = (
            db.query(ResearchDocument)
            .filter(
                ResearchDocument.owner_id == user_id,
                ResearchDocument.project_id.is_(None),
            )
            .order_by(ResearchDocument.created_at.desc())
            .all()
        )
        scope_name = "Main Workspace"

    if not docs:
        return {
            "status": "empty",
            "scope": scope_name,
            "count": 0,
            "summaries": [],
            "message": "No documents uploaded in this workspace yet. Upload documents to generate summaries.",
        }

    from ai.agents.paper_analyzer_agent import PaperAnalyzerAgent

    papers = [
        {
            "title": doc.filename,
            "filename": doc.filename,
            "document_id": doc.id,
            "abstract": doc.extracted_text[:8000],
            "extracted_characters": len(doc.extracted_text or ""),
        }
        for doc in docs
    ]

    analyzer = PaperAnalyzerAgent()
    analysis = analyzer.analyze(papers)

    summaries = []
    for paper in analysis.get("papers", []):
        raw_findings = paper.get("findings", [])
        clean_findings = [
            f for f in raw_findings
            if not f.lower().startswith("no specific findings")
        ]

        raw_methods = paper.get("methods", [])
        clean_methods = [
            m for m in raw_methods
            if not m.lower().startswith("method not explicitly")
        ]

        summaries.append({
            "document_id": paper.get("document_id"),
            "title": paper.get("title") or paper.get("filename"),
            "filename": paper.get("filename"),
            "extracted_characters": paper.get("extracted_characters", 0),
            "summary": paper.get("abstract_summary", ""),
            "key_findings": clean_findings,
            "methodology": clean_methods,
        })

    return {
        "status": "success",
        "scope": scope_name,
        "count": len(summaries),
        "summaries": summaries,
        "message": f"Successfully summarized {len(summaries)} document(s) in {scope_name}.",
    }


@router.post("/save-analysis")
def save_analysis(
    payload: AnalysisSaveRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Persist an analysis result for a project."""
    result = AnalysisResult(
        project_id=payload.project_id,
        owner_id=user_id,
        analysis_type="full",
        research_idea=payload.research_idea,
        document_ids_used=json.dumps(payload.document_ids) if payload.document_ids else None,
        result_json=payload.result_json,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return {
        "id": result.id,
        "project_id": result.project_id,
        "research_idea": result.research_idea,
        "created_at": result.created_at.isoformat() if result.created_at else "",
    }


@router.get("/analyses/{project_id}", response_model=list[AnalysisResultResponse])
def list_analyses(
    project_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """List persisted analyses for a project."""
    results = (
        db.query(AnalysisResult)
        .filter(
            AnalysisResult.project_id == project_id,
            AnalysisResult.owner_id == user_id,
        )
        .order_by(AnalysisResult.created_at.desc())
        .all()
    )
    return [
        AnalysisResultResponse(
            id=r.id,
            project_id=r.project_id,
            research_idea=r.research_idea,
            result_json=r.result_json,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in results
    ]
