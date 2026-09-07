from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Project


"""LEGACY / UNUSED duplicate — prefer app/db/repositories/project_repository.py.

This stub predates the active repository and lacks owner-scoping helpers
(list_for_owner, get_for_owner) plus the description field.  The active code
path (app/api/v1/routes/projects.py) imports ProjectRepository from
``app.db.repositories.project_repository``.  Kept only so legacy imports do
not crash; do not extend this file.
"""


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, title: str, domain: str, owner_id: int) -> Project:
        project = Project(title=title, domain=domain, owner_id=owner_id)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()
