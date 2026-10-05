# Troubleshooting (shell — grows with implementation)

- Import errors in tests → run from repo root: `python -m pytest backend/tests -q`.
- DB connection refused → `docker compose up db`, check `DATABASE_URL`.
- Slack `channel_not_found` → verify `SLACK_CHANNEL_ID` (ID, not name) + bot invited.
- OpenRouter structured-output failures → re-validate pinned model; record re-pin in `docs/decisions/`.
- Approval `409` → check `expires_at` (24h) and run state is `review_pending`.
