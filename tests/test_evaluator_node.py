"""Runtime EvaluatorNode tests for Phase 2 contracts.

These tests exercise the schema, consent-boundary, and approval checks
the EvaluatorNode performs before final response composition. Offline
grader behavior lives in ``tests/test_graders.py`` — keep the two
suites separate so we can measure evaluator catch rate later.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.evaluator import evaluate
from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    ApprovalStatus,
    ConsentState,
    EvaluatorReport,
    RiskBand,
    Workflow,
)


ROOT = Path(__file__).resolve().parents[1]


def _approval_matrix() -> dict:
    return yaml.safe_load((ROOT / "configs" / "approval_matrix.yaml").read_text())


def _l2_consent_sensitive_draft(
    *,
    consent_state: ConsentState,
    consent_reconfirmed: bool,
    approval_required: bool,
) -> AgentOutput:
    return AgentOutput(
        case_id="case_l2_consent",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        declared_risk_band=RiskBand.L2,
        consent_state=consent_state,
        consent_reconfirmed=consent_reconfirmed,
        draft_text="Synthetic draft for analyst review.",
        approval=ApprovalDecision(
            required=approval_required,
            status=ApprovalStatus.PENDING if approval_required else ApprovalStatus.NOT_REQUIRED,
            approver_role="partner_support_analyst" if approval_required else None,
        ),
    )


def test_evaluator_returns_evaluator_report_type() -> None:
    output = _l2_consent_sensitive_draft(
        consent_state=ConsentState.GRANTED,
        consent_reconfirmed=True,
        approval_required=False,
    )
    report = evaluate(output, approval_matrix=_approval_matrix())
    assert isinstance(report, EvaluatorReport)


def test_evaluator_blocks_l2_consent_sensitive_without_reconfirmation() -> None:
    """PLAN.md R1: L2 consent-sensitive output without reconfirmation must fail."""

    output = _l2_consent_sensitive_draft(
        consent_state=ConsentState.EXPIRED,
        consent_reconfirmed=False,
        approval_required=False,
    )
    report = evaluate(output, approval_matrix=_approval_matrix())
    consent = next(c for c in report.checks if c.name == "consent_boundary")
    assert consent.ok is False
    assert report.all_ok is False


def test_evaluator_passes_l2_consent_sensitive_with_reconfirmation() -> None:
    output = _l2_consent_sensitive_draft(
        consent_state=ConsentState.EXPIRED,
        consent_reconfirmed=True,
        approval_required=False,
    )
    report = evaluate(output, approval_matrix=_approval_matrix())
    consent = next(c for c in report.checks if c.name == "consent_boundary")
    assert consent.ok is True


def test_evaluator_passes_l2_consent_sensitive_with_approval_required() -> None:
    output = _l2_consent_sensitive_draft(
        consent_state=ConsentState.INSUFFICIENT,
        consent_reconfirmed=False,
        approval_required=True,
    )
    report = evaluate(output, approval_matrix=_approval_matrix())
    consent = next(c for c in report.checks if c.name == "consent_boundary")
    assert consent.ok is True


def test_evaluator_flags_missing_approval_when_matrix_requires_it() -> None:
    output = _l2_consent_sensitive_draft(
        consent_state=ConsentState.GRANTED,
        consent_reconfirmed=True,
        approval_required=False,
    )
    report = evaluate(output, approval_matrix=_approval_matrix())
    approval = next(c for c in report.checks if c.name == "approval_requirement")
    assert approval.ok is False, "matrix requires approval at L2 financial_links but output omitted it"


def test_evaluator_dict_path_still_runs_schema_check_only() -> None:
    """The legacy dict path must remain to avoid breaking earlier callers."""

    report = evaluate({"summary": "ok"}, required_fields=["summary", "risk_band"])
    assert isinstance(report, EvaluatorReport)
    assert report.all_ok is False
    names = {c.name for c in report.checks}
    assert names == {"schema_required_fields"}
