# ResearchOS Implementation Plan

## Phase 0: Audit Summary

### Current architecture

- Next.js, React, TypeScript, and Tailwind frontend.
- FastAPI, SQLAlchemy, Pydantic, and JWT backend.
- SQLite local development database with PostgreSQL configuration.
- Top-level AI agent and pipeline packages.
- Docker Compose services for the app and optional infrastructure.

### Implemented features

- User registration, login, JWT authentication, and `/auth/me`.
- Owner-scoped projects, research ideas, and persisted research plans.
- Paper CRUD, JSON import, owner-scoped deterministic search.
- Supervisor feedback persistence and owner notifications.
- Notification listing and mark-as-read behavior.
- Workspace UI for authentication, projects, papers, search, and notifications.
- Backend tests for the implemented workflows.

### Broken or incomplete features

- AI agents and research services are deterministic placeholders, not local model/RAG implementations.
- Paper upload, text extraction, embeddings, vector persistence, and semantic retrieval are not implemented.
- The root dashboard and supervisor dashboard are mostly static.
- Redis and Neo4j are configured but not used by the application.
- PostgreSQL schema migrations are absent.
- Docker health checks and reliable service startup ordering are incomplete.
- The application has no dependency health endpoint or Windows startup scripts.

### External and local dependencies

- Core runtime can use SQLite and the local deterministic engine without internet access.
- LangChain, LlamaIndex, sentence-transformers, FAISS, Chroma, Redis, Neo4j, and external LLM keys are optional future integrations but are currently listed in backend requirements.
- Docker Desktop is optional for the basic SQLite workflow and required only for the full Compose stack.

### Duplicate or risky areas

- Duplicate project repository modules exist; the active implementation is under `backend/app/db/repositories`.
- Legacy demo dependencies in `backend/app/core/deps.py` return a fixed user and must not be used by routes.
- CORS is permissive for development and must be configurable for production.
- Existing databases need migrations when model columns change; `create_all` only supports fresh local SQLite databases.

## Expanded implementation plan

### P0: Local application baseline

1. Make SQLite data paths and local configuration explicit.
2. Add truthful `/health/dependencies` reporting.
3. Add Windows CMD and PowerShell startup scripts.
4. Remove placeholder authentication dependencies from the active surface.
5. Keep projects, ideas, papers, plans, supervisor review, and notifications working offline.
6. Add migration-safe schema evolution before introducing follow-up data.

### P1: Follow-up and communication foundation

1. Add owner-scoped research tasks, follow-ups, and reminders.
2. Add explicit notification preferences and communication consent.
3. Add in-app, development email, and development voice provider abstractions.
4. Add append-only communication logs with retryable delivery status.
5. Add a lightweight due-item executor that is safe to invoke from a local process.
6. Integrate follow-ups into the existing workspace without changing current research APIs.

### P2: Legal research foundation

1. Add a separate law route namespace and owner-scoped legal matters.
2. Store legal source provenance and distinguish fact, source, inference, and suggestion.
3. Add local legal source ingestion/search without fabricating authorities or citations.
4. Add legal follow-up tasks using the shared follow-up primitives.

### P3: Local evidence intelligence

1. Add local file upload for PDF, TXT, Markdown, and DOCX where available.
2. Extract and persist document text and metadata.
3. Add a local library provider and persistent lightweight vector index.
4. Add grounded paper summaries, comparison, and potential-gap records.
5. Clearly label deterministic fallback output as `LOCAL DEMO ANALYSIS`.

### P4: Research intelligence

1. Add local dataset and tool catalogues.
2. Add methodology and experiment entities and APIs.
3. Add local NetworkX/JSON knowledge graph storage.
4. Add editable roadmap milestones and dependencies.

### P5: Collaboration UI

1. Add authenticated supervisor dashboard and review screens.
2. Add project detail, paper viewer, research notes, and profile screens.
3. Add navigation and consistent loading, empty, and error states.

### P6: Reliability and release

1. Add Alembic migrations for PostgreSQL.
2. Add Docker health checks and startup readiness.
3. Expand CI with tests, typecheck, lint, and build.
4. Add end-to-end browser coverage.
5. Harden CORS, secrets, file validation, rate limits, and production configuration.

## Safety constraints

- Never alter or reset existing user records.
- New phone communication is opt-in only and uses a mock provider by default.
- Development email and voice providers log delivery attempts; they never claim external delivery.
- Legal results must retain provenance and must never invent authorities, quotations, or citations.
- Existing authentication, paper discovery, research analysis, and API response contracts remain compatible.

## Current acceptance target

A fresh Windows checkout must support:

`install dependencies -> start backend -> SQLite initializes -> register -> create project -> add idea -> generate plan -> add/search paper -> receive notification`

All implemented behavior must be executed and tested before the project is described as complete.
