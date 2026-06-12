"""Run v2.3 on held-out adversarial v3 repeatedly and summarize variance.

This is the M7 candidate-side variance loop. It is opt-in and credentialed:
each run drafts 28 synthetic cases with ``llm_candidate_v2_3`` and grades those
drafts with the model/NLI semantic adapter. Raw eval reports, traces, and model
decision files are written under ``reports/llm_repeats/`` (gitignored). The
tracked output is the public-safe aggregate summary only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.run import run_eval  # noqa: E402
from evals.semantic_model_adapter import SemanticAdapterResponse  # noqa: E402
from evals.semantic_calibration import (  # noqa: E402
    SUPPORTED_CONSENT_OVERFLAG,
    calibrate_consent_overflags,
)
from scripts.audit_forward_looking import audit_traces_dir  # noqa: E402
from scripts.build_semantic_replay_adversarial_v3_llm import build_replay_fixture  # noqa: E402
from scripts.check_llm_env import check_llm_env  # noqa: E402
from scripts.check_semantic_gate import evaluate_semantic_gate  # noqa: E402
from scripts.generate_semantic_decisions import generate_semantic_decision_file  # noqa: E402


SUMMARY_VERSION = "llm_adversarial_v3_candidate_v2_3_variance_v0"
DATASET = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v3.jsonl"
)
PROFILE = "llm_candidate_v2_3"
REPLAY_PROFILE = "improved_v0"
DEFAULT_OUT_DIR = REPO_ROOT / "reports" / "llm_repeats" / "adversarial_v3_v2_3"
DEFAULT_SUMMARY_MD = (
    REPO_ROOT / "reports" / "llm_adversarial_v3_candidate_v2_3_variance_summary.md"
)
DEFAULT_SUMMARY_JSON = (
    REPO_ROOT / "reports" / "llm_adversarial_v3_candidate_v2_3_variance_summary.json"
)
FORBIDDEN_PUBLIC_SUBSTRINGS: tuple[str, ...] = (
    "draft_text",
    "draft_excerpt",
    "final_response",
    "evidence_spans",
    "rationale",
    "traces/local/llm_",
    "reports/llm_repeats/",
    "semantic_model_decisions_raw",
)


class VarianceRunError(RuntimeError):
    """Raised when the variance runner cannot complete coherently."""


def _timestamp_dir(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")


def _load_cases(path: Path) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        case_id = str(row.get("case_id") or "")
        if not case_id:
            raise VarianceRunError(f"{path}: line {line_no} missing case_id")
        cases[case_id] = row
    return cases


def _decision_root(decision_file: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profile = decision_file.get("profile")
    decisions = decision_file.get("decisions")
    if not isinstance(profile, str) or not isinstance(decisions, dict):
        raise VarianceRunError("semantic decision file missing profile/decisions")
    profile_decisions = decisions.get(profile)
    if not isinstance(profile_decisions, dict):
        raise VarianceRunError(f"semantic decision file missing decisions for {profile!r}")
    return profile_decisions


def _semantic_flag_cases(
    decisions: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    flagged: list[dict[str, str]] = []
    for case_id, decision in sorted(decisions.items()):
        if not decision.get("makes_unsupported_claim"):
            continue
        flagged.append(
            {
                "case_id": str(case_id),
                "claim_type": str(decision.get("claim_type") or "unknown"),
                "calibration": str(decision.get("calibration") or "unknown"),
            }
        )
    return flagged


def _apply_consent_calibration(
    *,
    raw_decision_file: dict[str, Any],
    cases: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = raw_decision_file.get("profile")
    if not isinstance(profile, str):
        raise VarianceRunError("raw semantic decision file missing profile")
    calibrated, cleared = calibrate_consent_overflags(
        _decision_root(raw_decision_file), cases
    )
    out = dict(raw_decision_file)
    out["decisions"] = {profile: calibrated}
    out["consent_calibration_applied"] = True
    out["consent_calibration_cleared"] = cleared
    return out, cleared


def _calibration_invalid_clears(cleared: list[dict[str, Any]]) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    for entry in cleared:
        if (
            entry.get("reason") != SUPPORTED_CONSENT_OVERFLAG
            or entry.get("claim_type") != "consent"
            or entry.get("consent_state") != "granted"
        ):
            invalid.append(
                {
                    "case_id": str(entry.get("case_id")),
                    "reason": str(entry.get("reason")),
                    "claim_type": str(entry.get("claim_type")),
                    "consent_state": str(entry.get("consent_state")),
                }
            )
    return invalid


def _cost_stats(samples: list[float]) -> dict[str, Any]:
    if not samples:
        return {"samples_usd": [], "total_usd": 0.0, "mean_usd": 0.0}
    return {
        "samples_usd": [round(v, 6) for v in samples],
        "total_usd": round(sum(samples), 6),
        "mean_usd": round(statistics.fmean(samples), 6),
        "min_usd": round(min(samples), 6),
        "max_usd": round(max(samples), 6),
        "stdev_usd": round(statistics.stdev(samples), 6) if len(samples) >= 2 else None,
    }


def build_summary(per_run: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the public-safe variance summary from per-run metric rows."""

    invalid_clears = [
        {"run": row["run"], **entry}
        for row in per_run
        for entry in row.get("calibration_invalid_clears", [])
    ]
    stable = (
        bool(per_run)
        and all(row["forward_looking_violations"] == 0 for row in per_run)
        and all(row["calibrated_semantic_flags"] == 0 for row in per_run)
        and not invalid_clears
    )
    total_cost_samples = [float(row.get("total_est_cost_usd", 0.0)) for row in per_run]
    summary = {
        "version": SUMMARY_VERSION,
        "synthetic": True,
        "not_ready_for_pilot": True,
        "profile": PROFILE,
        "dataset": "financial_links_reliability_adversarial_v3",
        "run_count": len(per_run),
        "stability_verdict": "STABLE" if stable else "NOT_STABLE",
        "acceptance_criteria": {
            "forward_looking_violations_all_zero": all(
                row["forward_looking_violations"] == 0 for row in per_run
            ),
            "calibrated_semantic_flags_all_zero": all(
                row["calibrated_semantic_flags"] == 0 for row in per_run
            ),
            "calibration_only_cleared_consent_granted": not invalid_clears,
        },
        "per_run": per_run,
        "calibration_invalid_clears": invalid_clears,
        "cost_stats_usd": _cost_stats(total_cost_samples),
        "verdict_note": (
            "STABLE across the captured runs: v2.3 had zero deterministic "
            "forward-looking violations, the calibrated semantic gate had zero "
            "flags, and calibration only cleared supported consent facts. M7 "
            "candidate-side evidence is defensible, while M7 remains OPEN / NOT "
            "READY FOR PILOT because launch criteria are broader."
            if stable
            else (
                "NOT STABLE under the captured runs. Treat any deterministic "
                "forward-looking hit as a candidate-control gap; treat any new "
                "non-consent or non-granted calibrated gate flag as an adjudication "
                "item. Do not tune the candidate to held-out cases."
            )
        ),
        "public_safety_note": (
            "Counts, case IDs, reason codes, and cost estimates only. Raw model "
            "drafts, model reasoning, quoted spans, trace paths, and semantic "
            "decision files remain local/gitignored."
        ),
    }
    _assert_public_safe(summary)
    return summary


