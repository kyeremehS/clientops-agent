# Local development

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
docker compose up db
python -m pytest backend/tests -q
uvicorn app.main:app --reload  # run from backend/
```

```powershell
# Frontend (after B4)
cd frontend
pnpm install
pnpm dev
```

Env: copy `.env.example` to `.env`. Never commit real tokens.
Slice 1 needs `OPENROUTER_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`.
