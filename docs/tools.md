# Tools (Slice 1–2 — slack_post + research tools implemented)

Status: `slack_post` (B5) plus `web_search` / `website_fetch` (C1) accepted.
All tools typed; network clients share the timeout/retry/no-bodies-logged doctrine.

## Research tools (C1)

- `SearchProvider.search(objective, max_results) → list[SearchResult]`
  in `backend/app/tools/search.py`. Adapters: `ParallelSearchProvider`
  (Fast mode, `x-api-key`, excerpts), `TavilySearchProvider` (`basic` depth,
  Bearer auth, content snippets), `SerperSearchProvider` (SERP organic
  snippets, `X-API-KEY`), `MockSearchProvider` (canned, records queries).
  Switch via `SEARCH_PROVIDER`; `mock` is the safe default.
- `WebsiteFetcher.fetch(url) → FetchResult{url, final_url, text, content_hash,
  truncated}` in `backend/app/tools/fetch.py`. First-party httpx + stdlib
  HTML parsing. Refuses non-http(s) schemes and private/loopback/link-local
  destinations (SSRF guard), caps bytes (streamed) and chars, text responses
  only. Hash covers `final_url + text` for stable artifact identity.

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
