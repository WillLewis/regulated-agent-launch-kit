"""Pure synthetic launch-gate decision engine.

This module consumes already-loaded local eval artifacts and gate config.
It does not read files, call graders, call models, or inspect runtime
EvaluatorNode state.
"""

from __future__ import annotations

from typing import Any

from app.schemas import (
    GateStatus,
    LaunchDecision,
    LaunchGateResult,
    LaunchTier,
    LaunchVerdict,
)


READY_POSTURE = (
    "READY FOR INTERNAL PILOT (synthetic) — all gating launch gates pass on "
    "the committed synthetic slice; not a production or regulatory claim."
)
CONSTRAINTS_POSTURE = (
    "PILOT WITH CONSTRAINTS (synthetic) — named exceptions required in "
    "deployment/pilot_readiness_review.md."
)
DO_NOT_PILOT_POSTURE = (
    "NOT READY FOR PILOT — local synthetic vertical slice only; computed from "
    "launch gates, not a launch-readiness claim."
)


SignalOutcome = tuple[Any, bool, dict[str, Any]]


def decide(
    gates_config: dict,
    *,
    eval_run: dict | None,
    regression_runs: list[dict] | None = None,
    semantic_audits: list[dict] | None = None,
    redaction_reports: list[dict] | None = None,
    risk_weights: dict | None = None,
    pilot_review_present: bool = False,
    inputs_digest: dict[str, str] | None = None,
) -> LaunchDecision:
    """Compute the synthetic launch verdict from loaded artifacts only."""

    normalized_regressions = regression_runs or []
    normalized_semantics = semantic_audits or []
    normalized_redactions = redaction_reports or []
    high_risk_bands = set(gates_config.get("high_risk_bands") or [])
    raw_gates = list(gates_config.get("gates") or [])

    deferred_missing_gate: dict | None = None
    non_missing_results: dict[str, LaunchGateResult] = {}
    for gate in raw_gates:
        if gate["signal"] == "missing_backing_artifact_count":
            deferred_missing_gate = gate
            continue
        result = _evaluate_gate(
            gate,
            _extract_signal(
                gate["signal"],
                eval_run=eval_run,
                regression_runs=normalized_regressions,
                semantic_audits=normalized_semantics,
                redaction_reports=normalized_redactions,
                risk_weights=risk_weights,
                high_risk_bands=high_risk_bands,
                pilot_review_present=pilot_review_present,
            ),
        )
        non_missing_results[result.gate_id] = result

    missing_backing_artifact_count = sum(
        1
        for result in non_missing_results.values()
        if result.gating
        and result.evidence.get("input_present") is False
        and result.gate_id != "ready_inputs_complete"
    )

    missing_result: LaunchGateResult | None = None
    if deferred_missing_gate is not None:
        missing_result = _evaluate_gate(
            deferred_missing_gate,
            (
                missing_backing_artifact_count,
                True,
                {
                    "signal": "missing_backing_artifact_count",
                    "input_present": True,
                    "missing_gate_count": missing_backing_artifact_count,
                    "sentinel_backing_artifact": "(all gate backing artifacts)",
                },
            ),
        )

    gate_results: list[LaunchGateResult] = []
    for gate in raw_gates:
        if gate["signal"] == "missing_backing_artifact_count":
            if missing_result is not None:
                gate_results.append(missing_result)
            continue
        gate_results.append(non_missing_results[gate["id"]])

    verdict, blockers, rationale = _decide_verdict(gate_results)
    return LaunchDecision(
        verdict=verdict,
        posture_line=_posture_line(verdict),
        gate_results=gate_results,
        blockers=blockers,
        rationale=rationale,
        inputs_digest=dict(inputs_digest or {}),
        gates_version=str(gates_config.get("version", "launch_gates_v0")),
        synthetic=True,
    )


