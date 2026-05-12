"""LangGraph orchestrator for the Financial Links vertical slice.

Wires the synthetic deterministic nodes the architecture target in
``README.md`` draws::

    IntakeNormalizer
      → OrchestratorAgent
      → FinancialLinksReliabilityAgent
      → EvaluatorNode
      → HumanApprovalNode  (only when approval.required is True)
      → FinalResponseComposer

The graph is deterministic. It never calls an external API or model;
the specialist node delegates to
``app.agents.financial_links_reliability_agent.handle`` so every
existing schema, profile (``baseline_v0`` / ``improved_v0``), grader,
regression seed, and redaction policy stays in force without change.

The runtime EvaluatorNode and the offline graders remain *separate*
modules with distinct return types per the
"evaluator-and-grader separation" rule in ``AGENTS.md`` — this graph
only invokes the runtime evaluator (``app.evaluator.evaluate``) on the
draft path. Offline graders run later, against the trace, in
``evals/run.py``.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents import financial_links_reliability_agent
from app.evaluator import evaluate
from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    Case,
    ConsentState,
    EvaluatorReport,
    HandoffPayload,
    RiskBand,
    Workflow,
)
from app.tools.synthetic_connectivity_tools import lookup_consent_state


# Public node names. Tests and the trace's ``specialist_path`` field
# both depend on these strings, so they are exported.
NODE_INTAKE: str = "IntakeNormalizer"
NODE_ORCHESTRATOR: str = "OrchestratorAgent"
NODE_SPECIALIST: str = "FinancialLinksReliabilityAgent"
NODE_EVALUATOR: str = "EvaluatorNode"
NODE_HUMAN_APPROVAL: str = "HumanApprovalNode"
NODE_FINAL: str = "FinalResponseComposer"

GRAPH_NODE_NAMES: tuple[str, ...] = (
    NODE_INTAKE,
    NODE_ORCHESTRATOR,
    NODE_SPECIALIST,
    NODE_EVALUATOR,
    NODE_HUMAN_APPROVAL,
    NODE_FINAL,
)


_AGENT_OUTPUT_REQUIRED_FIELDS: list[str] = [
    "case_id",
    "workflow",
    "declared_risk_band",
    "consent_state",
    "draft_text",
    "approval",
]


_SPECIALIST_FOR_WORKFLOW: dict[Workflow, str] = {
    Workflow.FINANCIAL_LINKS_RELIABILITY: NODE_SPECIALIST,
}


class GraphState(TypedDict, total=False):
    """LangGraph state for one Financial Links case.

    Keys are populated incrementally as nodes run. Values are Pydantic
    instances where the schema is already defined (so
    ``HandoffPayload``'s required-field invariants are still enforced
    per PLAN.md R9).
    """

    # Inputs
    case_dict: dict[str, Any]
    profile: str
    approval_matrix: dict[str, Any]

    # IntakeNormalizer
    case: Case
    initial_consent_state: ConsentState

    # OrchestratorAgent
    handoff: HandoffPayload
    orchestrator_decision: str
    specialist_path: list[str]

    # FinancialLinksReliabilityAgent
    agent_output: AgentOutput

    # EvaluatorNode
    evaluator_report: EvaluatorReport

    # HumanApprovalNode / FinalResponseComposer
    approval: ApprovalDecision
    final_response: str


def _append_path(state: GraphState, node: str) -> list[str]:
    """Return a new specialist_path with ``node`` appended."""

    return [*state.get("specialist_path", []), node]


def _node_intake(state: GraphState) -> dict[str, Any]:
    case_dict = state["case_dict"]
    case = Case(
        case_id=str(case_dict["case_id"]),
        workflow=Workflow(case_dict["workflow"]),
        risk_band=RiskBand(case_dict["risk_band"]),
        consent_sensitive=bool(case_dict.get("consent_sensitive", False)),
        payload=dict(case_dict.get("synthetic_facts", {})),
    )
    user_id = case.payload.get("user_id")
    if user_id is None:
        initial_consent = ConsentState.UNKNOWN
    else:
        initial_consent = ConsentState(lookup_consent_state(user_id)["consent_state"])
    return {
        "case": case,
        "initial_consent_state": initial_consent,
        "specialist_path": _append_path(state, NODE_INTAKE),
    }


def _node_orchestrator(state: GraphState) -> dict[str, Any]:
    case = state["case"]
    if case.workflow not in _SPECIALIST_FOR_WORKFLOW:
        raise NotImplementedError(
            "Graph runner only supports workflow "
            f"{Workflow.FINANCIAL_LINKS_RELIABILITY.value}; got {case.workflow.value}"
        )
    specialist = _SPECIALIST_FOR_WORKFLOW[case.workflow]

    handoff = HandoffPayload(
        case_id=case.case_id,
        workflow=case.workflow,
        from_node=NODE_ORCHESTRATOR,
        to_agent=specialist,
        declared_risk_band=case.risk_band,
        consent_state=state["initial_consent_state"],
        consent_reconfirmed=False,
        route_context={
            "institution_id": case.payload.get("institution_id"),
            "partner_id": case.payload.get("partner_id"),
        },
        notes=None,
    )
    return {
        "handoff": handoff,
        "orchestrator_decision": specialist,
        "specialist_path": _append_path(state, NODE_ORCHESTRATOR),
    }


def _node_specialist(state: GraphState) -> dict[str, Any]:
    agent_output = financial_links_reliability_agent.handle(
        case=state["case"],
        handoff=state["handoff"],
        approval_matrix=state["approval_matrix"],
        profile=state["profile"],
    )
    return {
        "agent_output": agent_output,
        "specialist_path": _append_path(state, NODE_SPECIALIST),
    }


def _node_evaluator(state: GraphState) -> dict[str, Any]:
    case_dict = state["case_dict"]
    report = evaluate(
        state["agent_output"],
        required_fields=_AGENT_OUTPUT_REQUIRED_FIELDS,
        approval_matrix=state["approval_matrix"],
        required_policy_ids=list(case_dict.get("required_policy_ids", [])),
    )
    return {
        "evaluator_report": report,
        "specialist_path": _append_path(state, NODE_EVALUATOR),
    }


def _route_after_evaluator(state: GraphState) -> str:
    """Conditional edge: HumanApprovalNode only when approval is required."""

    if state["agent_output"].approval.required:
        return NODE_HUMAN_APPROVAL
    return NODE_FINAL


def _node_human_approval(state: GraphState) -> dict[str, Any]:
    """Synthetic human-approval checkpoint.

    This deterministic slice does not actually suspend the graph for a
    human decision — that requires a checkpointer + a resume signal. It
    *does* record the approval posture on the trace path so an analyst
    can see that a case routed through human review. A real deployment
    would interrupt here.
    """

    return {
        "approval": state["agent_output"].approval,
        "specialist_path": _append_path(state, NODE_HUMAN_APPROVAL),
    }


def _node_final(state: GraphState) -> dict[str, Any]:
    return {
        "approval": state.get("approval", state["agent_output"].approval),
        "final_response": state["agent_output"].draft_text,
        "specialist_path": _append_path(state, NODE_FINAL),
    }


def build_graph():
    """Build (but do not compile) the StateGraph."""

    graph = StateGraph(GraphState)
    graph.add_node(NODE_INTAKE, _node_intake)
    graph.add_node(NODE_ORCHESTRATOR, _node_orchestrator)
    graph.add_node(NODE_SPECIALIST, _node_specialist)
    graph.add_node(NODE_EVALUATOR, _node_evaluator)
    graph.add_node(NODE_HUMAN_APPROVAL, _node_human_approval)
    graph.add_node(NODE_FINAL, _node_final)

    graph.set_entry_point(NODE_INTAKE)
    graph.add_edge(NODE_INTAKE, NODE_ORCHESTRATOR)
    graph.add_edge(NODE_ORCHESTRATOR, NODE_SPECIALIST)
    graph.add_edge(NODE_SPECIALIST, NODE_EVALUATOR)
    graph.add_conditional_edges(
        NODE_EVALUATOR,
        _route_after_evaluator,
        {
            NODE_HUMAN_APPROVAL: NODE_HUMAN_APPROVAL,
            NODE_FINAL: NODE_FINAL,
        },
    )
    graph.add_edge(NODE_HUMAN_APPROVAL, NODE_FINAL)
    graph.add_edge(NODE_FINAL, END)
    return graph


_COMPILED_GRAPH: Any = None


def get_compiled_graph() -> Any:
    """Return a cached compiled graph instance."""

    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph().compile()
    return _COMPILED_GRAPH


def invoke_graph(
    case_dict: dict[str, Any],
    profile: str,
    approval_matrix: dict[str, Any],
) -> GraphState:
    """Run one case through the compiled graph and return the final state."""

    initial_state: GraphState = {
        "case_dict": case_dict,
        "profile": profile,
        "approval_matrix": approval_matrix,
    }
    return get_compiled_graph().invoke(initial_state)
