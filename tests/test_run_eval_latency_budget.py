"""Tests for the latency-vs-budget block on the eval report.

`evals/run.py` now emits a ``comparison_by_risk_band`` block inside
``synthetic_latency_envelope``. Each band with measured samples gets a
categorical ``verdict`` against the synthetic p50/p95 budget from
``configs/latency_budgets.yaml``. These tests lock in:

1. The block exists on a fresh eval-report run.
2. The verdict computation is correct for each of the four branches
   (within_p50, between_p50_and_p95, exceeds_p95, no_budget).
3. ``mean_vs_p95_ratio`` is the rounded mean ÷ p95 ratio when both are
   present, and ``None`` when there is no budget.
4. Bands with zero samples are omitted (no misleading rows).
5. The block surfaces alongside the existing ``measured_ms`` /
   ``synthetic_planning_envelope`` sections without disturbing them.
"""

from __future__ import annotations

from pathlib import Path

from evals.run import (
    LATENCY_VERDICT_BETWEEN,
    LATENCY_VERDICT_EXCEEDS_P95,
    LATENCY_VERDICT_NO_BUDGET,
    LATENCY_VERDICT_WITHIN_P50,
    _compute_latency_vs_budget,
    run_eval,
)


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"


# ---------------------------------------------------------------------------
# Pure verdict logic
# ---------------------------------------------------------------------------

ENVELOPE_FIXTURE: dict[str, dict[str, int]] = {
    "L1": {"p50_ms": 2000, "p95_ms": 4000},
    "L2": {"p50_ms": 3500, "p95_ms": 7000},
    "L3": {"p50_ms": 6000, "p95_ms": 12000},
}


def test_verdict_within_p50_when_mean_below_p50() -> None:
    comp = _compute_latency_vs_budget(
        {"L1": [100, 200, 300]},  # mean = 200 << 2000
        ENVELOPE_FIXTURE,
    )
    assert comp["L1"]["verdict"] == LATENCY_VERDICT_WITHIN_P50
    assert comp["L1"]["measured_mean_ms"] == 200
    assert comp["L1"]["measured_max_ms"] == 300
    assert comp["L1"]["count"] == 3


def test_verdict_between_p50_and_p95_when_mean_in_corridor() -> None:
    # L2 budget: p50=3500, p95=7000. Pick samples whose mean lands in
    # the corridor.
    comp = _compute_latency_vs_budget(
        {"L2": [4000, 5000, 6000]},  # mean = 5000
        ENVELOPE_FIXTURE,
    )
    assert comp["L2"]["verdict"] == LATENCY_VERDICT_BETWEEN
    assert comp["L2"]["mean_vs_p95_ratio"] == round(5000 / 7000, 3)


def test_verdict_exceeds_p95_when_mean_above_p95() -> None:
    # L1 p95 = 4000; this LLM-ish sample lands above it.
    samples = [5895, 6605, 7590]  # mean = 6696 (rounded)
    comp = _compute_latency_vs_budget({"L1": samples}, ENVELOPE_FIXTURE)
    assert comp["L1"]["verdict"] == LATENCY_VERDICT_EXCEEDS_P95
    expected_mean = int(round(sum(samples) / len(samples)))
    assert comp["L1"]["measured_mean_ms"] == expected_mean
    assert comp["L1"]["mean_vs_p95_ratio"] == round(expected_mean / 4000, 3)


def test_verdict_no_budget_when_band_missing_from_envelope() -> None:
    comp = _compute_latency_vs_budget(
        {"L4": [1000, 2000, 3000]},
        ENVELOPE_FIXTURE,  # has L1/L2/L3 only
    )
    assert comp["L4"]["verdict"] == LATENCY_VERDICT_NO_BUDGET
    assert comp["L4"]["p50_ms"] is None
    assert comp["L4"]["p95_ms"] is None
    assert comp["L4"]["mean_vs_p95_ratio"] is None


def test_bands_with_no_samples_are_omitted() -> None:
    comp = _compute_latency_vs_budget(
        {"L1": [], "L2": [3000]},
        ENVELOPE_FIXTURE,
    )
    assert "L1" not in comp
    assert "L2" in comp


# ---------------------------------------------------------------------------
# Integration with the eval runner
# ---------------------------------------------------------------------------


def test_run_eval_report_carries_comparison_by_risk_band(tmp_path: Path) -> None:
    """The deterministic smoke run must surface a populated comparison
    block alongside the existing samples_by_risk_band."""

    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="improved_v0",
    )
    envelope = report.synthetic_latency_envelope
    assert "comparison_by_risk_band" in envelope
    comparison = envelope["comparison_by_risk_band"]
    assert comparison, "deterministic smoke run must populate at least one band"

    # Deterministic runner is near-instant — every band should be well
    # inside the synthetic p50 budget.
    for band, row in comparison.items():
        assert row["verdict"] == LATENCY_VERDICT_WITHIN_P50, (
            f"deterministic profile latency in band {band} should be within p50; "
            f"got verdict={row['verdict']!r} (mean={row['measured_mean_ms']}ms)"
        )
        assert row["count"] >= 1
        assert row["p50_ms"] is not None
        assert row["p95_ms"] is not None


def test_run_eval_preserves_existing_latency_keys(tmp_path: Path) -> None:
    """Adding comparison_by_risk_band must not disturb existing
    consumers reading samples_by_risk_band / synthetic_planning_envelope."""

    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="improved_v0",
    )
    envelope = report.synthetic_latency_envelope
    assert "synthetic_planning_envelope" in envelope
    assert "measured_ms" in envelope
    assert "samples_by_risk_band" in envelope["measured_ms"]
    # Comparison and measured-samples bands match (or measured is a
    # superset; bands with no comparison budget still appear in
    # measured but become no_budget in comparison).
    measured_bands = set(envelope["measured_ms"]["samples_by_risk_band"])
    comparison_bands = set(envelope["comparison_by_risk_band"])
    assert comparison_bands == measured_bands
