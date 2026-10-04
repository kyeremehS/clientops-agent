# Architecture (scaffold)

## Stack

Backend: Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL.
Frontend: Next.js, TypeScript.
Agent/workflow: custom state machine, LLM abstraction, typed tools. No LangGraph yet.
Infra: Docker Compose, GitHub Actions.
Testing: pytest.

## Module map

- `backend/app/api/` — REST contract. Pydantic schemas in `schemas/` are the single source of truth.
- `backend/app/agents/research/`, `backend/app/agents/qualification/` — agent implementations.
- `backend/app/orchestrator/` — custom state machine, scheduling.
- `backend/app/policy/` — deterministic scope and safety checks, fail closed.
- `backend/app/tools/` — typed tool wrappers.
- `backend/app/evidence/` — observations, artifacts, findings, reports.
- `backend/app/db/` — SQLAlchemy session/base.
- `backend/app/llm/` — provider abstraction.
- `frontend/` — thin Next.js client, talks to backend only via API.
- `evaluation/` — cases + evaluators + `run.py`.

See `docs/decisions/` for ADRs.
