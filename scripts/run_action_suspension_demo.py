"""Run the M9 synthetic action-suspension demo and emit trace artifacts.

Credential-free, deterministic, synthetic. Drives all four suspend/resume
scenarios through the real ``app.action_suspension`` graph (which interrupts
before ``HumanApprovalNode``), scores each completed trace with the offline
``grade_action_suspension`` grader, and writes one public-safe trace JSON per
scenario under ``traces/local/action_suspension/``.

The traces show the artifact shape: the requested synthetic action, the
approval decision, the action execution state, the node/state sequence, the
runtime evaluator report, and the offline grader result. No model is called and
no external system is touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.action_suspension import SCENARIOS, run_suspension_scenario  # noqa: E402
from evals.action_suspension_grader import grade_action_suspension  # noqa: E402

DEFAULT_OUT_DIR = REPO_ROOT / "traces" / "local" / "action_suspension"


def run_demo(out_dir: Path) -> list[dict[str, object]]:
    """Run every scenario, write its trace, and return a small summary list."""

    out_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        trace = run_suspension_scenario(scenario)
        grader = grade_action_suspension(trace)
        trace.grader_results = [grader.model_dump(mode="json")]
        out_path = out_dir / f"{scenario}.json"
        out_path.write_text(json.dumps(trace.model_dump(mode="json"), indent=2) + "\n")
        try:
            trace_path = str(out_path.relative_to(REPO_ROOT))
        except ValueError:
            trace_path = str(out_path)
        summary.append(
            {
                "scenario": scenario,
                "suspended_before_approval": trace.suspended_before_approval,
                "approval_status": trace.approval.status.value,
                "executed": trace.execution.executed,
                "execution_count": trace.execution.execution_count,
                "evaluator_all_ok": trace.evaluator_report.all_ok,
                "grader_passed": grader.passed,
                "grader_failure_label": grader.failure_label,
                "trace_path": trace_path,
            }
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the M9 synthetic action-suspension demo (credential-free) and "
            "emit one trace per scenario. No model call, no external system."
        )
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    summary = run_demo(args.out_dir)

    # Every scenario must show correct gating: the action never executes without
    # an approved decision, and the approved path executes exactly once.
    print(f"OK: M9 action-suspension demo -> {args.out_dir} (synthetic; no model call)")
    for row in summary:
        print(
            f"  - {row['scenario']:16} suspended_before_approval="
            f"{row['suspended_before_approval']!s:5} approval={row['approval_status']:9} "
            f"executed={row['executed']!s:5} count={row['execution_count']} "
            f"grader={'PASS' if row['grader_passed'] else 'FAIL'}"
        )
    # The harness proves the gate; if any scenario regressed into an unsafe
    # execution, surface it as a non-zero exit (a real regression signal).
    bad = [r for r in summary if not r["grader_passed"]]
    if bad:
        print(
            f"ERROR: {len(bad)} scenario(s) failed the action-suspension grader: "
            f"{[r['scenario'] for r in bad]}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
