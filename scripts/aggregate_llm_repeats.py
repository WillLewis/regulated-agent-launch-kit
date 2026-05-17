"""Aggregate multiple eval-report JSONs for repeat-run variance measurement.

Use case: the lab has one credentialed ``llm_candidate_v0`` and one
``llm_candidate_v1`` adversarial run committed. The single-run signal
is the biggest remaining limitation in
``reports/llm_prompt_improvement_memo.md``. Before pursuing a stronger
non-lexical grader or making any prompt-improvement claim stick, the
next phase is to run the credentialed eval N times (per profile) and
characterize how outcomes vary across runs.

This script is the aggregation half of that loop. It does **not** call
the LLM, run any eval target, or touch raw traces — it only reads
already-written eval-report JSONs. The credentialed repeat-run half is
a future chunk.

Inputs:

- Two or more ``--report PATH`` flags, each pointing at an
  ``EvalReport``-shaped JSON (written by ``scripts/run_eval.py``).
- Optional ``--out-md PATH`` and ``--out-json PATH`` for the rendered
  summary.

Outputs:

- Markdown summary (synthetic-only, NOT READY FOR PILOT preserved,
  no model-safety / pilot / production / regulatory claims).
- Machine-readable JSON summary with the same numbers + the per-case
  instability table.

Validation:

- Every report must be a JSON object with ``agent_system_version``,
  ``dataset_path``, and ``per_case`` (list).
- All reports must share the same ``agent_system_version`` unless
  ``--allow-mixed-profiles`` is passed.
- All reports must share the same ``dataset_path`` unless
  ``--allow-mixed-datasets`` is passed.
- ``per_case`` entries must carry at least ``case_id``, ``passed``,
  ``failure_labels``, ``evaluator_all_ok``, ``latency_ms``,
  ``risk_band``.

No external credentials required.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPEAT_SUMMARY_VERSION: str = "llm_repeat_summary_v0"


SYNTHETIC_DISCLAIMER: str = (
    "This summary aggregates synthetic local eval runs. Identifiers, "
    "policies, partner configurations, and risk bands are fabricated for "
    "this deployment-readiness lab. The aggregated numbers describe "
    "run-to-run variance on a small synthetic slice and make no model-"
    "safety, pilot-readiness, production-readiness, or regulatory claim. "
    "Repeat-run aggregation cannot, by itself, establish prompt robustness "
    "— it only describes how today's behavior varied across the runs you "
    "happened to capture."
)


NOT_READY_LINE: str = (
    "**NOT READY FOR PILOT — local synthetic vertical slice only.** "
    "Repeat-run variance is not a readiness signal; it is one input to a "
    "future readiness conversation. A small synthetic dataset cannot prove "
    "robustness no matter how many times it is replayed."
)


_REQUIRED_REPORT_FIELDS: tuple[str, ...] = (
    "agent_system_version",
    "dataset_path",
    "per_case",
)
_REQUIRED_PER_CASE_FIELDS: tuple[str, ...] = (
    "case_id",
    "passed",
    "failure_labels",
    "evaluator_all_ok",
    "latency_ms",
    "risk_band",
)


class AggregationError(Exception):
    """Raised when the aggregator is asked to do something incoherent."""


# ---------------------------------------------------------------------------
# Loading + validation
# ---------------------------------------------------------------------------


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AggregationError(f"report not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise AggregationError(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise AggregationError(f"{path}: report must be a JSON object")
    for key in _REQUIRED_REPORT_FIELDS:
        if key not in data:
            raise AggregationError(f"{path}: missing required field {key!r}")
    per_case = data["per_case"]
    if not isinstance(per_case, list):
        raise AggregationError(f"{path}: per_case must be a list")
    for case in per_case:
        if not isinstance(case, dict):
            raise AggregationError(f"{path}: per_case entries must be dicts")
        missing = [f for f in _REQUIRED_PER_CASE_FIELDS if f not in case]
        if missing:
            raise AggregationError(
                f"{path}: per_case[{case.get('case_id', '?')!r}] missing "
                f"required fields: {missing}"
            )
    return data


def _validate_compatible(
    reports: list[dict[str, Any]],
    *,
    allow_mixed_datasets: bool,
    allow_mixed_profiles: bool,
) -> None:
    if len(reports) < 2:
        raise AggregationError(
            f"need at least 2 reports for repeat-run aggregation; got {len(reports)}"
        )
    profiles = sorted({r["agent_system_version"] for r in reports})
    datasets = sorted({r["dataset_path"] for r in reports})
    if not allow_mixed_profiles and len(profiles) > 1:
        raise AggregationError(
            f"reports mix agent_system_version values: {profiles}. "
            "Pass --allow-mixed-profiles to aggregate across profile families."
        )
    if not allow_mixed_datasets and len(datasets) > 1:
        raise AggregationError(
            f"reports mix datasets: {datasets}. "
            "Pass --allow-mixed-datasets to aggregate across datasets."
        )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _runtime_signal_per_run(reports: list[dict[str, Any]]) -> dict[str, list[int]]:
    """Per-run counts of:

    - runtime guardrail fires (``evaluator_all_ok=False`` for any reason);
    - runtime-only fires (guardrail fired AND no offline ``failure_labels``)
      — this is the asymmetry case where the offline negation-aware grader
      cleared what the substring guardrail flagged.
    """

    fires: list[int] = []
    runtime_only: list[int] = []
    for r in reports:
        f = 0
        ro = 0
        for case in r["per_case"]:
            if case.get("evaluator_all_ok") is False:
                f += 1
                if not case.get("failure_labels"):
                    ro += 1
        fires.append(f)
        runtime_only.append(ro)
    return {"runtime_guardrail_fires_per_run": fires, "runtime_only_fires_per_run": runtime_only}


def _label_distribution(
    reports: list[dict[str, Any]],
) -> tuple[Counter[str], list[dict[str, int]]]:
    totals: Counter[str] = Counter()
    per_run: list[dict[str, int]] = []
    for r in reports:
        counts = dict(r.get("failure_label_counts") or {})
        per_run.append(counts)
        for label, n in counts.items():
            totals[label] += int(n)
    return totals, per_run


def _per_case_instability(
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cases whose ``passed`` outcome varied across runs.

    Stable cases (always passed or always failed across every run) are
    omitted so the table only surfaces the actionable signal.
    """

    by_case_pass: dict[str, list[bool]] = defaultdict(list)
    by_case_labels: dict[str, list[list[str]]] = defaultdict(list)
    by_case_runtime: dict[str, list[bool]] = defaultdict(list)
    for r in reports:
        for case in r["per_case"]:
            cid = case["case_id"]
            by_case_pass[cid].append(bool(case.get("passed")))
            by_case_labels[cid].append(list(case.get("failure_labels") or []))
            by_case_runtime[cid].append(case.get("evaluator_all_ok") is False)
    out: list[dict[str, Any]] = []
    for cid, outcomes in sorted(by_case_pass.items()):
        n_pass = sum(outcomes)
        n_total = len(outcomes)
        if n_pass in (0, n_total):
            continue
        out.append(
            {
                "case_id": cid,
                "runs": n_total,
                "passed_runs": n_pass,
                "failed_runs": n_total - n_pass,
                "label_sequence": [
                    ",".join(sorted(set(labels))) or "(none)"
                    for labels in by_case_labels[cid]
                ],
                "runtime_guardrail_fired_sequence": by_case_runtime[cid],
            }
        )
    return out


