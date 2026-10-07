"""Deterministic search-provider comparison harness (informational, never gated)."""

from search_eval.metrics import compute_metrics  # noqa: F401
from search_eval.objectives import load_objectives  # noqa: F401
from search_eval.report import save_run  # noqa: F401
from search_eval.runner import build_providers, run_comparison  # noqa: F401

__all__ = [
    "build_providers",
    "compute_metrics",
    "load_objectives",
    "run_comparison",
    "save_run",
]
