# 0002 — Custom State Machine + LLM Abstraction + Typed Tools

Status: accepted

- Orchestrator owns state transitions explicitly.
- LLM access goes through `backend/app/llm/` abstraction, never direct SDK calls in agents.
- All external effects go through typed tools in `backend/app/tools/` with Pydantic I/O.
