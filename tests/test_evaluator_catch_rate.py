"""Runtime EvaluatorNode + offline catch-rate measurement tests.

These tests lock in three things:

1. The runtime evaluator fires the new policy-citation and
   unsupported-claim checks on the baseline cases that should trigger
   them.
2. ``grade_evaluator_catch_rate`` returns a passing ``GraderResult``
   when the runtime caught an offline failure, and fails with
   ``EVALUATOR_MISS`` when it didn't.
3. The runtime ``EvaluatorReport`` and the offline ``GraderResult``
   remain structurally distinct, per AGENTS.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.agents import financial_links_reliability_agent
from app.evaluator import (
    evaluate,
    policy_citation_check,
    unsupported_claim_check,
)
from app.runner import run_case
from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    ApprovalStatus,
    Case,
    ConsentState,
    EvaluatorCheck,
    EvaluatorReport,
    GraderResult,
    HandoffPayload,
    PolicyReference,
    RiskBand,
    Severity,
    Workflow,
)
from evals.graders import (
    evaluator_catchable_categories,
    grade_evaluator_catch_rate,
)
from evals.run import run_eval


ROOT = Path(__file__).resolve().parents[1]
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
APPROVAL_MATRIX = yaml.safe_load((ROOT / "configs" / "approval_matrix.yaml").read_text())


def _case_dict(case_id: str) -> dict:
    for raw in FULL_V0_PATH.read_text().splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        if record["case_id"] == case_id:
            return record
    raise AssertionError(f"case_id {case_id!r} not in v0 dataset")


def _build_case(case_dict: dict) -> Case:
    return Case(
        case_id=case_dict["case_id"],
        workflow=Workflow(case_dict["workflow"]),
        risk_band=RiskBand(case_dict["risk_band"]),
        consent_sensitive=case_dict.get("consent_sensitive", False),
        payload=dict(case_dict.get("synthetic_facts", {})),
    )


def _run_agent(case_dict: dict, profile: str) -> AgentOutput:
    """Call the specialist directly so the runner doesn't intervene."""

    case = _build_case(case_dict)
    handoff = HandoffPayload(
        case_id=case.case_id,
        workflow=case.workflow,
        from_node="OrchestratorAgent",
        to_agent="FinancialLinksReliabilityAgent",
        declared_risk_band=case.risk_band,
        consent_state=ConsentState(case_dict["synthetic_facts"].get("expected_consent_state", "unknown")),
        consent_reconfirmed=False,
        route_context={
            "institution_id": case_dict["synthetic_facts"].get("institution_id"),
            "partner_id": case_dict["synthetic_facts"].get("partner_id"),
        },
    )
    return financial_links_reliability_agent.handle(
        case=case,
        handoff=handoff,
        approval_matrix=APPROVAL_MATRIX,
        profile=profile,
    )


# ---------------------------------------------------------------------------
# Runtime checks
# ---------------------------------------------------------------------------

def test_runtime_policy_citation_fires_on_baseline_partner_fallback() -> None:
    """case_fl_v0_005: baseline omits FL-PARTNER-FALLBACK-002. Runtime must catch it."""

    case_dict = _case_dict("case_fl_v0_005")
    output = _run_agent(case_dict, profile="baseline_v0")
    report = evaluate(
        output,
        required_fields=["case_id"],
        approval_matrix=APPROVAL_MATRIX,
        required_policy_ids=list(case_dict["required_policy_ids"]),
    )

    citation_check = next(c for c in report.checks if c.name == "policy_citation")
    assert citation_check.ok is False
    assert "FL-PARTNER-FALLBACK-002" in citation_check.metadata["missing"]


def test_runtime_unsupported_claim_fires_on_baseline_rebranded_case() -> None:
    """case_fl_v0_010: baseline injects an in-real-time overpromise. Runtime must catch it."""

    case_dict = _case_dict("case_fl_v0_010")
    output = _run_agent(case_dict, profile="baseline_v0")
    report = evaluate(
        output,
        required_fields=["case_id"],
        approval_matrix=APPROVAL_MATRIX,
        required_policy_ids=list(case_dict["required_policy_ids"]),
    )

    claim_check = next(c for c in report.checks if c.name == "unsupported_claim")
    assert claim_check.ok is False
    assert claim_check.metadata["matched_patterns"], "expected at least one matched pattern"


def test_runtime_policy_and_claim_checks_pass_for_improved_profile() -> None:
    """Both runtime checks must pass on every smoke case for improved_v0."""

    for case_id in ("case_fl_v0_005", "case_fl_v0_010"):
        case_dict = _case_dict(case_id)
        output = _run_agent(case_dict, profile="improved_v0")
        report = evaluate(
            output,
            required_fields=["case_id"],
            approval_matrix=APPROVAL_MATRIX,
            required_policy_ids=list(case_dict["required_policy_ids"]),
        )
        for name in ("policy_citation", "unsupported_claim"):
            check = next(c for c in report.checks if c.name == name)
            assert check.ok is True, (case_id, name, check)


def test_unsupported_claim_check_helper_passes_on_hedged_draft() -> None:
    output = AgentOutput(
        case_id="case_test",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        declared_risk_band=RiskBand.L1,
        consent_state=ConsentState.GRANTED,
        draft_text="Customer copy uses hedged language; no real-time guarantee is implied.",
        approval=ApprovalDecision(required=False, status=ApprovalStatus.NOT_REQUIRED),
    )
    assert unsupported_claim_check(output).ok is True


def test_policy_citation_check_helper_passes_when_required_cited() -> None:
    output = AgentOutput(
        case_id="case_test",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        declared_risk_band=RiskBand.L1,
        consent_state=ConsentState.GRANTED,
        draft_text="hedged",
        policy_references=[PolicyReference(policy_id="FL-COPY-STALE-003", retrieved=True)],
        approval=ApprovalDecision(required=False, status=ApprovalStatus.NOT_REQUIRED),
    )
    assert policy_citation_check(output, ["FL-COPY-STALE-003"]).ok is True


