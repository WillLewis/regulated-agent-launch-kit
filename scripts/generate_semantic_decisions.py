"""Generate ``SemanticDecision`` JSON with the opt-in model/NLI adapter.

This is the credentialed bridge between a completed eval run and the
fixture-compatible semantic lane:

1. run ``scripts/run_eval.py`` normally to create traces and an eval report;
2. run this script to classify each draft with the model/NLI adapter;
3. rerun ``scripts/run_eval.py --semantic-decisions <output>``.

The script is opt-in and can spend tokens. It never runs from ``make test`` and
it writes generated decision files under gitignored paths by default.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.schemas import TraceRecord  # noqa: E402
from evals.run import EvalReport  # noqa: E402
from evals.semantic_model_adapter import (  # noqa: E402
    SEMANTIC_ADAPTER_NAME,
    SemanticAdapterResponse,
    build_semantic_prompt,
    generate_semantic_decision,
)


SEMANTIC_DECISION_FILE_VERSION = "semantic_model_decisions_v0"


def _load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: line {line_no}: invalid JSON ({exc})")
        case_id = str(record.get("case_id", ""))
        if not case_id:
            raise SystemExit(f"{path}: line {line_no}: missing case_id")
        if case_id in cases:
            raise SystemExit(f"{path}: duplicate case_id {case_id!r}")
        cases[case_id] = record
    return cases


def _load_report(path: Path) -> EvalReport:
    try:
        return EvalReport.model_validate(json.loads(path.read_text()))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid eval report JSON ({exc})")
    except Exception as exc:
        raise SystemExit(f"{path}: invalid EvalReport shape ({exc})") from exc


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _load_trace(path_text: str) -> TraceRecord:
    path = _resolve_path(path_text)
    if not path.exists():
        raise SystemExit(f"trace not found: {path}")
    try:
        return TraceRecord.model_validate(json.loads(path.read_text()))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid trace JSON ({exc})")
    except Exception as exc:
        raise SystemExit(f"{path}: invalid TraceRecord shape ({exc})") from exc


def _validate_inputs(cases: dict[str, dict[str, Any]], report: EvalReport) -> None:
    report_ids = {case.case_id for case in report.per_case}
    dataset_ids = set(cases)
    if report_ids != dataset_ids:
        raise SystemExit(
            "dataset case IDs do not match eval-report case IDs; regenerate "
            "the report from the same dataset before generating semantic decisions."
        )


def generate_semantic_decision_file(
    *,
    dataset_path: Path,
    eval_report_path: Path,
    out: Path,
    model: str | None = None,
    timeout_s: float = 30.0,
    max_tokens: int = 512,
    decision_fn: Callable[..., SemanticAdapterResponse] = generate_semantic_decision,
) -> dict[str, Any]:
    """Generate and write a fixture-compatible semantic decision file.

    ``decision_fn`` is injectable for tests. Production callers use the
    default, which performs credential-gated model calls.
    """

    cases = _load_jsonl(dataset_path)
    report = _load_report(eval_report_path)
    _validate_inputs(cases, report)

    profile = report.agent_system_version
    decisions: dict[str, dict[str, Any]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    for case in report.per_case:
        trace = _load_trace(case.trace_path)
        if trace.agent_system_version != profile:
            raise SystemExit(
                f"{case.case_id}: trace profile {trace.agent_system_version!r} "
                f"does not match report profile {profile!r}"
            )
        draft = trace.final_response or ""
        prompt = build_semantic_prompt(cases[case.case_id], draft)
        started = time.perf_counter()
        response = decision_fn(
            prompt,
            model=model,
            timeout_s=timeout_s,
            max_tokens=max_tokens,
        )
        latency_ms = int(round((time.perf_counter() - started) * 1000))
        decisions[case.case_id] = response.decision.model_dump(mode="json")
        metadata[case.case_id] = {
            "adapter": SEMANTIC_ADAPTER_NAME,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "est_cost_usd": response.est_cost_usd,
            "cost_estimation_note": response.cost_estimation_note,
            "latency_ms": latency_ms,
        }
        total_cost += response.est_cost_usd
        total_input_tokens += response.input_tokens
        total_output_tokens += response.output_tokens

    output = {
        "version": SEMANTIC_DECISION_FILE_VERSION,
        "synthetic": True,
        "adapter": SEMANTIC_ADAPTER_NAME,
        "dataset_path": str(dataset_path),
        "source_eval_report": str(eval_report_path),
        "profile": profile,
        "note": (
            "Generated by the opt-in model/NLI semantic adapter. This file is "
            "a local decision source for scripts/run_eval.py --semantic-decisions; "
            "it is not a production, pilot, regulatory, or model-safety claim."
        ),
        "decisions": {profile: decisions},
        "adapter_metadata": {profile: metadata},
        "summary": {
            "case_count": len(decisions),
            "unsupported_claim_true_count": sum(
                1 for decision in decisions.values() if decision["makes_unsupported_claim"]
            ),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_est_cost_usd": round(total_cost, 6),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate fixture-compatible SemanticDecision JSON using the opt-in "
            "model/NLI adapter. This can make credentialed model calls."
        )
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--eval-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args(argv)

    output = generate_semantic_decision_file(
        dataset_path=args.dataset,
        eval_report_path=args.eval_report,
        out=args.out,
        model=args.model,
        timeout_s=args.timeout_s,
        max_tokens=args.max_tokens,
    )
    summary = output["summary"]
    print(
        "OK: wrote semantic model decisions -> "
        f"{args.out} ({summary['case_count']} cases, "
        f"unsupported_claim_true={summary['unsupported_claim_true_count']}, "
        f"est_cost_usd={summary['total_est_cost_usd']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
