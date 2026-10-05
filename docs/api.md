# API (Slice 1 — shells)

Status: stub — schemas land in `feat/api-approvals-ui`. Pydantic is single source of truth.

## Endpoints

- `GET /health` — implemented (scaffold).
- `POST /leads` — create lead, start run. Deferred.
- `GET /leads/{id}` — lead + research + qualification + decision. Deferred.
- `POST /approvals/{id}/approve` — approve if pending + not expired + correct run state.
  Late → `409 approval_expired`. Deferred.
- `POST /approvals/{id}/reject` — human reject. Deferred.

## Error behaviour

- `409 approval_expired` when approving after `expires_at`.
- `409 wrong_state` when run is not in `review_pending`.
- `404` for unknown lead/approval. Validation errors are Pydantic `422`.
