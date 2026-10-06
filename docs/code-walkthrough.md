# Code walkthrough — everything built through B4

Read this top to bottom. It explains every file we wrote, how the pieces connect,
and the patterns to reuse in B5–B6. Line counts are approximate as of `main` after B4.

## 1. The big picture

```text
Browser (/approvals) ──HTTP──▶ FastAPI ──▶ SQLAlchemy ──▶ PostgreSQL (prod) / SQLite (tests)
   thin UI only            validation +          tables +           data at rest
                           audit events          event chain
```

Two flows exist today (research → qualification → Slack come later):

```text
Flow A — intake:      POST /leads → Lead row + run.created event
                      POST /leads/{id}/approvals → Approval (pending, 24h) + approval.requested
Flow B — decision:    POST /approvals/{id}/approve|reject → re-validate → terminal state + event
```

Rule that shapes everything: **the UI never executes actions — it only records
decisions.** The backend re-validates every call (exists → pending → not expired),
so a stale button or a forged request cannot trigger anything.

## 2. Backend, module by module

### `backend/app/main.py` — wiring only

Creates the FastAPI app, mounts the leads router, registers a `lifespan` handler
that runs `Base.metadata.create_all()` once at startup (tables exist without
migrations for now; Alembic comes later). No business logic lives here.

### `backend/app/config.py` — env-only settings

A Pydantic `BaseSettings` class: `database_url`, `llm_provider`, `llm_model`
(`qwen/qwen3.8-27b:free`), `openrouter_api_key`, timeouts/retries/token caps,
all read from environment/`.env`. Nothing secret is hardcoded; tests override
`settings.database_url` with `monkeypatch` to point at throwaway SQLite files.

### `backend/app/db/` — persistence + audit chain (B1)

- **`base.py`** — `Base` (all models inherit it), `get_engine(url)`,
  `get_session_factory(url)`, and a `session_scope` context manager
  (commit on success, rollback on exception). No global session.
- **`models.py`** — seven tables, UUID primary keys:
  - `leads` — the inbound input: company, website, contact, message.
  - `research_artifacts` — one observation each: source URL, content,
    sha256 `content_hash`. (Written by research in a later brick.)
  - `qualifications` — the four LLM dimensions (0–3 each) plus the
    code-computed `score`. The LLM never writes a 0–100 number.
  - `decisions` — policy output: `REJECT` | `REVIEW` + reasons list.
  - `approvals` — `status` (pending/approved/rejected/expired),
    `requested_at`, `expires_at` (= requested + 24h), `decided_at`.
  - `actions` — the executed external effect: idempotency key (unique),
    channel, text, result. (Written by B5 Slack worker.)
  - `audit_events` — the immutable chain: `event_id`, `lead_id` (`run_id`
    is a property returning `str(lead_id)`), `event_type`, `timestamp`,
    `actor` (`system` or `human`), `payload` (JSON), `previous_event_id`
    (self-reference to the prior event), optional `content_hash`.
- **`events.py`** — the only way to write audit events:
  `append_audit_event(session, lead_id, event_type, ...)` looks up the latest
  event for the lead and links `previous_event_id` to it, so history is a
  tamper-evident chain. Also `approval_expiry()` (+24h), `is_approval_expired()`
  (normalizes naive vs aware datetimes — SQLite returns naive, Postgres aware),
  and `sha256_hex()`.

### `backend/app/schemas/` — the API contract (Pydantic = single source of truth)

- **`qualification.py`** — `QualificationResult`: the four 0–3 dimensions,
  `supporting_evidence_ids`, `summary`. `extra="forbid"` means if the model
  invents a field like `fit_score_100`, validation fails closed instead of
  silently passing it through.
- **`leads.py`** — `LeadCreate` (input), `LeadRead` and `ApprovalRead`
  (outputs). FastAPI uses these as `response_model`, so extra internals
  never leak over HTTP.

### `backend/app/policy/rules.py` — deterministic judgment (B3)

