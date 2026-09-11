import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import get_current_user
from app.db.models import Paper, Project, ResearchDocument
from app.db.repositories.paper_repository import PaperRepository
from app.schemas.papers import PaperCreate, PaperImportRequest, PaperResponse, PaperUpdate, ResearchDocumentResponse, RetrievalResult
from app.services.document_service import DocumentService

router = APIRouter()


def serialize(paper) -> PaperResponse:
    return PaperResponse.model_validate(paper)


def serialize_document(document: ResearchDocument) -> ResearchDocumentResponse:
    return ResearchDocumentResponse(
        id=document.id,
        paper_id=document.paper_id,
        project_id=getattr(document, 'project_id', None),
        filename=document.filename,
        content_type=document.content_type,
        extracted_characters=len(document.extracted_text),
        created_at=document.created_at,
    )


@router.get("/", response_model=list[PaperResponse])
def list_papers(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return [serialize(paper) for paper in PaperRepository(db).list_for_owner(user_id)]


@router.get("/search", response_model=list[PaperResponse])
def search_papers(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    return [serialize(paper) for paper in PaperRepository(db).search_for_owner(q.strip(), user_id, limit)]


@router.post("/", response_model=PaperResponse)
def create_paper(payload: PaperCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return serialize(PaperRepository(db).create(payload.model_dump(), user_id))


@router.post("/import", response_model=list[PaperResponse])
def import_papers(payload: PaperImportRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    repo = PaperRepository(db)
    return [serialize(repo.create(paper.model_dump(), user_id)) for paper in payload.papers]


@router.post("/upload", response_model=ResearchDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    paper_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    if paper_id is not None and not db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == user_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    if project_id is not None and not db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return serialize_document(DocumentService().ingest(db, user_id, file, paper_id, project_id=project_id))


@router.get("/documents", response_model=list[ResearchDocumentResponse])
def list_documents(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    query = db.query(ResearchDocument).filter(ResearchDocument.owner_id == user_id)
    if project_id is not None:
        query = query.filter(ResearchDocument.project_id == project_id)
    else:
        query = query.filter(ResearchDocument.project_id.is_(None))
    documents = query.order_by(ResearchDocument.created_at.desc()).all()
    return [serialize_document(document) for document in documents]


@router.get("/documents/project/{project_id}", response_model=list[ResearchDocumentResponse])
def list_project_documents(project_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    """List documents for a specific project."""
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    documents = (
        db.query(ResearchDocument)
        .filter(ResearchDocument.owner_id == user_id, ResearchDocument.project_id == project_id)
        .order_by(ResearchDocument.created_at.desc())
        .all()
    )
    return [serialize_document(document) for document in documents]


@router.get("/retrieve", response_model=list[RetrievalResult])
def retrieve_documents(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=10, ge=1, le=50),
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    return DocumentService.retrieve(db, user_id, q, limit, project_id=project_id)


# ---------------------------------------------------------------------------
# DOCUMENT CONTENT — used by Research Assistant to answer from real content
# ---------------------------------------------------------------------------

@router.get("/documents/{doc_id}/content")
def get_document_content(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Return the full extracted text of a document."""
    doc = (
        db.query(ResearchDocument)
        .filter(ResearchDocument.id == doc_id, ResearchDocument.owner_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "extracted_text": doc.extracted_text,
        "extracted_characters": len(doc.extracted_text),
        "project_id": doc.project_id,
    }


# ---------------------------------------------------------------------------
# DOCUMENT SUMMARY — generate a structured summary from extracted text
# ---------------------------------------------------------------------------

@router.get("/documents/{doc_id}/summary")
def get_document_summary(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Generate a structured summary from the document's extracted text."""
    doc = (
        db.query(ResearchDocument)
        .filter(ResearchDocument.id == doc_id, ResearchDocument.owner_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    text = doc.extracted_text
    text_lower = text.lower()

    # Extract keywords from content
    common_keywords = [
        "machine learning", "deep learning", "neural network", "classification",
        "regression", "clustering", "nlp", "natural language processing",
        "computer vision", "optimization", "algorithm", "dataset",
        "experiment", "evaluation", "methodology", "framework",
        "security", "network", "privacy", "encryption",
        "healthcare", "medical", "clinical", "diagnosis",
    ]
    found_keywords = [kw for kw in common_keywords if kw in text_lower]

    # Try to identify sections
    sections_found = []
    section_markers = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "methodology": "Methodology",
        "method": "Methods",
        "results": "Results",
        "conclusion": "Conclusion",
        "discussion": "Discussion",
        "related work": "Related Work",
        "background": "Background",
        "experiments": "Experiments",
        "evaluation": "Evaluation",
    }
    for marker, label in section_markers.items():
        if marker in text_lower:
            sections_found.append(label)

    # Build summary
    sentences = text.replace("?", ".").replace("!", ".").split(".")
    meaningful = [s.strip() for s in sentences if len(s.strip()) > 30][:10]

    return {
        "id": doc.id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "extracted_characters": len(text),
        "sections_detected": sections_found,
        "keywords_found": found_keywords[:15],
        "preview": " ".join(meaningful[:3]) if meaningful else "No meaningful content extracted.",
    }


# ---------------------------------------------------------------------------
# DOCUMENT DELETE
# ---------------------------------------------------------------------------

@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
) -> None:
    """Delete a document and its stored file."""
    doc = (
        db.query(ResearchDocument)
        .filter(ResearchDocument.id == doc_id, ResearchDocument.owner_id == user_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Remove stored file if it exists
    try:
        file_path = Path(doc.storage_path)
        if file_path.is_file():
            os.remove(file_path)
    except Exception:
        pass  # Best-effort file cleanup
    db.delete(doc)
    db.commit()


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    paper = PaperRepository(db).get_for_owner(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return serialize(paper)


@router.patch("/{paper_id}", response_model=PaperResponse)
def update_paper(paper_id: int, payload: PaperUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    paper = PaperRepository(db).get_for_owner(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)
    db.commit()
    db.refresh(paper)
    return serialize(paper)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(paper_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    paper = PaperRepository(db).get_for_owner(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    PaperRepository(db).delete(paper)


@router.post("/compare")
def compare_papers(
    paper_ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    """Compare the user's saved papers using their real stored metadata.

    Every claim in the response is derived from the actual stored records
    (titles, years, venues, citation counts, DOIs, abstracts).  When the
    user has no papers to compare, the endpoint says so instead of
    fabricating a comparison.
    """
    query = db.query(Paper).filter(Paper.owner_id == user_id)
    if paper_ids:
        query = query.filter(Paper.id.in_(paper_ids))
    papers = query.order_by(Paper.id.asc()).all()

    if not papers:
        return {
            "comparison": {
                "summary": "No saved papers to compare. Add papers first, then run the comparison again.",
                "papers_compared": 0,
                "papers": [],
                "strengths": [],
                "gaps": [],
            }
        }

    ordered = [
        {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
            "doi": paper.doi,
            "citation_count": paper.citation_count,
            "evidence_level": paper.evidence_level,
            "has_abstract": bool(paper.abstract and paper.abstract.strip()),
        }
        for paper in papers
    ]

    with_doi = sum(1 for p in ordered if p["doi"])
    with_abstract = sum(1 for p in ordered if p["has_abstract"])
    with_venue = sum(1 for p in ordered if p["venue"])
    total_citations = sum(p["citation_count"] or 0 for p in ordered)
    years = [p["year"] for p in ordered if p["year"]]
    year_span = f"{min(years)}–{max(years)}" if len(years) >= 2 else (str(years[0]) if years else "n/a")

    summary = (
        f"Compared {len(ordered)} saved paper(s) spanning {year_span}. "
        f"{with_abstract} have an abstract on file, {with_doi} have a DOI, and "
        f"{with_venue} record a venue. Total recorded citations: {total_citations}."
    )

    strengths = []
    if with_abstract:
        strengths.append(f"{with_abstract} of {len(ordered)} paper(s) include an abstract for content analysis.")
    if with_doi:
        strengths.append(f"{with_doi} paper(s) have a DOI, which makes them verifiable and citable.")
    if total_citations > 0:
        strengths.append(f"The collection records {total_citations} total citation(s).")
    if not strengths:
        strengths.append("No strengths could be derived: add abstracts, DOIs, or citation counts to the records.")

    gaps = []
    if not with_abstract:
        gaps.append("No abstract is stored for any paper — add abstracts to enable content-level comparison.")
    if not with_doi:
        gaps.append("No paper has a DOI — add DOIs to make the records verifiable.")
    if not years:
        gaps.append("No publication years are recorded — add years to compare recency.")
    if not gaps:
        gaps.append("No obvious metadata gaps in the compared records.")

    return {
        "comparison": {
            "summary": summary,
            "papers_compared": len(ordered),
            "papers": ordered,
            "strengths": strengths,
            "gaps": gaps,
        }
    }
