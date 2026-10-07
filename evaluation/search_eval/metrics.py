"""Deterministic metrics over a recorded run. No LLM, no network."""

import statistics
from itertools import combinations


def normalize_url(url: str) -> str:
    return (url or "").strip().lower().rstrip("/")


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0  # identical (both empty) — documented convention
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _latency_stats(latencies: list[int]) -> dict:
    if not latencies:
        return {"mean_ms": None, "p50_ms": None}
    return {"mean_ms": round(statistics.mean(latencies), 1), "p50_ms": statistics.median(latencies)}


def compute_metrics(run: dict) -> dict:
    """Roll up per-provider stats + cross-provider URL overlap per objective."""
    providers: dict[str, dict] = {}
    for name in run["providers"]:
        calls = [c for c in run["calls"] if c["provider"] == name]
        ok = [c for c in calls if c["error"] is None]
        latencies = [c["latency_ms"] for c in ok if c["latency_ms"] is not None]
        results = [r for c in ok for r in c["results"]]
        seen: dict[str, int] = {}
        for r in results:
            norm = normalize_url(r["url"])
            if norm:
                seen[norm] = seen.get(norm, 0) + 1
        providers[name] = {
            "calls": len(calls),
            "errors": len(calls) - len(ok),
            "error_types": sorted({c["error"]["type"] for c in calls if c["error"]}),
            "results": len(results),
            "excerpt_chars": sum(len(r["excerpt"]) for r in results),
            **_latency_stats(latencies),
            "dup_urls": sorted(url for url, n in seen.items() if n > 1),
        }

    overlap: dict[str, float | None] = {}
    objective_ids = [o["id"] for o in run["objectives"]]
    for left, right in combinations(sorted(run["providers"]), 2):
        scores: list[float] = []
        for objective_id in objective_ids:
            left_urls = {
                normalize_url(r["url"])
                for c in run["calls"]
                if c["provider"] == left
                and c["objective_id"] == objective_id
                and c["error"] is None
                for r in c["results"]
                if normalize_url(r["url"])
            }
            right_urls = {
                normalize_url(r["url"])
                for c in run["calls"]
                if c["provider"] == right
                and c["objective_id"] == objective_id
                and c["error"] is None
                for r in c["results"]
                if normalize_url(r["url"])
            }
            scores.append(_jaccard(left_urls, right_urls))
        key = f"{left}|{right}"
        overlap[key] = round(statistics.mean(scores), 3) if scores else None

    return {
        "objectives": len(objective_ids),
        "providers": providers,
        "url_overlap_jaccard_mean": overlap,
    }
