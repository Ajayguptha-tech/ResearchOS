from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Paper


class PaperRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict, owner_id: int) -> Paper:
        paper = Paper(**data, owner_id=owner_id)
        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)
        return paper

    def list_for_owner(self, owner_id: int) -> list[Paper]:
        return self.db.query(Paper).filter(Paper.owner_id == owner_id).order_by(Paper.id.asc()).all()

    def get_for_owner(self, paper_id: int, owner_id: int) -> Paper | None:
        return self.db.query(Paper).filter(Paper.id == paper_id, Paper.owner_id == owner_id).first()

    def search_for_owner(self, query: str, owner_id: int, limit: int) -> list[Paper]:
        pattern = f"%{query.lower()}%"
        papers = (
            self.db.query(Paper)
            .filter(
                Paper.owner_id == owner_id,
                or_(
                    Paper.title.ilike(pattern),
                    Paper.abstract.ilike(pattern),
                    Paper.authors.ilike(pattern),
                    Paper.venue.ilike(pattern),
                    Paper.doi.ilike(pattern),
                ),
            )
            .all()
        )
        return sorted(papers, key=lambda paper: (-self._score(paper, query), paper.id))[:limit]

    @staticmethod
    def _score(paper: Paper, query: str) -> int:
        normalized_query = query.lower()
        fields = (paper.title, paper.abstract, paper.authors, paper.venue, paper.doi)
        return sum((field or "").lower().count(normalized_query) for field in fields)

    def delete(self, paper: Paper) -> None:
        self.db.delete(paper)
        self.db.commit()
