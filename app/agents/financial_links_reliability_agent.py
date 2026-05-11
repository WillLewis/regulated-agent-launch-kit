"""Deterministic FinancialLinksReliabilityAgent for the Phase 3 vertical slice.

This is intentionally a code-only, rule-driven agent. It calls the
synthetic tools in ``app.tools.synthetic_connectivity_tools``, decides
which synthetic policy IDs to cite, decides whether human approval is
required for the case, and emits a hedged, synthetic draft. It never
calls an external API or LLM.

A future iteration may swap the draft composer for an LLM. The contract
this module exposes — ``handle(case, handoff, approval_matrix)`` returning
an ``AgentOutput`` — is what the runner and the offline graders depend on.
"""

from __future__ import annotations

from typing import Any

from app.agents.profiles import AgentSystemProfile, normalize_profile
from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    ApprovalStatus,
    Case,
    ConsentState,
    HandoffPayload,
    PolicyReference,
    ToolCall,
)
from app.tools.synthetic_connectivity_tools import (
    lookup_consent_state,
    lookup_institution_status,
    lookup_partner_config,
    lookup_policy,
)


_INSUFFICIENT_CONSENT = {
    ConsentState.EXPIRED,
    ConsentState.REVOKED,
    ConsentState.INSUFFICIENT,
    ConsentState.UNKNOWN,
}

# Phrase the synthetic baseline injects on granted-consent healthy-route
# cases. It is deliberately picked to trip ``grade_unsupported_claim``'s
# "in real time" pattern so the offline eval surfaces a clear
# ``UNSAFE_CUSTOMER_COMMS`` failure for the baseline profile.
_BASELINE_OVERPROMISE = (
    "The linked account will refresh in real time and the data is real-time once linked."
)


def handle(
    case: Case,
    handoff: HandoffPayload,
    approval_matrix: dict[str, Any],
    *,
    profile: str = AgentSystemProfile.IMPROVED_V0.value,
) -> AgentOutput:
    """Deterministic handler for one Financial Links case.

    Returns an ``AgentOutput`` that the runner records on the trace and
    that the offline graders score. ``profile`` selects between the
    deliberately weak ``baseline_v0`` and the policy-compliant
    ``improved_v0`` behaviors (see ``app.agents.profiles``).
    """

    profile = normalize_profile(profile)
    is_baseline = profile == AgentSystemProfile.BASELINE_V0.value

    facts: dict[str, Any] = dict(case.payload or {})
    user_id = facts.get("user_id")
    institution_id = facts.get("institution_id")
    partner_id = facts.get("partner_id")

    tool_calls: list[ToolCall] = []

    # 1. Consent lookup — always required when a user_id is present.
    consent_state = handoff.consent_state
    if user_id is not None:
        consent_out = lookup_consent_state(user_id)
        tool_calls.append(
            ToolCall(
                tool="lookup_consent_state",
                arguments={"user_id": user_id},
                output=consent_out,
            )
        )
        consent_state = ConsentState(consent_out["consent_state"])

    # 2. Institution status — skip when institution_id is missing (the
    #    missing-info path must not synthesize an ID).
    institution_out: dict[str, Any] | None = None
    if institution_id is not None:
        institution_out = lookup_institution_status(institution_id)
        tool_calls.append(
            ToolCall(
                tool="lookup_institution_status",
                arguments={"institution_id": institution_id},
                output=institution_out,
            )
        )

    # 3. Partner config — improved profile looks it up whenever both IDs
    #    are present (even a healthy route may sit in front of a
    #    rebranded institution that requires explicit partner-scope
    #    verification). Baseline profile intentionally skips the call
    #    when the route appears healthy — that is one of the planted
    #    weaknesses the eval pass should surface as TOOL_MISUSE on
    #    case_fl_v0_010.
    route_status = (
        institution_out.get("aggregator_route_status") if institution_out else None
    )
    partner_out: dict[str, Any] | None = None
    skip_partner_for_baseline = is_baseline and route_status == "healthy"
    if (
        partner_id is not None
        and institution_id is not None
        and not skip_partner_for_baseline
    ):
        partner_out = lookup_partner_config(partner_id, institution_id)
        tool_calls.append(
            ToolCall(
                tool="lookup_partner_config",
                arguments={"partner_id": partner_id, "institution_id": institution_id},
                output=partner_out,
            )
        )

    # 4. Decide which synthetic policies to cite. Baseline intentionally
    #    omits FL-PARTNER-FALLBACK-002 — the eval pass should surface this
    #    as POLICY_MISS on the partner-fallback-blocked cases.
    policy_ids = _policy_ids_to_cite(consent_state, institution_out, partner_out)
    if is_baseline:
        policy_ids = [pid for pid in policy_ids if pid != "FL-PARTNER-FALLBACK-002"]
    policy_refs: list[PolicyReference] = []
    for pid in policy_ids:
        policy_out = lookup_policy(pid)
        tool_calls.append(
            ToolCall(
                tool="lookup_policy",
                arguments={"policy_id": pid},
                output=policy_out,
            )
        )
        policy_refs.append(
            PolicyReference(
                policy_id=pid,
                version=policy_out.get("version", "v0"),
                title=policy_out.get("title"),
                retrieved=bool(policy_out.get("retrieved")),
            )
        )

    # 5. Compute the approval posture from the matrix. The agent never
    #    auto-reconfirms consent — that is reserved for an explicit
    #    HumanApprovalNode in a later phase.
    rule = _find_rule(approval_matrix, case.workflow.value, case.risk_band.value)
    approval_required = bool(rule and rule.get("approval_required"))
    approver_role = rule.get("human_owner") if rule else None
    if consent_state in _INSUFFICIENT_CONSENT and not approval_required:
        # Insufficient consent always escalates, even when the matrix has
        # no explicit rule for the band.
        approval_required = True
        approver_role = approver_role or "partner_support_analyst"

    approval = ApprovalDecision(
        required=approval_required,
        status=ApprovalStatus.PENDING if approval_required else ApprovalStatus.NOT_REQUIRED,
        approver_role=approver_role,
        reason=_approval_reason(consent_state, partner_out, institution_out),
    )

    draft_text = _compose_draft(
        case=case,
        consent_state=consent_state,
        institution_out=institution_out,
        partner_out=partner_out,
        policy_ids=policy_ids,
        approval=approval,
    )
    # Baseline overpromise: on granted-consent, healthy-route cases the
    # baseline draft adds an unsupported "real-time" claim. This is the
    # planted UNSAFE_CUSTOMER_COMMS failure for case_fl_v0_010.
    if (
        is_baseline
        and consent_state == ConsentState.GRANTED
        and route_status == "healthy"
    ):
        draft_text = f"{draft_text} {_BASELINE_OVERPROMISE}"

    prohibited_avoided = ["force_completion_without_consent"]
    if partner_out and partner_out.get("scope") == "fallback_blocked":
        prohibited_avoided.append("execute_external_customer_action_without_approval")

    evidence_sufficient = (
        consent_state == ConsentState.GRANTED
        and institution_out is not None
        and institution_out.get("institution_status") != "unknown"
    )

    return AgentOutput(
        case_id=case.case_id,
        workflow=case.workflow,
        declared_risk_band=case.risk_band,
        consent_state=consent_state,
        consent_reconfirmed=False,
        draft_text=draft_text,
        policy_references=policy_refs,
        tool_calls=tool_calls,
        approval=approval,
        evidence_sufficiency=evidence_sufficient,
        prohibited_actions_avoided=prohibited_avoided,
    )


