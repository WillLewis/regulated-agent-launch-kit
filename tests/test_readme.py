"""README assertions for the Phase 2 Synthetic Domain Model exit gate.

These are lightweight presence/discipline checks — they do not validate
prose quality, only that the documented contracts and public-safety
stance stay in the README as Phase 2 advances.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _readme() -> str:
    return (ROOT / "README.md").read_text()


def test_readme_has_synthetic_domain_model_section() -> None:
    readme = _readme()
    assert "## Synthetic Domain Model" in readme


def test_readme_domain_model_references_phase_2_contracts() -> None:
    readme = _readme()
    lower = readme.lower()
    assert "synthetic case" in lower
    assert "handoffpayload" in lower or "handoff payload" in lower
    assert "agentoutput" in lower
    assert "approval matrix" in lower
    assert "synthetic tools" in lower


def test_readme_notes_evaluator_grader_separation() -> None:
    readme = _readme()
    assert "EvaluatorReport" in readme
    assert "GraderResult" in readme
    lower = readme.lower()
    assert "runtime evaluator" in lower
    assert "offline grader" in lower


def test_readme_records_r8_approval_grading_asymmetry() -> None:
    readme = _readme()
    lower = readme.lower()
    assert "r8" in lower
    assert "approval_band_independent_of_declared" in readme


def test_readme_flags_latency_budgets_as_synthetic_not_production() -> None:
    readme = _readme()
    assert "configs/latency_budgets.yaml" in readme
    lower = readme.lower()
    assert "not production" in lower or "not production sla" in lower


def test_readme_avoids_pilot_or_production_readiness_claims() -> None:
    """Guard against the obvious overclaim phrases creeping in later.

    The forbidden list is intentionally narrow (positive-claim phrases
    only); broader words like "regulatory compliance" can legitimately
    appear inside a disclaimer ("does not imply regulatory compliance"),
    so they are not blocked here.
    """

    readme = _readme().lower()
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "ready for pilot",
        "ready for production",
    )
    for phrase in forbidden:
        assert phrase not in readme, f"README must not claim: {phrase!r}"
