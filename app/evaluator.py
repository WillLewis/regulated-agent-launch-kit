"""Runtime EvaluatorNode for the LangGraph multi-agent system.

This module is intentionally separate from ``evals.graders``:

- ``EvaluatorNode`` runs **inline** before the final response is composed
  and decides whether to block, escalate, or allow the output. It returns
  ``EvaluatorReport`` / ``EvaluatorCheck``.
- Offline graders run **after** a trace is complete and produce
  ``GraderResult`` objects for eval reports.

Mixing the two creates an evaluator that cannot be honestly graded.
See the "Evaluator and grader separation" non-negotiable in ``AGENTS.md``.
"""

from __future__ import annotations

from typing import Any

from app.schemas import (
    AgentOutput,
    ConsentState,
    EvaluatorCheck,
    EvaluatorReport,
    RiskBand,
    Workflow,
)


_L2_OR_ABOVE = {RiskBand.L2, RiskBand.L3, RiskBand.L4}
_INSUFFICIENT_CONSENT = {
    ConsentState.EXPIRED,
    ConsentState.REVOKED,
    ConsentState.INSUFFICIENT,
    ConsentState.UNKNOWN,
}


def schema_check(output: dict[str, Any], required_fields: list[str]) -> EvaluatorCheck:
    """Verify required fields are present in an agent output draft."""

    missing = [field for field in required_fields if field not in output]
    return EvaluatorCheck(
        name="schema_required_fields",
        ok=not missing,
        reason=None if not missing else f"missing required fields: {missing}",
        metadata={"required_fields": list(required_fields), "missing": missing},
    )


def consent_boundary_check(output: AgentOutput) -> EvaluatorCheck:
    """Block L2+ consent-sensitive drafts without re-confirmation/approval.

    Implements PLAN.md R1: L2 consent-sensitive cases must show explicit
    re-confirmation or surface a human-approval requirement before
    user-impacting guidance is drafted.
    """

    needs_gate = (
        output.declared_risk_band in _L2_OR_ABOVE
        and output.consent_state in _INSUFFICIENT_CONSENT
    )
    satisfied = output.consent_reconfirmed or output.approval.required
    ok = (not needs_gate) or satisfied
    return EvaluatorCheck(
        name="consent_boundary",
        ok=ok,
        reason=(
            None
            if ok
            else (
                "L2+ consent-sensitive output requires consent_reconfirmed=True "
                "or approval.required=True"
            )
        ),
        metadata={
            "declared_risk_band": output.declared_risk_band.value,
            "consent_state": output.consent_state.value,
            "consent_reconfirmed": output.consent_reconfirmed,
            "approval_required": output.approval.required,
        },
    )


def approval_requirement_check(
    output: AgentOutput,
    approval_matrix: dict[str, Any],
) -> EvaluatorCheck:
    """Flag drafts missing the approval the matrix demands.

    Uses the agent's declared workflow + risk band to look up the matrix.
    Offline graders independently compute the *true* required band per
    PLAN.md R8, so this runtime check only catches drafts that admit they
    need approval and then fail to surface it.
    """

    required_by_matrix = _matrix_requires_approval(
        approval_matrix, output.workflow, output.declared_risk_band
    )
    ok = (not required_by_matrix) or output.approval.required
    return EvaluatorCheck(
        name="approval_requirement",
        ok=ok,
        reason=(
            None
            if ok
            else (
                "Approval matrix requires approval for "
                f"{output.workflow.value} @ {output.declared_risk_band.value} "
                "but output.approval.required is False"
            )
        ),
        metadata={
            "workflow": output.workflow.value,
            "declared_risk_band": output.declared_risk_band.value,
            "matrix_required": required_by_matrix,
            "output_required": output.approval.required,
        },
    )


def _matrix_requires_approval(
    approval_matrix: dict[str, Any],
    workflow: Workflow,
    risk_band: RiskBand,
) -> bool:
    for rule in approval_matrix.get("rules", []) or []:
        if rule.get("workflow") != workflow.value:
            continue
        if rule.get("risk_band") != risk_band.value:
            continue
        if rule.get("approval_required"):
            return True
    return False


def evaluate(
    output: dict[str, Any] | AgentOutput,
    required_fields: list[str] | None = None,
    approval_matrix: dict[str, Any] | None = None,
) -> EvaluatorReport:
    """Run runtime checks against an agent's draft output.

    Returns an ``EvaluatorReport``. Does **not** return ``GraderResult`` —
    that shape is reserved for offline graders in ``evals.graders``.

    ``output`` may be a raw dict (for the schema check only) or an
    ``AgentOutput`` (for consent/approval checks). Passing ``AgentOutput``
    enables all available runtime checks.
    """

    checks: list[EvaluatorCheck] = []

    if isinstance(output, AgentOutput):
        as_dict = output.model_dump()
        if required_fields is not None:
            checks.append(schema_check(as_dict, required_fields))
        checks.append(consent_boundary_check(output))
        if approval_matrix is not None:
            checks.append(approval_requirement_check(output, approval_matrix))
        return EvaluatorReport(checks=checks)

    if required_fields is not None:
        checks.append(schema_check(output, required_fields))
    return EvaluatorReport(checks=checks)
