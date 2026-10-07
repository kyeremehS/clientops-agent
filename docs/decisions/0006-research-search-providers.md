# 0006 — Research search providers (Parallel Fast default + Tavily + Serper)

Status: accepted

Research needs discovery over the public web. Scraping HTML search pages is
unofficial, rate-limited, and shapeshifts without notice — rejected for the
same reliability reasons the LLM and Slack clients use real APIs.

Decision:

- Three adapters behind one sync `SearchProvider` protocol
  (`backend/app/tools/search.py`): `search(objective, max_results)` →
  `list[SearchResult{title, url, excerpt}]`. Agents depend on the protocol only.
- `SEARCH_PROVIDER=parallel|tavily|serper|mock`. `mock` is the safe default
  (no key, no spend, no network) and backs unit tests.
- **Parallel Fast is the default**: objective-in/excerpts-out maps directly onto
  `ResearchArtifact`, ~700ms, $1/1k requests, $5/mo free credits. Verified from
  `docs.parallel.ai/search-quickstart` (`x-api-key` header, `mode: "fast"`).
- Parallel `/v1/search` requires `search_queries` (V1 migration: at least one
  non-empty query; Beta accepted objective-only). `ParallelSearchProvider`
  derives one query from the objective (truncated to 200 chars) and sends
  `advanced_settings.max_results` — interface stays `search(objective,
  max_results)` so agents never build queries.
- Tavily (`basic` depth, Bearer auth) and Serper (SERP `organic` snippets,
  `X-API-KEY`) stay one env var away for A/B comparison.
- Direct REST APIs, not MCP: retries, timeouts, budgets, logging, and mocking
  stay under our control (ADR 0005 doctrine).
- Comparison method: `python evaluation/compare_search.py` runs the
  `evaluation/objectives.json` dataset (18 objectives) against every keyed
  provider and persists `evaluation/runs/<ts>/{raw_results.json,metrics.json,
  report.md}` (gitignored). Deterministic metrics only — latency, errors,
  excerpt volume, dup URLs, cross-provider URL overlap. Relevance judgment
  is human and recorded here before any default change. Vendor benchmarks
  are not evidence.

`website_fetch` stays first-party (httpx + stdlib parsing, SSRF/size guards):
Serper's thin snippets make it mandatory there, nice-to-have elsewhere.