def _evaluate_gate(gate: dict, outcome: SignalOutcome) -> LaunchGateResult:
    observed, input_present, evidence = outcome
    tier = LaunchTier(gate["tier"])
    comparator = gate["comparator"]
    gating = bool(gate["gating"])

    if not input_present:
        if not gating:
            status = GateStatus.NOT_APPLICABLE
            explanation = "Advisory gate has no backing input in the provided artifacts."
        elif tier is LaunchTier.DO_NOT_PILOT:
            status = GateStatus.NOT_APPLICABLE
            explanation = "Do-not-pilot gate has no backing input and cannot pass."
        else:
            status = GateStatus.FAIL
            explanation = "Required backing input is missing, so the gate fails closed."
    elif comparator == "advisory":
        status = GateStatus.NOT_APPLICABLE
        explanation = "Advisory signal surfaced for review; it does not gate the verdict."
    else:
        passed = _compare(observed, comparator, gate["threshold"])
        status = GateStatus.PASS if passed else GateStatus.FAIL
        explanation = (
            f"Observed {gate['signal']}={observed!r}; expected "
            f"{comparator} {gate['threshold']!r}."
        )

    return LaunchGateResult(
        gate_id=gate["id"],
        tier=tier,
        status=status,
        observed=observed,
        threshold=gate["threshold"],
        comparator=comparator,
        gating=gating,
        backing_artifact=gate["backing_artifact"],
        explanation=explanation,
        evidence=evidence,
    )


def _compare(observed: Any, comparator: str, threshold: Any) -> bool:
    if comparator == "==":
        return observed == threshold
    if comparator == ">=":
        try:
            return observed >= threshold
        except TypeError:
            return False
    raise ValueError(f"Unsupported launch-gate comparator: {comparator}")


def _decide_verdict(
    gate_results: list[LaunchGateResult],
) -> tuple[LaunchVerdict, list[str], str]:
    dnp_blockers = [
        result.gate_id
        for result in gate_results
        if result.gating
        and result.tier is LaunchTier.DO_NOT_PILOT
        and result.status is GateStatus.FAIL
    ]
    if dnp_blockers:
        return (
            LaunchVerdict.DO_NOT_PILOT,
            dnp_blockers,
            f"Launch blocked by do-not-pilot gates: {', '.join(dnp_blockers)}.",
        )

    ready_results = [
        result
        for result in gate_results
        if result.gating and result.tier is LaunchTier.READY
    ]
    ready_blockers = [
        result.gate_id
        for result in ready_results
        if result.status is not GateStatus.PASS
    ]
    if ready_results and not ready_blockers:
        return (
            LaunchVerdict.READY_FOR_INTERNAL_PILOT,
            [],
            "All gating launch gates passed on the synthetic artifact slice.",
        )

    named_constraints = next(
        (
            result
            for result in gate_results
            if result.gate_id == "named_constraints_recorded"
        ),
        None,
    )
    if named_constraints is None or named_constraints.status is not GateStatus.PASS:
        blockers = [*ready_blockers, "missing_named_exceptions"]
        return (
            LaunchVerdict.DO_NOT_PILOT,
            blockers,
            "Ready gates did not all pass and named constrained-pilot "
            f"exceptions are missing: {', '.join(blockers)}.",
        )

    return (
        LaunchVerdict.PILOT_WITH_CONSTRAINTS,
        ready_blockers,
        "Ready gates need named exceptions before pilot: "
        f"{', '.join(ready_blockers)}. Human sign-off remains in "
        "deployment/pilot_readiness_review.md.",
    )


def _posture_line(verdict: LaunchVerdict) -> str:
    if verdict is LaunchVerdict.READY_FOR_INTERNAL_PILOT:
        return READY_POSTURE
    if verdict is LaunchVerdict.PILOT_WITH_CONSTRAINTS:
        return CONSTRAINTS_POSTURE
    return DO_NOT_PILOT_POSTURE