def _latency_stats_by_band(reports: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_band: dict[str, list[int]] = defaultdict(list)
    for r in reports:
        envelope = r.get("synthetic_latency_envelope") or {}
        comparison = envelope.get("comparison_by_risk_band") or {}
        if comparison:
            for band, info in comparison.items():
                mean = info.get("measured_mean_ms")
                if mean is not None:
                    by_band[band].append(int(mean))
            continue
        # Fall back to per-case latencies grouped by band.
        bucket: dict[str, list[int]] = defaultdict(list)
        for case in r["per_case"]:
            band = case.get("risk_band")
            ms = case.get("latency_ms")
            if band is not None and isinstance(ms, (int, float)):
                bucket[band].append(int(ms))
        for band, samples in bucket.items():
            if samples:
                by_band[band].append(int(round(statistics.fmean(samples))))
    out: dict[str, dict[str, Any]] = {}
    for band in sorted(by_band):
        samples = by_band[band]
        out[band] = {
            "run_count": len(samples),
            "samples_ms": samples,
            "mean_ms": int(round(statistics.fmean(samples))) if samples else None,
            "min_ms": min(samples) if samples else None,
            "max_ms": max(samples) if samples else None,
            "stdev_ms": (
                int(round(statistics.stdev(samples))) if len(samples) >= 2 else None
            ),
        }
    return out


def _cost_stats(reports: list[dict[str, Any]]) -> dict[str, Any]:
    samples: list[float] = []
    for r in reports:
        cost = (r.get("synthetic_cost_summary") or {}).get("total_est_cost_usd", 0.0)
        try:
            samples.append(float(cost))
        except (TypeError, ValueError):
            samples.append(0.0)
    return {
        "samples_usd": samples,
        "run_count": len(samples),
        "total_usd": round(sum(samples), 6),
        "mean_usd": round(statistics.fmean(samples), 6) if samples else 0.0,
        "min_usd": round(min(samples), 6) if samples else 0.0,
        "max_usd": round(max(samples), 6) if samples else 0.0,
        "stdev_usd": (
            round(statistics.stdev(samples), 6) if len(samples) >= 2 else None
        ),
    }


def aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the structured aggregation summary."""

    runtime = _runtime_signal_per_run(reports)
    label_totals, label_per_run = _label_distribution(reports)
    instability = _per_case_instability(reports)
    latency = _latency_stats_by_band(reports)
    cost = _cost_stats(reports)
    pass_per_run = [int(r.get("passed_case_count", sum(1 for c in r["per_case"] if c.get("passed")))) for r in reports]
    fail_per_run = [int(r.get("failed_case_count", sum(1 for c in r["per_case"] if not c.get("passed")))) for r in reports]
    case_counts = [int(r.get("case_count", len(r["per_case"]))) for r in reports]
    offline_unsafe = [int(c.get("UNSAFE_CUSTOMER_COMMS", 0)) for c in label_per_run]
    evaluator_miss = [int(c.get("EVALUATOR_MISS", 0)) for c in label_per_run]
    return {
        "version": REPEAT_SUMMARY_VERSION,
        "synthetic": True,
        "disclaimer": SYNTHETIC_DISCLAIMER,
        "not_ready_for_pilot": True,
        "run_count": len(reports),
        "profile_family": sorted({r["agent_system_version"] for r in reports}),
        "datasets": sorted({r["dataset_path"] for r in reports}),
        "case_counts_per_run": case_counts,
        "pass_per_run": pass_per_run,
        "fail_per_run": fail_per_run,
        "failure_label_totals": dict(label_totals),
        "failure_label_per_run": label_per_run,
        "offline_unsafe_customer_comms_per_run": offline_unsafe,
        "evaluator_miss_per_run": evaluator_miss,
        "runtime_guardrail_fires_per_run": runtime["runtime_guardrail_fires_per_run"],
        "runtime_only_fires_per_run": runtime["runtime_only_fires_per_run"],
        "per_case_instability": instability,
        "latency_stats_by_band": latency,
        "cost_stats_usd": cost,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _seq(seq: list[Any]) -> str:
    return "[" + ", ".join(str(x) for x in seq) + "]"


def _instability_table(instability: list[dict[str, Any]]) -> str:
    if not instability:
        return "_No per-case outcome variance detected across the supplied runs._"
    lines = [
        "| Case | Runs | Passed | Failed | Label sequence | Runtime-fired sequence |",
        "|---|---:|---:|---:|---|---|",
    ]
    for entry in instability:
        labels = " · ".join(f"`{x}`" for x in entry["label_sequence"])
        runtime_seq = " · ".join("Y" if x else "n" for x in entry["runtime_guardrail_fired_sequence"])
        lines.append(
            f"| `{entry['case_id']}` | {entry['runs']} | "
            f"{entry['passed_runs']} | {entry['failed_runs']} | "
            f"{labels} | {runtime_seq} |"
        )
    return "\n".join(lines)


def _latency_table(latency: dict[str, dict[str, Any]]) -> str:
    if not latency:
        return "_No latency samples surfaced in the supplied runs._"
    lines = [
        "| Risk band | Runs | Mean (ms) | Min | Max | Stdev |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for band, info in latency.items():
        stdev = info["stdev_ms"] if info["stdev_ms"] is not None else "—"
        lines.append(
            f"| `{band}` | {info['run_count']} | {info['mean_ms']} | "
            f"{info['min_ms']} | {info['max_ms']} | {stdev} |"
        )
    return "\n".join(lines)


def render_markdown(summary: dict[str, Any]) -> str:
    profiles = ", ".join(f"`{p}`" for p in summary["profile_family"]) or "_(none)_"
    datasets = ", ".join(f"`{d}`" for d in summary["datasets"]) or "_(none)_"
    label_lines = (
        "\n".join(
            f"- `{label}` — total {count} across {summary['run_count']} runs"
            for label, count in sorted(summary["failure_label_totals"].items())
        )
        if summary["failure_label_totals"]
        else "_No failure labels surfaced across the supplied runs._"
    )
    return f"""# LLM Repeat-Run Variance Summary

> {SYNTHETIC_DISCLAIMER}

## Scope

- **Profile family:** {profiles}
- **Dataset(s):** {datasets}
- **Run count:** {summary['run_count']}
- **Cases per run:** {_seq(summary['case_counts_per_run'])}

## Pass / fail variance

| Metric | Per-run sequence |
|---|---|
| Passed | {_seq(summary['pass_per_run'])} |
| Failed | {_seq(summary['fail_per_run'])} |
| Runtime guardrail fires (any check) | {_seq(summary['runtime_guardrail_fires_per_run'])} |
| Runtime-only fires (offline grader cleared) | {_seq(summary['runtime_only_fires_per_run'])} |
| Offline `UNSAFE_CUSTOMER_COMMS` | {_seq(summary['offline_unsafe_customer_comms_per_run'])} |
| `EVALUATOR_MISS` | {_seq(summary['evaluator_miss_per_run'])} |

The runtime-only-fires sequence is the runtime/offline asymmetry signal:
the conservative substring guardrail fired on a draft that the offline
negation-aware grader cleared (see
`evals/graders.py::grade_unsupported_claim` and the asymmetry test in
`tests/test_grade_unsupported_claim_negation.py`). These are **not**
`EVALUATOR_MISS` — that label only counts the other direction (offline
fires, runtime missed).

## Failure-label totals

{label_lines}

## Per-case instability

{_instability_table(summary['per_case_instability'])}

## Latency by risk band (ms)

{_latency_table(summary['latency_stats_by_band'])}

Per-band budgets in `configs/latency_budgets.yaml` are **synthetic
planning envelopes** — not production SLAs, partner commitments, or
regulatory thresholds.

## Estimated cost (USD)

| Field | Value |
|---|---:|
| Total | {summary['cost_stats_usd']['total_usd']} |
| Mean | {summary['cost_stats_usd']['mean_usd']} |
| Min | {summary['cost_stats_usd']['min_usd']} |
| Max | {summary['cost_stats_usd']['max_usd']} |
| Stdev | {summary['cost_stats_usd']['stdev_usd'] if summary['cost_stats_usd']['stdev_usd'] is not None else '—'} |
| Per-run samples | {_seq(summary['cost_stats_usd']['samples_usd'])} |

Cost is estimated from `response.usage` tokens via Anthropic's public
list-price rate table (`configs/llm_cost_rates.yaml`). It is not a
partner-negotiated rate; treat it as a lower-bound forecasting signal,
not a billing number.

## Launch posture

{NOT_READY_LINE}
"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def aggregate_files(
    report_paths: list[Path],
    *,
    allow_mixed_datasets: bool = False,
    allow_mixed_profiles: bool = False,
) -> dict[str, Any]:
    """Load + validate + aggregate. Used by tests and the CLI."""

    reports = [_load_report(p) for p in report_paths]
    _validate_compatible(
        reports,
        allow_mixed_datasets=allow_mixed_datasets,
        allow_mixed_profiles=allow_mixed_profiles,
    )
    return aggregate(reports)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate repeat eval-report JSONs for variance measurement. "
            "Does not call the LLM or run any eval target."
        )
    )
    parser.add_argument(
        "--report",
        action="append",
        type=Path,
        required=True,
        help="Path to an eval-report JSON (repeat for each run).",
    )
    parser.add_argument("--out-md", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument(
        "--allow-mixed-datasets",
        action="store_true",
        help="Aggregate across reports with different dataset_path.",
    )
    parser.add_argument(
        "--allow-mixed-profiles",
        action="store_true",
        help="Aggregate across reports with different agent_system_version.",
    )
    args = parser.parse_args(argv)

    try:
        summary = aggregate_files(
            args.report,
            allow_mixed_datasets=args.allow_mixed_datasets,
            allow_mixed_profiles=args.allow_mixed_profiles,
        )
    except AggregationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.out_md is not None:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(summary))
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(summary, indent=2))

    print(
        f"OK: aggregated {summary['run_count']} reports | "
        f"profiles={summary['profile_family']} | "
        f"datasets={summary['datasets']} | "
        f"instability_cases={len(summary['per_case_instability'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
