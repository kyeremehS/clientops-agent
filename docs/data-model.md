# Data model (Slice 1 — names + relations)

Status: stub — columns and migrations land in `feat/db-events`.

## Entities

- `Lead` — inbound input: company, website, contact, message. 1:N with artifacts.
- `ResearchArtifact` — one observation: source URL, fetched content, content_hash.
- `Qualification` — LLM dimensions + code-computed score (see `policy.md`).
- `Decision` — policy output: REJECT | REVIEW + reasons.
- `Approval` — for REVIEW: requested_at, expires_at (24h), status pending/approved/rejected/expired.
- `Action` — approved external effect: Slack post + idempotency key + result.
- `AuditEvent` — immutable chain: event_id, run_id, event_type, timestamp, actor,
  payload, previous_event_id, content_hash (on artifacts).

## Relations

```text
Lead 1—N ResearchArtifact
Lead 1—1 Qualification → 1—1 Decision → 0—1 Approval → 0—1 Action
Lead 1—N AuditEvent (ordered by previous_event_id)
```

Invariants: every material claim links to ≥1 artifact; score computed in code,
never stored from LLM; expired approvals never link to an Action.