Two **pure functions** (no I/O, no DB, no LLM — trivially testable):

- `score(dims)` → `sum / 12 * 100`. Raises `ValueError` on missing,
  out-of-range, or non-int input (fail closed on bad data).
- `decide(dims, supporting_count)` → `("REVIEW" | "REJECT", reasons)`:
  `evidence_quality <= 1` → REVIEW (weak evidence escalates, never rejects);
  fewer than 2 supporting items → REVIEW; `score < 40` → REJECT; else REVIEW.
  Note there is no "approve" outcome — **nothing is ever auto-allowed**.

### `backend/app/llm/` — the only place that calls the model (B2)

- **`client.py`** — `OpenRouterClient.complete_json(messages, response_model)`:
  sends `response_format` with a JSON-schema derived from the Pydantic model,
  parses the reply, validates it, returns `(parsed_model, usage)`.
  Guardrails: per-request timeout, retry-with-backoff **only** on 429/5xx/
  timeouts (a 400 or bad output fails immediately — retrying won't fix it),
  `max_tokens` cap plus an optional total-token budget (`LLMBudgetExceededError`),
  and structured logging of model/latency/token counts **without** prompt or
  response bodies (they may contain lead PII).
- **`errors.py`** — seven typed exceptions (`LLMTimeoutError`,
  `LLMRateLimitError`, `LLMValidationError`, …). Callers match on type,
  never on message text.

### `backend/app/api/` — HTTP surface (B4)

- **`deps.py`** — `get_session()`: yields one request-scoped session
  (commit/rollback/close handled). Tests swap it via FastAPI
  `dependency_overrides`, so tests never touch the real database.
- **`leads.py`** — the router:
  - `POST /leads` (201): insert Lead + `run.created` event.
  - `GET /leads/{id}`: detail or `404 lead_not_found`.
  - `POST /leads/{id}/approvals` (201): guard against duplicate/approved
    (`409 wrong_state`), then create a pending approval + `approval.requested`.
  - `GET /approvals/pending`: the queue, oldest first.
  - `POST /approvals/{id}/approve|reject`: `_require_actionable()` checks
    pending-ness then expiry. A late call marks the approval `expired`,
    emits `approval.expired`, and returns `409 approval_expired`.
    Success emits `approval.approved|rejected` with `actor="human"`.

### Stubs (shape of what's coming)

`orchestrator/` (state machine), `agents/research|qualification`,
`tools/` (`web_search`, `website_fetch`, `slack_post`), `evidence/` each hold
an `__init__.py` describing their future job. B5 fills the Slack tool +
action worker; later bricks fill agents/orchestrator.

## 3. Frontend (`frontend/`)

A thin Next.js App Router client — it displays state and calls the API,
nothing more:

- **`lib/api.ts`** — typed `fetch` wrapper (`Approval` type, `pendingApprovals`,
  `approve`, `reject`). Base URL from `NEXT_PUBLIC_API_BASE_URL`, default
  `http://localhost:8000`. Non-OK responses throw the backend's `detail`
  string so the UI can show `approval_expired` verbatim.
- **`app/approvals/page.tsx`** — server component (`force-dynamic`, no caching)
  that loads the pending queue.
- **`app/approvals/approval-card.tsx`** — client component per approval:
  Approve/Reject buttons, local status update, error display. Even if the
  button is stale, the backend's re-validation is the real guard.
- **`app/page.tsx` / `layout.tsx` / `next.config.mjs`** — home page, root
  layout, default config. Verified with `pnpm build`.

## 4. Tests (`backend/tests/`)

One fixture pattern everywhere: **isolated SQLite file per test**
(`tmp_path`), `Base.metadata.create_all`, dependency override, `TestClient`.
No live Postgres, no API keys needed (the one live OpenRouter check skips
without `OPENROUTER_API_KEY`).

- **`test_health.py`** — `/health` returns `{"status":"ok"}` (wiring smoke test).
- **`test_db_events.py`** (B1) — event chain links `previous_event_id`
  correctly; artifact hash is a 64-char sha256; expiry math is exactly 24h;
  25h-old approval reads expired, fresh one doesn't.
- **`test_llm_client.py`** (B2) — mocked `httpx.MockTransport`: success parses
  and validates; 429 retried then succeeds; 429-exhausted → `LLMRateLimitError`;
  400 never retried; invented `fit_score_100` field and out-of-range dimension
  → `LLMValidationError`; empty key → `LLMConfigError`; timeout →
  `LLMTimeoutError`; over-budget → `LLMBudgetExceededError`.
- **`test_policy.py`** (B3) — score math (0/66.7/100), no slot for a model-made
  score, eq 0/1 → REVIEW, single item → REVIEW, low-fit → REJECT,
  sufficient → REVIEW (never auto-allow), bad input raises.
- **`test_api_approvals.py`** (B4) — create/get lead, 404s, approve/reject happy
  paths, double-approve 409, duplicate-request 409, backdated-expiry 409 plus
  terminal `expired` status. (SQLite stores UUID/Datetime slightly differently
  than Postgres — the tests taught us to pass real `UUID` objects and normalize
  naive datetimes; see `events._as_aware`.)

## 5. Config, infra, packaging

- **`docker-compose.yml`** — Postgres 16 only (`db` service, `clientops` DB,
  `pgdata` volume). Backend/frontend run locally in Slice 1.
- **`.env.example`** — every env var with empty secrets:
  `DATABASE_URL`, ports, `LLM_PROVIDER/MODEL/OPENROUTER_API_KEY`,
  `SLACK_BOT_TOKEN/SLACK_CHANNEL_ID`, `NEXT_PUBLIC_API_BASE_URL`.
- **`backend/requirements.txt` + `pyproject.toml`** — pinned ranges,
  `pytest` config (`pythonpath` so `app.*` imports work from repo root),
  ruff/black line-length 100. SQLAlchemy is pinned to `>=2.0,<2.1`
  (see `decisions/0004`: 2.1.3's DLL is blocked by Application Control on the
  dev machine, 2.0.36 predates Python 3.14 typing — 2.0.54 verified).
- **`.github/workflows/ci.yml`** — on push/PR: install + `pytest`, plus a
  conventions job (required docs exist).
- **`frontend/package.json` + `pnpm-lock.yaml`** — Next 14 / React 18 /
  TypeScript 5, lockfile committed.

## 6. Docs map

`product.md` (what/why) → `architecture.md` (module map) → `workflow.md`
(states) → `data-model.md` (tables) → `agents.md` (boundaries) → `policy.md`
(locked rules) → `evaluation.md` (3 cases + metrics) → `api.md`, `tools.md`,
`deployment.md` (filled just-in-time per brick). `roadmap.md` tracks bricks
D0–B4 done; `decisions/0001–0005` record the irreversible calls;
`runbooks/` cover local dev, testing, troubleshooting.

## 7. Patterns to reuse in B5–B6

1. Pure functions for decisions; I/O at the edges (`policy/rules.py`).
2. Only one module touches each external system (`llm/`, and soon Slack).
3. Typed errors matched by type, never message text.
4. Re-validate at execution time, not just at request time (approve endpoint).
5. Idempotency keys on anything that writes externally (already in `actions` table).
6. Log counts/latencies, never bodies or secrets.
7. Fail closed: unknown state, bad input, expired approval → refuse with a code.

## 8. Try it yourself

```powershell
# Backend API end to end (needs DB from `docker compose up db`)
uvicorn app.main:app --reload   # from backend/
curl -X POST localhost:8000/leads -H "Content-Type: application/json" `
  -d '{"company":"Acme Logistics","website":"https://acme.test","message":"Hi"}'
# → copy id → POST /leads/{id}/approvals → POST /approvals/{aid}/approve
# Queue UI:
cd frontend; pnpm install; pnpm dev   # open /approvals, needs backend running
```
