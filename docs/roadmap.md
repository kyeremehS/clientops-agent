# Roadmap — Slice 1 (progress tracker)

Single source for "where are we?". Check a box only when its `done-when` passes.
One brick at a time; docs just-in-time per box.

- [x] D0 scaffold — skeleton + conventions on `main` (`bbdd86a`)
- [x] D1 docs-settled (this branch) — thin specs in `docs/`, no code
  - done-when: `python -m pytest backend/tests -q` passes, all links in `docs/` resolve
- [x] B1 db-events — SQLAlchemy models + audit event chain + approval expiry
  - docs: `docs/data-model.md`, `docs/decisions/0004-sqlalchemy-2.0-pure-python.md`
  - done-when: `python -m pytest backend/tests -q` incl. event-chain + expiry tests
- [x] B2 llm-openrouter — OpenRouter client, pinned `qwen/qwen3.8-27b:free`, JSON-schema → Pydantic
  - docs: `docs/agents.md`, `docs/decisions/0005-agents-honestly-guidance.md`
  - done-when: mocked guardrail tests pass; live structured-output check runs with key
- [x] B3 scoring-policy — pure `score(dims)` + `decide(...)` + unit tests
  - docs: `docs/policy.md` (already locked; no change needed)
  - done-when: `eq<=1→REVIEW`, `count<2→REVIEW`, `score<40→REJECT` tests pass
- [x] B4 api-approvals-ui — endpoints + re-validation + minimal Next.js queue
  - docs: `docs/api.md` (filled)
  - done-when: approve/reject happy + expired/late-approve `409` paths tested, `pnpm build` passes
- [x] B5 slack-audit — idempotent `chat.postMessage` to test `#sales-leads` + audit write
  - docs: `docs/tools.md`, `docs/deployment.md`, `docs/api.md` (execute endpoint)
  - done-when: retry + idempotency + audit-chain tests pass (mocked Slack)
- [x] B6 eval-slice1 — 3 cases in `evaluation/cases/` + `run.py` summary
  - docs: `docs/evaluation.md` (filled)
  - done-when: `python evaluation/run.py` reports 3/3 + 0 policy violations

Slice 1 complete: D0, D1, B1–B6.

## Slice 2 — close the loop (in progress)

- [x] C1 research-tools — SearchProvider protocol + Parallel/Tavily/Serper + mock + first-party fetch
  - docs: `docs/tools.md` (filled), `docs/decisions/0006-research-search-providers.md`
  - done-when: mocked adapter/fetch tests pass; `evaluation/compare_search.py` runs
- [x] C1b search-eval-harness — deterministic comparison runner (objectives dataset + persisted runs + overlap metrics)
  - docs: `evaluation/README.md` (filled)
  - done-when: mocked harness tests pass; one live `--limit 1` run persisted to `evaluation/runs/`
- [ ] C2 agents — research + qualification prompts writing artifact/qualification rows
- [ ] C3 orchestrator + wiring — end-to-end run pipeline, DB-backed state machine
- [ ] C4 live eval — eval cases through the real pipeline, recorded results
- [ ] C5 hardening — Alembic, API auth, budgets
- [ ] C6 breadth — CRM/email actions, more sources
- [ ] C7 demo polish — README demo, frontend run-detail view
