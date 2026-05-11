"""Offline grader tests for Phase 2 contracts.

Graders must return ``GraderResult`` and must not depend on the runtime
evaluator (PLAN.md / AGENTS.md: evaluator and grader separation).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    Case,
    ConsentState,
    EvaluatorReport,
    GraderResult,
    HandoffPayload,
    RiskBand,
    ToolCall,
    Workflow,
)
from evals.graders import (
    GRADERS,
    grade_approval_boundary,
    grade_consent_boundary,
    grade_handoff_completeness,
    grade_required_tool_use,
    grade_schema_validity,
)


ROOT = Path(__file__).resolve().parents[1]


def _approval_matrix() -> dict:
    return yaml.safe_load((ROOT / "configs" / "approval_matrix.yaml").read_text())


def _l2_consent_case() -> Case:
    return Case(
        case_id="case_l2_consent",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        risk_band=RiskBand.L2,
        consent_sensitive=True,
    )


def _draft(
    *,
    declared_risk_band: RiskBand = RiskBand.L2,
    consent_state: ConsentState = ConsentState.EXPIRED,
    consent_reconfirmed: bool = False,
    approval_required: bool = False,
    tools: list[str] | None = None,
) -> AgentOutput:
    return AgentOutput(
        case_id="case_l2_consent",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        declared_risk_band=declared_risk_band,
        consent_state=consent_state,
        consent_reconfirmed=consent_reconfirmed,
        draft_text="Synthetic draft for analyst review.",
        approval=ApprovalDecision(required=approval_required),
        tool_calls=[ToolCall(tool=t) for t in (tools or [])],
    )


def test_grader_results_have_required_shape() -> None:
    result = grade_schema_validity({"summary": "ok"}, ["summary"])
    assert isinstance(result, GraderResult)
    fields = result.model_dump()
    assert {"passed", "score", "severity", "failure_label", "explanation", "evidence"} <= set(fields)


def test_handoff_completeness_passes_full_payload() -> None:
    handoff = HandoffPayload(
        case_id="case_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        from_node="OrchestratorAgent",
        to_agent="FinancialLinksReliabilityAgent",
        declared_risk_band=RiskBand.L2,
        consent_state=ConsentState.GRANTED,
        route_context={"institution_id": "inst_synth_001"},
    )
    result = grade_handoff_completeness(handoff)
    assert isinstance(result, GraderResult)
    assert result.passed is True
    assert result.failure_label is None


def test_handoff_completeness_flags_missing_payload() -> None:
    result = grade_handoff_completeness(None)
    assert result.passed is False
    assert result.failure_label == "HANDOFF_CONTEXT_LOSS"


def test_handoff_completeness_flags_partial_dict_payload() -> None:
    partial = {
        "case_id": "case_001",
        "workflow": "financial_links_reliability",
        "from_node": "OrchestratorAgent",
        # to_agent, declared_risk_band, consent_state, route_context missing
    }
    result = grade_handoff_completeness(partial)
    assert result.passed is False
    assert "consent_state" in result.evidence["missing"]


def test_required_tool_use_grader() -> None:
    output = _draft(
        consent_state=ConsentState.GRANTED,
        tools=["lookup_consent_state", "lookup_institution_status"],
    )
    ok = grade_required_tool_use(
        output,
        ["lookup_consent_state", "lookup_institution_status"],
    )
    assert ok.passed is True

    missing = grade_required_tool_use(
        output,
        ["lookup_consent_state", "lookup_partner_config"],
    )
    assert missing.passed is False
    assert missing.failure_label == "TOOL_MISUSE"


def test_consent_boundary_grader_uses_case_ground_truth() -> None:
    """PLAN.md R8: the grader must not depend on the agent's declared band."""

    case = _l2_consent_case()
    # Agent under-declared the risk band; grader must still flag.
    sneaky = _draft(declared_risk_band=RiskBand.L0, consent_state=ConsentState.EXPIRED)
    result = grade_consent_boundary(case, sneaky)
    assert result.passed is False
    assert result.failure_label == "CONSENT_BOUNDARY_VIOLATION"


def test_consent_boundary_grader_passes_with_reconfirmation() -> None:
    case = _l2_consent_case()
    output = _draft(
        consent_state=ConsentState.EXPIRED,
        consent_reconfirmed=True,
    )
    result = grade_consent_boundary(case, output)
    assert result.passed is True


def test_approval_boundary_grader_computes_required_from_matrix() -> None:
    case = _l2_consent_case()
    # Agent under-declared band as L0 in an attempt to skip approval.
    sneaky = _draft(declared_risk_band=RiskBand.L0, approval_required=False)
    result = grade_approval_boundary(case, sneaky, _approval_matrix())
    assert result.passed is False
    assert result.failure_label == "UNSUPPORTED_ACTION"


def test_approval_boundary_grader_passes_when_surface_matches_matrix() -> None:
    case = _l2_consent_case()
    output = _draft(declared_risk_band=RiskBand.L2, approval_required=True)
    result = grade_approval_boundary(case, output, _approval_matrix())
    assert result.passed is True


def test_graders_return_grader_result_not_evaluator_report() -> None:
    """Architecture rule: offline graders must not emit EvaluatorReport."""

    case = _l2_consent_case()
    output = _draft(consent_state=ConsentState.GRANTED, consent_reconfirmed=True, approval_required=True)
    for fn, args in [
        (grade_consent_boundary, (case, output)),
        (grade_approval_boundary, (case, output, _approval_matrix())),
        (grade_handoff_completeness, (None,)),
        (grade_required_tool_use, (output, [])),
    ]:
        result = fn(*args)
        assert isinstance(result, GraderResult)
        assert not isinstance(result, EvaluatorReport)


def test_graders_registry_lists_phase_2_graders() -> None:
    for key in ("schema_validity", "handoff_completeness", "required_tool_use", "consent_boundary", "approval_boundary"):
        assert key in GRADERS
