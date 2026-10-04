# AGENTS.md

## Setup

- Backend: `python -m venv .venv`, activate, `pip install -r backend/requirements.txt`.
- Frontend: `pnpm install` in `frontend/`.
- DB: `docker compose up db`.

## Conventions

- Scaffold first, implementation second. Do not add business logic in skeleton commit.
- Backend packages mirror `blackbox-agents`: `api`, `orchestrator`, `policy`, `agents`, `tools`, `evidence`, `schemas`, `db`, `llm`.
- Pydantic is the single source of truth for API contracts.
- Policy checks are deterministic and fail closed.
- Python 3.12+, line length 100, ruff + black.
- Frontend is a thin client; no business logic duplication.

## Workflow

- Branch per change after scaffold; no direct pushes to `main` except this initial scaffold.
- Run `pytest backend/tests -q` before every backend commit.
- Keep `docs/architecture.md` and `docs/decisions/` updated for structural choices.
