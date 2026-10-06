# Evaluation (Slice 1 — implemented in B6)

Status: accepted. Deterministic spine; no API keys needed.

## Cases (`evaluation/cases/*.json`)

1. `qualified-lead` — clear pain, 3 strong sources, dims 2/2/2/2 → fit 66.7 →
   REVIEW. Full chain to approved → Slack is the demo path.
2. `no-opportunity` — brochure site, dims 1/0/1/2 → fit 33.3 → REJECT.
   Proves the system says no with evidence.
3. `adversarial` — inflated "10M orders" claim citing nonexistent `c99`,
   eq=1 → REVIEW via weak-evidence escalation. The ungrounded ref is
   **flagged, not missed** (`expected_grounded: false`).

## Checks (`evaluation/evaluators/checks.py`)

- `check_decision` — policy outcome matches the labeled expectation.
- `check_grounding` — every claim ref and supporting id names a real artifact.
- `check_no_auto_action` — outcome is always REJECT or REVIEW, never an
  auto-allow. Violations must be 0.

## Running

```powershell
python evaluation/run.py   # from repo root → 3/3 PASS + metric summary, exit 0
```

## Reproducibility

- Pinned model only (`LLM_MODEL`), never `openrouter/free` router in eval.
- Deterministic scoring/policy asserted in unit tests separately from LLM variance.
- Live-model qualification checks are opt-in (`test_llm_client.py` live test),
  never part of the 3/3 gate.
