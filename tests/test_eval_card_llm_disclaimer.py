"""Tests for the conditional eval-card disclaimer + operational rider.

The card's top disclaimer (and its operational-metrics rider) used to
hard-code 'no LLM call' / 'makes no model calls'. That's false on cards
that compare an LLM profile to a deterministic reference (or any pair
where at least one profile is ``llm_candidate_v0``). These tests lock
in:

1. Deterministic pairs (e.g. ``baseline_v0`` vs ``improved_v0``) keep
   the original ``SYNTHETIC_DISCLAIMER`` and the original operational
   rider verbatim — so existing card outputs and existing tests stay
   byte-equivalent.
2. Any pair that includes an LLM profile renders the new
   ``LLM_SYNTHETIC_DISCLAIMER`` and a rider that does *not* claim the
   runner made no model calls.
3. The new disclaimer remains synthetic-only and makes no model-safety
   / pilot / production claim.

The tests avoid real LLM calls by swapping the ``agent_system_version``
on an in-memory ``EvalReport`` built from a deterministic run; the
disclaimer logic only inspects that field, so the swap is sufficient.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.run import EvalReport, run_eval
from scripts.generate_eval_card import (
    LLM_SYNTHETIC_DISCLAIMER,
    SYNTHETIC_DISCLAIMER,
    _is_llm_profile,
    render_card,
)


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)


@pytest.fixture()
def deterministic_pair(tmp_path: Path) -> tuple[EvalReport, EvalReport]:
    baseline_path = tmp_path / "baseline.json"
    improved_path = tmp_path / "improved.json"
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline_path,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=improved_path,
        agent_system_version="improved_v0",
    )
    baseline = EvalReport.model_validate_json(baseline_path.read_text())
    improved = EvalReport.model_validate_json(improved_path.read_text())
    return baseline, improved


@pytest.fixture()
def llm_pair(tmp_path: Path) -> tuple[EvalReport, EvalReport]:
    """Reference (improved_v0) vs a stand-in 'llm_candidate_v0' candidate.

    We never actually call the LLM here. We run the deterministic
    `improved_v0` profile twice, then relabel the second report's
    `agent_system_version` so the disclaimer branch sees an LLM profile.
    The disclaimer logic only inspects that label, so this fully
    exercises the conditional.
    """

    reference_path = tmp_path / "reference.json"
    candidate_path = tmp_path / "candidate.json"
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "reference_traces",
        report_out=reference_path,
        agent_system_version="improved_v0",
    )
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "candidate_traces",
        report_out=candidate_path,
        agent_system_version="baseline_v0",
    )
    reference = EvalReport.model_validate_json(reference_path.read_text())
    candidate = EvalReport.model_validate_json(candidate_path.read_text())
    candidate = candidate.model_copy(update={"agent_system_version": "llm_candidate_v0"})
    return reference, candidate


def test_is_llm_profile_recognizes_llm_candidate_v0() -> None:
    assert _is_llm_profile("llm_candidate_v0")
    # Convention is the `llm_` prefix.
    assert _is_llm_profile("llm_anything_else")
    assert not _is_llm_profile("baseline_v0")
    assert not _is_llm_profile("improved_v0")
    assert not _is_llm_profile("")


def test_deterministic_pair_keeps_original_disclaimer_and_rider(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    baseline, improved = deterministic_pair
    text = render_card(baseline, improved)
    assert SYNTHETIC_DISCLAIMER in text, (
        "deterministic pair must still render the original SYNTHETIC_DISCLAIMER "
        "byte-equivalent so existing cards and tests stay green"
    )
    assert LLM_SYNTHETIC_DISCLAIMER not in text
    # Original operational rider phrase must be present unchanged.
    assert "makes no model calls" in text
    # Original launch-posture rider phrase must be present unchanged.
    assert "(so cost and latency become meaningful)" in text


def test_llm_pair_swaps_in_llm_disclaimer_and_rider(
    llm_pair: tuple[EvalReport, EvalReport],
) -> None:
    reference, candidate = llm_pair
    text = render_card(reference, candidate)
    assert LLM_SYNTHETIC_DISCLAIMER in text, (
        "LLM-paired card must use the LLM-aware top disclaimer"
    )
    assert SYNTHETIC_DISCLAIMER not in text, (
        "LLM-paired card must NOT carry the deterministic 'no LLM call' disclaimer"
    )
    # Operational rider phrase that would be a lie for an LLM run must be gone.
    assert "makes no model calls" not in text
    # And the new rider must acknowledge a real LLM call on at least one profile.
    assert "real LLM call on at least one\nprofile" in text or (
        "real LLM call on at least one profile" in text
    )
    # Launch-posture rider must reflect that a model is in the pair already.
    assert "(so cost and latency become meaningful)" not in text
    assert "owes: LLM cost capture" not in text
    assert "redacted evidence pack covering the LLM" not in text
    assert "estimated LLM cost" in text
    assert "redacted evidence pack" in text


def test_llm_disclaimer_keeps_public_safety_stance(
    llm_pair: tuple[EvalReport, EvalReport],
) -> None:
    reference, candidate = llm_pair
    text = render_card(reference, candidate).lower()
    # Synthetic / no-claim language must still be there.
    assert "synthetic" in text
    assert "no production-readiness" in text or "no production" in text
    # No positive readiness or model-safety claims.
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
        "regulatory-compliant",
    )
    for phrase in forbidden:
        assert phrase not in text, f"LLM card must not claim {phrase!r}"
    # And the launch posture must remain NOT READY FOR PILOT.
    assert "not ready for pilot" in text


def test_llm_disclaimer_module_constant_is_distinct_and_truthful() -> None:
    assert LLM_SYNTHETIC_DISCLAIMER != SYNTHETIC_DISCLAIMER
    assert "no LLM call" not in LLM_SYNTHETIC_DISCLAIMER
    assert "llm_candidate_v0" in LLM_SYNTHETIC_DISCLAIMER
    assert "draft_text" in LLM_SYNTHETIC_DISCLAIMER
