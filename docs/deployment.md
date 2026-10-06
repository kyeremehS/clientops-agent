# Deployment (Slice 1 — local dev + Slack wiring)

Status: accepted for Slice 1 scope. No containers for app code yet.

- `docker compose up db` — postgres:16, DB `clientops` (see `docker-compose.yml`).
- Env (see `.env.example`): `DATABASE_URL`, `BACKEND_PORT`, `FRONTEND_API_BASE_URL`,
  `NEXT_PUBLIC_API_BASE_URL`, `LLM_PROVIDER=openrouter`, `LLM_MODEL`,
  `OPENROUTER_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`.
- Slack setup: test workspace, dedicated `#sales-leads` channel, bot token with
  `chat:write` scope, bot invited to the channel. Channel **ID** (not name) in
  `SLACK_CHANNEL_ID`. Verify with `POST /approvals/{id}/execute` against a test
  approval; `channel_not_found` means the ID is wrong or the bot isn't invited.
- Backend runs locally via uvicorn; frontend via `pnpm dev`. No containerized
  backend/frontend in Slice 1.
