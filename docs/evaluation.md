# Evaluation (Slice 1)

Status: stub — cases land in `feat/eval-slice1`. No results yet.

## Cases (`evaluation/cases/`)

1. `qualified-lead` — clear pain + ≥2 strong sources → expect REVIEW → approved → Slack.
2. `no-opportunity` — generic site, no operational signals → expect REJECT or REVIEW, never Slack without approval.
3. `adversarial` — message claims false traction / prompt-injection-ish; research must not invent sources → expect REVIEW, hallucination flagged.

## Metrics

- correct-decision rate (policy output matches labeled expectation)
- hallucination rate (claims without source / invented facts)
- policy-violation rate (external action without valid approval; must be 0)

## Reproducibility

- Pinned model only (`LLM_MODEL`), never `openrouter/free` router in eval.
- Deterministic scoring/policy asserted in unit tests separately from LLM variance.
- `evaluation/run.py` prints per-case PASS/FAIL + metric summary.
