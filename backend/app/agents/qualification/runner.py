"""Qualification runner. Reasons over artifacts; receives no tools by construction."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.qualification.prompts import build_qualification_prompt
from app.db.models import Qualification, ResearchArtifact
from app.llm import GroqClient, OpenAIClient, OpenRouterClient
from app.policy import score
from app.schemas.leads import LeadCreate
from app.schemas.qualification import QualificationResult

_NO_SUPPORT_SUMMARY = "no sufficiently supported automation opportunity found"


def _empty_result() -> QualificationResult:
    """All-zero dims with the fixed sentence. No model call."""
    return QualificationResult(
        operational_pain=0,
        automation_plausibility=0,
        relevance=0,
        evidence_quality=0,
        supporting_evidence_ids=[],
        summary=_NO_SUPPORT_SUMMARY,
    )


def persist_result(lead_id: UUID, session: Session) -> tuple[QualificationResult, float]:
    """Persist the all-zero 'no support' result without calling the model."""
    return _persist(lead_id, _empty_result(), session)


def run_qualification(
    lead_id: UUID,
    lead: LeadCreate,
    llm: OpenRouterClient | GroqClient | OpenAIClient,
    session: Session,
) -> tuple[QualificationResult, float]:
    """Rate dimensions, persist the qualification row, return (result, fit).

    supporting_evidence_ids not matching stored artifacts are dropped; if
    that empties the list, evidence_quality is capped at 1 so policy
    escalates to REVIEW. Empty evidence short-circuits to all-zero dims
    without calling the model.
    """
    rows = list(
        session.scalars(select(ResearchArtifact).where(ResearchArtifact.lead_id == lead_id))
    )
    known_ids = {str(row.id) for row in rows}
    if not rows:
        return _persist(lead_id, _empty_result(), session)

    evidence = [{"id": str(r.id), "url": r.source_url, "text": r.content} for r in rows]
    parsed, _ = llm.complete_json(
        [{"role": "user", "content": build_qualification_prompt(lead, evidence)}],
        QualificationResult,
        "qualification",
    )
    kept = [i for i in parsed.supporting_evidence_ids if i in known_ids]
    if parsed.supporting_evidence_ids and not kept:
        parsed = parsed.model_copy(
            update={"supporting_evidence_ids": [], "evidence_quality": 1}
        )
    else:
        parsed = parsed.model_copy(update={"supporting_evidence_ids": kept})
    return _persist(lead_id, parsed, session)


def _persist(
    lead_id: UUID, result: QualificationResult, session: Session
) -> tuple[QualificationResult, float]:
    fit = score(
        {
            "operational_pain": result.operational_pain,
            "automation_plausibility": result.automation_plausibility,
            "relevance": result.relevance,
            "evidence_quality": result.evidence_quality,
        }
    )
    session.add(
        Qualification(
            lead_id=lead_id,
            operational_pain=result.operational_pain,
            automation_plausibility=result.automation_plausibility,
            relevance=result.relevance,
            evidence_quality=result.evidence_quality,
            supporting_evidence_ids=result.supporting_evidence_ids,
            summary=result.summary,
            score=fit,
        )
    )
    session.commit()
    return result, fit
