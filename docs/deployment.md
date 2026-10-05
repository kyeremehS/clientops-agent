# Deployment (Slice 1 — shell)

Status: stub — hardens in later slice. Local dev only for now.

- `docker compose up db` — postgres:16, DB `clientops` (see `docker-compose.yml`).
- Env (see `.env.example`): `DATABASE_URL`, `BACKEND_PORT`, `FRONTEND_API_BASE_URL`,
  `LLM_PROVIDER=openrouter`, `LLM_MODEL`, `OPENROUTER_API_KEY`,
  `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`.
- Backend runs locally via uvicorn; frontend via `pnpm dev`. No containerized
  backend/frontend in Slice 1.
