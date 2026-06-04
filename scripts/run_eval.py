"""CLI for the local offline eval pass.

Runs every case in a dataset through the deterministic runner, writes
one trace JSON per case to a local directory, scores the run with the
offline graders, and emits a single JSON report. Requires no
credentials.

Example:

    uv run python scripts/run_eval.py \\
        --dataset case_studies/financial_links_reliability/evals/smoke.jsonl \\
        --traces-out traces/local/smoke \\
        --report-out reports/local_smoke_eval.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agents.profiles import DEFAULT_PROFILE, KNOWN_PROFILES  # noqa: E402
from evals.run import run_eval  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local offline eval pass over a synthetic Financial Links "
            "JSONL dataset. Writes per-case traces and a single JSON report."
        )
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to the JSONL dataset (e.g. evals/smoke.jsonl).",
    )
    parser.add_argument(
        "--traces-out",
        required=True,
        type=Path,
        help="Directory to write per-case trace JSON.",
    )
    parser.add_argument(
        "--report-out",
        required=True,
        type=Path,
        help="Path to write the eval report JSON.",
    )
    parser.add_argument(
        "--agent-system-version",
        default=DEFAULT_PROFILE.value,
        choices=sorted(KNOWN_PROFILES),
        help=(
            "Agent-system profile to run. Default is the policy-compliant "
            "improved profile; pass 'baseline_v0' to evaluate the deliberately "
            "weak synthetic baseline (used to demonstrate failing cases the "
            "improved profile fixes)."
        ),
    )
    parser.add_argument(
        "--semantic-decisions",
        type=Path,
        default=None,
        help=(
            "Optional fixture-backed SemanticDecision JSON. When supplied, "
            "the report includes an extra unsupported_claim_semantic grader "
            "row. This is local-only and does not call a model."
        ),
    )
    args = parser.parse_args(argv)

    if not args.dataset.exists():
        print(f"dataset not found: {args.dataset}", file=sys.stderr)
        return 1

    report = run_eval(
        dataset_path=args.dataset,
        traces_out=args.traces_out,
        report_out=args.report_out,
        agent_system_version=args.agent_system_version,
        semantic_decisions_path=args.semantic_decisions,
    )

    print(
        f"OK: {report.case_count} cases | "
        f"passed={report.passed_case_count} failed={report.failed_case_count} | "
        f"report -> {args.report_out}"
    )
    if report.failure_label_counts:
        print(f"  failure_label_counts: {report.failure_label_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
