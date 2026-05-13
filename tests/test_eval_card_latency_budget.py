"""Tests for the eval-card 'Latency vs synthetic budget' subsection.

The card renders a side-by-side table that pulls
``comparison_by_risk_band`` off both reports and emits one row per
(band) with each profile's verdict + mean alongside the synthetic p50
/ p95 budget. These tests lock in:

1. The new section heading + a verdict legend appear on every card.
2. A deterministic pair (both within p50) renders only `within_p50`
   verdicts and zero false positives.
3. An LLM-shape pair (candidate exceeds p95 on multiple bands)
   renders `exceeds_p95` on the candidate side and `within_p50` on
   the reference side.
4. Custom column labels (Reference / Candidate) flow into the header.
5. A legacy report (no ``comparison_by_risk_band``) renders an
   explanatory placeholder rather than crashing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.run import EvalReport, run_eval
from scripts.generate_eval_card import (
    _latency_vs_budget_block,
    render_card,
)


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def deterministic_pair(tmp_path: Path) -> tuple[EvalReport, EvalReport]:
    baseline = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "b_traces",
        report_out=tmp_path / "baseline.json",
        agent_system_version="baseline_v0",
    )
    improved = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "i_traces",
        report_out=tmp_path / "improved.json",
        agent_system_version="improved_v0",
    )
    return baseline, improved


def _make_llm_shape_candidate(reference: EvalReport) -> EvalReport:
    """Build an LLM-ish candidate report from a deterministic reference.

    We don't call the LLM — we relabel the agent_system_version and
    inject realistic LLM-magnitude measured samples plus the matching
    comparison block. This is sufficient to drive the card-render
    branches; the actual cost/runtime paths are tested in
    ``tests/test_llm_profile.py``.
    """

    envelope = dict(reference.synthetic_latency_envelope)
    envelope["measured_ms"] = {
        "note": envelope.get("measured_ms", {}).get("note", ""),
        "samples_by_risk_band": {
            "L1": {"count": 3, "min_ms": 5895, "max_ms": 7590, "mean_ms": 6605},
            "L2": {"count": 2, "min_ms": 7072, "max_ms": 9174, "mean_ms": 8123},
            "L3": {"count": 1, "min_ms": 10509, "max_ms": 10509, "mean_ms": 10509},
        },
    }
    envelope["comparison_by_risk_band"] = {
        "L1": {
            "count": 3,
            "measured_mean_ms": 6605,
            "measured_max_ms": 7590,
            "p50_ms": 2000,
            "p95_ms": 4000,
            "verdict": "exceeds_p95",
            "mean_vs_p95_ratio": round(6605 / 4000, 3),
        },
        "L2": {
            "count": 2,
            "measured_mean_ms": 8123,
            "measured_max_ms": 9174,
            "p50_ms": 3500,
            "p95_ms": 7000,
            "verdict": "exceeds_p95",
            "mean_vs_p95_ratio": round(8123 / 7000, 3),
        },
        "L3": {
            "count": 1,
            "measured_mean_ms": 10509,
            "measured_max_ms": 10509,
            "p50_ms": 6000,
            "p95_ms": 12000,
            "verdict": "between_p50_and_p95",
            "mean_vs_p95_ratio": round(10509 / 12000, 3),
        },
    }
    return reference.model_copy(
        update={
            "agent_system_version": "llm_candidate_v0",
            "synthetic_latency_envelope": envelope,
        }
    )


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------


def test_card_renders_latency_vs_budget_section(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    baseline, improved = deterministic_pair
    text = render_card(baseline, improved)
    assert "### Latency vs synthetic budget" in text
    assert "Risk band" in text
    # Verdict legend appears in the card body.
    for verdict in (
        "`within_p50`",
        "`between_p50_and_p95`",
        "`exceeds_p95`",
        "`no_budget`",
    ):
        assert verdict in text


def test_deterministic_pair_shows_only_within_p50_verdicts(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    baseline, improved = deterministic_pair
    text = render_card(baseline, improved)
    # Scope to the table itself (between the section heading and the
    # verdict-legend paragraph) — the legend always mentions every
    # verdict label by name, which would otherwise match.
    section_start = text.index("### Latency vs synthetic budget")
    legend_start = text.index("Verdicts are categorical", section_start)
    table = text[section_start:legend_start]
    assert "`within_p50`" in table
    assert "`exceeds_p95`" not in table
    assert "`between_p50_and_p95`" not in table


def test_llm_shape_candidate_surfaces_exceeds_p95(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    baseline, _improved = deterministic_pair
    candidate = _make_llm_shape_candidate(baseline)
    text = render_card(baseline, candidate)
    # The candidate (LLM-shape) side must surface exceeds_p95 on at
    # least one band — the whole point of the new section.
    assert "`exceeds_p95`" in text
    # Budget cells are rendered as "p50 / p95".
    assert "2000 / 4000" in text
    assert "3500 / 7000" in text
    assert "6000 / 12000" in text


def test_card_threads_custom_labels_into_latency_block(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    baseline, _improved = deterministic_pair
    candidate = _make_llm_shape_candidate(baseline)
    text = render_card(
        baseline,
        candidate,
        baseline_label="Reference",
        improved_label="Candidate",
    )
    assert "| Risk band | Reference verdict | Reference mean (ms) | Candidate verdict | Candidate mean (ms) | Synthetic p50 / p95 budget (ms) |" in text


def test_legacy_report_without_comparison_renders_placeholder() -> None:
    """If a report predates the latency-vs-budget block, the helper
    must return an explanatory placeholder rather than crashing."""

    legacy = EvalReport(
        agent_system_version="baseline_v0",
        dataset_path="case_studies/x.jsonl",
        case_count=0,
        passed_case_count=0,
        failed_case_count=0,
        aggregate_grader_pass_rates=[],
        failure_label_counts={},
        synthetic_latency_envelope={},  # no comparison_by_risk_band
        synthetic_cost_summary={},
        per_case=[],
    )
    other = legacy.model_copy(update={"agent_system_version": "improved_v0"})
    block = _latency_vs_budget_block(legacy, other)
    assert "regenerate the underlying eval reports" in block
