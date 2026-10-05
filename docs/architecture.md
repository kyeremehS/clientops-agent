# Architecture (Slice 1)

Status: accepted

## Stack

Backend: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL.
Frontend: Next.js + TypeScript (thin client, approvals queue only).
Agent/workflow: custom state machine, OpenRouter LLM abstraction, typed tools.
Infra: Docker Compose (postgres only in Slice 1), GitHub Actions.
Testing: pytest + evaluation runner.

## Flow

```text
Next.js → FastAPI → Orchestrator (state machine) → Research/Qualification agents
  → Tools (web_search, website_fetch) + LLM (OpenRouter, pinned model)
  → Policy (deterministic) → Approval API → Slack worker → Postgres + Audit events
```

## Module map

- `backend/app/api/` — REST contract. Pydantic in `schemas/` is single source of truth.
- `backend/app/agents/research/`, `backend/app/agents/qualification/` — LLM judgment only.
- `backend/app/orchestrator/` — owns state transitions, retries, HITL wait, expiry.
- `backend/app/policy/` — deterministic reject/review, fail closed. Pure functions.
- `backend/app/tools/` — typed wrappers, Pydantic I/O. Slice 1: `web_search`, `website_fetch`, `slack_post`.
- `backend/app/llm/` — OpenRouter client + JSON-schema → Pydantic. Only place that calls the model.
- `backend/app/evidence/` — observations, artifacts, findings, content hashes.
- `backend/app/db/` — SQLAlchemy session/base + event chain.
- `frontend/` — approvals queue only. Never executes actions directly.
- `evaluation/` — 3 Slice 1 cases + `run.py`.

See `docs/decisions/` for ADRs and `docs/roadmap.md` for build order.
