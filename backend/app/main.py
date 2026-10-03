import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from app.api.v1.routes import (
    auth,
    communications,
    evidence_sessions,
    followups,
    notifications,
    paper_drafts,
    papers,
    projects,
    references,
    reminders,
    research,
    research_papers,
    supervisor,
)
from app.core.config import settings
from app.db.base import Base
from app.db.migrations import reset_database, upgrade_sqlite_schema
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Log email configuration on startup (no secrets — NEVER log passwords)
    env_file_path = settings.model_config.get("env_file", "(unknown)")
    logger.warning(
        "[Startup] Config file: %s",
        env_file_path,
    )
    provider = settings.email_provider.strip().lower() if settings.email_provider else "brevo"
    if provider == "brevo":
        from app.services.email_service import _resolve_brevo_sender
        sender, sender_err = _resolve_brevo_sender()
        if sender_err:
            logger.error("[Startup] ⚠ Brevo configuration error: %s", sender_err)
        else:
            logger.info(
                "[Startup] Email provider: Brevo | Sender: %s <%s> | API Key configured: %s",
                sender.get("name"),
                sender.get("email"),
                "yes" if bool(settings.brevo_api_key) else "NO — NOT SET",
            )
    elif provider == "resend":
        from app.services.email_service import _resolve_resend_from
        from_addr, from_err = _resolve_resend_from()
        if from_err:
            logger.error("[Startup] ⚠ Resend configuration error: %s", from_err)
        else:
            logger.info(
                "[Startup] Email provider: Resend | Sender: %s | API Key configured: %s",
                from_addr,
                "yes" if bool(settings.resend_api_key) else "NO — NOT SET",
            )
    elif provider == "smtp":
        logger.warning(
            "[Startup] Email provider: %s | SMTP host: %s | SMTP port: %s | "
            "SMTP username: %s | SMTP from: %s | SMTP password set: %s",
            settings.email_provider or "(not set)",
            settings.smtp_host or "(not set)",
            settings.smtp_port,
            settings.smtp_username or "(not set)",
            settings.smtp_from or settings.email_from,
            "yes" if settings.smtp_password else "NO — NOT SET",
        )
        issues = []
        if not settings.smtp_host or not settings.smtp_host.strip():
            issues.append("SMTP_HOST")
        if not settings.smtp_username or not settings.smtp_username.strip():
            issues.append("SMTP_USERNAME")
        if not settings.smtp_password or not settings.smtp_password.strip():
            issues.append("SMTP_PASSWORD")
        if not (settings.smtp_from and settings.smtp_from.strip()):
            issues.append("SMTP_FROM (will use EMAIL_FROM as fallback)")
        if issues:
            logger.warning(
                "[Startup] ⚠ EMAIL_PROVIDER=smtp but missing: %s. "
                "OTP emails will fail. Edit backend/.env and restart.",
                ", ".join(issues),
            )
        else:
            logger.warning(
                "[Startup] ✓ SMTP fully configured."
            )
    else:
        logger.info("[Startup] Email provider: console (development mode)")

    # Create database tables automatically
    if settings.database_url.startswith("sqlite"):
        reset_database(engine)
        Base.metadata.create_all(bind=engine)
        upgrade_sqlite_schema(engine)
    else:
        Base.metadata.create_all(bind=engine)

    # Create required directories
    Path(settings.vector_store_path).mkdir(
        parents=True,
        exist_ok=True,
    )

    Path(settings.upload_dir).mkdir(
        parents=True,
        exist_ok=True,
    )

    # Start Reminder Agent background task (checks due reminders every 5s)
    reminder_agent_stop = asyncio.Event()

    async def _reminder_agent_loop():
        from app.db.session import SessionLocal
        from app.services.reminder_agent import process_due_reminders, recover_stale_reminders

        logger.info("[Startup] Reminder Agent background worker started")
        # On startup, recover any reminders that were interrupted in 'processing' state
        try:
            with SessionLocal() as db:
                recover_stale_reminders(db)
        except Exception as exc:
            logger.error("[ReminderAgent] Startup recovery error: %s", exc)

        while not reminder_agent_stop.is_set():
            try:
                with SessionLocal() as db:
                    process_due_reminders(db)
            except Exception as exc:
                logger.error("[ReminderAgent] Background check error: %s", exc)
            try:
                await asyncio.wait_for(reminder_agent_stop.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass

    reminder_task = asyncio.create_task(_reminder_agent_loop())

    try:
        yield
    finally:
        reminder_agent_stop.set()
        reminder_task.cancel()
        try:
            await reminder_task
        except (asyncio.CancelledError, Exception):
            pass


app = FastAPI(
    title="ResearchOS API",
    version="0.1.0",
    description="AI Research Intelligence Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.ngrok.*|.*\.vercel\.app)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def fix_proxy_redirect_location(request: Request, call_next):
    response = await call_next(request)
    location = response.headers.get("location")
    if location and ("127.0.0.1:8000" in location or "localhost:8000" in location):
        from urllib.parse import urlparse
        parsed = urlparse(location)
        relative_location = parsed.path
        if parsed.query:
            relative_location += f"?{parsed.query}"
        response.headers["location"] = relative_location
    return response


# ---------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["auth"],
)

app.include_router(
    projects.router,
    prefix="/api/v1/projects",
    tags=["projects"],
)

app.include_router(
    research.router,
    prefix="/api/v1/research",
    tags=["research"],
)

app.include_router(
    papers.router,
    prefix="/api/v1/papers",
    tags=["papers"],
)

app.include_router(
    notifications.router,
    prefix="/api/v1/notifications",
    tags=["notifications"],
)

app.include_router(
    supervisor.router,
    prefix="/api/v1/supervisor",
    tags=["supervisor"],
)

app.include_router(
    followups.router,
    prefix="/api/v1/followups",
    tags=["followups"],
)

app.include_router(
    communications.router,
    prefix="/api/v1/communications",
    tags=["communications"],
)

app.include_router(
    reminders.router,
    prefix="/api/v1/reminders",
    tags=["reminders"],
)

app.include_router(
    research_papers.router,
    prefix="/api/v1/research-papers",
    tags=["research-papers"],
)

app.include_router(
    references.router,
    prefix="/api/v1/references",
    tags=["references"],
)

app.include_router(
    paper_drafts.router,
    prefix="/api/v1/paper-drafts",
    tags=["paper-drafts"],
)

app.include_router(
    evidence_sessions.router,
    prefix="/api/v1/evidence-sessions",
    tags=["evidence-sessions"],
)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "researchos-backend",
    }


# ---------------------------------------------------------
# DEPENDENCY HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health/dependencies")
def dependency_health() -> dict[str, object]:
    checks: dict[str, dict[str, str]] = {}

    # Database
    try:
        with engine.connect():
            checks["database"] = {
                "status": "ok",
                "detail": engine.dialect.name,
            }
    except Exception as exc:
        checks["database"] = {
            "status": "offline",
            "detail": str(exc),
        }

    # Storage directories
    for name, configured_path in (
        ("vector_store", settings.vector_store_path),
        ("file_storage", settings.upload_dir),
    ):
        path = Path(configured_path)

        checks[name] = {
            "status": (
                "ok"
                if path.exists() and path.is_dir()
                else "offline"
            ),
            "detail": str(path),
        }

    # AI provider
    checks["ai_provider"] = {
        "status": (
            "ready"
            if settings.ai_provider == "local"
            else "offline"
        ),
        "detail": settings.ai_provider,
    }

    overall_status = (
        "ok"
        if all(
            item["status"] in {"ok", "ready"}
            for item in checks.values()
        )
        else "degraded"
    )

    return {
        "status": overall_status,
        "checks": checks,
    }


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "ResearchOS backend is running",
        "environment": settings.environment,
    }
