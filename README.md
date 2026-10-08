# clientops-agent

A sales lead comes in. The system researches the company online, scores
whether there's a real automation opportunity, and — only after a human
clicks approve — posts to Slack. Every step is saved as evidence.

## How it works

1. **Lead arrives** — company name, website, and message (via API or UI).
2. **Research** — web search + website fetch gather facts with source URLs.
3. **Qualification** — the AI rates four dimensions 0–3 (operational pain,
   automation plausibility, relevance, evidence quality). It proposes;
   it never decides.
4. **Policy (code, not AI)** — fit score below 40 → REJECT. Weak evidence
   (≤1) or fewer than 2 sources → REVIEW. Nothing sends itself, ever.
5. **Human approval** — REVIEW cases wait in a web queue. Approvals expire
   after 24 hours.
6. **Slack action + audit** — on approval, one message posts to #sales-leads
   (exactly once — retries can't double-send). Each step links into a
   tamper-evident audit chain.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
docker compose up db            # Postgres
Copy-Item .env.example .env     # then fill in your keys; never commit tokens
python -m pytest backend/tests -q
```

Backend runs from `backend/`: `uvicorn app.main:app --reload`.
Frontend runs from `frontend/`: `pnpm install; pnpm dev`.

## Safety rules

- AI proposes, code disposes, humans authorize. No automatic external action.
- Ambiguous scope means stop, not proceed.
- Prompts, search results, and web pages are untrusted input — secrets never
  go into prompts, logs, or stored evidence.
