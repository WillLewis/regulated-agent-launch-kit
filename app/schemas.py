"""Pydantic schemas for the regulated-agent-launch-kit.

Locks in the contract between two intentionally distinct surfaces:

- Runtime: ``app.evaluator`` emits ``EvaluatorCheck`` / ``EvaluatorReport``
  before the final response is composed.
- Offline: ``evals.graders`` emit ``GraderResult`` after a trace completes.

Keeping these as separate types prevents the runtime evaluator from being
silently swapped for offline grading (or vice versa). See the
"Evaluator and grader separation" non-negotiable in ``AGENTS.md``.

Phase 2 also introduces the synthetic domain model: ``Workflow``,
``ConsentState``, ``ApprovalStatus``, ``ToolCall``, ``PolicyReference``,
``HandoffPayload``, ``ApprovalDecision``, ``AgentOutput``, and
``TraceRecord``. Handoff payloads are Pydantic-enforced per PLAN.md R9,
and consent state is first-class per PLAN.md R1.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class Severity(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class Workflow(str, Enum):
    FINANCIAL_LINKS_RELIABILITY = "financial_links_reliability"
    CREDIT_WELLNESS_OFFER_ACTIVATION = "credit_wellness_offer_activation"
    PRIVACY_IDENTITY_ALERT_TRIAGE = "privacy_identity_alert_triage"
    SUBSCRIPTION_ACTION = "subscription_action"


class ConsentState(str, Enum):
    GRANTED = "granted"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class AggregatorRouteStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class InstitutionStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REBRANDED = "rebranded"
    UNKNOWN = "unknown"


class PartnerScopeStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    FALLBACK_PERMITTED = "fallback_permitted"
    FALLBACK_BLOCKED = "fallback_blocked"
    UNKNOWN = "unknown"


class Case(BaseModel):
    case_id: str
    workflow: Workflow
    risk_band: RiskBand
    consent_sensitive: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Synthetic tool invocation captured for traces and graders."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    error: str | None = None


class PolicyReference(BaseModel):
    """Pointer to a synthetic policy that informed the agent's output."""

    policy_id: str
    version: str = "v0"
    title: str | None = None
    retrieved: bool = True


class HandoffPayload(BaseModel):
    """Orchestrator → specialist handoff. Pydantic-enforced per PLAN.md R9.

    Required fields capture the consent, risk, and route context that
    specialists must not have to re-derive. Missing any of them is itself
    an architectural failure and surfaces as ``HANDOFF_CONTEXT_LOSS``.
    """

    case_id: str
    workflow: Workflow
    from_node: str
    to_agent: str
    declared_risk_band: RiskBand
    consent_state: ConsentState
    consent_reconfirmed: bool = False
    route_context: dict[str, Any]
    notes: str | None = None


class ApprovalDecision(BaseModel):
    """Agent's declared approval posture for a draft.

    Note: the *true* required approval is computed by the offline
    approval-boundary grader from case features + approval matrix, not
    from this field. Per PLAN.md R8, the grader must not consume the
    agent's declared band.
    """

    required: bool
    status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    approver_role: str | None = None
    reason: str | None = None


class AgentOutput(BaseModel):
    """Specialist-agent output contract.

    First-class consent fields (PLAN.md R1) and a Pydantic-enforced
    approval decision (PLAN.md R8/R9) keep the runtime evaluator and the
    offline graders honest about the same facts.

    ``est_cost_usd`` is populated only when the specialist routes draft
    generation through the LLM adapter (``llm_candidate_v0``). The
    deterministic profiles report ``0.0``. The runner threads this
    value onto the resulting :class:`TraceRecord` so the eval report's
    ``synthetic_cost_summary`` aggregates it without special-casing.
    """

    case_id: str
    workflow: Workflow
    declared_risk_band: RiskBand
    consent_state: ConsentState
    consent_reconfirmed: bool = False
    draft_text: str
    policy_references: list[PolicyReference] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    approval: ApprovalDecision
    evidence_sufficiency: bool = False
    prohibited_actions_avoided: list[str] = Field(default_factory=list)
    est_cost_usd: float = 0.0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_model: str | None = None
    llm_cost_estimation_note: str | None = None


class EvaluatorCheck(BaseModel):
    """Single inline check produced by the runtime EvaluatorNode."""

    name: str
    ok: bool
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluatorReport(BaseModel):
    """Bundle of EvaluatorChecks from one runtime EvaluatorNode invocation."""

    checks: list[EvaluatorCheck] = Field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(check.ok for check in self.checks)


class GraderResult(BaseModel):
    """Offline grader output. Shape is fixed by ``AGENTS.md``."""

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    failure_label: str | None = None
    explanation: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class TraceRecord(BaseModel):
    """Local trace artifact written per case.

    Mirrors the trace fields listed in ``AGENTS.md`` so a reviewer can
    reconstruct the run without Braintrust credentials.
    """

    trace_id: str
    dataset_id: str
    case_id: str
    workflow: Workflow
    risk_band: RiskBand
    agent_system_version: str
    policy_version: str
    orchestrator_decision: str
    specialist_path: list[str] = Field(default_factory=list)
    handoff: HandoffPayload | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    evaluator_report: EvaluatorReport = Field(default_factory=EvaluatorReport)
    approval: ApprovalDecision | None = None
    final_response: str | None = None
    grader_results: list[GraderResult] = Field(default_factory=list)
    failure_labels: list[str] = Field(default_factory=list)
    latency_ms: int = 0
    est_cost_usd: float = 0.0