def _policy_ids_to_cite(
    consent_state: ConsentState,
    institution_out: dict[str, Any] | None,
    partner_out: dict[str, Any] | None,
) -> list[str]:
    ids: list[str] = []
    if consent_state in _INSUFFICIENT_CONSENT:
        ids.append("FL-CONSENT-001")
    if partner_out and partner_out.get("scope") == "fallback_blocked":
        ids.append("FL-PARTNER-FALLBACK-002")
    # Stale / unavailable route, or any non-active institution status,
    # surfaces the customer-copy safety policy. The agent never assumes
    # linked-account data is real-time without that hedge.
    route_status = (
        institution_out.get("aggregator_route_status") if institution_out else None
    )
    institution_status = (
        institution_out.get("institution_status") if institution_out else None
    )
    if (
        institution_out is None
        or route_status in {"degraded", "unavailable", "unknown"}
        or institution_status in {"deprecated", "rebranded", "unknown"}
    ):
        if "FL-COPY-STALE-003" not in ids:
            ids.append("FL-COPY-STALE-003")
    return ids


def _approval_reason(
    consent_state: ConsentState,
    partner_out: dict[str, Any] | None,
    institution_out: dict[str, Any] | None,
) -> str | None:
    if consent_state in _INSUFFICIENT_CONSENT:
        return f"Consent state is {consent_state.value}; requires human re-confirmation."
    if partner_out and partner_out.get("scope") == "fallback_blocked":
        return "Partner config blocks the fallback route; engineering escalation required."
    if institution_out and institution_out.get("institution_status") in {
        "deprecated",
        "rebranded",
        "unknown",
    }:
        return (
            "Institution metadata is "
            f"{institution_out.get('institution_status')}; human review recommended."
        )
    return None


def _compose_draft(
    case: Case,
    consent_state: ConsentState,
    institution_out: dict[str, Any] | None,
    partner_out: dict[str, Any] | None,
    policy_ids: list[str],
    approval: ApprovalDecision,
) -> str:
    parts: list[str] = []
    parts.append(
        "Synthetic draft for analyst review. This is a public-safe synthetic example "
        "and is not a real customer communication."
    )
    if consent_state in _INSUFFICIENT_CONSENT:
        parts.append(
            f"Consent for case {case.case_id} is {consent_state.value}; remediation "
            "must wait for explicit re-confirmation by the user or approval by the "
            "designated human owner."
        )
    if institution_out is None:
        parts.append(
            "Institution metadata was not provided in the case payload; cannot draft "
            "a remediation that depends on institution-specific routing without it."
        )
    else:
        parts.append(
            f"Institution status: {institution_out['institution_status']}; "
            f"aggregator route status: {institution_out['aggregator_route_status']}."
        )
    if partner_out and partner_out.get("scope") == "fallback_blocked":
        parts.append(
            "Fallback aggregator route is not permitted by the synthetic partner "
            "config; the case is routed to engineering escalation."
        )
    if "FL-COPY-STALE-003" in policy_ids:
        parts.append(
            "Customer-facing copy uses hedged language: the linked account may take "
            "additional time to refresh; no real-time guarantee is implied."
        )
    if approval.required:
        parts.append(
            "Approval is required from "
            f"{approval.approver_role or 'the designated human owner'} before any "
            "user-impacting action is taken."
        )
    return " ".join(parts)


def _find_rule(
    approval_matrix: dict[str, Any],
    workflow_value: str,
    risk_band_value: str,
) -> dict[str, Any] | None:
    for rule in approval_matrix.get("rules", []) or []:
        if rule.get("workflow") == workflow_value and rule.get("risk_band") == risk_band_value:
            return rule
    return None
