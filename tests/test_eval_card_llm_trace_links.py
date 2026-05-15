"""Tests for the LLM-card trace-link safety fix.

The eval-card generator used to link to ``traces/local/llm_*`` paths
on cards comparing an LLM profile. Those raw paths embed real model
draft text and must never appear in a tracked / public artifact.
``scripts/generate_eval_card.py`` now picks the matching redacted
trace path (``traces/redacted/llm_*/<name>.redacted.json``) when one
exists, or falls back to a plain-text instruction. Deterministic
profiles continue to link directly.

These tests lock in:

1. LLM-profile cards contain zero ``traces/local/llm_`` substrings.
2. When the matching redacted trace exists, the card links to it.
3. When the redacted trace doesn't exist, the card emits the
   plain-text fallback instruction.
4. Deterministic profiles still keep their direct trace links.
5. The LLM card still surfaces failing case IDs and labels — the
   safety fix doesn't hide failures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.run import EvalReport, run_eval
from scripts.generate_eval_card import (
    REDACTED_LLM_TRACE_FALLBACK,
    _failing_case_block,
    _redacted_trace_path,
    render_card,
)


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
ADVERSARIAL_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)


# ---------------------------------------------------------------------------
# Pure path mapping
# ---------------------------------------------------------------------------


def test_redacted_trace_path_maps_llm_local_to_llm_redacted() -> None:
    raw = "traces/local/llm_adversarial/case_fl_adv_v0_002.json"
    assert (
        _redacted_trace_path(raw)
        == "traces/redacted/llm_adversarial/case_fl_adv_v0_002.redacted.json"
    )


def test_redacted_trace_path_returns_none_for_deterministic_traces() -> None:
    """Non-LLM trace paths must NOT be rewritten — those cards keep
    the direct link to their (deterministic, public-safe) trace."""

    assert _redacted_trace_path("traces/local/baseline_v0/case_fl_v0_005.json") is None
    assert _redacted_trace_path("traces/local/improved_v0/case_fl_v0_005.json") is None
    assert _redacted_trace_path("traces/redacted/llm_adversarial/x.redacted.json") is None


# ---------------------------------------------------------------------------
# LLM card never links to traces/local/llm_
# ---------------------------------------------------------------------------


def _make_llm_candidate(reference: EvalReport, fail_count: int = 4) -> EvalReport:
    """Build an LLM-shape candidate report by relabeling a deterministic
    one and injecting failing cases that would normally trigger the
    raw-trace link.

    We don't call the LLM; the card branch we're testing only inspects
    ``agent_system_version`` and ``per_case`` shape.
    """

    from evals.run import CaseEvalResult
    from app.schemas import GraderResult, Severity

    failing_cases = []
    for n in range(1, fail_count + 1):
        failing_cases.append(
            CaseEvalResult(
                case_id=f"case_fl_adv_v0_00{n}",
                workflow="financial_links_reliability",
                risk_band="L1",
                trace_path=f"traces/local/llm_adversarial/case_fl_adv_v0_00{n}.json",
                grader_results=[
                    GraderResult(
                        passed=False,
                        score=0.0,
                        severity=Severity.L2,
                        failure_label="UNSAFE_CUSTOMER_COMMS",
                        explanation="Synthetic test failure",
                        evidence={},
                    )
                ],
                failure_labels=["UNSAFE_CUSTOMER_COMMS"],
                evaluator_all_ok=False,
                approval_required=False,
                passed=False,
                latency_ms=6500,
                est_cost_usd=0.005,
            )
        )
    return reference.model_copy(
        update={
            "agent_system_version": "llm_candidate_v0",
            "per_case": failing_cases,
            "case_count": len(failing_cases),
            "passed_case_count": 0,
            "failed_case_count": len(failing_cases),
            "failure_label_counts": {"UNSAFE_CUSTOMER_COMMS": len(failing_cases)},
        }
    )


@pytest.fixture()
def reference_report(tmp_path: Path) -> EvalReport:
    return run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "ref",
        report_out=tmp_path / "ref.json",
        agent_system_version="improved_v0",
    )


def test_llm_card_contains_no_raw_local_llm_trace_links(
    reference_report: EvalReport,
) -> None:
    candidate = _make_llm_candidate(reference_report)
    text = render_card(reference_report, candidate)
    # The defining invariant: zero raw-LLM-trace substrings anywhere
    # in the card.
    assert "traces/local/llm_" not in text, (
        "LLM card must not link to traces/local/llm_*; those paths "
        "embed raw model output. Use the redacted trace path or the "
        "fallback instruction instead."
    )


def test_llm_card_falls_back_when_redacted_trace_missing(
    reference_report: EvalReport, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When traces/redacted/llm_adversarial/<x>.redacted.json doesn't
    exist on disk, the card emits the plain-text fallback. We force
    the existence check to fail by pointing REPO_ROOT at a tmp dir
    that's empty."""

    import scripts.generate_eval_card as gen

    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    candidate = _make_llm_candidate(reference_report)
    text = render_card(reference_report, candidate)
    assert REDACTED_LLM_TRACE_FALLBACK in text


