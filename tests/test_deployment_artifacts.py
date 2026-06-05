"""Phase 1 deployment artifact tests.

Verifies that the Phase 1 deliverables under ``deployment/`` exist with
substantive content and no unresolved ``TODO:`` placeholders. These docs
are the foundation of the deployment-readiness narrative; thin or stub
docs defeat the purpose of doing Phase 1 before code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PHASE_1_DOCS = [
    "deployment/customer_workflow_map.md",
    "deployment/value_case.md",
    "deployment/kpi_tree.md",
    "deployment/acceptance_criteria.md",
    "deployment/risk_register.md",
    "deployment/dependency_map.md",
]


@pytest.mark.parametrize("doc", PHASE_1_DOCS)
def test_phase_1_doc_exists(doc: str) -> None:
    assert (ROOT / doc).exists(), doc


@pytest.mark.parametrize("doc", PHASE_1_DOCS)
def test_phase_1_doc_has_no_unresolved_todo(doc: str) -> None:
    content = (ROOT / doc).read_text()
    assert "TODO:" not in content, f"{doc} still contains a TODO: placeholder"


@pytest.mark.parametrize("doc", PHASE_1_DOCS)
def test_phase_1_doc_is_substantive(doc: str) -> None:
    content = (ROOT / doc).read_text()
    assert len(content) >= 1500, f"{doc} appears thin ({len(content)} chars)"


def test_workflow_map_covers_required_sections() -> None:
    content = (ROOT / "deployment/customer_workflow_map.md").read_text()
    for header in (
        "Current Manual Workflow",
        "Future-State",
        "Pain Points",
        "Stakeholders",
        "Decision Points",
        "Approval Points",
        "Human-Owned",
    ):
        assert header in content, header


def test_workflow_map_keeps_synthetic_only_stance() -> None:
    content = (ROOT / "deployment/customer_workflow_map.md").read_text().lower()
    assert "synthetic" in content


def test_value_case_links_outcomes_to_evidence() -> None:
    content = (ROOT / "deployment/value_case.md").read_text().lower()
    for keyword in ("hypothesis", "metric", "evidence"):
        assert keyword in content, keyword


def test_risk_register_lists_known_phase_1_risks() -> None:
    content = (ROOT / "deployment/risk_register.md").read_text().lower()
    for risk_keyword in (
        "consent",
        "evaluator",
        "schema",
        "latency",
        "redaction",
        "synthetic",
        "escalation",
    ):
        assert risk_keyword in content, risk_keyword


def test_plan_tracks_phase_status_and_locked_decisions() -> None:
    """PLAN.md must record per-phase status and the locked decisions.

    The Financial Links flagship local proof loop is complete through
    Phase 3; PLAN.md should still capture the next-step recommendation
    and the deferred items.
    """

    plan = (ROOT / "PLAN.md").read_text()
    for phase in ("Phase 1", "Phase 2", "Phase 3"):
        assert phase in plan, f"PLAN.md missing {phase!r}"

    plan_lower = plan.lower()
    assert "complete" in plan_lower
    # The "active" status was retired when Phase 3 closed; PLAN.md must
    # still surface what's next and what's deferred.
    assert "recommended" in plan_lower
    assert "deferred" in plan_lower
    assert "Locked Decisions" in plan, "PLAN.md must record locked decisions for Phase 2/3"


def test_readme_links_all_phase_1_docs() -> None:
    readme = (ROOT / "README.md").read_text()
    for doc in PHASE_1_DOCS:
        assert f"]({doc})" in readme, f"README missing markdown link to {doc}"


# --- Phase 2 deployment docs -------------------------------------------------
# The remaining deployment-leadership artifacts: a launch-decision review, an
# exec update, an adoption plan, a field-feedback log, and a delivery plan.
# They must be substantive, placeholder-free, synthetic-only, honestly
# pre-pilot, and grounded in generated artifacts — not narrative.

PHASE_2_DOCS = [
    "deployment/pilot_readiness_review.md",
    "deployment/exec_update.md",
    "deployment/adoption_plan.md",
    "deployment/field_feedback_to_product.md",
    "deployment/delivery_plan.md",
]

PHASE_2_REQUIRED_SECTIONS = {
    "deployment/pilot_readiness_review.md": [
        "## Ready",
        "## Blocked",
        "## Pilot Only With Constraints",
        "## Approval Boundaries",
        "## Monitored Metrics",
        "## Rollback Conditions",
    ],
    "deployment/exec_update.md": [
        "## Status",
        "## What Changed",
        "## Top Metric Movement",
        "## Top Unresolved Risk",
        "## Decision Needed",
        "## Recommendation",
        "## Next Milestone",
    ],
    "deployment/adoption_plan.md": [
        "## Pilot Users",
        "## Onboarding",
        "## Operating Cadence",
        "## Adoption Risks",
    ],
    "deployment/field_feedback_to_product.md": [
        "## Deployment Learnings",
        "## Product Feedback Categories",
        "## Feedback Loop",
    ],
    "deployment/delivery_plan.md": [
        "## Phases",
        "## Milestones",
        "## Review Gates",
    ],
}


@pytest.mark.parametrize("doc", PHASE_2_DOCS)
def test_phase_2_doc_exists(doc: str) -> None:
    assert (ROOT / doc).exists(), doc


@pytest.mark.parametrize("doc", PHASE_2_DOCS)
def test_phase_2_doc_has_no_unresolved_todo(doc: str) -> None:
    content = (ROOT / doc).read_text()
    assert "TODO:" not in content, f"{doc} still contains a TODO: placeholder"


@pytest.mark.parametrize("doc", PHASE_2_DOCS)
def test_phase_2_doc_is_substantive(doc: str) -> None:
    content = (ROOT / doc).read_text()
    assert len(content) >= 1500, f"{doc} appears thin ({len(content)} chars)"


@pytest.mark.parametrize("doc", PHASE_2_DOCS)
def test_phase_2_doc_keeps_synthetic_stance(doc: str) -> None:
    content = (ROOT / doc).read_text().lower()
    assert "synthetic" in content, doc


@pytest.mark.parametrize("doc", PHASE_2_DOCS)
def test_phase_2_doc_makes_no_readiness_overclaim(doc: str) -> None:
    lower = (ROOT / doc).read_text().lower()
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, f"{doc} overclaims: {forbidden!r}"


@pytest.mark.parametrize("doc", PHASE_2_DOCS)
def test_phase_2_doc_grounds_claims_in_artifacts(doc: str) -> None:
    """Each Phase 2 doc must reference at least one generated artifact or
    deployment doc path so readiness claims are traceable, not narrative."""

    content = (ROOT / doc).read_text()
    artifact_markers = (
        "reports/",
        "evidence_packs/",
        "configs/",
        "case_studies/",
        "deployment/",
    )
    assert any(marker in content for marker in artifact_markers), doc


@pytest.mark.parametrize(
    "doc,sections", list(PHASE_2_REQUIRED_SECTIONS.items())
)
def test_phase_2_doc_has_required_sections(doc: str, sections: list[str]) -> None:
    content = (ROOT / doc).read_text()
    for header in sections:
        assert header in content, f"{doc} missing section {header!r}"


def test_pilot_readiness_review_posture_and_approval_link() -> None:
    content = (ROOT / "deployment/pilot_readiness_review.md").read_text()
    assert "NOT READY FOR PILOT" in content
    assert "configs/approval_matrix.yaml" in content


def test_exec_update_holds_posture_and_recommends_no_pilot() -> None:
    content = (ROOT / "deployment/exec_update.md").read_text()
    assert "NOT READY FOR PILOT" in content
    assert "do not pilot" in content.lower(), "exec update must not recommend a pilot go"


def test_delivery_plan_has_owners_acceptance_gates_and_codex_reviews() -> None:
    content = (ROOT / "deployment/delivery_plan.md").read_text()
    assert "NOT READY FOR PILOT" in content
    assert "Codex" in content
    assert "acceptance gate" in content.lower()
    assert "deployment/acceptance_criteria.md" in content


def test_field_feedback_grounds_learnings_in_generated_artifacts() -> None:
    content = (ROOT / "deployment/field_feedback_to_product.md").read_text()
    assert "reports/llm_adversarial_v1_semantic_audit_summary.md" in content
    assert "regressions_semantic_adversarial_v1" in content
