"""Research output schema. Single source of truth for claim synthesis output."""

from pydantic import BaseModel, Field


class ResearchClaim(BaseModel):
    """One factual claim about the named lead, tied to sources."""

    model_config = {"extra": "forbid"}

    claim: str
    evidence_refs: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Synthesis output. Thin evidence → inconclusive, never invented claims."""

    model_config = {"extra": "forbid"}

    claims: list[ResearchClaim] = Field(default_factory=list)
    inconclusive: bool = False
    note: str = ""