def _case_list(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "none"
    return ", ".join(f"`{entry['case_id']}`" for entry in entries)


def _cleared_list(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "none"
    return ", ".join(
        f"`{entry['case_id']}` ({entry['claim_type']}/{entry['consent_state']})"
        for entry in entries
    )


def render_markdown(summary: dict[str, Any]) -> str:
    """Render a public-safe Markdown summary."""

    lines = [
        "# v2.3 Held-out v3 Variance Summary",
        "",
        "> NOT READY FOR PILOT — synthetic variance check only. This report carries "
        "counts, case IDs, reason codes, and cost estimates; raw drafts and model "
        "decision evidence stay local.",
        "",
        f"- **Profile:** `{summary['profile']}`",
        f"- **Dataset:** `{summary['dataset']}`",
        f"- **Runs:** N={summary['run_count']}",
        f"- **Stability verdict:** **{summary['stability_verdict']}**",
        f"- **Estimated total cost:** ${summary['cost_stats_usd']['total_usd']}",
        "",
        "## Per-run Metrics",
        "",
        "| Run | Forward-looking violations | Raw semantic flags | "
        "Calibrated semantic flags | Calibration cleared |",
        "| ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["per_run"]:
        lines.append(
            f"| {row['run']} | {row['forward_looking_violations']} | "
            f"{row['raw_semantic_flags']} | {row['calibrated_semantic_flags']} | "
            f"{_cleared_list(row['calibration_cleared'])} |"
        )

    lines += [
        "",
        "## Acceptance",
        "",
        f"- Forward-looking violations all zero: "
        f"{summary['acceptance_criteria']['forward_looking_violations_all_zero']}",
        f"- Calibrated semantic flags all zero: "
        f"{summary['acceptance_criteria']['calibrated_semantic_flags_all_zero']}",
        f"- Calibration only cleared `claim_type=consent` with `consent_state=granted`: "
        f"{summary['acceptance_criteria']['calibration_only_cleared_consent_granted']}",
        "",
        "## Flag Detail",
        "",
    ]
    for row in summary["per_run"]:
        lines += [
            f"### Run {row['run']}",
            "",
            f"- Forward-looking violation cases: {_case_list(row['forward_violation_cases'])}",
            f"- Raw semantic flag cases: {_case_list(row['raw_semantic_flag_cases'])}",
            f"- Calibrated semantic flag cases: "
            f"{_case_list(row['calibrated_semantic_flag_cases'])}",
            "",
        ]

    lines += [
        "## Verdict",
        "",
        summary["verdict_note"],
        "",
        "_This is a small-N stochastic repeat check on a synthetic held-out slice. It "
        "does not establish model safety, production readiness, pilot readiness, "
        "regulatory compliance, or M7 closure._",
        "",
    ]
    md = "\n".join(lines)
    _assert_public_safe(md)
    return md


def _assert_public_safe(value: dict[str, Any] | str) -> None:
    text = value if isinstance(value, str) else json.dumps(value)
    leaked = [needle for needle in FORBIDDEN_PUBLIC_SUBSTRINGS if needle in text]
    if leaked:
        raise VarianceRunError(f"variance summary leaks public-unsafe content: {leaked}")


def _report_cost(report: Any) -> float:
    payload = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
    return float((payload.get("synthetic_cost_summary") or {}).get("total_est_cost_usd", 0.0))


def run_variance(
    *,
    runs: int,
    out_dir: Path = DEFAULT_OUT_DIR,
    summary_md: Path = DEFAULT_SUMMARY_MD,
    summary_json: Path = DEFAULT_SUMMARY_JSON,
    skip_preflight: bool = False,
    decision_fn: Callable[..., SemanticAdapterResponse] | None = None,
    timestamp: str | None = None,
    model: str | None = None,
    timeout_s: float = 30.0,
    max_tokens: int = 512,
) -> dict[str, Any]:
    """Execute the credentialed repeat loop and write the public-safe summary."""

    if runs < 1:
        raise VarianceRunError(f"--runs must be >= 1; got {runs}")
    if not DATASET.exists():
        raise VarianceRunError(f"dataset not found: {DATASET}")
    if not skip_preflight:
        env = check_llm_env()
        if not env.ok:
            raise VarianceRunError(
                "credentialed v2.3/v3 variance run requires Anthropic credentials:\n"
                + env.render()
            )

    cases = _load_cases(DATASET)
    ts = timestamp or _timestamp_dir()
    base_dir = Path(out_dir) / PROFILE / ts
    per_run: list[dict[str, Any]] = []
    started = time.time()

    for run_index in range(1, runs + 1):
        run_started = time.time()
        run_dir = base_dir / f"run_{run_index:03d}"
        run_dir.mkdir(parents=True, exist_ok=True)

        eval_report_path = run_dir / "eval_report.json"
        traces_dir = run_dir / "traces"
        report = run_eval(
            dataset_path=DATASET,
            traces_out=traces_dir,
            report_out=eval_report_path,
            agent_system_version=PROFILE,
        )
        draft_cost = _report_cost(report)

        forward_audit = audit_traces_dir(
            traces_dir, source_label=f"run_{run_index:03d}"
        )

        raw_decisions_path = run_dir / "semantic_model_decisions_raw.json"
        decision_kwargs: dict[str, Any] = {
            "dataset_path": DATASET,
            "eval_report_path": eval_report_path,
            "out": raw_decisions_path,
            "model": model,
            "timeout_s": timeout_s,
            "max_tokens": max_tokens,
        }
        if decision_fn is not None:
            decision_kwargs["decision_fn"] = decision_fn
        raw_decision_file = generate_semantic_decision_file(**decision_kwargs)
        semantic_cost = float(
            (raw_decision_file.get("summary") or {}).get("total_est_cost_usd", 0.0)
        )
        raw_decisions = _decision_root(raw_decision_file)
        raw_flag_cases = _semantic_flag_cases(raw_decisions)

        calibrated_file, cleared = _apply_consent_calibration(
            raw_decision_file=raw_decision_file, cases=cases
        )
        calibrated_path = run_dir / "semantic_model_decisions_calibrated.json"
        calibrated_path.write_text(json.dumps(calibrated_file, indent=2) + "\n")
        calibrated_decisions = _decision_root(calibrated_file)
        calibrated_flag_cases = _semantic_flag_cases(calibrated_decisions)

        replay = build_replay_fixture(
            calibrated_file,
            replay_profile=REPLAY_PROFILE,
            source_label="per-run calibrated semantic decisions (gitignored)",
        )
        replay_path = run_dir / "semantic_replay_decisions_calibrated.json"
        replay_path.write_text(json.dumps(replay, indent=2) + "\n")

        gate_report_path = run_dir / "semantic_model_eval.json"
        gate_report = run_eval(
            dataset_path=DATASET,
            traces_out=run_dir / "semantic_model_traces",
            report_out=gate_report_path,
            agent_system_version=REPLAY_PROFILE,
            semantic_decisions_path=replay_path,
        )
        gate_result = evaluate_semantic_gate(gate_report.model_dump(mode="json"))
        gate_flag_cases = [
            {"case_id": str(item.get("case_id")), "failure_label": str(item.get("failure_label"))}
            for item in gate_result.failing
        ]
        gate_flag_count = len(gate_flag_cases)
        if gate_flag_count != len(calibrated_flag_cases):
            raise VarianceRunError(
                f"run {run_index}: calibrated decision flags ({len(calibrated_flag_cases)}) "
                f"do not match semantic gate flags ({gate_flag_count})"
            )

        elapsed_s = round(time.time() - run_started, 3)
        row = {
            "run": run_index,
            "case_count": int(forward_audit["case_count"]),
            "forward_looking_violations": int(
                forward_audit["forward_looking_violations"]
            ),
            "forward_violation_cases": list(forward_audit["violation_cases"]),
            "raw_semantic_flags": len(raw_flag_cases),
            "raw_semantic_flag_cases": raw_flag_cases,
            "calibrated_semantic_flags": gate_flag_count,
            "calibrated_semantic_flag_cases": calibrated_flag_cases,
            "calibration_cleared": cleared,
            "calibration_invalid_clears": _calibration_invalid_clears(cleared),
            "draft_est_cost_usd": round(draft_cost, 6),
            "semantic_grader_est_cost_usd": round(semantic_cost, 6),
            "total_est_cost_usd": round(draft_cost + semantic_cost, 6),
            "elapsed_s": elapsed_s,
        }
        per_run.append(row)
        print(
            f"run {run_index}/{runs}: forward={row['forward_looking_violations']} "
            f"raw_semantic={row['raw_semantic_flags']} "
            f"calibrated_semantic={row['calibrated_semantic_flags']} "
            f"cleared={len(row['calibration_cleared'])} "
            f"cost_usd={row['total_est_cost_usd']} elapsed_s={elapsed_s}"
        )

    summary = build_summary(per_run)
    summary["total_elapsed_s"] = round(time.time() - started, 3)
    _assert_public_safe(summary)

    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2) + "\n")
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(render_markdown(summary))
    print(
        f"OK: wrote v2.3/v3 variance summary for {runs} run(s) -> "
        f"{summary_md} and {summary_json}"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--summary-md", type=Path, default=DEFAULT_SUMMARY_MD)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--max-tokens", type=int, default=512)
    args = parser.parse_args(argv)

    try:
        run_variance(
            runs=args.runs,
            out_dir=args.out_dir,
            summary_md=args.summary_md,
            summary_json=args.summary_json,
            model=args.model,
            timeout_s=args.timeout_s,
            max_tokens=args.max_tokens,
        )
    except VarianceRunError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
