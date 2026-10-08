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
- Always merge the branch to `main` and delete it locally + on origin after merge.
- Run `pytest backend/tests -q` before every backend commit.
- Keep `docs/architecture.md` and `docs/decisions/` updated for structural choices.
- Docs are just-in-time: update the corresponding doc in the same PR as code.
- Track progress in `docs/roadmap.md` — check a box only when its done-when passes.
- Commits are short: `<type>(<scope>): <what changed>`, ~50 chars, no body
  unless the why is non-obvious. Types: feat, fix, chore, docs, test, refactor.
