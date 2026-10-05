# 0003 — Slice 1 locks

Status: accepted

- Slack: test workspace, fixed channel; `SLACK_BOT_TOKEN` + `SLACK_CHANNEL_ID`.
- LLM: OpenRouter, pinned `qwen/qwen3.8-27b:free`; validate structured-output
  before treating as final; never `openrouter/free` router in eval.
- Fit score deterministic in code: `sum(dims)/12*100`; LLM never emits 0-100.
- Insufficient evidence = `evidence_quality <= 1` → REVIEW, never auto-reject.
- Require ≥2 supporting evidence items, else REVIEW.
- Auto-reject only when `score < 40` with sufficient evidence.
- Approval expires after 24h; late approve → `409 approval_expired`.
- Zero automatic external action in Slice 1.
