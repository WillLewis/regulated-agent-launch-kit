"""Single-case runner for the Financial Links vertical slice.

The runner is the public Python API used by ``scripts/run_case.py``,
``scripts/run_eval.py``, and the eval-loop tests. Its execution path
is graph-backed (see ``app.graph``): every case flows through
``IntakeNormalizer → OrchestratorAgent → FinancialLinksReliabilityAgent
→ EvaluatorNode → HumanApprovalNode? → FinalResponseComposer``. The
graph itself is deterministic and never calls an external API or model.

Public surface:

- ``run_case(case_dict, ...)`` — runs one case and returns a ``RunResult``
  wrapping the ``AgentOutput`` and the ``TraceRecord``.
- ``load_default_approval_matrix()`` — reads ``configs/approval_matrix.yaml``.

The function signature and ``RunResult`` shape are preserved across
the graph migration so existing callers and tests keep working.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.agents.profiles import DEFAULT_PROFILE, normalize_profile
from app.graph import invoke_graph
from app.schemas import AgentOutput, TraceRecord


REPO_ROOT = Path(__file__).resolve().parents[1]
_APPROVAL_MATRIX_PATH = REPO_ROOT / "configs" / "approval_matrix.yaml"


class RunResult(BaseModel):
    """Wraps the trace and the underlying agent output from one run."""

    trace: TraceRecord
    agent_output: AgentOutput


def load_default_approval_matrix() -> dict[str, Any]:
    return yaml.safe_load(_APPROVAL_MATRIX_PATH.read_text())


def run_case(
    case_dict: dict[str, Any],
    approval_matrix: dict[str, Any] | None = None,
    *,
    agent_system_version: str = DEFAULT_PROFILE.value,
    policy_version: str = "financial_links_policies_v0",
    dataset_id: str | None = None,
) -> RunResult:
    """Run one Financial Links case end-to-end through the graph.

    ``agent_system_version`` selects the agent-system profile (see
    ``app.agents.profiles``); the value is also recorded on the trace.

    Deterministic. No external API, model, or service is called. All
    tool calls are synthetic.
    """

    profile = normalize_profile(agent_system_version)
    matrix = approval_matrix or load_default_approval_matrix()

    final_state = invoke_graph(case_dict, profile=profile, approval_matrix=matrix)

    case = final_state["case"]
    agent_output: AgentOutput = final_state["agent_output"]
    dataset_id_value = dataset_id or case_dict.get("dataset_id") or "unknown_dataset"

    trace = TraceRecord(
        trace_id=str(uuid.uuid4()),
        dataset_id=dataset_id_value,
        case_id=case.case_id,
        workflow=case.workflow,
        risk_band=case.risk_band,
        agent_system_version=profile,
        policy_version=policy_version,
        orchestrator_decision=final_state["orchestrator_decision"],
        specialist_path=list(final_state.get("specialist_path", [])),
        handoff=final_state["handoff"],
        tool_calls=list(agent_output.tool_calls),
        evaluator_report=final_state["evaluator_report"],
        approval=final_state.get("approval", agent_output.approval),
        final_response=final_state.get("final_response", agent_output.draft_text),
        grader_results=[],
        failure_labels=[],
        latency_ms=0,
        est_cost_usd=0.0,
    )

    return RunResult(trace=trace, agent_output=agent_output)
