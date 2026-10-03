"""Small, non-destructive SQLite compatibility upgrades.

Production deployments should use an Alembic migration history.  The local
application supports existing SQLite databases created before new nullable
columns were introduced, so startup can safely add those columns without
touching user data.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def upgrade_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "phone_number" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(32)"))
        if "email_verified" not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0"))

        # Drop UNIQUE constraint on users.email if it exists.
        # SQLite does not support ALTER TABLE DROP CONSTRAINT, so we
        # recreate the table without the unique index.
        _drop_email_unique_constraint(engine, inspector)

    # Add project_id to research_documents if missing
    if "research_documents" in tables:
        doc_columns = {column["name"] for column in inspector.get_columns("research_documents")}
        if "project_id" not in doc_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE research_documents ADD COLUMN project_id INTEGER"))

    # Add description to projects if missing
    if "projects" in tables:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "description" not in project_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE projects ADD COLUMN description TEXT"))

    # Create evidence_sessions table if it does not exist
    if "evidence_sessions" not in tables:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS evidence_sessions ("
                "id INTEGER PRIMARY KEY,"
                "project_id INTEGER NOT NULL REFERENCES projects(id),"
                "owner_id INTEGER NOT NULL REFERENCES users(id),"
                "title VARCHAR(500) NOT NULL,"
                "description TEXT,"
                "notes TEXT,"
                "session_date DATETIME,"
                "status VARCHAR(50) DEFAULT 'active',"
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_sessions_project_id ON evidence_sessions (project_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_sessions_owner_id ON evidence_sessions (owner_id)"))

    # Create evidence_session_items table if it does not exist
    # NOTE: column is ``note`` (singular) to match app.db.models.EvidenceSessionItem.
    if "evidence_session_items" not in tables:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS evidence_session_items ("
                "id INTEGER PRIMARY KEY,"
                "session_id INTEGER NOT NULL REFERENCES evidence_sessions(id) ON DELETE CASCADE,"
                "item_type VARCHAR(20) NOT NULL,"
                "item_id INTEGER NOT NULL,"
                "note TEXT,"
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_evidence_session_items_session_id ON evidence_session_items (session_id)"))

    # Non-destructive repair: an older migration created evidence_session_items with
    # a ``notes`` column while the model uses ``note``.  Align existing databases
    # without touching any data (SQLite RENAME COLUMN is available since 3.25.0).
    if "evidence_session_items" in tables:
        item_columns = {column["name"] for column in inspector.get_columns("evidence_session_items")}
        if "notes" in item_columns and "note" not in item_columns:
            logger.info("[Migration] Renaming evidence_session_items.notes -> note (non-destructive)")
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE evidence_session_items RENAME COLUMN notes TO note"))

    # Add is_recent to papers if missing
    if "papers" in tables:
        paper_columns = {column["name"] for column in inspector.get_columns("papers")}
        if "is_recent" not in paper_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE papers ADD COLUMN is_recent BOOLEAN DEFAULT 0"))

    # Create paper_drafts table if it does not exist
    if "paper_drafts" not in tables:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS paper_drafts ("
                "id INTEGER PRIMARY KEY,"
                "project_id INTEGER NOT NULL REFERENCES projects(id),"
                "owner_id INTEGER NOT NULL REFERENCES users(id),"
                "title VARCHAR(500) NOT NULL,"
                "instruction TEXT,"
                "content TEXT DEFAULT '',"
                "word_count INTEGER DEFAULT 0,"
                "status VARCHAR(32) DEFAULT 'draft',"
                "source_document_ids TEXT,"
                "source_paper_ids TEXT,"
                "current_version INTEGER DEFAULT 1,"
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
                "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_paper_drafts_project_id ON paper_drafts (project_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_paper_drafts_owner_id ON paper_drafts (owner_id)"))

    # Create paper_draft_versions table if it does not exist
    if "paper_draft_versions" not in tables:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS paper_draft_versions ("
                "id INTEGER PRIMARY KEY,"
                "draft_id INTEGER NOT NULL REFERENCES paper_drafts(id) ON DELETE CASCADE,"
                "version_number INTEGER NOT NULL,"
                "title VARCHAR(500) NOT NULL,"
                "content TEXT NOT NULL,"
                "word_count INTEGER DEFAULT 0,"
                "instruction TEXT,"
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_paper_draft_versions_draft_id ON paper_draft_versions (draft_id)"))

    # Create project_references table if it does not exist
    if "project_references" not in tables:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE IF NOT EXISTS project_references ("
                "id INTEGER PRIMARY KEY,"
                "project_id INTEGER NOT NULL REFERENCES projects(id),"
                "owner_id INTEGER NOT NULL REFERENCES users(id),"
                "title VARCHAR(500) NOT NULL,"
                "url VARCHAR(1024),"
                "authors TEXT,"
                "year INTEGER,"
                "notes TEXT,"
                "reference_type VARCHAR(50) DEFAULT 'paper',"
                "created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_references_project_id ON project_references (project_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_references_owner_id ON project_references (owner_id)"))

    # Add email_sent, email_sent_at, last_error to user_reminders if missing
    if "user_reminders" in tables:
        reminder_columns = {column["name"] for column in inspector.get_columns("user_reminders")}
        if "email_sent" not in reminder_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_reminders ADD COLUMN email_sent BOOLEAN DEFAULT 0"))
        if "email_sent_at" not in reminder_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_reminders ADD COLUMN email_sent_at DATETIME"))
        if "last_error" not in reminder_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_reminders ADD COLUMN last_error TEXT"))
        if "timezone" not in reminder_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_reminders ADD COLUMN timezone VARCHAR(64) DEFAULT 'Asia/Kolkata'"))



def _drop_email_unique_constraint(engine: Engine, inspector) -> None:
    """Remove the UNIQUE constraint from users.email if present.

    SQLite stores UNIQUE constraints as unique indexes.  We detect
    the index and, if it is the only thing enforcing uniqueness on
    email, rebuild the table without it.
    """
    indexes = inspector.get_indexes("users")
    email_unique = None
    for idx in indexes:
        if idx.get("column_names") == ["email"] and idx.get("unique", False):
            email_unique = idx
            break

    if email_unique is None:
        return  # no unique constraint to remove

    idx_name = email_unique["name"]
    logger.info("[Migration] Dropping UNIQUE constraint '%s' on users.email", idx_name)

    with engine.begin() as conn:
        # 1. Collect column definitions from the current table
        columns_info = inspector.get_columns("users")
        pk_columns = inspector.get_pk_constraint("users").get("constrained_columns", [])
        fks = inspector.get_foreign_keys("users")

        col_defs = []
        for col in columns_info:
            parts = [f"{col['name']} {col['type']}"]
            if col["name"] in pk_columns:
                parts.append("PRIMARY KEY")
            if not col.get("nullable", True):
                parts.append("NOT NULL")
            col_defs.append(" ".join(parts))

        create_cols = ", ".join(col_defs)

        # 2. Create temp table, copy, drop, rename
        conn.execute(text(f"CREATE TABLE users_new ({create_cols})"))
        conn.execute(text("INSERT INTO users_new SELECT * FROM users"))
        conn.execute(text("DROP TABLE users"))
        conn.execute(text("ALTER TABLE users_new RENAME TO users"))

        # 3. Recreate non-unique indexes
        for idx in indexes:
            if idx["name"] == idx_name:
                continue  # skip the unique one we're removing
            cols = ", ".join(idx["column_names"])
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx['name']} ON users ({cols})"))

        # 4. Recreate foreign keys
        for fk in fks:
            ref_cols = ", ".join(fk["referred_columns"])
            local_cols = ", ".join(fk["constrained_columns"])
            ref_table = fk["referred_table"]
            conn.execute(
                text(
                    f"ALTER TABLE users ADD CONSTRAINT {fk['name']} "
                    f"FOREIGN KEY ({local_cols}) REFERENCES {ref_table} ({ref_cols})"
                )
            )

    logger.info("[Migration] UNIQUE constraint on users.email removed successfully")


def reset_database(engine: Engine) -> None:
    """Drop all application data tables and recreate from models.

    Only runs when the RESEARCHOS_RESET_DB environment variable is set to "1".
    This ensures a completely fresh start with no legacy data.
    """
    import os
    if os.environ.get("RESEARCHOS_RESET_DB", "") != "1":
        return

    logger.info("[DB] RESEARCHOS_RESET_DB=1 — dropping and recreating all tables")
    from app.db.base import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
