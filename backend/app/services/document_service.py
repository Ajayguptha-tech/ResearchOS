from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Paper, ResearchDocument


class DocumentService:
    allowed_extensions = {
        ".txt", ".md", ".markdown",
        ".pdf", ".docx",
        ".csv", ".xlsx", ".xls",
        ".pptx",
        ".png", ".jpg", ".jpeg", ".webp",
        ".html", ".htm", ".json", ".xml",
    }

    # Maximum characters to extract for AI context (prevents huge docs)
    MAX_EXTRACT_CHARS = 80_000

    def ingest(self, db: Session, owner_id: int, upload: UploadFile, paper_id: int | None, project_id: int | None = None) -> ResearchDocument:
        original_name = Path(upload.filename or "document").name
        extension = Path(original_name).suffix.lower()
        if extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{extension}'. Supported: PDF, DOCX, TXT, Markdown, CSV, XLSX, PPTX, PNG, JPG, JPEG, WEBP.",
            )

        data = upload.file.read(settings.max_upload_bytes + 1)
        if not data:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded file is empty")
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The uploaded file exceeds the configured size limit")

        text = self._extract_text(data, extension, original_name)

        # Truncate if too large for AI context
        if len(text) > self.MAX_EXTRACT_CHARS:
            text = text[:self.MAX_EXTRACT_CHARS] + f"\n\n[Document truncated at {self.MAX_EXTRACT_CHARS} characters for AI context limits]"

        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No readable text was found in the uploaded file. If this is a scanned PDF or image, OCR support is not available in this environment.",
            )

        storage_dir = Path(settings.upload_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        stored_path = storage_dir / f"{uuid4().hex}{extension}"
        stored_path.write_bytes(data)

        document = ResearchDocument(
            owner_id=owner_id,
            project_id=project_id,
            paper_id=paper_id,
            filename=original_name,
            content_type=upload.content_type or "application/octet-stream",
            storage_path=str(stored_path),
            extracted_text=text,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def _extract_text(data: bytes, extension: str, filename: str = "") -> str:
        """Extract text content from various document formats."""

        # ---- TXT / Markdown ----
        if extension in {".txt", ".md", ".markdown"}:
            return data.decode("utf-8", errors="replace")

        # ---- PDF ----
        if extension == ".pdf":
            return DocumentService._extract_pdf(data)

        # ---- DOCX ----
        if extension == ".docx":
            return DocumentService._extract_docx(data)

        # ---- CSV ----
        if extension == ".csv":
            return DocumentService._extract_csv(data)

        # ---- XLSX ----
        if extension == ".xlsx":
            return DocumentService._extract_xlsx(data)

        # ---- XLS (legacy binary format; openpyxl cannot read it) ----
        if extension == ".xls":
            return DocumentService._extract_xls(data)

        # ---- PPTX ----
        if extension == ".pptx":
            return DocumentService._extract_pptx(data)

        # ---- Images: PNG, JPG, JPEG, WEBP ----
        if extension in {".png", ".jpg", ".jpeg", ".webp"}:
            return DocumentService._extract_image(data, filename)

        # ---- HTML ----
        if extension in {".html", ".htm"}:
            return DocumentService._extract_html(data)

        # ---- JSON ----
        if extension == ".json":
            return DocumentService._extract_json(data)

        # ---- XML ----
        if extension == ".xml":
            return DocumentService._extract_xml(data)

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{extension}'",
        )

    @staticmethod
    def _extract_pdf(data: bytes) -> str:
        try:
            from pypdf import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(data))
            pages = []
            scanned_pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"[Page {i + 1}]\n{text.strip()}")
                else:
                    # Check if page has images (scanned)
                    try:
                        resources = page.get("/Resources") or {}
                        xobjects = resources.get("/XObject")
                        if xobjects:
                            scanned_pages.append(i + 1)
                    except Exception:
                        scanned_pages.append(i + 1)

            if not pages and scanned_pages:
                return (
                    f"[PDF contains {len(scanned_pages)} scanned image page(s) with no text layer.\n"
                    f"Pages: {', '.join(str(p) for p in scanned_pages)}\n"
                    f"OCR is required to extract text from this PDF.]"
                )

            result = "\n\n".join(pages)

            if scanned_pages and pages:
                result += (
                    f"\n\n[Note: Pages {', '.join(str(p) for p in scanned_pages)} "
                    f"contain scanned images and could not be read as text.]"
                )

            return result if result.strip() else "[PDF contains no extractable text]"
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF extraction library (pypdf) is not installed. Run: pip install pypdf",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read PDF: {exc}",
            )

    @staticmethod
    def _extract_docx(data: bytes) -> str:
        try:
            from docx import Document
            from io import BytesIO

            doc = Document(BytesIO(data))
            parts = []

            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    # Preserve heading styles
                    if paragraph.style and paragraph.style.name.startswith("Heading"):
                        parts.append(f"\n{text}")
                    else:
                        parts.append(text)

            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))

            return "\n\n".join(parts) if parts else "[DOCX contains no text content]"
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DOCX extraction library (python-docx) is not installed. Run: pip install python-docx",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read DOCX: {exc}",
            )

    @staticmethod
    def _extract_csv(data: bytes) -> str:
        try:
            text = data.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)
            if not rows:
                return "[CSV file is empty]"

            # First row is headers
            headers = rows[0]
            parts = [f"Columns: {', '.join(headers)}"]
            parts.append(f"Total rows: {len(rows) - 1}")

            # Include first 50 data rows as sample
            sample_rows = rows[1:51]
            for i, row in enumerate(sample_rows, 1):
                parts.append(f"Row {i}: {' | '.join(str(c) for c in row)}")

            if len(rows) > 51:
                parts.append(f"[Showing 50 of {len(rows) - 1} rows]")

            return "\n".join(parts)
        except Exception:
            return data.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_xlsx(data: bytes) -> str:
        try:
            from openpyxl import load_workbook
            from io import BytesIO

            wb = load_workbook(BytesIO(data), read_only=True, data_only=True)
            parts = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                parts.append(f"=== Sheet: {sheet_name} ===")

                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    parts.append("(empty sheet)")
                    continue

                # Headers
                headers = [str(c) if c is not None else "" for c in rows[0]]
                parts.append(f"Columns: {', '.join(headers)}")
                parts.append(f"Total rows: {len(rows) - 1}")

                # Sample rows
                for i, row in enumerate(rows[1:51], 1):
                    cells = [str(c) if c is not None else "" for c in row]
                    parts.append(f"Row {i}: {' | '.join(cells)}")

                if len(rows) > 51:
                    parts.append(f"[Showing 50 of {len(rows) - 1} rows]")

            wb.close()
            return "\n\n".join(parts) if parts else "[XLSX file is empty]"
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="XLSX extraction library (openpyxl) is not installed. Run: pip install openpyxl",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read XLSX: {exc}",
            )

    @staticmethod
    def _extract_xls(data: bytes) -> str:
        """Extract text from legacy .xls workbooks using xlrd (if installed)."""
        try:
            import xlrd
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Legacy .xls extraction requires the 'xlrd' library, which is not "
                    "installed in this environment. Convert the file to .xlsx and "
                    "re-upload, or install xlrd (pip install xlrd) to enable .xls support."
                ),
            )
        try:
            from io import BytesIO

            workbook = xlrd.open_workbook(file_contents=data)
            parts = []
            for sheet in workbook.sheets():
                parts.append(f"=== Sheet: {sheet.name} ===")
                parts.append(f"Total rows: {sheet.nrows}")
                for row_index in range(min(sheet.nrows, 51)):
                    cells = []
                    for col_index in range(sheet.ncols):
                        value = sheet.cell_value(row_index, col_index)
                        cells.append("" if value is None else str(value))
                    parts.append(f"Row {row_index + 1}: {' | '.join(cells)}")
                if sheet.nrows > 51:
                    parts.append(f"[Showing 50 of {sheet.nrows} rows]")
            return "\n\n".join(parts) if parts else "[XLS file is empty]"
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read XLS: {exc}",
            )

    @staticmethod
    def _extract_pptx(data: bytes) -> str:
        try:
            from pptx import Presentation
            from io import BytesIO

            prs = Presentation(BytesIO(data))
            parts = []

            for i, slide in enumerate(prs.slides, 1):
                slide_text = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            text = paragraph.text.strip()
                            if text:
                                slide_text.append(text)
                    if shape.has_table:
                        for row in shape.table.rows:
                            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                            if cells:
                                slide_text.append(" | ".join(cells))

                if slide_text:
                    parts.append(f"[Slide {i}]\n" + "\n".join(slide_text))

            return "\n\n".join(parts) if parts else "[PPTX contains no text content]"
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PPTX extraction library (python-pptx) is not installed. Run: pip install python-pptx",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read PPTX: {exc}",
            )

    @staticmethod
    def _extract_image(data: bytes, filename: str = "") -> str:
        """Extract text description from an image using Pillow.

        Since OCR (pytesseract) is not available, we extract metadata
        and provide a description of the image for the AI to understand
        its context. This is honest — we don't pretend to read text from images.
        """
        try:
            from PIL import Image
            from io import BytesIO

            img = Image.open(BytesIO(data))
            width, height = img.size
            format_name = img.format or "Unknown"
            mode = img.mode

            parts = [
                f"[Image: {filename}]",
                f"Format: {format_name}",
                f"Dimensions: {width} x {height} pixels",
                f"Color mode: {mode}",
            ]

            # Extract EXIF metadata if available
            try:
                exif = img.getexif()
                if exif:
                    metadata_items = []
                    for tag_id, value in exif.items():
                        tag_name = str(tag_id)
                        metadata_items.append(f"  {tag_name}: {value}")
                    if metadata_items:
                        parts.append("Metadata:")
                        parts.extend(metadata_items[:10])  # Limit to 10 items
            except Exception:
                pass

            parts.append("")
            parts.append("[Note: Text content cannot be extracted from images without OCR support.")
            parts.append("To enable OCR, install Tesseract-OCR and pytesseract.]")

            return "\n".join(parts)
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image processing library (Pillow) is not installed. Run: pip install Pillow",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read image: {exc}",
            )

    @staticmethod
    def _extract_html(data: bytes) -> str:
        """Extract text from HTML by stripping tags."""
        try:
            text = data.decode("utf-8", errors="replace")
            # Simple tag stripping
            import re
            clean = re.sub(r"<[^>]+>", " ", text)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean if clean else "[HTML contains no text content]"
        except Exception:
            return data.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_json(data: bytes) -> str:
        """Extract text from JSON by pretty-printing."""
        try:
            import json
            parsed = json.loads(data.decode("utf-8", errors="replace"))
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            return data.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_xml(data: bytes) -> str:
        """Extract text from XML by stripping tags."""
        try:
            text = data.decode("utf-8", errors="replace")
            import re
            clean = re.sub(r"<[^>]+>", " ", text)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean if clean else "[XML contains no text content]"
        except Exception:
            return data.decode("utf-8", errors="replace")

    @staticmethod
    def retrieve(db: Session, owner_id: int, query: str, limit: int, project_id: int | None = None) -> list[dict[str, object]]:
        """Retrieve document excerpts relevant to a query, optionally scoped to a project."""
        terms = [term for term in re.findall(r"[a-z0-9]{2,}", query.lower())]
        results: list[dict[str, object]] = []

        query_filter = [ResearchDocument.owner_id == owner_id]
        if project_id is not None:
            query_filter.append(ResearchDocument.project_id == project_id)

        for document in db.query(ResearchDocument).filter(*query_filter).all():
            text = document.extracted_text
            normalized = text.lower()
            occurrences = sum(normalized.count(term) for term in terms)
            if not occurrences:
                continue
            first_position = min((normalized.find(term) for term in terms if normalized.find(term) >= 0), default=0)
            start, end = max(0, first_position - 180), min(len(text), first_position + 420)
            excerpt = text[start:end].strip().replace("\n", " ")
            results.append({"document_id": document.id, "filename": document.filename, "paper_id": document.paper_id, "score": round(occurrences / max(len(terms), 1), 3), "excerpt": excerpt})
        return sorted(results, key=lambda item: (-float(item["score"]), int(item["document_id"])))[:limit]

    @staticmethod
    def analysis_papers(
        db: Session,
        owner_id: int,
        query: str,
        document_ids: list[int] | None = None,
        project_id: int | None = None,
    ) -> list[dict[str, object]]:
        """Normalize owner-scoped uploaded documents for the existing agents.

        Returns documents as 'papers' with the full extracted text as the abstract,
        so that agents can actually read and analyze the document content.
        """
        if document_ids:
            documents = (
                db.query(ResearchDocument)
                .filter(
                    ResearchDocument.owner_id == owner_id,
                    ResearchDocument.id.in_(document_ids),
                )
                .all()
            )
            if len(documents) != len(set(document_ids)):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more uploaded documents were not found.",
                )
        else:
            # When no specific document IDs, search within the project if provided
            if project_id is not None:
                # Get all documents for this project and score them
                all_project_docs = (
                    db.query(ResearchDocument)
                    .filter(
                        ResearchDocument.owner_id == owner_id,
                        ResearchDocument.project_id == project_id,
                    )
                    .all()
                )
                if all_project_docs:
                    # Score each document against the query
                    terms = [term for term in re.findall(r"[a-z0-9]{2,}", query.lower())]
                    scored = []
                    for doc in all_project_docs:
                        text = doc.extracted_text.lower()
                        occurrences = sum(text.count(term) for term in terms)
                        if occurrences > 0:
                            scored.append((doc, occurrences))
                    # If keyword matches found, use them; otherwise use all project docs
                    if scored:
                        scored.sort(key=lambda x: -x[1])
                        documents = [s[0] for s in scored[:20]]
                    else:
                        documents = all_project_docs[:20]
                else:
                    documents = []
            else:
                matches = DocumentService.retrieve(db, owner_id, query, limit=50)
                matched_ids = [int(match["document_id"]) for match in matches]
                if not matched_ids:
                    return []
                documents = (
                    db.query(ResearchDocument)
                    .filter(
                        ResearchDocument.owner_id == owner_id,
                        ResearchDocument.id.in_(matched_ids),
                    )
                    .all()
                )

        linked_paper_ids = [document.paper_id for document in documents if document.paper_id]
        linked_papers = {
            paper.id: paper
            for paper in db.query(Paper)
            .filter(Paper.owner_id == owner_id, Paper.id.in_(linked_paper_ids))
            .all()
        } if linked_paper_ids else {}

        normalized: list[dict[str, object]] = []
        for document in documents:
            content = document.extracted_text.strip()
            if not content:
                continue
            linked_paper = linked_papers.get(document.paper_id)
            authors = []
            if linked_paper and linked_paper.authors:
                authors = [author.strip() for author in linked_paper.authors.split(",") if author.strip()]
            normalized.append(
                {
                    "id": f"local-document-{document.id}",
                    "document_id": document.id,
                    "paper_id": document.paper_id,
                    "title": linked_paper.title if linked_paper else document.filename,
                    "abstract": content,  # Full extracted text for AI analysis
                    "authors": authors,
                    "year": linked_paper.year if linked_paper else None,
                    "url": "",
                    "doi": linked_paper.doi if linked_paper else None,
                    "venue": linked_paper.venue if linked_paper else None,
                    "citation_count": linked_paper.citation_count if linked_paper else 0,
                    "source": "local_uploaded_document",
                    "filename": document.filename,
                    "content_type": document.content_type,
                    "extracted_characters": len(content),
                }
            )
        return normalized
