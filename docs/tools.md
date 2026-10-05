# Tools (Slice 1 — shells)

Status: stub — contracts land in `feat/tools-research`. All tools typed with Pydantic I/O.

## Slice 1 tools

- `web_search(query) → [{title, url, snippet}]` — public web only. No auth.
- `website_fetch(url) → {url, text, content_hash}` — fetch + extract readable text.
- `slack_post(channel_id, text, idempotency_key) → {message_ts, ok}` — bot token,
  `chat:write`, idempotent per approval. Implementation in `feat/slack-audit`.

## Later (not Slice 1)

LinkedIn, company registries, news, Crunchbase — introduce auth/legal concerns.
Deferred until core loop is proven.
