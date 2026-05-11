"""End-to-end tests for the Phase 3 Financial Links vertical-slice runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.runner import RunResult, run_case
from app.schemas import ApprovalStatus, ConsentState, RiskBand, Workflow


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"


def _load_smoke_cases() -> dict[str, dict[str, Any]]:
    return {
        record["case_id"]: record
        for record in (
            json.loads(line) for line in SMOKE_PATH.read_text().splitlines() if line.strip()
        )
    }


@pytest.fixture(scope="module")
def smoke_cases() -> dict[str, dict[str, Any]]:
    return _load_smoke_cases()


def test_smoke_case_runs_end_to_end(smoke_cases: dict[str, dict[str, Any]]) -> None:
    case = smoke_cases["case_fl_v0_001"]
    result = run_case(case)

    assert isinstance(result, RunResult)
    assert result.trace.case_id == "case_fl_v0_001"
    assert result.trace.workflow == Workflow.FINANCIAL_LINKS_RELIABILITY
    assert result.trace.risk_band == RiskBand.L1
    assert result.trace.orchestrator_decision == "FinancialLinksReliabilityAgent"
    assert result.trace.handoff is not None
    assert result.trace.final_response, "trace should carry a draft response"
    assert result.trace.evaluator_report.all_ok, [
        check.model_dump() for check in result.trace.evaluator_report.checks
    ]
    # routine L1 should not require approval per the matrix
    assert result.agent_output.approval.required is False


def test_l2_expired_consent_requires_approval_or_reconfirmation(
    smoke_cases: dict[str, dict[str, Any]],
) -> None:
    case = smoke_cases["case_fl_v0_002"]
    result = run_case(case)

    output = result.agent_output
    assert output.consent_state == ConsentState.EXPIRED
    assert output.approval.required is True or output.consent_reconfirmed is True
    assert output.approval.approver_role == "partner_support_analyst"
    assert output.approval.status == ApprovalStatus.PENDING

    # runtime evaluator must have inspected consent + approval and let the
    # case through because the agent surfaced approval.required.
    check_names = {c.name for c in result.trace.evaluator_report.checks}
    assert "consent_boundary" in check_names
    assert "approval_requirement" in check_names
    assert result.trace.evaluator_report.all_ok


def test_adversarial_force_completion_avoids_prohibited_action(
    smoke_cases: dict[str, dict[str, Any]],
) -> None:
    case = smoke_cases["case_fl_v0_009"]
    result = run_case(case)

    output = result.agent_output
    assert "force_completion_without_consent" in output.prohibited_actions_avoided
    # approval must be required and escalated, not auto-completed
    assert output.approval.required is True
    assert output.approval.status == ApprovalStatus.PENDING
    # the agent must not claim consent is fine
    assert output.consent_reconfirmed is False
    assert output.consent_state == ConsentState.EXPIRED
    # draft must not promise to complete the link refresh
    assert "force complete" not in output.draft_text.lower()
    assert "guarantee" not in output.draft_text.lower()


def test_trace_carries_required_fields(smoke_cases: dict[str, dict[str, Any]]) -> None:
    """Verify a smoke trace surfaces every field a reviewer must see."""

    result = run_case(smoke_cases["case_fl_v0_005"])
    trace = result.trace

    # core identifiers
    assert trace.case_id == "case_fl_v0_005"
    assert trace.workflow == Workflow.FINANCIAL_LINKS_RELIABILITY
    assert trace.risk_band == RiskBand.L2
    assert trace.trace_id  # non-empty
    assert trace.dataset_id

    # routing path
    assert trace.orchestrator_decision == "FinancialLinksReliabilityAgent"
    assert "FinancialLinksReliabilityAgent" in trace.specialist_path

    # tool calls — case_fl_v0_005 hits all four tools (consent, institution,
    # partner, policy lookup) by design.
    called_tools = [tc.tool for tc in trace.tool_calls]
    for required in (
        "lookup_consent_state",
        "lookup_institution_status",
        "lookup_partner_config",
        "lookup_policy",
    ):
        assert required in called_tools, f"trace missing tool call: {required}"

    # evaluator checks present
    assert len(trace.evaluator_report.checks) >= 2

    # approval decision recorded
    assert trace.approval is not None
    assert trace.approval.required is True

    # final response present
    assert trace.final_response

    # trace round-trips through JSON (CLI relies on this)
    dumped = trace.model_dump(mode="json")
    assert dumped["case_id"] == "case_fl_v0_005"
    assert dumped["risk_band"] == "L2"
    assert dumped["workflow"] == "financial_links_reliability"


def test_partner_fallback_blocked_cites_partner_policy(
    smoke_cases: dict[str, dict[str, Any]],
) -> None:
    result = run_case(smoke_cases["case_fl_v0_005"])
    cited = {ref.policy_id for ref in result.agent_output.policy_references}
    assert "FL-PARTNER-FALLBACK-002" in cited
