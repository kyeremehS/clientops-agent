"""Research agent. Code runs the fixed plan; the model synthesizes claims."""

from app.agents.research.prompts import build_claim_queries, build_research_prompt
from app.agents.research.runner import run_research

__all__ = ["build_claim_queries", "build_research_prompt", "run_research"]
