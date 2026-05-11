"""Smoke CLI: run one synthetic Financial Links case and write a local trace.

This is intentionally the smallest possible end-to-end path. It loads a
single case from a JSONL dataset by ``case_id``, runs it through
``app.runner.run_case``, and writes the resulting ``TraceRecord`` as JSON.
No credentials and no network calls are required.

Example:

    uv run python scripts/run_case.py \\
        --case-id case_fl_v0_001 \\
        --dataset case_studies/financial_links_reliability/evals/smoke.jsonl \\
        --trace-out traces/local/case_fl_v0_001.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agents.profiles import DEFAULT_PROFILE, KNOWN_PROFILES  # noqa: E402
from app.runner import run_case  # noqa: E402


def _load_case(dataset: Path, case_id: str) -> dict[str, Any]:
    for line_no, raw in enumerate(dataset.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"line {line_no}: invalid JSON ({exc})")
        if record.get("case_id") == case_id:
            return record
    raise SystemExit(f"case_id {case_id!r} not found in {dataset}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one synthetic Financial Links case and write a local trace."
    )
    parser.add_argument("--case-id", required=True, help="Case ID to run.")
    parser.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Path to the JSONL dataset (e.g. evals/smoke.jsonl).",
    )
    parser.add_argument(
        "--trace-out",
        required=True,
        type=Path,
        help="Path to write the resulting trace JSON.",
    )
    parser.add_argument(
        "--agent-system-version",
        default=DEFAULT_PROFILE.value,
        choices=sorted(KNOWN_PROFILES),
        help=(
            "Agent-system profile to run. Default is the policy-compliant "
            "improved profile; pass 'baseline_v0' to run the deliberately "
            "weak synthetic baseline."
        ),
    )
    args = parser.parse_args(argv)

    if not args.dataset.exists():
        print(f"dataset not found: {args.dataset}", file=sys.stderr)
        return 1

    case_dict = _load_case(args.dataset, args.case_id)
    result = run_case(case_dict, agent_system_version=args.agent_system_version)

    args.trace_out.parent.mkdir(parents=True, exist_ok=True)
    args.trace_out.write_text(
        json.dumps(result.trace.model_dump(mode="json"), indent=2)
    )

    checks = result.trace.evaluator_report.checks
    failed = [c.name for c in checks if not c.ok]
    print(
        f"OK: ran {args.case_id} -> {args.trace_out} "
        f"(evaluator: {len(checks)} checks, {len(failed)} failing)"
    )
    if failed:
        print(f"  failing checks: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
