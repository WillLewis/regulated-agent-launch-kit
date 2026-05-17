"""Re-grade an existing local eval report under the current
``grade_unsupported_claim`` implementation.

The grader changed from a flat substring match to a negation-aware
pass. Existing on-disk eval reports (e.g.
``reports/llm_adversarial_eval.json``) were produced under the old
grader; this script lets us recompute the grader outcome **without
calling the LLM again** by re-running only ``grade_unsupported_claim``
and the dependent ``grade_evaluator_catch_rate`` against the
already-captured per-case traces.

Inputs:

- ``--report PATH``  — the existing eval report JSON
- ``--traces PATH``  — the directory of raw per-case trace JSONs

In-place rewrite: the report's ``per_case[*].grader_results[6]``
(unsupported_claim) and ``grader_results[7]`` (catch-rate) are
replaced, per-case ``failure_labels`` / ``passed`` / ``evaluator_all_ok``
are recomputed, and the report-level
``aggregate_grader_pass_rates`` / ``failure_label_counts`` /
``passed_case_count`` / ``failed_case_count`` are recomputed.
``latency_ms`` / ``est_cost_usd`` / ``synthetic_latency_envelope`` are
preserved verbatim — they were measured at runtime and the grader
change does not affect them.

The script never calls the LLM and requires no credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.schemas import EvaluatorReport, GraderResult  # noqa: E402
from evals.graders import (  # noqa: E402
    grade_evaluator_catch_rate,
    grade_unsupported_claim,
)


_GRADER_NAMES: list[str] = [
    "schema_validity",
    "handoff_completeness",
    "required_tool_use",
    "consent_boundary",
    "approval_boundary",
    "policy_retrieval",
    "unsupported_claim",
    "evaluator_catch_rate",
]
_UNSUPPORTED_CLAIM_INDEX: int = _GRADER_NAMES.index("unsupported_claim")
_CATCH_RATE_INDEX: int = _GRADER_NAMES.index("evaluator_catch_rate")


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"file not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")


def _draft_text_from_trace(trace: dict[str, Any]) -> str:
    return (
        trace.get("final_response")
        or trace.get("draft_text")
        or ""
    )


def regrade_report(report_path: Path, traces_dir: Path) -> dict[str, Any]:
    report = _load_json(report_path)
    if not isinstance(report, dict):
        raise SystemExit(f"{report_path}: report must be a JSON object")
    per_case = report.get("per_case")
    if not isinstance(per_case, list):
        raise SystemExit(f"{report_path}: report is missing per_case[]")

    label_counter: Counter[str] = Counter()
    grader_totals: dict[str, list[bool]] = defaultdict(list)

    for case in per_case:
        case_id = case.get("case_id")
        if not case_id:
            raise SystemExit(f"{report_path}: per_case entry missing case_id")
        trace_path = traces_dir / f"{case_id}.json"
        trace = _load_json(trace_path)
        draft_text = _draft_text_from_trace(trace)

        # Re-grade the unsupported_claim check.
        new_uc = grade_unsupported_claim({"draft_text": draft_text})
        grader_results = list(case.get("grader_results") or [])
        if len(grader_results) <= _CATCH_RATE_INDEX:
            raise SystemExit(
                f"{case_id}: expected {_CATCH_RATE_INDEX + 1} grader_results, "
                f"got {len(grader_results)}"
            )
        grader_results[_UNSUPPORTED_CLAIM_INDEX] = new_uc.model_dump(mode="json")

        # Re-grade the catch-rate (it depends on the new unsupported_claim).
        primary = [
            GraderResult.model_validate(g)
            for g in grader_results[:_CATCH_RATE_INDEX]
        ]
        evaluator_report = EvaluatorReport.model_validate(
            trace.get("evaluator_report") or {"checks": []}
        )
        new_catch = grade_evaluator_catch_rate(primary, evaluator_report)
        grader_results[_CATCH_RATE_INDEX] = new_catch.model_dump(mode="json")

        case["grader_results"] = grader_results

        # Recompute case-level fields.
        case_failure_labels: list[str] = []
        for g in grader_results:
            if not g.get("passed") and g.get("failure_label"):
                if g["failure_label"] not in case_failure_labels:
                    case_failure_labels.append(g["failure_label"])
        case["failure_labels"] = case_failure_labels
        case["evaluator_all_ok"] = evaluator_report.all_ok
        case["passed"] = evaluator_report.all_ok and all(
            g.get("passed") for g in grader_results
        )

        for name, g in zip(_GRADER_NAMES, grader_results, strict=True):
            grader_totals[name].append(bool(g.get("passed")))
        for label in case_failure_labels:
            label_counter[label] += 1

    # Rebuild aggregate pass rates.
    new_rates: list[dict[str, Any]] = []
    for name in _GRADER_NAMES:
        bools = grader_totals.get(name) or []
        total = len(bools)
        passed = sum(bools)
        new_rates.append(
            {
                "name": name,
                "total": total,
                "passed": passed,
                "pass_rate": (passed / total) if total else 0.0,
            }
        )
    report["aggregate_grader_pass_rates"] = new_rates
    report["failure_label_counts"] = dict(label_counter)
    report["passed_case_count"] = sum(1 for c in per_case if c.get("passed"))
    report["failed_case_count"] = sum(1 for c in per_case if not c.get("passed"))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Re-grade an existing eval report under the current "
            "grade_unsupported_claim implementation, using the on-disk "
            "per-case traces. Does not call the LLM."
        )
    )
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--traces", required=True, type=Path)
    args = parser.parse_args(argv)

    report = regrade_report(args.report, args.traces)
    args.report.write_text(json.dumps(report, indent=2))
    print(
        f"OK: regraded {args.report.name} | "
        f"passed={report['passed_case_count']} "
        f"failed={report['failed_case_count']} "
        f"failure_label_counts={report['failure_label_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
