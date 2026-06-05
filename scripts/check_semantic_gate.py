"""Reusable, credential-free blocking gate for the offline semantic grader.

M7a: promotes ``unsupported_claim_semantic`` from an optional *reporting* lane
into a reusable *blocking* gate. Given a local eval report JSON (produced by
``scripts/run_eval.py --semantic-decisions <fixture>`` or any future
credentialed semantic audit that writes the same report shape), this gate:

1. requires ``aggregate_grader_pass_rates`` to include the
   ``unsupported_claim_semantic`` grader;
2. **fails** (exit 1) if that grader flagged any case, printing the failing
   ``case_id`` values and their ``failure_label``;
3. **fails closed** (exit 1) if the semantic grader is absent — unless
   ``--allow-missing`` is passed, which downgrades absence to a warning so the
   gate can be a no-op on reports that intentionally did not run the lane.

This script makes **no** model or network call and needs **no** credentials —
it only reads a JSON report already on disk. It is intentionally NOT wired into
the default ``GRADERS`` / default eval run; the deterministic public proof loop
is unchanged. A clean gate result proves only that the semantic lane in *that
report* carried no flagged cases; it is not a model-safety, pilot-readiness,
production-readiness, or regulatory claim. The posture remains
**NOT READY FOR PILOT** until a larger credentialed semantic audit runs clean.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.semantic_audit import SEMANTIC_GRADER_NAME  # noqa: E402

SEMANTIC_GRADER = SEMANTIC_GRADER_NAME  # "unsupported_claim_semantic"


@dataclass
class SemanticGateResult:
    """Outcome of evaluating the semantic gate over one eval report."""

    present: bool
    passed: bool
    total: int
    passed_count: int
    failing: list[dict[str, Any]] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def evaluate_semantic_gate(
    report: dict[str, Any],
    *,
    allow_missing: bool = False,
) -> SemanticGateResult:
    """Pure function: decide whether ``report`` clears the semantic gate.

    The per-case ``grader_results`` align positionally with
    ``aggregate_grader_pass_rates`` (the eval-runner contract), so the index of
    the semantic grader in the aggregate list is used to read each case's
    semantic result. Fails closed on absence and on any aggregate-level
    semantic failure, even when per-case detail is unavailable.
    """

    rates = report.get("aggregate_grader_pass_rates")
    names = [r.get("name") for r in rates] if isinstance(rates, list) else []

    if SEMANTIC_GRADER not in names:
        if allow_missing:
            return SemanticGateResult(
                present=False,
                passed=True,
                total=0,
                passed_count=0,
                messages=[
                    f"WARN: report has no {SEMANTIC_GRADER!r} grader; allowed by "
                    "--allow-missing (semantic gate NOT enforced for this report).",
                ],
            )
        return SemanticGateResult(
            present=False,
            passed=False,
            total=0,
            passed_count=0,
            messages=[
                f"FAIL (fail-closed): report has no {SEMANTIC_GRADER!r} grader.",
                "  The default deterministic eval does not include the semantic "
                "lane. Produce a report with `scripts/run_eval.py "
                "--semantic-decisions <fixture>`, or pass --allow-missing to skip "
                "the gate explicitly.",
            ],
        )

    idx = names.index(SEMANTIC_GRADER)
    rate_row = rates[idx] if isinstance(rates[idx], dict) else {}
    total = int(rate_row.get("total", 0) or 0)
    agg_passed = int(rate_row.get("passed", total) or 0)
    agg_failures = max(0, total - agg_passed)

    failing: list[dict[str, Any]] = []
    per_case = report.get("per_case", [])
    if isinstance(per_case, list):
        for case in per_case:
            if not isinstance(case, dict):
                continue
            results = case.get("grader_results", [])
            if not isinstance(results, list) or idx >= len(results):
                continue
            result = results[idx] if isinstance(results[idx], dict) else {}
            if not result.get("passed", True):
                # Capture ONLY the case_id + failure_label. The grader's
                # ``explanation`` / ``evidence`` embed the semantic decision's
                # ``rationale`` / ``evidence_spans``, which on a real credentialed
                # audit quote customer-draft text (the draft-bearing keys that
                # ``evals.semantic_audit`` fails closed on). The gate never needs
                # them, so it must not lift them into its output.
                failing.append(
                    {
                        "case_id": case.get("case_id"),
                        "failure_label": result.get("failure_label"),
                    }
                )

    # Fail closed if the aggregate row reports failures the per-case detail did
    # not surface (malformed/partial report): the gate must not pass a report
    # that says cases failed just because it could not enumerate them.
    detail_gap = agg_failures - len(failing)
    passed = len(failing) == 0 and agg_failures == 0
    passed_count = total - max(len(failing), agg_failures)

    if passed:
        messages = [
            f"PASS: {SEMANTIC_GRADER} clean — {total}/{total} synthetic case(s) "
            "cleared the blocking semantic gate.",
            "  (Synthetic eval lane only; not a model-safety or pilot-readiness "
            "claim.)",
        ]
    else:
        messages = [
            f"FAIL: {SEMANTIC_GRADER} flagged "
            f"{max(len(failing), agg_failures)} of {total} case(s) — blocking gate.",
        ]
        for entry in failing:
            messages.append(
                f"  - {entry['case_id']}: {entry['failure_label']}"
            )
        if detail_gap > 0:
            messages.append(
                f"  - (+{detail_gap} more failing case(s) reported in the "
                "aggregate but missing per-case detail)"
            )

    return SemanticGateResult(
        present=True,
        passed=passed,
        total=total,
        passed_count=passed_count,
        failing=failing,
        messages=messages,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Credential-free blocking gate for the offline "
            "unsupported_claim_semantic grader. Exit 0 when the semantic lane in "
            "the report is clean; exit 1 when it flagged any case or is absent "
            "(unless --allow-missing). No model or network call is made."
        )
    )
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="Path to a local eval report JSON (from run_eval.py --semantic-decisions).",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Downgrade an absent semantic grader from a fail-closed error to a "
            "warning (gate becomes a no-op for that report)."
        ),
    )
    args = parser.parse_args(argv)

    if not args.report.exists():
        print(f"FAIL: report not found: {args.report}", file=sys.stderr)
        return 1
    try:
        report = json.loads(args.report.read_text())
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid report JSON ({args.report}): {exc}", file=sys.stderr)
        return 1
    if not isinstance(report, dict):
        print(f"FAIL: report must be a JSON object: {args.report}", file=sys.stderr)
        return 1

    result = evaluate_semantic_gate(report, allow_missing=args.allow_missing)
    stream = sys.stdout if result.passed else sys.stderr
    header = "OK" if result.passed else "BLOCKED"
    print(f"{header}: semantic gate on {args.report}", file=stream)
    for line in result.messages:
        print(line, file=stream)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
