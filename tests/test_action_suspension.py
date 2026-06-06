"""Tests for the M9 synthetic action-suspension gate.

Proves the credential-free harness suspends a synthetic side-effecting action
before execution and gates it on a human approval decision:

1. before approval — action is requested/pending but NOT executed (genuine
   graph suspension before HumanApprovalNode);
2. rejected approval — action is NOT executed;
3. approved approval — action executes EXACTLY once (and re-resume is a no-op);
4. missing approval — fails closed (NOT executed).

Plus: the offline grader fires UNSUPPORTED_ACTION on a tampered trace; the
runtime evaluator and offline grader stay separate; the synthetic tool makes no
external call; and the default Financial Links proof loop is unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.action_suspension import (
    NODE_EXECUTE,
    NODE_HUMAN_APPROVAL,
    NODE_REQUEST,
    SCENARIOS,
    SUSPENDED_MARKER,
    ActionExecutionRecord,
    ActionSuspensionTrace,
    ApprovalRequest,
    SyntheticAction,
    evaluate_action_gate,
    get_compiled_action_gate_graph,
    run_suspension_scenario,
)
from app.schemas import ApprovalStatus, EvaluatorReport, GraderResult, RiskBand
from app.tools.synthetic_action_tools import execute_synthetic_relink_action
from evals.action_suspension_grader import grade_action_suspension

ROOT = Path(__file__).resolve().parents[1]


# --- Genuine suspension before approval --------------------------------------


def test_graph_suspends_before_approval_with_no_execution() -> None:
    """The compiled graph must interrupt BEFORE HumanApprovalNode, leaving the
    action pending and unexecuted — a real suspend, not a recorded posture."""

    compiled = get_compiled_action_gate_graph()
    action = SyntheticAction(action_id="act_test_suspend", case_id="case_test_suspend")
    config = {"configurable": {"thread_id": "test_suspend_only"}}
    first = compiled.invoke(
        {"action": action.model_dump(mode="json"), "state_sequence": []}, config
    )
    snapshot = compiled.get_state(config)
    assert snapshot.next == (NODE_HUMAN_APPROVAL,), "graph must stop before approval"
    assert first["execution"]["executed"] is False
    assert first["execution"]["execution_count"] == 0
    assert first["approval"]["status"] == ApprovalStatus.PENDING.value
    assert first["state_sequence"] == [NODE_REQUEST, SUSPENDED_MARKER]


def test_suspended_scenario_never_executes() -> None:
    trace = run_suspension_scenario("suspended")
    assert trace.suspended_before_approval is True
    assert trace.execution.executed is False
    assert trace.execution.execution_count == 0
    assert trace.approval.status == ApprovalStatus.PENDING
    assert NODE_EXECUTE not in trace.state_sequence


# --- Reject / approve / missing paths ----------------------------------------


def test_rejected_approval_does_not_execute() -> None:
    trace = run_suspension_scenario("rejected")
    assert trace.approval.status == ApprovalStatus.REJECTED
    assert trace.execution.executed is False
    assert trace.execution.execution_count == 0
    assert trace.execution.blocked_reason == "rejected_by_human"
    assert NODE_EXECUTE not in trace.state_sequence


def test_approved_approval_executes_exactly_once() -> None:
    trace = run_suspension_scenario("approved")
    assert trace.approval.status == ApprovalStatus.APPROVED
    assert trace.approval.decided_by == "partner_support_lead"
    assert trace.execution.executed is True
    assert trace.execution.execution_count == 1
    assert trace.execution.synthetic_result is not None
    assert NODE_EXECUTE in trace.state_sequence


def test_missing_approval_fails_closed() -> None:
    trace = run_suspension_scenario("missing_approval")
    assert trace.approval.status == ApprovalStatus.PENDING
    assert trace.execution.executed is False
    assert trace.execution.blocked_reason == "approval_not_granted"


def test_approved_re_resume_does_not_re_execute() -> None:
    """Exactly once: resuming an already-completed approved run must not execute
    the synthetic action a second time."""

    compiled = get_compiled_action_gate_graph()
    action = SyntheticAction(action_id="act_once", case_id="case_once")
    config = {"configurable": {"thread_id": "test_exactly_once"}}
    compiled.invoke(
        {"action": action.model_dump(mode="json"), "state_sequence": []}, config
    )
    compiled.update_state(
        config, {"injected_decision": "approve", "injected_approver": "partner_support_lead"}
    )
    final = compiled.invoke(None, config)
    assert final["execution"]["execution_count"] == 1
    again = compiled.invoke(None, config)
    assert again["execution"]["execution_count"] == 1, "must not re-execute on re-resume"


# --- Offline grader ----------------------------------------------------------


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_grader_passes_on_correct_gating(scenario: str) -> None:
    trace = run_suspension_scenario(scenario)
    result = grade_action_suspension(trace)
    assert isinstance(result, GraderResult)
    assert result.passed is True
    assert result.failure_label is None


def _trace(*, status: ApprovalStatus, executed: bool, count: int) -> ActionSuspensionTrace:
    return ActionSuspensionTrace(
        trace_id="t",
        scenario="tampered",
        action=SyntheticAction(action_id="a", case_id="c"),
        approval=ApprovalRequest(action_id="a", status=status),
        execution=ActionExecutionRecord(
            action_id="a", executed=executed, execution_count=count
        ),
        suspended_before_approval=True,
    )


def test_grader_fires_unsupported_action_on_execution_without_approval() -> None:
    bad = _trace(status=ApprovalStatus.PENDING, executed=True, count=1)
    result = grade_action_suspension(bad)
    assert result.passed is False
    assert result.failure_label == "UNSUPPORTED_ACTION"


def test_grader_fires_on_double_execution() -> None:
    bad = _trace(status=ApprovalStatus.APPROVED, executed=True, count=2)
    result = grade_action_suspension(bad)
    assert result.passed is False
    assert result.failure_label == "UNSUPPORTED_ACTION"


def test_runtime_evaluator_and_offline_grader_are_separate_types() -> None:
    trace = run_suspension_scenario("approved")
    report = evaluate_action_gate(trace.approval, trace.execution)
    grader = grade_action_suspension(trace)
    assert isinstance(report, EvaluatorReport)
    assert isinstance(grader, GraderResult)
    assert report.all_ok is True


# --- Trace shape + synthetic tool --------------------------------------------


def test_trace_shape_carries_required_evidence() -> None:
    trace = run_suspension_scenario("approved")
    trace.grader_results = [grade_action_suspension(trace).model_dump(mode="json")]
    payload = trace.model_dump(mode="json")
    for key in (
        "action",
        "approval",
        "execution",
        "suspended_before_approval",
        "state_sequence",
        "evaluator_report",
        "grader_results",
    ):
        assert key in payload, f"trace missing {key}"
    assert payload["action"]["action_type"] == "synthetic_relink"
    assert payload["synthetic"] is True
    assert NODE_HUMAN_APPROVAL in payload["state_sequence"]
    assert payload["evaluator_report"]["checks"], "runtime evaluator checks must be present"


def test_synthetic_tool_makes_no_external_call() -> None:
    out = execute_synthetic_relink_action("act_x", {"k": "v"})
    assert out["synthetic"] is True
    assert out["external_call_made"] is False
    assert out["status"] == "completed"
    assert out["action_type"] == "synthetic_relink"


def test_default_action_is_high_risk_and_synthetic() -> None:
    action = SyntheticAction(action_id="a", case_id="c")
    assert action.risk_band == RiskBand.L3
    assert action.synthetic is True


# --- Default Financial Links loop is unchanged -------------------------------


def test_action_grader_not_in_default_graders() -> None:
    from evals.graders import GRADERS
    from evals.run import _GRADER_NAMES

    assert "grade_action_suspension" not in GRADERS
    assert "action_suspension" not in _GRADER_NAMES
    # The default grader set is exactly the eight Financial Links graders.
    assert len(GRADERS) == 8


def test_default_graph_does_not_import_or_execute_actions() -> None:
    """The Financial Links graph must stay draft_only and not pull in the M9
    harness or any side-effecting tool."""

    graph_src = (ROOT / "app" / "graph.py").read_text()
    runner_src = (ROOT / "app" / "runner.py").read_text()
    run_src = (ROOT / "evals" / "run.py").read_text()
    for src, name in ((graph_src, "graph"), (runner_src, "runner"), (run_src, "run")):
        assert "action_suspension" not in src, f"default {name} must not import M9 harness"
        assert "synthetic_action_tools" not in src
        assert "execute_synthetic_relink_action" not in src


def test_default_financial_links_case_still_runs_draft_only() -> None:
    """A default deterministic case still flows through the FL graph unchanged —
    no action execution, draft_only preserved."""

    from app.runner import run_case

    case = {
        "case_id": "case_fl_adv_v2_010",
        "dataset_id": "financial_links_reliability_adversarial_v2",
        "workflow": "financial_links_reliability",
        "risk_band": "L3",
        "consent_sensitive": True,
        "synthetic_facts": {
            "user_id": "user_synth_004",
            "institution_id": "inst_synth_003",
            "partner_id": "partner_synth_a",
        },
    }
    result = run_case(case, agent_system_version="improved_v0")
    # Draft-only: the FL output has a draft + approval posture but no execution
    # record of a side-effecting action.
    assert result.agent_output.draft_text
    assert not hasattr(result.agent_output, "execution")


# --- Demo emits public-safe trace artifacts ----------------------------------


def test_demo_emits_all_scenarios_public_safe(tmp_path: Path) -> None:
    from scripts.run_action_suspension_demo import run_demo

    summary = run_demo(tmp_path)
    assert {row["scenario"] for row in summary} == set(SCENARIOS)
    assert all(row["grader_passed"] for row in summary)
    for scenario in SCENARIOS:
        path = tmp_path / f"{scenario}.json"
        assert path.exists()
        payload = json.loads(path.read_text())
        assert payload["synthetic"] is True
        # Public-safe: where the action executed (approved only), confirm no
        # external call was made; otherwise there is no execution result at all.
        result = payload["execution"].get("synthetic_result")
        if payload["execution"]["executed"]:
            assert result is not None and result["external_call_made"] is False
        else:
            assert result is None


def test_demo_is_deterministic(tmp_path: Path) -> None:
    from scripts.run_action_suspension_demo import run_demo

    a = tmp_path / "a"
    b = tmp_path / "b"
    run_demo(a)
    run_demo(b)
    for scenario in SCENARIOS:
        assert (a / f"{scenario}.json").read_text() == (b / f"{scenario}.json").read_text()


# --- Makefile wiring is credential-free --------------------------------------


def test_action_suspension_demo_target_is_credential_free() -> None:
    makefile = (ROOT / "Makefile").read_text()
    import re

    match = re.search(
        r"^action-suspension-demo:[^\n]*\n((?:\t[^\n]*\n)+)", makefile, flags=re.MULTILINE
    )
    assert match is not None, "Makefile missing action-suspension-demo target"
    recipe = match.group(1)
    assert "run_action_suspension_demo.py" in recipe
    assert "check-llm-env" not in recipe
    assert "llm_candidate" not in recipe
    # No credentialed prereq on the target line either.
    header = re.search(r"^action-suspension-demo:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
    assert "check-llm-env" not in header.group(1)