def _extract_signal(
    signal: str,
    *,
    eval_run: dict | None,
    regression_runs: list[dict],
    semantic_audits: list[dict],
    redaction_reports: list[dict],
    risk_weights: dict | None,
    high_risk_bands: set[str],
    pilot_review_present: bool,
) -> SignalOutcome:
    if signal == "l3_evaluator_miss_count":
        return _l3_evaluator_miss_count(eval_run, high_risk_bands)
    if signal == "l3_semantic_only_unsafe_count":
        return _l3_semantic_only_unsafe_count(semantic_audits, high_risk_bands)
    if signal == "l3_consent_violation_count":
        return _l3_consent_violation_count(eval_run, high_risk_bands)
    if signal == "min_redaction_coverage":
        return _min_redaction_coverage(redaction_reports)
    if signal == "high_risk_regression_failure_count":
        return _high_risk_regression_failure_count(regression_runs, high_risk_bands)
    if signal == "min_deterministic_grader_pass_rate":
        return _min_deterministic_grader_pass_rate(eval_run)
    if signal == "regression_total_failed_count":
        return _regression_total_failed_count(regression_runs)
    if signal == "risk_weighted_pass_rate":
        return _risk_weighted_pass_rate(eval_run, risk_weights)
    if signal == "l3_unsupported_miss_count":
        return _l3_unsupported_miss_count(
            eval_run,
            semantic_audits,
            high_risk_bands,
        )
    if signal == "pilot_review_present":
        return (
            bool(pilot_review_present),
            True,
            {"signal": signal, "input_present": True},
        )
    raise ValueError(f"Unsupported launch-gate signal: {signal}")


def _l3_evaluator_miss_count(
    eval_run: dict | None,
    high_risk_bands: set[str],
) -> SignalOutcome:
    present = eval_run is not None
    case_ids = [
        case.get("case_id")
        for case in _per_case(eval_run)
        if _is_high_risk(case, high_risk_bands)
        and "EVALUATOR_MISS" in _failure_labels(case)
    ]
    return (
        len(case_ids),
        present,
        {
            "signal": "l3_evaluator_miss_count",
            "input_present": present,
            "case_ids": case_ids,
        },
    )


def _l3_semantic_only_unsafe_count(
    semantic_audits: list[dict],
    high_risk_bands: set[str],
) -> SignalOutcome:
    present = bool(semantic_audits)
    case_ids: list[str] = []
    for report in semantic_audits:
        for profile in report.get("profiles", []) or []:
            semantic = profile.get("semantic", {}) or {}
            risk_by_case = semantic.get("flagged_case_risk_bands", {}) or {}
            lexical_vs_semantic = profile.get("lexical_vs_semantic", {}) or {}
            semantic_only_ids = (
                lexical_vs_semantic.get("semantic_only_flag_case_ids", []) or []
            )
            for case_id in semantic_only_ids:
                if risk_by_case.get(case_id) in high_risk_bands:
                    case_ids.append(case_id)
    return (
        len(case_ids),
        present,
        {
            "signal": "l3_semantic_only_unsafe_count",
            "input_present": present,
            "case_ids": case_ids,
            "audit_count": len(semantic_audits),
        },
    )


def _l3_consent_violation_count(
    eval_run: dict | None,
    high_risk_bands: set[str],
) -> SignalOutcome:
    present = eval_run is not None
    case_ids = [
        case.get("case_id")
        for case in _per_case(eval_run)
        if _is_high_risk(case, high_risk_bands)
        and "CONSENT_BOUNDARY_VIOLATION" in _failure_labels(case)
    ]
    return (
        len(case_ids),
        present,
        {
            "signal": "l3_consent_violation_count",
            "input_present": present,
            "case_ids": case_ids,
        },
    )


def _min_redaction_coverage(redaction_reports: list[dict]) -> SignalOutcome:
    present = bool(redaction_reports)
    coverages: list[float] = []
    total_uncovered = 0
    for report in redaction_reports:
        summary = report.get("summary", {}) or {}
        preserved = int(summary.get("preserved_count", 0) or 0)
        preserve_missing = int(summary.get("preserve_missing_count", 0) or 0)
        total_uncovered += int(summary.get("uncovered_count", 0) or 0)
        denominator = preserved + preserve_missing
        coverages.append((preserved / denominator) if denominator else 0.0)
    observed = min(coverages) if coverages else None
    return (
        observed,
        present,
        {
            "signal": "min_redaction_coverage",
            "input_present": present,
            "coverages": coverages,
            "total_uncovered_count": total_uncovered,
        },
    )


def _high_risk_regression_failure_count(
    regression_runs: list[dict],
    high_risk_bands: set[str],
) -> SignalOutcome:
    present = bool(regression_runs)
    case_ids: list[str] = []
    for report in regression_runs:
        for case in _per_case(report):
            if _is_high_risk(case, high_risk_bands) and case.get("passed") is False:
                case_ids.append(case.get("case_id"))
    return (
        len(case_ids),
        present,
        {
            "signal": "high_risk_regression_failure_count",
            "input_present": present,
            "case_ids": case_ids,
            "run_count": len(regression_runs),
        },
    )


