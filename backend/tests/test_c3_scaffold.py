"""C3 scaffold contracts. Signatures stable; behavior lands in implementation."""

import inspect
from uuid import UUID

from sqlalchemy.orm import Session

from app.orchestrator import runner as runner_module
from app.orchestrator import states as states_module
from app.policy import safety as safety_module
from app.schemas.runs import RunRead


def test_state_signature():
    sig = inspect.signature(states_module.lead_state)
    assert list(sig.parameters) == ["session", "lead_id"]
    assert sig.parameters["session"].annotation is Session
    assert sig.parameters["lead_id"].annotation is UUID
    assert sig.return_annotation is str


def test_runner_signature():
    params = list(inspect.signature(runner_module.run_lead).parameters)
    assert params == [
        "lead_id",
        "session",
        "search",
        "fetcher",
        "llm",
        "max_results",
        "tool_budget",
    ]


def test_safety_surface():
    assert issubclass(safety_module.GuardBlockedError, Exception)
    assert list(inspect.signature(safety_module.check).parameters) == [
        "tracker",
        "tool_name",
        "args",
    ]
    assert list(inspect.signature(safety_module.classify).parameters) == ["tool_name"]


def test_run_read_schema():
    from uuid import uuid4

    read = RunRead(
        lead_id=uuid4(), state="review_pending", outcome="REVIEW", fit=66.7, reasons=["r"]
    )
    assert read.approval_id is None and read.reasons == ["r"]
