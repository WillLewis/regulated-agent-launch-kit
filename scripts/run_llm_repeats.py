"""Opt-in credentialed repeat-run capture for LLM variance measurement.

The aggregation half of this loop is
``scripts/aggregate_llm_repeats.py``. This script is the **capture**
half: it runs the credentialed eval pipeline ``--runs N`` times against
the same dataset for one ``llm_candidate_v*`` profile, writes raw
per-run eval reports + traces to gitignored local paths, and prints a
short cost / pass / fail summary.

Hard guardrails:

- Refuses to run unless ``ANTHROPIC_API_KEY`` + the ``anthropic`` SDK
  are present (calls ``scripts.check_llm_env.check_llm_env`` first).
- Refuses deterministic / unknown profiles by default. Pass
  ``--allow-non-llm-profile`` to opt in to running this loop against a
  non-``llm_*`` profile (useful for the aggregator's own tests against
  deterministic baselines, not for real evaluation).
- Never silently falls back to a deterministic profile if the LLM
  adapter is unconfigured — the underlying ``LLMAdapterConfigError``
  bubbles up.

Output layout:

    <out-dir>/<profile>/<timestamp>/
      run_001/
        eval_report.json
        traces/<case_id>.json
      run_002/
        eval_report.json
        traces/<case_id>.json
      ...

The per-run ``eval_report.json`` files are exactly the
``EvalReport``-shaped JSONs ``scripts/aggregate_llm_repeats.py``
consumes — point the aggregator at the timestamp directory and it
collects every ``run_*/eval_report.json`` automatically.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_llm_env import check_llm_env  # noqa: E402


# Profile names this script accepts by default. The deterministic
# ``baseline_v0`` / ``improved_v0`` are excluded because there is no
# variance to measure (they are deterministic) and because running them
# under this script's output layout would imply a credentialed run.
_DEFAULT_ALLOWED_PROFILES: frozenset[str] = frozenset(
    {"llm_candidate_v0", "llm_candidate_v1"}
)


class RepeatRunnerError(RuntimeError):
    """Raised when the repeat-runner refuses to run a configuration."""


def _timestamp_dir(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")


def plan_run_paths(
    *,
    out_dir: Path,
    profile: str,
    runs: int,
    timestamp: str | None = None,
) -> tuple[Path, list[dict[str, Path]]]:
    """Compute the output directory + per-run path bundle without
    creating anything on disk. Used by tests and the CLI.

    Returns ``(timestamped_dir, [{'eval_report': ..., 'traces_dir': ...}, ...])``.
    """

    if runs < 1:
        raise RepeatRunnerError(f"--runs must be >= 1; got {runs}")
    ts = timestamp or _timestamp_dir()
    base = Path(out_dir) / profile / ts
    plan: list[dict[str, Path]] = []
    for i in range(1, runs + 1):
        run_dir = base / f"run_{i:03d}"
        plan.append(
            {
                "run_dir": run_dir,
                "eval_report": run_dir / "eval_report.json",
                "traces_dir": run_dir / "traces",
            }
        )
    return base, plan


def _resolve_run_eval() -> Callable[..., Any]:
    """Lazy import of ``evals.run.run_eval`` so the script doesn't pull
    LangGraph into the import path when --help is called."""

    from evals.run import run_eval  # noqa: PLC0415

    return run_eval


def _ensure_profile_allowed(
    profile: str, *, allow_non_llm_profile: bool
) -> None:
    if profile in _DEFAULT_ALLOWED_PROFILES:
        return
    if allow_non_llm_profile:
        # Caller has explicitly opted in to a non-LLM profile (e.g. for
        # aggregator regression testing). Still don't allow arbitrary
        # strings — must be a known profile.
        try:
            from app.agents.profiles import KNOWN_PROFILES  # noqa: PLC0415
        except ImportError as exc:
            raise RepeatRunnerError(
                f"cannot validate profile {profile!r}: {exc}"
            ) from exc
        if profile not in KNOWN_PROFILES:
            raise RepeatRunnerError(
                f"unknown profile {profile!r}; known profiles: "
                f"{sorted(KNOWN_PROFILES)}"
            )
        return
    raise RepeatRunnerError(
        f"profile {profile!r} is not an LLM-candidate profile; "
        f"this script captures variance for {sorted(_DEFAULT_ALLOWED_PROFILES)} only. "
        "Pass --allow-non-llm-profile to override (useful for aggregator "
        "regression testing against deterministic profiles; never for real "
        "variance measurement)."
    )


def _ensure_credentials() -> None:
    """Hard preflight: refuse to spend tokens without credentials + SDK."""

    result = check_llm_env()
    if not result.ok:
        raise RepeatRunnerError(
            "credentialed repeat-run capture requires ANTHROPIC_API_KEY + "
            "the anthropic SDK. The preflight failed:\n" + result.render()
        )


def run_repeats(
    *,
    dataset: Path,
    profile: str,
    runs: int,
    out_dir: Path,
    allow_non_llm_profile: bool = False,
    skip_preflight: bool = False,
    run_eval_fn: Callable[..., Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Execute ``runs`` credentialed eval invocations against ``dataset``.

    ``run_eval_fn`` is injectable so tests can replace the real
    ``evals.run.run_eval`` with a fake. ``skip_preflight`` exists only
    for those tests — the CLI always runs the preflight.

    Returns a structured summary (also printed) with the per-run report
    paths so the aggregator can be pointed at the right files
    without rediscovering them.
    """

    _ensure_profile_allowed(profile, allow_non_llm_profile=allow_non_llm_profile)
    if not skip_preflight:
        _ensure_credentials()
    if not dataset.exists():
        raise RepeatRunnerError(f"dataset not found: {dataset}")

    eval_fn = run_eval_fn or _resolve_run_eval()
    ts = timestamp or _timestamp_dir()
    base_dir, plan = plan_run_paths(
        out_dir=out_dir, profile=profile, runs=runs, timestamp=ts
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    per_run: list[dict[str, Any]] = []
    started = time.time()
    for idx, entry in enumerate(plan, start=1):
        run_started = time.time()
        report = eval_fn(
            dataset_path=dataset,
            traces_out=entry["traces_dir"],
            report_out=entry["eval_report"],
            agent_system_version=profile,
        )
        elapsed = round(time.time() - run_started, 3)
        report_dict = (
            report.model_dump(mode="json")
            if hasattr(report, "model_dump")
            else dict(report or {})
        )
        per_run.append(
            {
                "run_index": idx,
                "report_path": str(entry["eval_report"]),
                "traces_dir": str(entry["traces_dir"]),
                "passed_case_count": int(report_dict.get("passed_case_count", 0)),
                "failed_case_count": int(report_dict.get("failed_case_count", 0)),
                "failure_label_counts": dict(
                    report_dict.get("failure_label_counts") or {}
                ),
                "total_est_cost_usd": float(
                    (report_dict.get("synthetic_cost_summary") or {}).get(
                        "total_est_cost_usd", 0.0
                    )
                ),
                "elapsed_s": elapsed,
            }
        )
        print(
            f"  run {idx}/{runs}: passed={per_run[-1]['passed_case_count']} "
            f"failed={per_run[-1]['failed_case_count']} "
            f"labels={per_run[-1]['failure_label_counts']} "
            f"cost_usd={per_run[-1]['total_est_cost_usd']} "
            f"elapsed_s={elapsed} "
            f"-> {entry['eval_report']}"
        )

    total_elapsed = round(time.time() - started, 3)
    total_cost = round(sum(r["total_est_cost_usd"] for r in per_run), 6)
    return {
        "profile": profile,
        "dataset": str(dataset),
        "runs": runs,
        "base_dir": str(base_dir),
        "timestamp": ts,
        "per_run": per_run,
        "total_est_cost_usd": total_cost,
        "total_elapsed_s": total_elapsed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run N credentialed adversarial evals for an llm_candidate_v* "
            "profile and write each run's outputs under "
            "<out-dir>/<profile>/<timestamp>/run_<i>/. Does NOT call the "
            "deterministic-only path."
        )
    )
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--runs", required=True, type=int)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--allow-non-llm-profile",
        action="store_true",
        help=(
            "Opt in to running this loop against a non-llm_* profile. "
            "Intended for aggregator regression testing only; never for "
            "real variance measurement."
        ),
    )
    args = parser.parse_args(argv)

    try:
        summary = run_repeats(
            dataset=args.dataset,
            profile=args.profile,
            runs=args.runs,
            out_dir=args.out_dir,
            allow_non_llm_profile=args.allow_non_llm_profile,
        )
    except RepeatRunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary_path = Path(summary["base_dir"]) / "_run_manifest.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(
        f"OK: captured {summary['runs']} runs of {summary['profile']} | "
        f"total_est_cost_usd={summary['total_est_cost_usd']} | "
        f"base={summary['base_dir']} | manifest={summary_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