def _min_deterministic_grader_pass_rate(eval_run: dict | None) -> SignalOutcome:
    present = eval_run is not None
    rates = _aggregate_grader_pass_rates(eval_run)
    deterministic_rates = {
        name: rate
        for name, rate in rates.items()
        if name != "unsupported_claim_semantic"
    }
    observed = min(deterministic_rates.values()) if deterministic_rates else 0.0
    return (
        observed,
        present,
        {
            "signal": "min_deterministic_grader_pass_rate",
            "input_present": present,
            "pass_rates": deterministic_rates,
            "excluded_grader": "unsupported_claim_semantic",
        },
    )


def _regression_total_failed_count(regression_runs: list[dict]) -> SignalOutcome:
    present = bool(regression_runs)
    total_failed = 0
    for report in regression_runs:
        if "failed_case_count" in report:
            total_failed += int(report.get("failed_case_count") or 0)
        else:
            total_failed += sum(1 for case in _per_case(report) if case.get("passed") is False)
    return (
        total_failed,
        present,
        {
            "signal": "regression_total_failed_count",
            "input_present": present,
            "run_count": len(regression_runs),
        },
    )


def _risk_weighted_pass_rate(
    eval_run: dict | None,
    risk_weights: dict | None,
) -> SignalOutcome:
    present = eval_run is not None and risk_weights is not None
    weights = _risk_band_weights(risk_weights)
    total_weight = 0.0
    passed_weight = 0.0
    for case in _per_case(eval_run):
        weight = float(weights.get(case.get("risk_band"), 1.0))
        total_weight += weight
        if case.get("passed") is True:
            passed_weight += weight
    observed = (passed_weight / total_weight) if total_weight else 0.0
    return (
        observed,
        present,
        {
            "signal": "risk_weighted_pass_rate",
            "input_present": present,
            "passed_weight": passed_weight,
            "total_weight": total_weight,
        },
    )


def _l3_unsupported_miss_count(
    eval_run: dict | None,
    semantic_audits: list[dict],
    high_risk_bands: set[str],
) -> SignalOutcome:
    evaluator_count, evaluator_present, evaluator_evidence = _l3_evaluator_miss_count(
        eval_run,
        high_risk_bands,
    )
    semantic_count, semantic_present, semantic_evidence = _l3_semantic_only_unsafe_count(
        semantic_audits,
        high_risk_bands,
    )
    present = evaluator_present and semantic_present
    return (
        evaluator_count + semantic_count,
        present,
        {
            "signal": "l3_unsupported_miss_count",
            "input_present": present,
            "evaluator": evaluator_evidence,
            "semantic": semantic_evidence,
        },
    )


def _per_case(report: dict | None) -> list[dict]:
    if not report:
        return []
    return list(report.get("per_case", []) or [])


def _is_high_risk(case: dict, high_risk_bands: set[str]) -> bool:
    return case.get("risk_band") in high_risk_bands


def _failure_labels(case: dict) -> set[str]:
    return set(case.get("failure_labels") or [])


def _aggregate_grader_pass_rates(eval_run: dict | None) -> dict[str, float]:
    if not eval_run:
        return {}
    raw_rates = eval_run.get("aggregate_grader_pass_rates", {}) or {}
    if isinstance(raw_rates, dict):
        rates: dict[str, float] = {}
        for name, value in raw_rates.items():
            if isinstance(value, dict):
                rate = value.get("pass_rate", 0.0)
            else:
                rate = value
            rates[str(name)] = float(rate)
        return rates

    rates = {}
    for entry in raw_rates:
        name = entry.get("name")
        if name is None:
            continue
        rates[str(name)] = float(entry.get("pass_rate", 0.0))
    return rates


def _risk_band_weights(risk_weights: dict | None) -> dict[str, float]:
    if not risk_weights:
        return {}
    weights: dict[str, float] = {}
    for band, config in (risk_weights.get("risk_bands", {}) or {}).items():
        if isinstance(config, dict):
            weights[str(band)] = float(config.get("weight", 1.0))
        else:
            weights[str(band)] = float(config)
    return weights
