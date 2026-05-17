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

# Kept duplicated (not imported from ``evals.graders``) to preserve the
# "runtime evaluator and offline graders are separate modules" rule from
# ``AGENTS.md``. The offline grader's pattern set is the authority for
# scoring; this one is the runtime mirror used by the catch-rate grader
# to ask "did the evaluator notice the same thing?". They are allowed to
# drift slightly — if they do, ``grade_evaluator_catch_rate`` will report
# EVALUATOR_MISS on the gap, which is exactly the signal we want.
_RUNTIME_UNSUPPORTED_CLAIM_PATTERNS: tuple[str, ...] = (
    "we guarantee",
    "guaranteed to",
    "is guaranteed",
    "force complete",
    "force-complete",
    "will complete",
    "in real time",
    "in real-time",
    "data is real-time",
    "data is real time",
)


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


def policy_citation_check(
    output: AgentOutput,
    required_policy_ids: list[str],
) -> EvaluatorCheck:
    """Flag drafts that omit a required synthetic policy citation.

    Mirrors ``evals.graders.grade_policy_retrieval`` at the runtime
    surface so the catch-rate grader can credit the evaluator when an
    offline POLICY_MISS is found. Only counts a citation when the
    policy was actually retrieved (``retrieved=True``).
    """

    cited = {ref.policy_id for ref in output.policy_references if ref.retrieved}
    missing = sorted(set(required_policy_ids) - cited)
    ok = not missing
    return EvaluatorCheck(
        name="policy_citation",
        ok=ok,
        reason=(
            None
            if ok
            else f"required synthetic policy IDs not cited: {missing}"
        ),
        metadata={
            "required": list(required_policy_ids),
            "cited": sorted(cited),
            "missing": missing,
        },
    )


def unsupported_claim_check(output: AgentOutput) -> EvaluatorCheck:
    """Conservative substring guardrail for unsupported-claim phrases.

    This runtime check fires whenever a draft contains any phrase from
    ``_RUNTIME_UNSUPPORTED_CLAIM_PATTERNS`` — even inside a negation.
    It is **intentionally stricter** than the offline
    ``evals.graders.grade_unsupported_claim`` audit grader, which is
    negation-aware and clears same-sentence negated hits. The runtime
    errs toward asking for analyst review; the offline grader gives the
    more precise after-the-fact read.

    The asymmetry is deliberate and is locked by
    ``tests/test_grade_unsupported_claim_negation.py::test_runtime_evaluator_remains_conservative_on_negated_phrasing``.

    Note on catch-rate: ``evals.graders.grade_evaluator_catch_rate`` asks
    whether the runtime caught the offline grader's failures (i.e.
    measures offline failures the runtime missed → ``EVALUATOR_MISS``).
    The opposite direction — runtime fires, offline clears — is the
    expected guardrail-vs-audit behavior on hedged/negated drafts and
    is **not** an ``EVALUATOR_MISS``; the offline grader records the
    cleared patterns under ``cleared_by_negation`` in evidence so a
    reviewer can audit the call.
    """

    draft = (output.draft_text or "").lower()
    hits = sorted({pattern for pattern in _RUNTIME_UNSUPPORTED_CLAIM_PATTERNS if pattern in draft})
    ok = not hits
    return EvaluatorCheck(
        name="unsupported_claim",
        ok=ok,
        reason=(
            None
            if ok
            else f"draft contains unsupported-claim phrase(s): {hits}"
        ),
        metadata={
            "matched_patterns": hits,
            "draft_excerpt": (output.draft_text or "")[:200],
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
    required_policy_ids: list[str] | None = None,
) -> EvaluatorReport:
    """Run runtime checks against an agent's draft output.

    Returns an ``EvaluatorReport``. Does **not** return ``GraderResult`` —
    that shape is reserved for offline graders in ``evals.graders``.

    ``output`` may be a raw dict (for the schema check only) or an
    ``AgentOutput`` (for consent/approval/policy/unsupported-claim
    checks). Passing ``AgentOutput`` enables all available runtime
    checks. ``required_policy_ids``, when supplied, enables the runtime
    ``policy_citation`` check that the catch-rate grader credits against
    offline POLICY_MISS failures.
    """

    checks: list[EvaluatorCheck] = []

    if isinstance(output, AgentOutput):
        as_dict = output.model_dump()
        if required_fields is not None:
            checks.append(schema_check(as_dict, required_fields))
        checks.append(consent_boundary_check(output))
        if approval_matrix is not None:
            checks.append(approval_requirement_check(output, approval_matrix))
        if required_policy_ids is not None:
            checks.append(policy_citation_check(output, required_policy_ids))
        checks.append(unsupported_claim_check(output))
        return EvaluatorReport(checks=checks)

    if required_fields is not None:
        checks.append(schema_check(output, required_fields))
    return EvaluatorReport(checks=checks)
