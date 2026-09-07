# ResearchOS

ResearchOS is an AI-powered research intelligence platform that converts a research idea into an evidence-backed roadmap with semantic retrieval, literature analysis, methodology generation, experiment planning, and supervisor review.

## Architecture summary

- Frontend: Next.js + React + TypeScript + Tailwind + shadcn/ui
- Backend: FastAPI + SQLAlchemy + Pydantic + JWT
- AI: LangChain + LlamaIndex + Gemini + embeddings + vector search
- Data: PostgreSQL + FAISS/ChromaDB + Neo4j
- Ops: Docker + GitHub Actions

## Project layout

```text
ResearchOS/
├── .github/
│   └── workflows/
├── ai/
│   ├── agents/
│   ├── pipelines/
│   ├── prompts/
│   └── models/
├── backend/
│   ├── app/
│   └── requirements.txt
├── database/
├── docs/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── infra/
│   └── docker/
├── knowledge_graph/
├── tests/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The default development database is SQLite at `backend/data/researchos.db` and is created automatically when the API starts. Redis, Neo4j, and external AI providers are not required for the local MVP.

On Windows, double-click `start-researchos.bat`, or run `start-backend.bat` and `start-frontend.bat` in separate terminals. The dependency report is available at `http://localhost:8000/health/dependencies`.

To use PostgreSQL, set `DATABASE_URL` before launching the backend. The included Docker Compose file provides PostgreSQL, Redis, Neo4j, the backend, and the frontend as an optional full stack.

### Docker

With Docker Desktop running:

```bash
docker compose up --build -d
```

Open `http://localhost:3000/workspace` for the UI and `http://localhost:8000/docs` for the API. The application also works without Docker using the Windows startup scripts above.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Key modules

- `backend/app/api/v1` – versioned REST API routes
- `backend/app/services` – domain logic and orchestration
- `backend/app/db` – SQLAlchemy setup and repositories
- `ai/agents` – specialized AI research agents
- `knowledge_graph` – Neo4j schema and graph queries
- `frontend/app` – next app routes and dashboard pages

## Evidence-backed AI rule

All research recommendations must be anchored in retrieved evidence, literature metadata, and explicit citations where available. AI recommendations should be clearly labeled as either:

- evidence-backed findings, or
- speculative AI-generated opportunities

## License

This project is created for research and product development workflows.
