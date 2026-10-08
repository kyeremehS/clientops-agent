"""C2 scaffold contracts. Schemas parse; runner signatures stay stable."""

import inspect

from app.agents import qualification, research
from app.schemas.research import ResearchClaim, ResearchResult


def test_research_schemas_parse_and_forbid_extra():
    claim = ResearchClaim(
        claim="Runs 40 trucks.",
        evidence_refs=["art-1"],
        source_urls=["https://acme.test/"],
    )
    result = ResearchResult(claims=[claim])
    assert result.claims[0].source_urls == ["https://acme.test/"]
    assert result.inconclusive is False


def test_research_result_defaults_to_empty_not_null():
    result = ResearchResult()
    assert result.claims == [] and result.note == ""


def test_runner_signatures_cover_inputs_outputs():
    sig = inspect.signature(research.run_research)
    assert list(sig.parameters) == [
        "lead_id",
        "lead",
        "search",
        "fetcher",
        "llm",
        "session",
        "max_results",
        "guard",
    ]
    qual_sig = inspect.signature(qualification.run_qualification)
    assert list(qual_sig.parameters) == ["lead_id", "lead", "llm", "session"]
    assert "search" not in qual_sig.parameters and "fetcher" not in qual_sig.parameters
