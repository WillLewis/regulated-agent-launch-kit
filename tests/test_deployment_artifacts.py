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


def test_plan_marks_phase_1_complete_and_phase_2_active() -> None:
    plan = (ROOT / "PLAN.md").read_text()
    assert "Phase 1" in plan
    assert "Phase 2" in plan
    plan_lower = plan.lower()
    assert "complete" in plan_lower
    assert "active" in plan_lower
    assert "Locked Decisions" in plan, "PLAN.md must record locked decisions for Phase 2/3"


def test_readme_links_all_phase_1_docs() -> None:
    readme = (ROOT / "README.md").read_text()
    for doc in PHASE_1_DOCS:
        assert f"]({doc})" in readme, f"README missing markdown link to {doc}"
