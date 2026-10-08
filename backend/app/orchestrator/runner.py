"""End-to-end run pipeline: research → qualify → decide → approval.

Synchronous and single-pass. Humans act later through the approvals API;
the pipeline never pauses waiting. Verdict rows persist here (C2 left
them to this step); the approval itself is created through the same
helper as the API so both paths stay identical.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.qualification.runner import run_qualification
from app.agents.research.runner import run_research
from app.db.events import append_audit_event, create_approval
from app.db.models import Decision, Lead
from app.llm.client import OpenRouterClient
from app.orchestrator.states import lead_state
from app.policy import REVIEW, decide
from app.policy.safety import SafetyTracker, check
from app.schemas.leads import LeadCreate
from app.tools.fetch import WebsiteFetcher
from app.tools.search import SearchProvider


class LeadNotFoundError(ValueError):
    """Raised when a run targets a lead id with no row. Maps to 404."""


def run_lead(
    lead_id: UUID,
    session: Session,
    search: SearchProvider,
    fetcher: WebsiteFetcher,
    llm: OpenRouterClient,
    max_results: int = 5,
    tool_budget: int = 30,
) -> dict:
    """Execute one full pass and return the run summary."""
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFoundError(f"lead not found: {lead_id}")
    tracker = SafetyTracker(max_calls=tool_budget)

    def guard(tool_name: str, args: dict) -> str:
        return check(tracker, tool_name, args)

    append_audit_event(session, lead_id, "run.started", payload={"max_results": max_results})
    lead_in = LeadCreate(
        company=lead.company, website=lead.website, contact=lead.contact, message=lead.message
    )
    research = run_research(lead_id, lead_in, search, fetcher, llm, session, max_results, guard)
    append_audit_event(
        session,
        lead_id,
        "research.completed",
        payload={"claims": len(research.claims), "inconclusive": research.inconclusive},
    )
    qualification, fit = run_qualification(lead_id, lead_in, llm, session)
    append_audit_event(session, lead_id, "qualification.completed", payload={"fit": round(fit, 1)})
    outcome, reasons = decide(
        {
            "operational_pain": qualification.operational_pain,
            "automation_plausibility": qualification.automation_plausibility,
            "relevance": qualification.relevance,
            "evidence_quality": qualification.evidence_quality,
        },
        len(qualification.supporting_evidence_ids),
    )
    session.add(Decision(lead_id=lead_id, outcome=outcome, reasons=reasons))
    session.flush()
    append_audit_event(session, lead_id, "decision.made", payload={"outcome": outcome})
    approval_id = None
    if outcome == REVIEW:
        approval_id = create_approval(session, lead_id).id
    session.commit()
    return {
        "lead_id": lead_id,
        "state": lead_state(session, lead_id),
        "outcome": outcome,
        "fit": fit,
        "approval_id": approval_id,
        "reasons": reasons,
        "claims": [
            {"claim": c.claim, "source_urls": list(c.source_urls)} for c in research.claims
        ],
    }
