"""Deterministic single-case runner for the Phase 3 Financial Links slice.

This is the minimal vertical slice: IntakeNormalizer → OrchestratorAgent →
FinancialLinksReliabilityAgent → EvaluatorNode → TraceRecord. There is no
LangGraph dependency yet — the goal of this slice is to wire the schemas,
synthetic tools, runtime evaluator, and trace artifact together so the
offline graders have something honest to score.

Functions exposed:

- ``run_case(case_dict, ...)`` — runs one case and returns a ``RunResult``
  wrapping the ``AgentOutput`` and the ``TraceRecord``.
- ``load_default_approval_matrix()`` — reads ``configs/approval_matrix.yaml``.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.agents import financial_links_reliability_agent
from app.agents.profiles import DEFAULT_PROFILE, normalize_profile
from app.evaluator import evaluate
from app.schemas import (
    AgentOutput,
    Case,
    ConsentState,
    HandoffPayload,
    RiskBand,
    TraceRecord,
    Workflow,
)
from app.tools.synthetic_connectivity_tools import lookup_consent_state


REPO_ROOT = Path(__file__).resolve().parents[1]
_APPROVAL_MATRIX_PATH = REPO_ROOT / "configs" / "approval_matrix.yaml"

# Required-field list passed to the runtime evaluator's schema check.
_AGENT_OUTPUT_REQUIRED_FIELDS: list[str] = [
    "case_id",
    "workflow",
    "declared_risk_band",
    "consent_state",
    "draft_text",
    "approval",
]


_SPECIALIST_FOR_WORKFLOW: dict[Workflow, str] = {
    Workflow.FINANCIAL_LINKS_RELIABILITY: "FinancialLinksReliabilityAgent",
}


class RunResult(BaseModel):
    """Wraps the trace and the underlying agent output from one run."""

    trace: TraceRecord
    agent_output: AgentOutput


def load_default_approval_matrix() -> dict[str, Any]:
    return yaml.safe_load(_APPROVAL_MATRIX_PATH.read_text())


def run_case(
    case_dict: dict[str, Any],
    approval_matrix: dict[str, Any] | None = None,
    *,
    agent_system_version: str = DEFAULT_PROFILE.value,
    policy_version: str = "financial_links_policies_v0",
    dataset_id: str | None = None,
) -> RunResult:
    """Run one Financial Links case end-to-end.

    ``agent_system_version`` selects the agent-system profile (see
    ``app.agents.profiles``); the value is also recorded on the trace.

    The function is intentionally deterministic. It does not call any
    external API, model, or service. All tool calls are synthetic.
    """

    profile = normalize_profile(agent_system_version)
    matrix = approval_matrix or load_default_approval_matrix()

    case = _build_case(case_dict)
    dataset_id_value = dataset_id or case_dict.get("dataset_id") or "unknown_dataset"

    if case.workflow not in _SPECIALIST_FOR_WORKFLOW:
        raise NotImplementedError(
            f"Phase 3 runner only supports workflow "
            f"{Workflow.FINANCIAL_LINKS_RELIABILITY.value}; got {case.workflow.value}"
        )
    specialist = _SPECIALIST_FOR_WORKFLOW[case.workflow]

    # IntakeNormalizer: read the user_id, derive the orchestrator's initial
    # picture of consent. The synthetic tool is the canonical source.
    user_id = case.payload.get("user_id")
    initial_consent_state = _initial_consent_state(user_id)

    handoff = HandoffPayload(
        case_id=case.case_id,
        workflow=case.workflow,
        from_node="OrchestratorAgent",
        to_agent=specialist,
        declared_risk_band=case.risk_band,
        consent_state=initial_consent_state,
        consent_reconfirmed=False,
        route_context={
            "institution_id": case.payload.get("institution_id"),
            "partner_id": case.payload.get("partner_id"),
        },
        notes=None,
    )

    agent_output = financial_links_reliability_agent.handle(
        case=case,
        handoff=handoff,
        approval_matrix=matrix,
        profile=profile,
    )

    evaluator_report = evaluate(
        agent_output,
        required_fields=_AGENT_OUTPUT_REQUIRED_FIELDS,
        approval_matrix=matrix,
    )

    trace = TraceRecord(
        trace_id=str(uuid.uuid4()),
        dataset_id=dataset_id_value,
        case_id=case.case_id,
        workflow=case.workflow,
        risk_band=case.risk_band,
        agent_system_version=profile,
        policy_version=policy_version,
        orchestrator_decision=specialist,
        specialist_path=[specialist],
        handoff=handoff,
        tool_calls=list(agent_output.tool_calls),
        evaluator_report=evaluator_report,
        approval=agent_output.approval,
        final_response=agent_output.draft_text,
        grader_results=[],
        failure_labels=[],
        latency_ms=0,
        est_cost_usd=0.0,
    )

    return RunResult(trace=trace, agent_output=agent_output)


def _build_case(case_dict: dict[str, Any]) -> Case:
    return Case(
        case_id=str(case_dict["case_id"]),
        workflow=Workflow(case_dict["workflow"]),
        risk_band=RiskBand(case_dict["risk_band"]),
        consent_sensitive=bool(case_dict.get("consent_sensitive", False)),
        payload=dict(case_dict.get("synthetic_facts", {})),
    )


def _initial_consent_state(user_id: str | None) -> ConsentState:
    if user_id is None:
        return ConsentState.UNKNOWN
    return ConsentState(lookup_consent_state(user_id)["consent_state"])
