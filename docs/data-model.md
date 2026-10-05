# Data model (Slice 1 — implemented in B1)

Status: accepted. Tables in `backend/app/db/models.py`, helpers in `events.py`.

## Tables

- `leads` — id (UUID PK), company (255, not null), website (1024), contact (1024),
  message (text), created_at (tz).
- `research_artifacts` — id, lead_id FK→leads (index, cascade), source_url (2048),
  content (text), content_hash (sha256 hex, 64), created_at.
- `qualifications` — id, lead_id FK unique (1-1), operational_pain / automation_plausibility /
  relevance / evidence_quality (int 0-3), supporting_evidence_ids (JSON list),
  summary (text), score (float, computed in code), created_at.
- `decisions` — id, lead_id FK unique, outcome (`REJECT` | `REVIEW`), reasons (JSON list).
- `approvals` — id, lead_id FK unique, status (`pending`/`approved`/`rejected`/`expired`),
  requested_at, expires_at (`requested_at + 24h`), decided_at (nullable).
- `actions` — id, lead_id FK unique, approval_id FK unique, idempotency_key (unique),
  channel_id, text, result, created_at.
- `audit_events` — event_id (UUID PK), lead_id FK→leads (index, cascade),
  event_type (64), timestamp, actor (default `system`), payload (JSON),
  previous_event_id (self-FK, nullable), content_hash (nullable). `run_id` = `str(lead_id)`.

## Relations

```text
Lead 1—N ResearchArtifact
Lead 1—1 Qualification → 1—1 Decision → 0—1 Approval → 0—1 Action
Lead 1—N AuditEvent (ordered by previous_event_id)
```

Invariants: every material claim links to ≥1 artifact; score computed in code,
never stored from LLM; expired approvals never link to an Action.
Chain writes go through `append_audit_event()` which sets `previous_event_id`
to the latest event for the lead.
