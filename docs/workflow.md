# Workflow (Slice 1)

Status: accepted

## States

```text
new → researching → researched → qualifying → qualified | disqualified
  → review_pending → approved → actioned
  → rejected | rejected_by_human | expired (terminal)
```

## Who transitions

- Machine: `new → researching → researched → qualifying → qualified/disqualified`,
  policy `→ review_pending / rejected`, `approved → actioned`, expiry `→ expired`.
- Human: `review_pending → approved | rejected_by_human` via `POST /approvals/{id}/approve|reject`.

## Rules

- Every transition emits an immutable audit event (see `policy.md`, `data-model.md`).
- `review_pending` carries `requested_at` + `expires_at` (requested + 24h).
- Expired approvals return `409 approval_expired` and cannot execute.
- Terminal states: `rejected`, `rejected_by_human`, `expired`, `actioned`.
- Full prompt/column details deferred to implementation PRs.