def test_llm_card_links_to_redacted_trace_when_present(
    reference_report: EvalReport, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Materialize the matching redacted-trace files in tmp_path and
    swap REPO_ROOT — the card should now link to them."""

    import scripts.generate_eval_card as gen

    redacted_dir = tmp_path / "traces" / "redacted" / "llm_adversarial"
    redacted_dir.mkdir(parents=True)
    for n in range(1, 5):
        (redacted_dir / f"case_fl_adv_v0_00{n}.redacted.json").write_text("{}")

    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    candidate = _make_llm_candidate(reference_report)
    text = render_card(reference_report, candidate)
    for n in range(1, 5):
        rel = f"traces/redacted/llm_adversarial/case_fl_adv_v0_00{n}.redacted.json"
        assert rel in text, f"card missing link to redacted trace {rel}"
    # And the fallback instruction must NOT appear when every redacted
    # trace exists.
    assert REDACTED_LLM_TRACE_FALLBACK not in text


def test_llm_card_still_lists_failing_case_ids_and_labels(
    reference_report: EvalReport,
) -> None:
    """The trace-link safety fix must not hide which cases failed or
    which labels they tripped — those are the entire point of the
    failing-case section."""

    candidate = _make_llm_candidate(reference_report)
    text = render_card(reference_report, candidate)
    for n in range(1, 5):
        assert f"case_fl_adv_v0_00{n}" in text, (
            f"LLM card must list failing case_id case_fl_adv_v0_00{n}"
        )
    assert "UNSAFE_CUSTOMER_COMMS" in text


# ---------------------------------------------------------------------------
# Deterministic cards keep direct trace links
# ---------------------------------------------------------------------------


def test_deterministic_card_keeps_direct_trace_links(tmp_path: Path) -> None:
    baseline = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "b",
        report_out=tmp_path / "b.json",
        agent_system_version="baseline_v0",
    )
    improved = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "i",
        report_out=tmp_path / "i.json",
        agent_system_version="improved_v0",
    )
    text = render_card(baseline, improved)

    # At least one failing baseline case must have its direct trace path
    # as a link (the existing behavior).
    failing = [c for c in baseline.per_case if not c.passed]
    assert failing, "baseline_v0 smoke run must surface at least one failure"
    for case in failing:
        assert case.trace_path in text, (
            f"deterministic card must keep its direct link to {case.trace_path}"
        )


def test_failing_case_block_picks_redacted_path_in_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unit-level check on _failing_case_block alone — independent of
    the broader card-render path."""

    import scripts.generate_eval_card as gen
    from evals.run import CaseEvalResult
    from app.schemas import GraderResult, Severity

    redacted_dir = tmp_path / "traces" / "redacted" / "llm_adversarial"
    redacted_dir.mkdir(parents=True)
    (redacted_dir / "case_X.redacted.json").write_text("{}")
    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)

    case = CaseEvalResult(
        case_id="case_X",
        workflow="financial_links_reliability",
        risk_band="L1",
        trace_path="traces/local/llm_adversarial/case_X.json",
        grader_results=[
            GraderResult(
                passed=False,
                score=0.0,
                severity=Severity.L2,
                failure_label="UNSAFE_CUSTOMER_COMMS",
                explanation="x",
                evidence={},
            )
        ],
        failure_labels=["UNSAFE_CUSTOMER_COMMS"],
        evaluator_all_ok=False,
        approval_required=False,
        passed=False,
        latency_ms=1,
        est_cost_usd=0.0,
    )
    block = _failing_case_block(
        [case], agent_system_version="llm_candidate_v0"
    )
    assert "traces/local/llm_" not in block
    assert "traces/redacted/llm_adversarial/case_X.redacted.json" in block
