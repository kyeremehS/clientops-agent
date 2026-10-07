"""Persist a run: raw_results.json (evidence) + metrics.json + report.md (human)."""

import json
from pathlib import Path

from search_eval.metrics import compute_metrics
from search_eval.runner import format_cost_reference


def _provider_table(metrics: dict) -> str:
    header = "| provider | calls | errors | results | excerpt_chars | latency_mean_ms | p50_ms | dup_urls |"
    sep = "|---|---|---|---|---|---|---|---|---|"
    rows = []
    for name, p in metrics["providers"].items():
        rows.append(
            f"| {name} | {p['calls']} | {p['errors']} | {p['results']} | "
            f"{p['excerpt_chars']} | {p['mean_ms']} | {p['p50_ms']} | {len(p['dup_urls'])} |"
        )
    return "\n".join([header, sep, *rows])


def _overlap_table(metrics: dict) -> str:
    lines = ["| pair | mean_url_overlap_jaccard |", "|---|---|"]
    for pair, score in metrics["url_overlap_jaccard_mean"].items():
        lines.append(f"| {pair} | {score} |")
    return "\n".join(lines)


def _objective_sections(run: dict) -> str:
    sections = []
    for objective in run["objectives"]:
        lines = [f"### {objective['id']}", f"> {objective['objective']}", ""]
        for call in run["calls"]:
            if call["objective_id"] != objective["id"]:
                continue
            if call["error"] is not None:
                lines.append(
                    f"- **{call['provider']}**: ERR "
                    f"{call['error']['type']}: {call['error']['message']}"
                )
                continue
            top = call["results"][0]["url"] if call["results"] else "-"
            lines.append(
                f"- **{call['provider']}** "
                f"({len(call['results'])} results, {call['latency_ms']}ms): {top}"
            )
            for result in call["results"][:3]:
                title = (result["title"] or "(no title)")[:80]
                lines.append(f"  - [{title}]({result['url']})")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def build_report_markdown(run: dict, metrics: dict) -> str:
    return (
        f"# Search comparison — {run['created_utc']}\n\n"
        f"Providers: {', '.join(run['providers'])} | "
        f"Objectives: {len(run['objectives'])} | "
        f"Reference cost/1k: {format_cost_reference()}\n\n"
        "Relevance judgment is human: grade titles/URLs below, record the "
        "verdict in docs/decisions/0006-research-search-providers.md.\n\n"
        "## Provider summary\n\n"
        f"{_provider_table(metrics)}\n\n"
        "## Cross-provider URL overlap (Jaccard, mean over objectives)\n\n"
        f"{_overlap_table(metrics)}\n\n"
        "## Per objective (top result per provider)\n\n"
        f"{_objective_sections(run)}\n"
    )


def save_run(out_dir: str | Path, run: dict) -> dict:
    """Write raw_results.json + metrics.json + report.md. Returns paths + metrics."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics = compute_metrics(run)
    (out / "raw_results.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "report.md").write_text(build_report_markdown(run, metrics), encoding="utf-8")
    return {
        "dir": str(out),
        "raw_results": str(out / "raw_results.json"),
        "metrics": str(out / "metrics.json"),
        "report": str(out / "report.md"),
        "metrics_data": metrics,
    }
