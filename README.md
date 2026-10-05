# clientops-agent

Turns an inbound lead into an evidence-backed, auditable operational decision:
research → evidence → opportunity assessment → deterministic policy →
human approval → Slack action → audit.

> Model proposes. App scores + applies policy. Human authorizes the external action.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
docker compose up db
python -m pytest backend/tests -q
```

Copy `.env.example` to `.env` (never commit tokens).

## Example workflow (Slice 1)

```text
Inbound lead → Research (web + website) → Qualification (LLM dims, code scores)
  → Policy (REJECT/REVIEW) → Frontend approvals queue → Slack #sales-leads → Audit chain
```

## Safety / guardrails

- Deterministic policy, fail closed. Fit `<40` → REJECT; weak evidence (`≤1`) → REVIEW.
- Zero automatic external action. Approvals expire after 24h (`409 approval_expired`).

## Documentation

- [Product](docs/product.md) · [Architecture](docs/architecture.md) · [Workflow](docs/workflow.md)
- [Agents](docs/agents.md) · [Policy](docs/policy.md) · [Evaluation](docs/evaluation.md)
- [Roadmap / progress](docs/roadmap.md) · [Runbooks](docs/runbooks/local-development.md)
- Decisions: [0001](docs/decisions/0001-no-langgraph-yet.md), [0002](docs/decisions/0002-custom-state-machine.md), [0003](docs/decisions/0003-slice1-locks.md)

Demo and evaluation results: TBD (land with Slice 1 build).
