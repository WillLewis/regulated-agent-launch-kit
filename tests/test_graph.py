"""Tests for the LangGraph-backed Financial Links runner.

These tests are intentionally focused on the graph wiring (node names,
routing, state population) and on the behaviors the runner contract
guarantees end-to-end. Existing runner / evaluator-catch-rate / profile
tests already cover the offline grader and trace-shape invariants; here
we lock in that those invariants survive the migration to a graph.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.graph import (
    GRAPH_NODE_NAMES,
    NODE_EVALUATOR,
    NODE_FINAL,
    NODE_HUMAN_APPROVAL,
    NODE_INTAKE,
    NODE_ORCHESTRATOR,
    NODE_SPECIALIST,
    build_graph,
    get_compiled_graph,
    invoke_graph,
)
from app.runner import run_case


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
APPROVAL_MATRIX_PATH = ROOT / "configs" / "approval_matrix.yaml"


def _load_smoke_cases() -> dict[str, dict]:
    return {
        json.loads(line)["case_id"]: json.loads(line)
        for line in SMOKE_PATH.read_text().splitlines()
        if line.strip()
    }


def _load_v0_case(case_id: str) -> dict:
    for raw in FULL_V0_PATH.read_text().splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        if record["case_id"] == case_id:
            return record
    raise AssertionError(f"case_id {case_id!r} not in v0 dataset")


def _approval_matrix() -> dict:
    return yaml.safe_load(APPROVAL_MATRIX_PATH.read_text())


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------

def test_graph_exposes_the_six_expected_node_names() -> None:
    assert GRAPH_NODE_NAMES == (
        "IntakeNormalizer",
        "OrchestratorAgent",
        "FinancialLinksReliabilityAgent",
        "EvaluatorNode",
        "HumanApprovalNode",
        "FinalResponseComposer",
    )


def test_compiled_graph_registers_every_node_name() -> None:
    builder = build_graph()
    registered = set(builder.nodes)
    for name in GRAPH_NODE_NAMES:
        assert name in registered, f"graph missing node {name!r}"


def test_compiled_graph_is_cached() -> None:
    assert get_compiled_graph() is get_compiled_graph()


# ---------------------------------------------------------------------------
# Smoke pass — improved profile
# ---------------------------------------------------------------------------

def test_smoke_case_runs_through_graph_with_expected_trace_fields() -> None:
    case = _load_smoke_cases()["case_fl_v0_001"]
    result = run_case(case, agent_system_version="improved_v0")

    trace = result.trace
    # Pre-graph guarantees still hold
    assert trace.case_id == "case_fl_v0_001"
    assert trace.orchestrator_decision == "FinancialLinksReliabilityAgent"
    assert "FinancialLinksReliabilityAgent" in trace.specialist_path
    assert trace.handoff is not None
    assert trace.handoff.from_node == NODE_ORCHESTRATOR
    assert trace.tool_calls, "tool calls must survive graph migration"
    assert trace.evaluator_report.all_ok
    assert trace.final_response


def test_specialist_path_records_every_visited_node_in_order() -> None:
    case = _load_smoke_cases()["case_fl_v0_001"]
    result = run_case(case, agent_system_version="improved_v0")

    # case_fl_v0_001 is L1 routine → approval not required → human-approval
    # node should be skipped. Path is intake → orch → specialist → eval → final.
    assert result.trace.specialist_path == [
        NODE_INTAKE,
        NODE_ORCHESTRATOR,
        NODE_SPECIALIST,
        NODE_EVALUATOR,
        NODE_FINAL,
    ]
    assert NODE_HUMAN_APPROVAL not in result.trace.specialist_path


def test_human_approval_node_visited_only_when_approval_required() -> None:
    """case_fl_v0_002 is L2 expired-consent → improved profile requires approval."""

    case = _load_smoke_cases()["case_fl_v0_002"]
    result = run_case(case, agent_system_version="improved_v0")

    assert result.agent_output.approval.required is True
    assert NODE_HUMAN_APPROVAL in result.trace.specialist_path
    # The human-approval node sits between EvaluatorNode and FinalResponseComposer.
    path = result.trace.specialist_path
    assert path.index(NODE_HUMAN_APPROVAL) > path.index(NODE_EVALUATOR)
    assert path.index(NODE_HUMAN_APPROVAL) < path.index(NODE_FINAL)


def test_l2_expired_consent_still_escalates_through_graph() -> None:
    case = _load_smoke_cases()["case_fl_v0_002"]
    result = run_case(case, agent_system_version="improved_v0")

    output = result.agent_output
    assert output.approval.required is True
    assert output.approval.approver_role == "partner_support_analyst"
    assert result.trace.evaluator_report.all_ok


# ---------------------------------------------------------------------------
# Profile divergence still surfaces
# ---------------------------------------------------------------------------

def test_baseline_vs_improved_diverge_on_partner_fallback_case() -> None:
    """case_fl_v0_005: baseline omits FL-PARTNER-FALLBACK-002; improved cites it."""

    case = _load_v0_case("case_fl_v0_005")
    baseline = run_case(case, agent_system_version="baseline_v0").agent_output
    improved = run_case(case, agent_system_version="improved_v0").agent_output

    baseline_cited = {ref.policy_id for ref in baseline.policy_references}
    improved_cited = {ref.policy_id for ref in improved.policy_references}
    assert "FL-PARTNER-FALLBACK-002" not in baseline_cited
    assert "FL-PARTNER-FALLBACK-002" in improved_cited


def test_baseline_failure_still_triggers_runtime_evaluator_through_graph() -> None:
    case = _load_v0_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="baseline_v0")
    failing = {check.name for check in result.trace.evaluator_report.checks if not check.ok}
    # Runtime policy_citation check should fire on the baseline missing policy.
    assert "policy_citation" in failing


def test_graph_handoff_payload_carries_route_context_per_r9() -> None:
    """PLAN.md R9: handoff is Pydantic-enforced with consent, risk, route context."""

    case = _load_v0_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="improved_v0")

    handoff = result.trace.handoff
    assert handoff is not None
    assert handoff.consent_state.value == "granted"
    assert handoff.declared_risk_band.value == "L2"
    assert handoff.route_context["institution_id"] == "inst_synth_003"
    assert handoff.route_context["partner_id"] == "partner_synth_a"


# ---------------------------------------------------------------------------
# Direct graph invocation (without going through run_case)
# ---------------------------------------------------------------------------

def test_invoke_graph_populates_full_state() -> None:
    case = _load_smoke_cases()["case_fl_v0_001"]
    state = invoke_graph(
        case_dict=case,
        profile="improved_v0",
        approval_matrix=_approval_matrix(),
    )

    for key in (
        "case",
        "initial_consent_state",
        "handoff",
        "orchestrator_decision",
        "specialist_path",
        "agent_output",
        "evaluator_report",
        "final_response",
    ):
        assert key in state, f"final state missing {key!r}"


@pytest.mark.parametrize(
    "case_id,expected_approval_required",
    [
        ("case_fl_v0_001", False),
        ("case_fl_v0_002", True),
        ("case_fl_v0_005", True),
    ],
)
def test_routing_depends_on_approval_required(
    case_id: str, expected_approval_required: bool
) -> None:
    case = _load_smoke_cases()[case_id]
    result = run_case(case, agent_system_version="improved_v0")
    assert result.agent_output.approval.required is expected_approval_required
    if expected_approval_required:
        assert NODE_HUMAN_APPROVAL in result.trace.specialist_path
    else:
        assert NODE_HUMAN_APPROVAL not in result.trace.specialist_path
