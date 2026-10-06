# 0005 — Agents Honestly as guiding reference

Status: accepted

Reference: *Agents Honestly* (agentshonestly.com) — production agentic systems.
It validates our architecture and sets the quality bar per brick:

- State ladder: business-process state in workflow/DB, facts in Postgres,
  judgment in the model. Matches our orchestrator / DB / `llm/` split.
  Scoring and policy stay deterministic code, never prompts.
- Escalation ladder: known sequence + must survive failure → workflow
  (custom state machine, no LangGraph). Research → qualification is a
  sequential pipeline with strict I/O, not multi-agent.
- Live questions get live tool calls, not an index. Validates `web_search` +
  `website_fetch` for Slice 1 over a vector DB.
- Retrieved text is untrusted input: source-required claims, fetch caps,
  per-host timeouts.
- Reliability is cross-cutting, not a later phase: every network client
  (LLM, tools, Slack) gets timeouts, retries with backoff, budgets,
  idempotency where it writes, and structured logging without secrets.
- HITL holds no thread: approvals are stateless rows with expiry,
  re-validated on act.
