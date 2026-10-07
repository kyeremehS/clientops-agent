# Evaluation

Slice 1 gate: `python evaluation/run.py` from the repo root.

- `cases/*.json` — 3 labeled cases (qualified, no-opportunity, adversarial).
- `evaluators/checks.py` — decision / grounding / no-auto-action checks.
- `run.py` — loads cases, validates against the Pydantic contract, runs
  score + decide, prints per-case PASS/FAIL + metric summary, exits nonzero
  on any failure or policy violation.

Provider comparison (informational, never gated):
`python evaluation/compare_search.py` from the repo root. Same objectives
against every keyed provider (keys from env, root `.env` fallback), prints
latency / excerpt volume / cost. Relevance judgment is human — record the
verdict in `docs/decisions/0006-research-search-providers.md` before
changing the default.
