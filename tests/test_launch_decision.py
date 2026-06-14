"""Fixture-driven tests for the pure launch decision engine."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from app.schemas import GateStatus, LaunchDecision, LaunchVerdict
from evals.launch_decision import decide


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def launch_gates() -> dict:
    return yaml.safe_load((ROOT / "configs" / "launch_gates.yaml").read_text())


@pytest.fixture(scope="module")
def risk_weights() -> dict:
    return yaml.safe_load((ROOT / "configs" / "risk_weights.yaml").read_text())


def _eval_run(per_case: list[dict] | None = None) -> dict:
    return {
        "per_case": per_case
        if per_case is not None
        else [
            {
                "case_id": "case_l1_clean",
                "workflow": "financial_links_reliability",
                "risk_band": "L1",
                "passed": True,
                "failure_labels": [],
            },
            {
                "case_id": "case_l3_clean",
                "workflow": "privacy_identity_alert_triage",
                "risk_band": "L3",
                "passed": True,
                "failure_labels": [],
            },
        ],
        "aggregate_grader_pass_rates": {
            "schema_validity": {"pass_rate": 1.0},
            "handoff_completeness": {"pass_rate": 1.0},
            "required_tool_use": {"pass_rate": 1.0},
            "consent_boundary": {"pass_rate": 1.0},
            "approval_boundary": {"pass_rate": 1.0},
            "policy_retrieval": {"pass_rate": 1.0},
            "unsupported_claim": {"pass_rate": 1.0},
            "evaluator_catch_rate": {"pass_rate": 1.0},
            "unsupported_claim_semantic": {"pass_rate": 0.0},
        },
    }


def _semantic_audit(
    semantic_only_case_ids: list[str] | None = None,
    risk_bands: dict[str, str] | None = None,
) -> dict:
    return {
        "profiles": [
            {
                "lexical_vs_semantic": {
                    "semantic_only_flag_case_ids": semantic_only_case_ids or [],
                },
                "semantic": {
                    "flagged_case_risk_bands": risk_bands or {},
                },
            },
        ],
    }


def _redaction_report(preserved: int, preserve_missing: int, uncovered: int = 0) -> dict:
    return {
        "summary": {
            "preserved_count": preserved,
            "preserve_missing_count": preserve_missing,
            "uncovered_count": uncovered,
        },
    }


def _regression_run(failed_case_count: int = 0, per_case: list[dict] | None = None) -> dict:
    return {
        "failed_case_count": failed_case_count,
        "per_case": per_case
        if per_case is not None
        else [
            {
                "case_id": "regression_l3_clean",
                "risk_band": "L3",
                "passed": True,
            },
        ],
    }


def _clean_inputs(risk_weights: dict) -> dict:
    return {
        "eval_run": _eval_run(),
        "regression_runs": [_regression_run()],
        "semantic_audits": [_semantic_audit()],
        "redaction_reports": [_redaction_report(17, 0, 0)],
        "risk_weights": risk_weights,
        "pilot_review_present": True,
        "inputs_digest": {"synthetic": "fixture"},
    }


def _gate(decision: LaunchDecision, gate_id: str):
    return next(result for result in decision.gate_results if result.gate_id == gate_id)


def test_clean_inputs_compute_ready(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    decision = decide(launch_gates, **_clean_inputs(risk_weights))

    assert decision.verdict is LaunchVerdict.READY_FOR_INTERNAL_PILOT
    assert decision.blockers == []
    assert decision.gates_version == "launch_gates_v0"
    assert "not a production or regulatory claim" in decision.posture_line


def test_l3_evaluator_miss_blocks_pilot(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    inputs = _clean_inputs(risk_weights)
    inputs["eval_run"]["per_case"][1]["failure_labels"] = ["EVALUATOR_MISS"]

    decision = decide(launch_gates, **inputs)

    assert decision.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "dnp_evaluator_miss_l3" in decision.blockers
    assert _gate(decision, "dnp_evaluator_miss_l3").status is GateStatus.FAIL


def test_l3_semantic_only_unsafe_claim_blocks_pilot(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    inputs = _clean_inputs(risk_weights)
    inputs["semantic_audits"] = [
        _semantic_audit(
            semantic_only_case_ids=["semantic_case_l3"],
            risk_bands={"semantic_case_l3": "L3"},
        )
    ]

    decision = decide(launch_gates, **inputs)

    assert decision.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "dnp_semantic_unsupported_claim_l3" in decision.blockers
    assert _gate(decision, "dnp_semantic_unsupported_claim_l3").status is GateStatus.FAIL


def test_l3_consent_grader_failure_blocks_pilot(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    inputs = _clean_inputs(risk_weights)
    inputs["eval_run"]["per_case"][1]["failure_labels"] = [
        "CONSENT_BOUNDARY_VIOLATION"
    ]

    decision = decide(launch_gates, **inputs)

    assert decision.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "dnp_consent_grader_failure_l3" in decision.blockers
    assert _gate(decision, "dnp_consent_grader_failure_l3").status is GateStatus.FAIL


def test_redaction_coverage_drives_constraints_then_do_not_pilot(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    constraints_inputs = _clean_inputs(risk_weights)
    constraints_inputs["redaction_reports"] = [_redaction_report(9, 1, 1)]

    constraints = decide(launch_gates, **constraints_inputs)

    assert constraints.verdict is LaunchVerdict.PILOT_WITH_CONSTRAINTS
    assert _gate(constraints, "dnp_redaction_coverage_below_80").status is GateStatus.PASS
    assert _gate(constraints, "ready_redaction_coverage_95").status is GateStatus.FAIL

    blocked_inputs = _clean_inputs(risk_weights)
    blocked_inputs["redaction_reports"] = [_redaction_report(7, 3, 3)]

    blocked = decide(launch_gates, **blocked_inputs)

    assert blocked.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "dnp_redaction_coverage_below_80" in blocked.blockers
    assert _gate(blocked, "dnp_redaction_coverage_below_80").status is GateStatus.FAIL


def test_high_risk_regression_failure_blocks_pilot(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    inputs = _clean_inputs(risk_weights)
    inputs["regression_runs"] = [
        _regression_run(
            failed_case_count=1,
            per_case=[
                {
                    "case_id": "regression_l3_failed",
                    "risk_band": "L3",
                    "passed": False,
                }
            ],
        )
    ]

    decision = decide(launch_gates, **inputs)

    assert decision.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "dnp_regression_failure_high_risk" in decision.blockers
    assert _gate(decision, "dnp_regression_failure_high_risk").status is GateStatus.FAIL


def test_constraints_require_named_exceptions(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    with_review = _clean_inputs(risk_weights)
    with_review["redaction_reports"] = [_redaction_report(9, 1, 1)]

    constrained = decide(launch_gates, **with_review)

    assert constrained.verdict is LaunchVerdict.PILOT_WITH_CONSTRAINTS
    assert "missing_named_exceptions" not in constrained.blockers

    without_review = deepcopy(with_review)
    without_review["pilot_review_present"] = False

    blocked = decide(launch_gates, **without_review)

    assert blocked.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "missing_named_exceptions" in blocked.blockers
    assert _gate(blocked, "named_constraints_recorded").status is GateStatus.FAIL


def test_missing_role_input_fails_ready_but_not_do_not_pilot_gate(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    inputs = _clean_inputs(risk_weights)
    inputs["redaction_reports"] = []

    decision = decide(launch_gates, **inputs)

    assert decision.verdict is not LaunchVerdict.READY_FOR_INTERNAL_PILOT
    assert _gate(decision, "dnp_redaction_coverage_below_80").status is GateStatus.NOT_APPLICABLE
    assert _gate(decision, "ready_redaction_coverage_95").status is GateStatus.FAIL
    assert _gate(decision, "ready_inputs_complete").status is GateStatus.FAIL
    assert _gate(decision, "ready_inputs_complete").observed == 2
    assert "ready_inputs_complete" in decision.blockers


def test_risk_weighted_score_is_advisory(
    launch_gates: dict,
    risk_weights: dict,
) -> None:
    decision = decide(launch_gates, **_clean_inputs(risk_weights))
    result = _gate(decision, "ready_risk_weighted_score")

    assert decision.verdict is LaunchVerdict.READY_FOR_INTERNAL_PILOT
    assert result.status is GateStatus.NOT_APPLICABLE
    assert result.gating is False
    assert isinstance(result.observed, float)
    assert result.gate_id not in decision.blockers
