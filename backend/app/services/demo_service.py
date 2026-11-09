"""Demo Account Service.

Ensures the dedicated, least-privilege demo account (demo@researchos.io) exists,
is verified, and has its password properly hashed with the application's PBKDF2
hasher. Provides sample isolated demo data that cannot access other users' data.
"""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import Project, ResearchIdea, ResearchPlan, User

logger = logging.getLogger(__name__)

DEMO_EMAIL = "demo@researchos.io"
DEMO_PASSWORD = "DemoPassword123!"
DEMO_NAME = "Demo Researcher"
DEMO_ROLE = "researcher"


def ensure_demo_account(db: Session) -> User:
    """Idempotently seed or update the dedicated demo account."""
    demo_user = db.query(User).filter(User.email == DEMO_EMAIL).first()

    if not demo_user:
        logger.info("[DemoService] Creating dedicated demo account: %s", DEMO_EMAIL)
        demo_user = User(
            email=DEMO_EMAIL,
            name=DEMO_NAME,
            password_hash=hash_password(DEMO_PASSWORD),
            email_verified=True,
            role=DEMO_ROLE,
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
    else:
        # Verify and update if needed
        updated = False
        if not demo_user.email_verified:
            demo_user.email_verified = True
            updated = True
        if demo_user.role != DEMO_ROLE:
            demo_user.role = DEMO_ROLE
            updated = True
        if not verify_password(DEMO_PASSWORD, demo_user.password_hash):
            demo_user.password_hash = hash_password(DEMO_PASSWORD)
            updated = True

        if updated:
            db.commit()
            db.refresh(demo_user)
            logger.info("[DemoService] Updated demo account credentials/state for %s", DEMO_EMAIL)

    # Ensure demo account has an isolated project
    demo_project = (
        db.query(Project)
        .filter(Project.owner_id == demo_user.id)
        .first()
    )
    if not demo_project:
        demo_project = Project(
            title="Multi-Agent AI Systems for Literature Discovery",
            domain="Artificial Intelligence",
            description="Demonstration research project exploring automated semantic analysis and paper gap detection.",
            status="active",
            owner_id=demo_user.id,
        )
        db.add(demo_project)
        db.commit()
        db.refresh(demo_project)

        # Seed sample research idea
        idea = ResearchIdea(
            title="Evidence-Backed Retrieval for Fast Academic Synthesis",
            description="Investigating how hybrid dense-sparse vector indexing accelerates academic literature reviews.",
            problem_statement="Researchers face high latency and hallucinations in generic LLM literature reviews.",
            status="active",
            project_id=demo_project.id,
        )
        db.add(idea)
        db.commit()
        db.refresh(idea)

        # Seed sample research plan
        plan = ResearchPlan(
            project_id=demo_project.id,
            idea_id=idea.id,
            steps=[
                "Define search keywords across academic databases",
                "Extract structured metadata and citations",
                "Perform comparative methodology and dataset analysis",
                "Synthesize findings and outline research roadmap",
            ],
            status="active",
        )
        db.add(plan)
        db.commit()
        logger.info("[DemoService] Seeded isolated demo project and plans for demo user")

    return demo_user
