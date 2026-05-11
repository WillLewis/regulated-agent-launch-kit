"""Phase 2 schema contract tests.

These tests lock in the synthetic domain model so the runtime evaluator
and the offline graders have a stable surface to reason about.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    ApprovalStatus,
    Case,
    ConsentState,
    EvaluatorReport,
    GraderResult,
    HandoffPayload,
    PolicyReference,
    RiskBand,
    ToolCall,
    TraceRecord,
    Workflow,
)


def test_phase_2_models_are_importable() -> None:
    assert Workflow.FINANCIAL_LINKS_RELIABILITY.value == "financial_links_reliability"
    assert ConsentState.GRANTED.value == "granted"
    assert ApprovalStatus.NOT_REQUIRED.value == "not_required"


def test_handoff_payload_requires_consent_risk_and_route_context() -> None:
    """PLAN.md R9: handoff is Pydantic-enforced, not validated only at trace time."""

    with pytest.raises(ValidationError) as excinfo:
        HandoffPayload(
            case_id="case_001",
            workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
            from_node="OrchestratorAgent",
            to_agent="FinancialLinksReliabilityAgent",
            declared_risk_band=RiskBand.L2,
            # consent_state, route_context intentionally omitted
        )

    missing = {err["loc"][0] for err in excinfo.value.errors()}
    assert "consent_state" in missing
    assert "route_context" in missing


def test_handoff_payload_accepts_full_context() -> None:
    handoff = HandoffPayload(
        case_id="case_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        from_node="OrchestratorAgent",
        to_agent="FinancialLinksReliabilityAgent",
        declared_risk_band=RiskBand.L2,
        consent_state=ConsentState.GRANTED,
        consent_reconfirmed=False,
        route_context={"institution_id": "inst_synth_001"},
    )
    assert handoff.consent_state is ConsentState.GRANTED
    assert handoff.route_context["institution_id"] == "inst_synth_001"


def test_agent_output_makes_consent_first_class() -> None:
    """PLAN.md R1: consent_state and consent_reconfirmed are first-class."""

    output = AgentOutput(
        case_id="case_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        declared_risk_band=RiskBand.L1,
        consent_state=ConsentState.GRANTED,
        consent_reconfirmed=False,
        draft_text="Synthetic hedged draft for analyst review.",
        approval=ApprovalDecision(required=False),
    )
    fields = AgentOutput.model_fields
    assert "consent_state" in fields
    assert "consent_reconfirmed" in fields
    assert output.approval.status is ApprovalStatus.NOT_REQUIRED


def test_evaluator_and_grader_types_remain_distinct() -> None:
    """AGENTS.md non-negotiable: separation of runtime evaluator vs offline grader."""

    assert EvaluatorReport is not GraderResult
    grader_fields = set(GraderResult.model_fields)
    evaluator_fields = set(EvaluatorReport.model_fields)
    assert {"passed", "score", "severity", "failure_label", "explanation", "evidence"} <= grader_fields
    assert "passed" not in evaluator_fields
    assert "score" not in evaluator_fields


def test_trace_record_round_trips() -> None:
    trace = TraceRecord(
        trace_id="trace_001",
        dataset_id="financial_links_v0",
        case_id="case_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        risk_band=RiskBand.L2,
        agent_system_version="baseline_v0",
        policy_version="financial_links_policies_v0",
        orchestrator_decision="route:FinancialLinksReliabilityAgent",
        specialist_path=["FinancialLinksReliabilityAgent"],
        tool_calls=[ToolCall(tool="lookup_consent_state", output={"consent_state": "granted"})],
    )
    again = TraceRecord.model_validate(trace.model_dump())
    assert again.case_id == "case_001"
    assert again.workflow is Workflow.FINANCIAL_LINKS_RELIABILITY


def test_case_carries_consent_sensitive_flag() -> None:
    case = Case(
        case_id="case_l2_consent",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        risk_band=RiskBand.L2,
        consent_sensitive=True,
    )
    assert case.consent_sensitive is True


def test_policy_reference_defaults_retrieved_true() -> None:
    ref = PolicyReference(policy_id="FL-CONSENT-001")
    assert ref.retrieved is True
    assert ref.version == "v0"
