"""Local offline eval runner for the Financial Links vertical slice.

This is the smallest honest eval pass:

- run every case through ``app.runner.run_case``;
- write one trace JSON per case under a ``traces_out`` directory;
- score each (case, agent_output, trace) with the offline graders in
  ``evals.graders``;
- aggregate grader pass rates, failure-label counts, evaluator outcomes,
  and a synthetic latency/cost summary into a local JSON report.

No external credentials are required. All cost numbers are 0.0 — the
runner is deterministic and does not call a model. Latency is measured
locally for transparency; the synthetic latency budgets in
``configs/latency_budgets.yaml`` are surfaced alongside the measured
values as planning envelopes only (not production SLAs).
"""

from __future__ import annotations

import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.agents.profiles import DEFAULT_PROFILE, normalize_profile
from app.runner import RunResult, load_default_approval_matrix, run_case
from app.schemas import Case, GraderResult, RiskBand, TraceRecord, Workflow
from evals.graders import (
    grade_approval_boundary,
    grade_consent_boundary,
    grade_handoff_completeness,
    grade_policy_retrieval,
    grade_required_tool_use,
    grade_schema_validity,
    grade_unsupported_claim,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
_LATENCY_BUDGETS_PATH = REPO_ROOT / "configs" / "latency_budgets.yaml"

# Required-field list aligned with app.runner so offline schema grading
# matches what the runtime evaluator was checking against.
_AGENT_OUTPUT_REQUIRED_FIELDS: list[str] = [
    "case_id",
    "workflow",
    "declared_risk_band",
    "consent_state",
    "draft_text",
    "approval",
]


class CaseEvalResult(BaseModel):
    """Per-case outcome captured in the eval report."""

    case_id: str
    workflow: str
    risk_band: str
    trace_path: str
    grader_results: list[GraderResult]
    failure_labels: list[str] = Field(default_factory=list)
    evaluator_all_ok: bool
    approval_required: bool
    passed: bool
    latency_ms: int = 0
    est_cost_usd: float = 0.0


class AggregateGraderRate(BaseModel):
    name: str
    total: int
    passed: int
    pass_rate: float


class EvalReport(BaseModel):
    """Local, credential-free eval report.

    Anything claimed in the README or webpage must be traceable back to
    a generated report like this one (synthetic only, no production
    claim).
    """

    version: str = "local_eval_v0"
    synthetic: bool = True
    agent_system_version: str
    dataset_path: str
    case_count: int
    passed_case_count: int
    failed_case_count: int
    aggregate_grader_pass_rates: list[AggregateGraderRate]
    failure_label_counts: dict[str, int] = Field(default_factory=dict)
    synthetic_latency_envelope: dict[str, Any] = Field(default_factory=dict)
    synthetic_cost_summary: dict[str, Any] = Field(default_factory=dict)
    per_case: list[CaseEvalResult] = Field(default_factory=list)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: line {line_no}: invalid JSON ({exc})")
    return records


def _grade_case(
    case_dict: dict[str, Any],
    run_result: RunResult,
    approval_matrix: dict[str, Any],
) -> list[GraderResult]:
    """Run every offline grader for one case.

    Each grader returns a ``GraderResult``. Failure labels are derived
    from the grader outputs by the caller — graders never mutate trace
    state directly.
    """

    case = Case(
        case_id=str(case_dict["case_id"]),
        workflow=Workflow(case_dict["workflow"]),
        risk_band=RiskBand(case_dict["risk_band"]),
        consent_sensitive=bool(case_dict.get("consent_sensitive", False)),
        payload=dict(case_dict.get("synthetic_facts", {})),
    )
    output = run_result.agent_output
    trace = run_result.trace

    results: list[GraderResult] = [
        grade_schema_validity(
            output.model_dump(mode="json"),
            _AGENT_OUTPUT_REQUIRED_FIELDS,
        ),
        grade_handoff_completeness(trace.handoff),
        grade_required_tool_use(output, list(case_dict.get("required_tools", []))),
        grade_consent_boundary(case, output),
        grade_approval_boundary(case, output, approval_matrix),
        grade_policy_retrieval(
            list(case_dict.get("required_policy_ids", [])),
            output,
        ),
        grade_unsupported_claim(output),
    ]
    return results


_GRADER_NAMES: list[str] = [
    "schema_validity",
    "handoff_completeness",
    "required_tool_use",
    "consent_boundary",
    "approval_boundary",
    "policy_retrieval",
    "unsupported_claim",
]


def _load_latency_envelope() -> dict[str, Any]:
    data = yaml.safe_load(_LATENCY_BUDGETS_PATH.read_text())
    return {
        "version": data.get("version"),
        "synthetic": data.get("synthetic", True),
        "note": (
            "Synthetic per-band planning envelope from configs/latency_budgets.yaml; "
            "not production SLAs, partner commitments, or regulatory thresholds."
        ),
        "by_risk_band": data.get("risk_bands", {}),
    }


def run_eval(
    dataset_path: Path,
    traces_out: Path,
    report_out: Path | None = None,
    *,
    agent_system_version: str = DEFAULT_PROFILE.value,
    approval_matrix: dict[str, Any] | None = None,
) -> EvalReport:
    """Run the offline eval pass and (optionally) write the report to disk.

    ``agent_system_version`` selects an entry from
    ``app.agents.profiles.AgentSystemProfile``. The default is the
    policy-compliant improved profile; pass ``baseline_v0`` explicitly
    to evaluate the deliberately weak baseline.
    """

    profile = normalize_profile(agent_system_version)
    dataset_path = Path(dataset_path)
    traces_out = Path(traces_out)
    traces_out.mkdir(parents=True, exist_ok=True)

    matrix = approval_matrix or load_default_approval_matrix()
    cases = _load_jsonl(dataset_path)

    per_case: list[CaseEvalResult] = []
    grader_totals: dict[str, list[bool]] = defaultdict(list)
    label_counter: Counter[str] = Counter()
    latency_samples_by_band: dict[str, list[int]] = defaultdict(list)
    total_cost_usd = 0.0

    for case_dict in cases:
        start = time.perf_counter()
        run_result = run_case(
            case_dict,
            approval_matrix=matrix,
            agent_system_version=profile,
        )
        elapsed_ms = int(round((time.perf_counter() - start) * 1000))

        grader_results = _grade_case(case_dict, run_result, matrix)

        failure_labels: list[str] = []
        # grader_results are returned in the order of _GRADER_NAMES, so a
        # positional zip is the authoritative name → result mapping.
        for name, gr in zip(_GRADER_NAMES, grader_results, strict=True):
            grader_totals[name].append(gr.passed)
            if not gr.passed and gr.failure_label:
                if gr.failure_label not in failure_labels:
                    failure_labels.append(gr.failure_label)
                label_counter[gr.failure_label] += 1

        trace: TraceRecord = run_result.trace
        trace.latency_ms = elapsed_ms
        trace.grader_results = grader_results
        trace.failure_labels = failure_labels
        latency_samples_by_band[trace.risk_band.value].append(elapsed_ms)
        total_cost_usd += trace.est_cost_usd

        trace_path = traces_out / f"{trace.case_id}.json"
        trace_path.write_text(json.dumps(trace.model_dump(mode="json"), indent=2))

        evaluator_all_ok = trace.evaluator_report.all_ok
        case_passed = evaluator_all_ok and all(gr.passed for gr in grader_results)

        per_case.append(
            CaseEvalResult(
                case_id=trace.case_id,
                workflow=trace.workflow.value,
                risk_band=trace.risk_band.value,
                trace_path=str(trace_path),
                grader_results=grader_results,
                failure_labels=failure_labels,
                evaluator_all_ok=evaluator_all_ok,
                approval_required=bool(trace.approval and trace.approval.required),
                passed=case_passed,
                latency_ms=elapsed_ms,
                est_cost_usd=trace.est_cost_usd,
            )
        )

    aggregate_rates = [
        AggregateGraderRate(
            name=name,
            total=len(grader_totals.get(name, [])),
            passed=sum(grader_totals.get(name, [])),
            pass_rate=(
                (sum(grader_totals[name]) / len(grader_totals[name]))
                if grader_totals.get(name)
                else 0.0
            ),
        )
        for name in _GRADER_NAMES
    ]

    cost_summary = {
        "note": (
            "Cost is a deterministic 0.0 placeholder for this synthetic run — "
            "no external model is called. Real cost surfaces here once an LLM "
            "is wired into the runner."
        ),
        "total_est_cost_usd": round(total_cost_usd, 6),
        "per_case_count": len(per_case),
    }

    latency_summary = {
        "synthetic_planning_envelope": _load_latency_envelope(),
        "measured_ms": {
            "note": (
                "Wall-clock latency for the deterministic runner only. The runner "
                "is near-instant; these numbers will become meaningful when an LLM "
                "is wired in."
            ),
            "samples_by_risk_band": {
                band: {
                    "count": len(samples),
                    "max_ms": max(samples),
                    "min_ms": min(samples),
                    "mean_ms": int(round(statistics.fmean(samples))),
                }
                for band, samples in latency_samples_by_band.items()
            },
        },
    }

    report = EvalReport(
        agent_system_version=profile,
        dataset_path=str(dataset_path),
        case_count=len(per_case),
        passed_case_count=sum(1 for c in per_case if c.passed),
        failed_case_count=sum(1 for c in per_case if not c.passed),
        aggregate_grader_pass_rates=aggregate_rates,
        failure_label_counts=dict(label_counter),
        synthetic_latency_envelope=latency_summary,
        synthetic_cost_summary=cost_summary,
        per_case=per_case,
    )

    if report_out is not None:
        report_out = Path(report_out)
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(json.dumps(report.model_dump(mode="json"), indent=2))

    return report
