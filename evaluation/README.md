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

## Live eval (C4, manual)

- `evaluation/live_eval.py` + `evaluation/live_cases/*.json`: real companies
  through the real pipeline (live search + live LLM + real websites) on
  scratch databases. 6 cases: strong-fit (2), weak-fit (2), thin-evidence
  (1), hostile-input (1).
- **The assertion that matters is relative, not absolute.** Per-case fit
  bands are hand-tuned and generalize poorly (the Russ & Daughters ceiling
  was moved from 40 to 60 after observing a 50 — recorded honestly in its
  `expectation_note`). The discriminating check is `check_ordering`:
  the mean fit of `strong` cases must beat the mean fit of `weak` cases by
  >= 15 points. Score bands drift with the web and the model; the ordering
  survives both.
- `role` = strong | weak | thin | mixed. `expectation_basis` = blind (prior
  registered before any run) | calibrated (adjusted after a run, and said
  so). Prefer blind for new cases; a contradicted prior is recorded as a
  wrong prior, not fixed by moving the threshold. `mixed` asserts gate +
  grounding only (no score band) and stays out of the ordering check.
- `expected_outcome` may be a list — both escalating outcomes are correct
  for a weak-signal company. Pinned: `LLM_PROVIDER=openai` + `gpt-5-mini`
  (reasoning model: cap is `max_completion_tokens`, budget 4000 because
  reasoning eats most of the completion).
- Invariants, which do generalize fully: `actions == 0` (human gate never
  bypassed), every cited URL appears in the fetched evidence, approval
  present when required, hostile input never auto-acts.
- This is a regression smoke gate on a handful of companies, **not** a
  quality benchmark. A mismatch exits nonzero for human triage — the live
  web shifts, so results are evidence, never a gate.
