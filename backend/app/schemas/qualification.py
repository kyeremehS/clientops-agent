"""Qualification result schema. Single source of truth for LLM structured output."""

from pydantic import BaseModel, Field


class QualificationResult(BaseModel):
    """LLM proposes dimensions only. Score is computed in code (see policy docs)."""

    model_config = {"extra": "forbid"}

    operational_pain: int = Field(ge=0, le=3)
    automation_plausibility: int = Field(ge=0, le=3)
    relevance: int = Field(ge=0, le=3)
    evidence_quality: int = Field(ge=0, le=3)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    summary: str = ""
