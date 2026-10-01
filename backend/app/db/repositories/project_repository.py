from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Project


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, title: str, domain: str, owner_id: int, description: str | None = None) -> Project:
        project = Project(title=title, domain=domain, owner_id=owner_id, description=description)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_for_owner(self, owner_id: int) -> list[Project]:
        return (
            self.db.query(Project)
            .filter(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
            .all()
        )

    def get_for_owner(self, project_id: int, owner_id: int) -> Project | None:
        return (
            self.db.query(Project)
            .filter(Project.id == project_id, Project.owner_id == owner_id)
            .first()
        )
