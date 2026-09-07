# ResearchOS Architecture

## Overview

ResearchOS is an AI-powered research platform that turns an initial research idea into an evidence-backed roadmap, citation-aware notes, experiment plans, and supervisor review flows.

## Layers

1. Frontend
2. API
3. Domain services
4. AI orchestration
5. Retrieval and graph systems
6. Relational storage

## Design principles

- evidence-backed recommendations
- clear separation of concerns
- modular AI agent workflow
- clean API contracts
- secure authentication and authorization

## Reuse rationale

This project intentionally borrows proven patterns from the reference systems:

- session-based auth and route guards from Aura-AI-System
- ML orchestration and recommendation pipeline from the law-agent project
- modern API + service abstraction patterns from both projects

## Production guardrails

- all AI suggestions must be clearly flagged
- citations are required for strong claims
- no final roadmap without supervisor approval in enterprise mode

## Implementation status

The project has been initialized with:

- FastAPI backend skeleton
- JWT-ready auth layer
- service and orchestration stubs
- Next.js frontend shell
- AI agent and graph starter modules
- Docker and CI scaffolding
