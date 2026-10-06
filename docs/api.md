# API (Slice 1 — implemented in B4)

Status: accepted. Pydantic schemas in `backend/app/schemas/` are the contract.

## Endpoints

- `GET /health` → `{"status":"ok"}`.
- `POST /leads` (201) — create lead from `{company, website, contact, message}`,
  emits `run.created`. Returns `LeadRead`.
- `GET /leads/{id}` — lead detail. Unknown → `404 lead_not_found`.
- `POST /leads/{id}/approvals` (201) — request approval for a lead.
  Emits `approval.requested`. Second pending (or post-approved) request → `409 wrong_state`.
- `GET /approvals/pending` — approvals queue for the frontend, oldest first.
- `POST /approvals/{id}/approve` — human approve. Re-validates: exists (`404`),
  still `pending` (`409 wrong_state`), not expired. Late → marks approval
  `expired`, emits `approval.expired`, returns `409 approval_expired`.
  Success emits `approval.approved` with `actor="human"`.
- `POST /approvals/{id}/reject` — same guards; success emits `approval.rejected`.
- `POST /approvals/{id}/execute` (B5) — send the approved Slack message exactly
  once. Requires `approved` status (`409 wrong_state` otherwise). Existing
  `Action` row → returned without re-sending. Slack failure → `502 slack_failed`,
  no `Action` row, `action.failed` event; safe to retry. Success emits
  `action.started` then `action.succeeded` and returns `ActionRead`.

## Error behaviour

- `404 lead_not_found` / `404 approval_not_found`.
- `409 wrong_state` — approval already decided, or duplicate request.
- `409 approval_expired` — past `expires_at`; approval is terminally `expired`.
- Pydantic validation failures → `422`.

Research/qualification/decision endpoints land with the orchestrator (later brick).
