# Evaluation

Slice 1 gate: `python evaluation/run.py` from the repo root.

- `cases/*.json` — 3 labeled cases (qualified, no-opportunity, adversarial).
- `evaluators/checks.py` — decision / grounding / no-auto-action checks.
- `run.py` — loads cases, validates against the Pydantic contract, runs
  score + decide, prints per-case PASS/FAIL + metric summary, exits nonzero
  on any failure or policy violation.

Provider comparison (informational, never gated):
`python evaluation/compare_search.py` from the repo root.

- `objectives.json` — 18 objectives (profile / pain-signals / news × 6 subjects).
- `search_eval/` — loader, runner (every objective × every keyed provider),
  deterministic metrics (latency, errors, excerpt volume, dup URLs,
  cross-provider URL overlap), Markdown report builder. No LLM, no network
  in metrics — fully reproducible from `raw_results.json`.
- `runs/<utc-ts>/{raw_results.json,metrics.json,report.md}` — per-run
  artifacts, gitignored (evidence stays local; only ADR verdicts commit).
- Flags: `--providers parallel,tavily --limit 2` for cheap smoke runs.
- Keys from env, root `.env` fallback; unkeyed providers skipped, one
  provider's failure never stops the run.

Relevance judgment is human — read `report.md`, record the verdict in
`docs/decisions/0006-research-search-providers.md` before changing the default.

Live pipeline eval (manual runs only — never CI, costs real credits):
`python evaluation/live_eval.py` from the repo root.

- `live_cases/*.json` — 3 real-company cases with loose expectations
  (outcome, fit floor/ceiling, approval presence, no external action,
  grounded citations). Fictional `.test` leads stay in `cases/` for the
  deterministic gate; live needs searchable companies.
- Runs each case through the real pipeline on scratch SQLite files and
  persists `runs/live-<ts>/{<case>.json,summary.json}` (gitignored).
- Loose by design: the live web shifts, so a mismatch exits nonzero for
  human triage, never as a build failure. A boring company must score low
  (fit ceiling); weak evidence escalates to REVIEW by policy (REJECT needs
  sufficient evidence, so thin-evidence cases never expect REJECT).
