"""M9 — synthetic action-suspension gate (credential-free, separate harness).

Proves that a ``HumanApprovalNode`` can **suspend a synthetic side-effecting
action before it executes** and gate it on a human approval decision. This is a
*separate* harness from the Financial Links proof loop: ``app.graph`` is
untouched and stays ``draft_only``. M9 does not change any default eval
behavior — it adds a dedicated graph that demonstrates the suspend/resume +
execute-once semantics a real deployment's approval gate would need.

The graph is a real ``langgraph.StateGraph`` compiled with a checkpointer and
``interrupt_before=[HumanApprovalNode]``, so the first ``invoke`` genuinely
**suspends before the approval node** (the action is requested but not
executed). A human decision is injected via ``update_state`` and the graph is
resumed with ``invoke(None, config)``:

- **suspended** (never resumed): action stays pending, never executes;
- **rejected**: resumes, routes around execution — never executes;
- **approved**: resumes, executes the synthetic tool **exactly once**;
- **missing approval** (resume with no decision): fails closed — never executes.

Everything is synthetic and deterministic. The runtime evaluator checks
(``evaluate_action_gate``) live here; the *offline* grader
(``evals.action_suspension_grader``) scores the completed trace independently —
the two surfaces stay separate per ``AGENTS.md``. ``app`` does not import
``evals``; the demo/tests attach grader results.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.schemas import (
    ApprovalStatus,
    EvaluatorCheck,
    EvaluatorReport,
    RiskBand,
)
from app.tools.synthetic_action_tools import (
    SYNTHETIC_ACTION_TYPE,
    execute_synthetic_relink_action,
)

# Public node names — tests and the trace's ``state_sequence`` depend on them.
NODE_REQUEST: str = "RequestActionNode"
NODE_HUMAN_APPROVAL: str = "HumanApprovalNode"
NODE_EXECUTE: str = "ExecuteActionNode"
NODE_SKIP: str = "SkipExecutionNode"
NODE_FINAL: str = "FinalComposerNode"

SUSPENDED_MARKER: str = "suspended_pending_approval"

DEFAULT_APPROVER_ROLE: str = "partner_support_lead"

SCENARIOS: tuple[str, ...] = ("suspended", "approved", "rejected", "missing_approval")


# --- Explicit schemas (task 1) ----------------------------------------------


class SyntheticAction(BaseModel):
    """A synthetic side-effecting action requested by the agent."""

    action_id: str
    action_type: str = SYNTHETIC_ACTION_TYPE
    case_id: str
    risk_band: RiskBand = RiskBand.L3
    approver_role: str = DEFAULT_APPROVER_ROLE
    synthetic_args: dict[str, Any] = Field(default_factory=dict)
    synthetic: bool = True


class ApprovalRequest(BaseModel):
    """The human-approval posture for one synthetic action."""

    action_id: str
    required: bool = True
    approver_role: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None
    reason: str | None = None


class ActionExecutionRecord(BaseModel):
    """Whether (and how often) the synthetic action actually executed."""

    action_id: str
    executed: bool = False
    execution_count: int = 0
    synthetic_result: dict[str, Any] | None = None
    blocked_reason: str | None = None


class ActionSuspensionTrace(BaseModel):
    """Local trace artifact for one M9 scenario (synthetic, public-safe)."""

    trace_id: str
    scenario: str
    synthetic: bool = True
    action: SyntheticAction
    approval: ApprovalRequest
    execution: ActionExecutionRecord
    suspended_before_approval: bool
    state_sequence: list[str] = Field(default_factory=list)
    evaluator_report: EvaluatorReport = Field(default_factory=EvaluatorReport)
    grader_results: list[Any] = Field(default_factory=list)


# --- Graph state + nodes -----------------------------------------------------
#
# The graph state holds **plain JSON-serializable dicts**, not pydantic models,
# so the checkpointer (MemorySaver) serializes it cleanly across the interrupt
# with no custom-type serde warnings. The pydantic schemas above are the
# external contract; the harness builds them from the final dict state.


class ActionGateState(TypedDict, total=False):
    action: dict[str, Any]
    approval: dict[str, Any]
    execution: dict[str, Any]
    injected_decision: str | None  # "approve" | "reject" | None
    injected_approver: str | None
    state_sequence: list[str]
    evaluator_checks: list[dict[str, Any]]


def _node_request_action(state: ActionGateState) -> dict[str, Any]:
    action = state["action"]
    approval = {
        "action_id": action["action_id"],
        "required": True,
        "approver_role": action.get("approver_role", DEFAULT_APPROVER_ROLE),
        "status": ApprovalStatus.PENDING.value,
        "decided_by": None,
        "reason": (
            "Synthetic side-effecting action requires explicit human approval "
            "before execution."
        ),
    }
    execution = {
        "action_id": action["action_id"],
        "executed": False,
        "execution_count": 0,
        "synthetic_result": None,
        "blocked_reason": "awaiting_human_approval",
    }
    return {
        "approval": approval,
        "execution": execution,
        "state_sequence": [NODE_REQUEST, SUSPENDED_MARKER],
    }


def _node_human_approval(state: ActionGateState) -> dict[str, Any]:
    """Records the injected human decision. The graph is compiled to interrupt
    *before* this node, so reaching it means a human decision step occurred."""

    approval = dict(state["approval"])
    decision = state.get("injected_decision")
    approver = state.get("injected_approver")
    if decision == "approve":
        approval["status"] = ApprovalStatus.APPROVED.value
        approval["decided_by"] = approver or approval.get("approver_role")
        approval["reason"] = "Human approver granted the synthetic action."
    elif decision == "reject":
        approval["status"] = ApprovalStatus.REJECTED.value
        approval["decided_by"] = approver or approval.get("approver_role")
        approval["reason"] = "Human approver rejected the synthetic action."
    else:
        # Resumed with no decision -> stays PENDING -> fail closed downstream.
        approval["reason"] = "Resumed without an approval decision; failing closed."
    return {
        "approval": approval,
        "state_sequence": [*state["state_sequence"], NODE_HUMAN_APPROVAL],
    }


def _route_after_approval(state: ActionGateState) -> str:
    if state["approval"]["status"] == ApprovalStatus.APPROVED.value:
        return NODE_EXECUTE
    return NODE_SKIP


def _node_execute_action(state: ActionGateState) -> dict[str, Any]:
    action = state["action"]
    approval = state["approval"]
    execution = dict(state["execution"])
    # Fail closed (defense in depth): only an APPROVED action may execute, and
    # only once.
    if approval["status"] != ApprovalStatus.APPROVED.value:
        execution["blocked_reason"] = "execution_blocked_not_approved"
        return {
            "execution": execution,
            "state_sequence": [*state["state_sequence"], NODE_EXECUTE],
        }
    if execution["executed"]:
        return {"state_sequence": [*state["state_sequence"], NODE_EXECUTE]}
    result = execute_synthetic_relink_action(
        action["action_id"], action.get("synthetic_args", {})
    )
    execution["executed"] = True
    execution["execution_count"] = execution["execution_count"] + 1
    execution["synthetic_result"] = result
    execution["blocked_reason"] = None
    return {
        "execution": execution,
        "state_sequence": [*state["state_sequence"], NODE_EXECUTE],
    }


def _node_skip_execution(state: ActionGateState) -> dict[str, Any]:
    approval = state["approval"]
    execution = dict(state["execution"])
    execution["blocked_reason"] = (
        "rejected_by_human"
        if approval["status"] == ApprovalStatus.REJECTED.value
        else "approval_not_granted"
    )
    return {
        "execution": execution,
        "state_sequence": [*state["state_sequence"], NODE_SKIP],
    }


def _node_final(state: ActionGateState) -> dict[str, Any]:
    checks = _evaluator_check_dicts(state["approval"], state["execution"])
    return {
        "evaluator_checks": checks,
        "state_sequence": [*state["state_sequence"], NODE_FINAL],
    }


def _evaluator_check_dicts(
    approval: dict[str, Any],
    execution: dict[str, Any],
) -> list[dict[str, Any]]:
    """Runtime gate self-checks as plain dicts (so they survive checkpointing).

    Distinct from the offline ``grade_action_suspension`` grader — this is the
    inline gate self-check; the grader independently scores the finished trace.
    """

    approved = approval["status"] == ApprovalStatus.APPROVED.value
    executed = bool(execution["executed"])
    count = int(execution["execution_count"])
    required = bool(approval["required"])
    return [
        {
            "name": "execution_requires_approval",
            "ok": (not executed) or approved,
            "reason": (
                None
                if (not executed) or approved
                else "synthetic action executed without an APPROVED decision"
            ),
            "metadata": {"executed": executed, "approval_status": approval["status"]},
        },
        {
            "name": "single_execution",
            "ok": count <= 1,
            "reason": None if count <= 1 else f"executed {count} times",
            "metadata": {"execution_count": count},
        },
        {
            "name": "approval_required_recorded",
            "ok": required,
            "reason": None if required else "side-effecting action not gated",
            "metadata": {"required": required},
        },
    ]


def evaluate_action_gate(
    approval: ApprovalRequest,
    execution: ActionExecutionRecord,
) -> EvaluatorReport:
    """Public runtime evaluator over the typed approval/execution records.

    Wraps :func:`_evaluator_check_dicts` so callers outside the graph (and the
    suspended-scenario path) can compute the same checks against the pydantic
    schemas.
    """

    checks = _evaluator_check_dicts(
        approval.model_dump(mode="json"), execution.model_dump(mode="json")
    )
    return EvaluatorReport(checks=[EvaluatorCheck(**c) for c in checks])


_COMPILED_GRAPH: Any = None


def build_action_gate_graph() -> StateGraph:
    graph = StateGraph(ActionGateState)
    graph.add_node(NODE_REQUEST, _node_request_action)
    graph.add_node(NODE_HUMAN_APPROVAL, _node_human_approval)
    graph.add_node(NODE_EXECUTE, _node_execute_action)
    graph.add_node(NODE_SKIP, _node_skip_execution)
    graph.add_node(NODE_FINAL, _node_final)

    graph.set_entry_point(NODE_REQUEST)
    graph.add_edge(NODE_REQUEST, NODE_HUMAN_APPROVAL)
    graph.add_conditional_edges(
        NODE_HUMAN_APPROVAL,
        _route_after_approval,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_SKIP: NODE_SKIP},
    )
    graph.add_edge(NODE_EXECUTE, NODE_FINAL)
    graph.add_edge(NODE_SKIP, NODE_FINAL)
    graph.add_edge(NODE_FINAL, END)
    return graph


def get_compiled_action_gate_graph() -> Any:
    """Compile (and cache) the gate graph with a checkpointer + an interrupt
    before the approval node so the first invoke genuinely suspends.

    The cached ``MemorySaver`` is keyed by ``thread_id`` and lives for the
    process; scenarios use distinct deterministic thread IDs so they never
    collide. This is fine for the deterministic demo/tests — a long-lived
    service would instead want per-run saver isolation.
    """

    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_action_gate_graph().compile(
            checkpointer=MemorySaver(),
            interrupt_before=[NODE_HUMAN_APPROVAL],
        )
    return _COMPILED_GRAPH


def default_synthetic_action(scenario: str) -> SyntheticAction:
    return SyntheticAction(
        action_id=f"act_synth_{scenario}",
        case_id=f"case_m9_{scenario}",
        risk_band=RiskBand.L3,
        approver_role=DEFAULT_APPROVER_ROLE,
        synthetic_args={"institution_id": "inst_synth_001", "partner_id": "partner_synth_a"},
    )


def run_suspension_scenario(
    scenario: str,
    *,
    action: SyntheticAction | None = None,
) -> ActionSuspensionTrace:
    """Drive one suspend/resume scenario and return its trace.

    ``scenario`` is one of :data:`SCENARIOS`. The ``suspended`` scenario stops at
    the interrupt and never resumes (proving a never-approved action never
    executes); the others resume with an injected decision.
    """

    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; expected one of {SCENARIOS}")

    compiled = get_compiled_action_gate_graph()
    action = action or default_synthetic_action(scenario)
    # Deterministic thread id keyed on action so re-runs are reproducible.
    config = {"configurable": {"thread_id": f"m9_{scenario}_{action.action_id}"}}

    first = compiled.invoke(
        {"action": action.model_dump(mode="json"), "state_sequence": []}, config
    )
    snapshot = compiled.get_state(config)
    # Genuine suspension proof: the graph stopped *before* the approval node and
    # the action has not executed.
    suspended_before_approval = (
        snapshot.next == (NODE_HUMAN_APPROVAL,)
        and not first["execution"]["executed"]
    )

    if scenario == "suspended":
        # Never resume. Build the trace from the suspended state; the final node
        # did not run, so compute the evaluator checks directly.
        approval_d = first["approval"]
        execution_d = first["execution"]
        state_sequence = list(first["state_sequence"])
        check_dicts = _evaluator_check_dicts(approval_d, execution_d)
    else:
        decision = {
            "approved": "approve",
            "rejected": "reject",
            "missing_approval": None,
        }[scenario]
        approver = action.approver_role if decision is not None else None
        compiled.update_state(
            config, {"injected_decision": decision, "injected_approver": approver}
        )
        final = compiled.invoke(None, config)
        approval_d = final["approval"]
        execution_d = final["execution"]
        state_sequence = list(final["state_sequence"])
        check_dicts = final["evaluator_checks"]

    return ActionSuspensionTrace(
        trace_id=f"m9_action_suspension_{scenario}",
        scenario=scenario,
        action=action,
        approval=ApprovalRequest.model_validate(approval_d),
        execution=ActionExecutionRecord.model_validate(execution_d),
        suspended_before_approval=suspended_before_approval,
        state_sequence=state_sequence,
        evaluator_report=EvaluatorReport(
            checks=[EvaluatorCheck(**c) for c in check_dicts]
        ),
    )
