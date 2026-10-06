# Tools (Slice 1 — slack_post implemented in B5)

Status: `slack_post` accepted in `backend/app/tools/slack.py`.
`web_search` / `website_fetch` remain stubs for the research brick.

## Slice 1 tools

- `web_search(query) → [{title, url, snippet}]` — public web only. No auth.
- `website_fetch(url) → {url, text, content_hash}` — fetch + extract readable text.
- `slack_post(channel_id, text) → {ts, channel}` — `SlackSender` in
  `backend/app/tools/slack.py`: bot token, `chat:write`, timeout, retry with
  backoff on 429/5xx/timeout and `ok:false rate_limited` only. Auth and config
  errors fail immediately. Bodies never logged. Message text is code-composed
  (`format_qualification_message`), never LLM output.
- Idempotency lives in the execute worker (`backend/app/api/actions.py`):
  one `Action` row per approval (`idempotency_key = approval:{id}`), so a retry
  after an ambiguous timeout returns the existing row without re-sending.

## Later (not Slice 1)

LinkedIn, company registries, news, Crunchbase — introduce auth/legal concerns.
Deferred until core loop is proven.
