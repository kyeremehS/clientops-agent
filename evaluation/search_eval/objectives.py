"""Objective dataset loading and validation."""

import json
from pathlib import Path

REQUIRED_KEYS = ("id", "objective")
DEFAULT_MAX_RESULTS = 5


def load_objectives(path: str | Path) -> list[dict]:
    """Load and validate [{id, objective, max_results?}]. Raises on bad data."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{path}: expected a non-empty JSON list")
    seen: set[str] = set()
    objectives: list[dict] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}[{i}]: expected an object")
        for key in REQUIRED_KEYS:
            if not entry.get(key) or not isinstance(entry[key], str):
                raise ValueError(f"{path}[{i}]: {key!r} must be a non-empty string")
        if entry["id"] in seen:
            raise ValueError(f"{path}[{i}]: duplicate id {entry['id']!r}")
        seen.add(entry["id"])
        max_results = entry.get("max_results", DEFAULT_MAX_RESULTS)
        if not isinstance(max_results, int) or max_results < 1:
            raise ValueError(f"{path}[{i}]: max_results must be a positive int")
        objectives.append(
            {"id": entry["id"], "objective": entry["objective"], "max_results": max_results}
        )
    return objectives
