"""Tests for the repeat-run aggregation harness.

``scripts/aggregate_llm_repeats.py`` is the local-only aggregation
side of the repeat-run variance phase. It does not call the LLM or
run any eval target. These tests exercise it against three
hand-crafted fixture reports under
``tests/fixtures/llm_repeats/``:

- ``run1.json`` — runtime-only flag on `case_fl_adv_v0_002`
  (runtime guardrail fires, offline grader clears).
- ``run2.json`` — every case passes cleanly.
- ``run3.json`` — one offline `UNSAFE_CUSTOMER_COMMS` failure on
  `case_fl_adv_v0_004` (`evaluator_all_ok=False`).

Together these three runs exercise: per-case instability detection,
the runtime-vs-offline asymmetry signal, offline `UNSAFE_CUSTOMER_COMMS`
counts, `EVALUATOR_MISS` accounting, per-band latency variance, cost
distribution, and the Markdown public-safety wording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.aggregate_llm_repeats import (
    AggregationError,
    NOT_READY_LINE,
    SYNTHETIC_DISCLAIMER,
    aggregate,
    aggregate_files,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "llm_repeats"
RUN_PATHS: tuple[Path, ...] = tuple(
    FIXTURE_DIR / name for name in ("run1.json", "run2.json", "run3.json")
)


@pytest.fixture()
def summary() -> dict:
    return aggregate_files(list(RUN_PATHS))


# ---------------------------------------------------------------------------
# Validation: rejects malformed / mixed inputs
# ---------------------------------------------------------------------------


def test_requires_at_least_two_reports() -> None:
    with pytest.raises(AggregationError) as exc:
        aggregate_files([RUN_PATHS[0]])
    assert "at least 2 reports" in str(exc.value)


def test_missing_report_file_raises(tmp_path: Path) -> None:
    with pytest.raises(AggregationError) as exc:
        aggregate_files([tmp_path / "missing.json", RUN_PATHS[0]])
    assert "report not found" in str(exc.value)


def test_malformed_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not really json")
    with pytest.raises(AggregationError) as exc:
        aggregate_files([bad, RUN_PATHS[0]])
    assert "invalid JSON" in str(exc.value)


def test_missing_per_case_raises(tmp_path: Path) -> None:
    bad = tmp_path / "no_per_case.json"
    bad.write_text(json.dumps({
        "agent_system_version": "llm_candidate_v0",
        "dataset_path": "x.jsonl",
    }))
    with pytest.raises(AggregationError) as exc:
        aggregate_files([bad, RUN_PATHS[0]])
    assert "per_case" in str(exc.value)


def test_mixed_datasets_rejected_by_default(tmp_path: Path) -> None:
    other = json.loads((RUN_PATHS[0]).read_text())
    other["dataset_path"] = "different.jsonl"
    other_path = tmp_path / "other.json"
    other_path.write_text(json.dumps(other))
    with pytest.raises(AggregationError) as exc:
        aggregate_files([RUN_PATHS[0], other_path])
    assert "mix datasets" in str(exc.value)


def test_mixed_datasets_allowed_with_flag(tmp_path: Path) -> None:
    other = json.loads((RUN_PATHS[0]).read_text())
    other["dataset_path"] = "different.jsonl"
    other_path = tmp_path / "other.json"
    other_path.write_text(json.dumps(other))
    summary = aggregate_files(
        [RUN_PATHS[0], other_path], allow_mixed_datasets=True
    )
    assert len(summary["datasets"]) == 2


def test_mixed_profile_families_rejected_by_default(tmp_path: Path) -> None:
    other = json.loads((RUN_PATHS[0]).read_text())
    other["agent_system_version"] = "llm_candidate_v1"
    other_path = tmp_path / "v1.json"
    other_path.write_text(json.dumps(other))
    with pytest.raises(AggregationError) as exc:
        aggregate_files([RUN_PATHS[0], other_path])
    assert "agent_system_version" in str(exc.value)


def test_mixed_profile_families_allowed_with_flag(tmp_path: Path) -> None:
    other = json.loads((RUN_PATHS[0]).read_text())
    other["agent_system_version"] = "llm_candidate_v1"
    other_path = tmp_path / "v1.json"
    other_path.write_text(json.dumps(other))
    summary = aggregate_files(
        [RUN_PATHS[0], other_path], allow_mixed_profiles=True
    )
    assert summary["profile_family"] == ["llm_candidate_v0", "llm_candidate_v1"]


# ---------------------------------------------------------------------------
# Pass/fail + label distributions
# ---------------------------------------------------------------------------


def test_run_and_case_count_summary(summary: dict) -> None:
    assert summary["run_count"] == 3
    assert summary["case_counts_per_run"] == [6, 6, 6]
    assert summary["profile_family"] == ["llm_candidate_v0"]
    assert summary["datasets"] == [
        "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl"
    ]


def test_pass_fail_per_run(summary: dict) -> None:
    assert summary["pass_per_run"] == [5, 6, 5]
    assert summary["fail_per_run"] == [1, 0, 1]


def test_failure_label_totals_aggregated(summary: dict) -> None:
    # run1 = {}, run2 = {}, run3 = {"UNSAFE_CUSTOMER_COMMS": 1}
    assert summary["failure_label_totals"] == {"UNSAFE_CUSTOMER_COMMS": 1}
    assert summary["failure_label_per_run"] == [
        {},
        {},
        {"UNSAFE_CUSTOMER_COMMS": 1},
    ]


def test_offline_unsafe_and_evaluator_miss_per_run(summary: dict) -> None:
    assert summary["offline_unsafe_customer_comms_per_run"] == [0, 0, 1]
    assert summary["evaluator_miss_per_run"] == [0, 0, 0]


# ---------------------------------------------------------------------------
# Runtime-vs-offline asymmetry
# ---------------------------------------------------------------------------


def test_runtime_guardrail_and_runtime_only_signals(summary: dict) -> None:
    # run1: case_002 evaluator_all_ok=False, no offline label → runtime-only.
    # run2: no flags.
    # run3: case_004 evaluator_all_ok=False AND has offline label → guardrail
    #       fires but NOT runtime-only.
    assert summary["runtime_guardrail_fires_per_run"] == [1, 0, 1]
    assert summary["runtime_only_fires_per_run"] == [1, 0, 0]


# ---------------------------------------------------------------------------
# Per-case instability
# ---------------------------------------------------------------------------


def test_per_case_instability_lists_only_unstable_cases(summary: dict) -> None:
    cids = [entry["case_id"] for entry in summary["per_case_instability"]]
    # case_002 varies (fails in run1, passes in runs 2+3).
    # case_004 varies (passes in runs 1+2, fails in run3).
    # Every other case passes in all three runs → stable, omitted.
    assert sorted(cids) == ["case_fl_adv_v0_002", "case_fl_adv_v0_004"]


def test_per_case_instability_carries_label_and_runtime_sequences(
    summary: dict,
) -> None:
    by_case = {e["case_id"]: e for e in summary["per_case_instability"]}
    c2 = by_case["case_fl_adv_v0_002"]
    assert c2["runs"] == 3
    assert c2["passed_runs"] == 2
    assert c2["failed_runs"] == 1
    assert c2["runtime_guardrail_fired_sequence"] == [True, False, False]
    # Run1 label sequence is "(none)" because failure came from the
    # runtime guardrail, not the offline grader.
    assert c2["label_sequence"][0] == "(none)"


# ---------------------------------------------------------------------------
# Latency stats by band
# ---------------------------------------------------------------------------


def test_latency_stats_collected_per_band(summary: dict) -> None:
    lat = summary["latency_stats_by_band"]
    for band in ("L1", "L2", "L3"):
        assert band in lat
        assert lat[band]["run_count"] == 3
        assert len(lat[band]["samples_ms"]) == 3
        assert lat[band]["mean_ms"] is not None
        assert lat[band]["min_ms"] <= lat[band]["mean_ms"] <= lat[band]["max_ms"]
        # Stdev defined when run_count >= 2.
        assert lat[band]["stdev_ms"] is not None


def test_latency_l1_mean_matches_fixture(summary: dict) -> None:
    # run1 L1 mean=8600, run2 L1 mean=9200, run3 L1 mean=8900 → mean ≈ 8900.
    assert summary["latency_stats_by_band"]["L1"]["mean_ms"] == 8900
    assert summary["latency_stats_by_band"]["L1"]["min_ms"] == 8600
    assert summary["latency_stats_by_band"]["L1"]["max_ms"] == 9200


# ---------------------------------------------------------------------------
# Cost stats
# ---------------------------------------------------------------------------


def test_cost_stats_aggregated(summary: dict) -> None:
    cost = summary["cost_stats_usd"]
    assert cost["run_count"] == 3
    assert cost["samples_usd"] == [0.029, 0.031, 0.034]
    assert cost["total_usd"] == round(sum([0.029, 0.031, 0.034]), 6)
    assert cost["mean_usd"] == round(sum([0.029, 0.031, 0.034]) / 3, 6)
    assert cost["min_usd"] == 0.029
    assert cost["max_usd"] == 0.034
    assert cost["stdev_usd"] is not None


# ---------------------------------------------------------------------------
# Markdown rendering: public-safe stance
# ---------------------------------------------------------------------------


def test_markdown_contains_not_ready_for_pilot(summary: dict) -> None:
    md = render_markdown(summary)
    assert "NOT READY FOR PILOT" in md
    assert NOT_READY_LINE in md
    assert SYNTHETIC_DISCLAIMER in md


def test_markdown_avoids_overclaims(summary: dict) -> None:
    lower = render_markdown(summary).lower()
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, (
            f"repeat-run summary must not claim {forbidden!r}"
        )


def test_markdown_surfaces_runtime_vs_offline_asymmetry(summary: dict) -> None:
    md = render_markdown(summary)
    assert "Runtime guardrail fires" in md
    assert "Runtime-only fires" in md
    assert "EVALUATOR_MISS" in md


def test_markdown_includes_per_case_instability_table(summary: dict) -> None:
    md = render_markdown(summary)
    assert "Per-case instability" in md
    assert "case_fl_adv_v0_002" in md
    assert "case_fl_adv_v0_004" in md


def test_markdown_does_not_require_raw_llm_paths(summary: dict) -> None:
    md = render_markdown(summary)
    # The aggregator works off the report JSONs only; no raw trace
    # path should leak into the public summary.
    assert "traces/local/llm_" not in md


# ---------------------------------------------------------------------------
# JSON-shaped summary smoke
# ---------------------------------------------------------------------------


def test_summary_is_serializable(summary: dict) -> None:
    blob = json.dumps(summary, indent=2)
    round_tripped = json.loads(blob)
    assert round_tripped["run_count"] == 3
    assert round_tripped["synthetic"] is True
    assert round_tripped["not_ready_for_pilot"] is True


# ---------------------------------------------------------------------------
# CLI smoke (runs the script in-process, no Anthropic call)
# ---------------------------------------------------------------------------


def test_cli_writes_md_and_json(tmp_path: Path) -> None:
    import subprocess
    import sys

    script = ROOT / "scripts" / "aggregate_llm_repeats.py"
    out_md = tmp_path / "summary.md"
    out_json = tmp_path / "summary.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--report",
            str(RUN_PATHS[0]),
            "--report",
            str(RUN_PATHS[1]),
            "--report",
            str(RUN_PATHS[2]),
            "--out-md",
            str(out_md),
            "--out-json",
            str(out_json),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out_md.exists()
    assert out_json.exists()
    md = out_md.read_text()
    assert "NOT READY FOR PILOT" in md
    payload = json.loads(out_json.read_text())
    assert payload["run_count"] == 3


# ---------------------------------------------------------------------------
# Pure aggregate() also works on in-memory dicts (no file required)
# ---------------------------------------------------------------------------


def test_aggregate_pure_function_handles_in_memory_dicts() -> None:
    reports = [json.loads(p.read_text()) for p in RUN_PATHS]
    summary = aggregate(reports)
    assert summary["run_count"] == 3
    assert summary["failure_label_totals"] == {"UNSAFE_CUSTOMER_COMMS": 1}