# ---------------------------------------------------------------------------
# Catch-rate grader
# ---------------------------------------------------------------------------

def _failing_gr(label: str) -> GraderResult:
    return GraderResult(
        passed=False,
        score=0.0,
        severity=Severity.L2,
        failure_label=label,
        explanation="synthetic test failure",
    )


def _failing_check(name: str) -> EvaluatorCheck:
    return EvaluatorCheck(name=name, ok=False, reason="synthetic test fail")


def _passing_check(name: str) -> EvaluatorCheck:
    return EvaluatorCheck(name=name, ok=True)


def test_catch_rate_passes_when_runtime_caught_failure() -> None:
    result = grade_evaluator_catch_rate(
        grader_results=[_failing_gr("POLICY_MISS")],
        evaluator_report=EvaluatorReport(checks=[_failing_check("policy_citation")]),
    )
    assert result.passed is True
    assert result.failure_label is None
    assert isinstance(result, GraderResult)


def test_catch_rate_fails_with_evaluator_miss_when_runtime_missed() -> None:
    result = grade_evaluator_catch_rate(
        grader_results=[_failing_gr("UNSAFE_CUSTOMER_COMMS")],
        evaluator_report=EvaluatorReport(checks=[_passing_check("unsupported_claim")]),
    )
    assert result.passed is False
    assert result.failure_label == "EVALUATOR_MISS"
    missed_labels = [m["label"] for m in result.evidence["missed"]]
    assert "UNSAFE_CUSTOMER_COMMS" in missed_labels


def test_catch_rate_ignores_out_of_scope_failures() -> None:
    """Architectural failures (TOOL_MISUSE etc.) are intentionally out of scope."""

    result = grade_evaluator_catch_rate(
        grader_results=[_failing_gr("TOOL_MISUSE"), _failing_gr("HANDOFF_CONTEXT_LOSS")],
        evaluator_report=EvaluatorReport(checks=[_passing_check("schema_required_fields")]),
    )
    assert result.passed is True, result.evidence
    assert result.failure_label is None


def test_catch_rate_aggregates_multiple_misses() -> None:
    result = grade_evaluator_catch_rate(
        grader_results=[
            _failing_gr("POLICY_MISS"),
            _failing_gr("UNSAFE_CUSTOMER_COMMS"),
        ],
        evaluator_report=EvaluatorReport(checks=[]),
    )
    assert result.passed is False
    missed_labels = {m["label"] for m in result.evidence["missed"]}
    assert missed_labels == {"POLICY_MISS", "UNSAFE_CUSTOMER_COMMS"}


def test_catchable_categories_are_explicit_and_small() -> None:
    scope = evaluator_catchable_categories()
    assert set(scope) == {
        "POLICY_MISS",
        "UNSAFE_CUSTOMER_COMMS",
        "CONSENT_BOUNDARY_VIOLATION",
        "UNSUPPORTED_ACTION",
    }


# ---------------------------------------------------------------------------
# Integration into the eval report
# ---------------------------------------------------------------------------

def test_v0_baseline_report_includes_catch_rate_aggregate(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp_path / "traces",
        agent_system_version="baseline_v0",
    )
    names = [rate.name for rate in report.aggregate_grader_pass_rates]
    assert "evaluator_catch_rate" in names


def test_v0_baseline_report_has_no_evaluator_miss(tmp_path: Path) -> None:
    """The runtime evaluator should catch every planted v0 baseline failure."""

    report = run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp_path / "traces",
        agent_system_version="baseline_v0",
    )
    assert "EVALUATOR_MISS" not in report.failure_label_counts, (
        f"runtime evaluator missed an in-scope offline failure; "
        f"label counts: {report.failure_label_counts}"
    )

    catch_rate = next(
        rate for rate in report.aggregate_grader_pass_rates
        if rate.name == "evaluator_catch_rate"
    )
    assert catch_rate.passed == catch_rate.total


def test_evaluator_report_and_grader_result_remain_distinct() -> None:
    """EvaluatorReport (runtime) and GraderResult (offline) stay separate types."""

    eval_report = EvaluatorReport(checks=[_passing_check("consent_boundary")])
    grader_result = grade_evaluator_catch_rate(
        grader_results=[],
        evaluator_report=eval_report,
    )
    assert isinstance(eval_report, EvaluatorReport)
    assert isinstance(grader_result, GraderResult)
    assert not isinstance(eval_report, GraderResult)
    assert not isinstance(grader_result, EvaluatorReport)


def test_runtime_evaluator_catches_baseline_via_runner(tmp_path: Path) -> None:
    """End-to-end: run_case + baseline + case_fl_v0_005 must surface a failing policy_citation."""

    case_dict = _case_dict("case_fl_v0_005")
    result = run_case(case_dict, agent_system_version="baseline_v0")
    failing_names = {c.name for c in result.trace.evaluator_report.checks if not c.ok}
    assert "policy_citation" in failing_names


@pytest.mark.parametrize(
    "case_id,expected_failing_check",
    [
        ("case_fl_v0_005", "policy_citation"),
        ("case_fl_v0_010", "unsupported_claim"),
    ],
)
def test_runner_evaluator_catches_planted_baseline_failures(
    case_id: str, expected_failing_check: str
) -> None:
    case_dict = _case_dict(case_id)
    result = run_case(case_dict, agent_system_version="baseline_v0")
    failing_names = {c.name for c in result.trace.evaluator_report.checks if not c.ok}
    assert expected_failing_check in failing_names, (case_id, failing_names)
