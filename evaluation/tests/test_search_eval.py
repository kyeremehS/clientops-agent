"""Harness unit tests. No network, no provider keys — mock/stub providers only."""

import json

import pytest

from app.tools.search import MockSearchProvider, SearchResult
from search_eval.envkeys import DOTENV_KEYS, load_dotenv_fallback
from search_eval.metrics import compute_metrics, normalize_url
from search_eval.objectives import load_objectives
from search_eval.report import build_report_markdown, save_run
from search_eval.runner import build_providers, run_comparison


class BoomProvider:
    def search(self, objective: str, max_results: int = 5):  # noqa: ANN202
        raise RuntimeError("network is lava")


def _objectives_file(tmp_path, entries):
    path = tmp_path / "objectives.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_load_objectives_ok_and_defaults(tmp_path):
    path = _objectives_file(
        tmp_path, [{"id": "a", "objective": "What does A do?"}, {"id": "b", "objective": "B news."}]
    )
    objectives = load_objectives(path)
    assert [o["id"] for o in objectives] == ["a", "b"]
    assert all(o["max_results"] == 5 for o in objectives)


def test_load_objectives_rejects_bad_data(tmp_path):
    with pytest.raises(ValueError):
        load_objectives(_objectives_file(tmp_path, []))
    with pytest.raises(ValueError):
        load_objectives(
            _objectives_file(
                tmp_path,
                [{"id": "a", "objective": "x"}, {"id": "a", "objective": "y"}],
            )
        )
    with pytest.raises(ValueError):
        load_objectives(_objectives_file(tmp_path, [{"id": "a"}]))
    with pytest.raises(ValueError):
        load_objectives(
            _objectives_file(tmp_path, [{"id": "a", "objective": "x", "max_results": 0}])
        )


def test_load_objectives_real_dataset():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    objectives = load_objectives(repo_root / "evaluation" / "objectives.json")
    assert len(objectives) >= 15
    assert len({o["id"] for o in objectives}) == len(objectives)


def test_runner_records_mock_queries_and_caps():
    mock = MockSearchProvider(
        results=[SearchResult(title=f"T{i}", url=f"https://t{i}.test") for i in range(4)]
    )
    objectives = [
        {"id": "o1", "objective": "first", "max_results": 2},
        {"id": "o2", "objective": "second", "max_results": 2},
    ]
    run = run_comparison({"mock": mock}, objectives)
    assert len(run["calls"]) == 2
    assert all(len(c["results"]) == 2 and c["error"] is None for c in run["calls"])
    assert mock.queries == [("first", 2), ("second", 2)]


def test_runner_isolates_provider_failure():
    mock = MockSearchProvider()
    objectives = [{"id": "o1", "objective": "x", "max_results": 5}]
    run = run_comparison({"boom": BoomProvider(), "mock": mock}, objectives)
    by_provider = {c["provider"]: c for c in run["calls"]}
    assert by_provider["boom"]["error"]["type"] == "RuntimeError"
    assert by_provider["boom"]["latency_ms"] is None
    assert by_provider["mock"]["error"] is None


def test_build_providers_skips_unkeyed_and_rejects_unknown(monkeypatch):
    for key in DOTENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    assert build_providers(["parallel", "tavily"]) == {}
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    assert list(build_providers(["serper"])) == ["serper"]
    with pytest.raises(ValueError):
        build_providers(["altavista"])


def test_dotenv_fallback_loads_only_wanted_keys(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        '\n'
        'PARALLEL_API_KEY="par-key"\n'
        "TAVILY_API_KEY=tav-key\n"
        "DATABASE_URL=postgresql://x\n"
        "MALFORMED\n",
        encoding="utf-8",
    )
    for key in DOTENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "from-shell")
    load_dotenv_fallback(env_file)
    import os

    assert os.environ["PARALLEL_API_KEY"] == "par-key"  # quotes stripped
    assert os.environ["TAVILY_API_KEY"] == "from-shell"  # shell wins
    assert "DATABASE_URL" not in os.environ


def _canned_run():
    def call(provider, objective_id, urls, latency_ms=100):
        return {
            "provider": provider,
            "objective_id": objective_id,
            "objective": objective_id,
            "max_results": 5,
            "latency_ms": latency_ms,
            "results": [
                {"title": u, "url": u, "excerpt": "e" * 10} for u in urls
            ],
            "error": None,
        }

    return {
        "created_utc": "2026-01-01T00:00:00Z",
        "providers": ["a", "b"],
        "objectives": [{"id": "o1", "objective": "o1", "max_results": 5}],
        "calls": [
            call("a", "o1", ["https://X.test/", "https://y.test"]),
            call("b", "o1", ["https://x.test", "https://z.test"]),
        ],
    }


def test_metrics_overlap_and_dup_urls():
    run = _canned_run()
    run["calls"].append(
        {
            "provider": "a",
            "objective_id": "o1",
            "objective": "o1",
            "max_results": 5,
            "latency_ms": 200,
            "results": [{"title": "t", "url": "https://Y.test/", "excerpt": "e"}],
            "error": None,
        }
    )
    metrics = compute_metrics(run)
    assert metrics["providers"]["a"]["results"] == 3
    assert metrics["providers"]["a"]["dup_urls"] == ["https://y.test"]
    # {x,y} vs {x,z} → 1/3
    assert metrics["url_overlap_jaccard_mean"]["a|b"] == pytest.approx(1 / 3, abs=1e-3)
    assert metrics["providers"]["a"]["mean_ms"] == 150.0


def test_metrics_tolerates_errors_and_empties():
    run = _canned_run()
    run["calls"][0]["error"] = {"type": "SearchRateLimitError", "message": "throttled"}
    run["calls"][0]["results"] = []
    run["calls"][0]["latency_ms"] = None
    run["calls"][1]["results"] = []
    metrics = compute_metrics(run)
    assert metrics["providers"]["a"]["errors"] == 1
    assert metrics["providers"]["a"]["error_types"] == ["SearchRateLimitError"]
    # both empty → identical by convention
    assert metrics["url_overlap_jaccard_mean"]["a|b"] == 1.0


def test_normalize_url():
    assert normalize_url("HTTPS://A.test/") == "https://a.test"
    assert normalize_url("") == ""


def test_save_run_writes_three_artifacts(tmp_path):
    out = save_run(tmp_path / "run1", _canned_run())
    import json as _json
    from pathlib import Path as _Path

    assert _Path(out["raw_results"]).is_file()
    assert _Path(out["report"]).is_file()
    metrics = _json.loads(_Path(out["metrics"]).read_text(encoding="utf-8"))
    assert metrics["objectives"] == 1
    report = _Path(out["report"]).read_text(encoding="utf-8")
    assert "## Provider summary" in report and "o1" in report


def test_build_report_markdown_shows_errors():
    run = _canned_run()
    run["calls"][0]["error"] = {"type": "SearchResponseError", "message": "bad key"}
    markdown = build_report_markdown(run, compute_metrics(run))
    assert "ERR SearchResponseError" in markdown
