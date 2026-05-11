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
        default="baseline_v0",
        help="Free-form label recorded on every trace and on the report.",
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
