"""Render a markdown eval card from two local JSON eval reports.

Reads a baseline and improved report produced by ``scripts/run_eval.py``
and writes a public-safe markdown summary. The card never asserts pilot
readiness, regulatory compliance, or real-world performance — every
number on it is synthetic and traceable back to the report JSON next to it.

Example:

    uv run python scripts/generate_eval_card.py \\
        --baseline-report reports/baseline_smoke_eval.json \\
        --improved-report reports/improved_smoke_eval.json \\
        --out reports/smoke_eval_card.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.run import AggregateGraderRate, CaseEvalResult, EvalReport  # noqa: E402


LAUNCH_POSTURE = (
    "NOT READY FOR PILOT — local synthetic vertical slice only; "
    "proceed to evaluator catch-rate and regression-loop work."
)

SYNTHETIC_DISCLAIMER = (
    "This card is generated from synthetic local eval runs. Identifiers, "
    "policies, partner configurations, and risk bands are fabricated for "
    "this lab. No production-readiness, regulatory, or partner claim is "
    "made by this document. Numbers reflect a deterministic Phase 3 "
    "Financial Links runner with no LLM call."
)


def _load_report(path: Path) -> EvalReport:
    if not path.exists():
        raise SystemExit(f"report not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object, got {type(data).__name__}")
    try:
        return EvalReport.model_validate(data)
    except ValidationError as exc:
        raise SystemExit(f"{path}: report does not match EvalReport shape:\n{exc}")


def _validate_pair(baseline: EvalReport, improved: EvalReport) -> None:
    if baseline.agent_system_version == improved.agent_system_version:
        raise SystemExit(
            "baseline and improved reports use the same agent_system_version "
            f"({baseline.agent_system_version!r}); they must differ to render a "
            "before/after eval card."
        )
    if baseline.dataset_path != improved.dataset_path:
        raise SystemExit(
            "baseline and improved reports were run against different datasets:\n"
            f"  baseline: {baseline.dataset_path}\n"
            f"  improved: {improved.dataset_path}\n"
            "render an eval card against the same dataset for both profiles."
        )
    if baseline.case_count != improved.case_count:
        raise SystemExit(
            "baseline and improved reports have different case counts "
            f"({baseline.case_count} vs {improved.case_count}); cannot compare."
        )


def _grader_table(
    baseline_rates: list[AggregateGraderRate],
    improved_rates: list[AggregateGraderRate],
) -> str:
    improved_by_name = {rate.name: rate for rate in improved_rates}
    lines = [
        "| Grader | Baseline | Improved | Δ pass rate |",
        "|---|---:|---:|---:|",
    ]
    for rate in baseline_rates:
        other = improved_by_name.get(rate.name)
        if other is None:
            continue
        delta = other.pass_rate - rate.pass_rate
        lines.append(
            f"| `{rate.name}` | {rate.passed}/{rate.total} ({rate.pass_rate:.2f}) | "
            f"{other.passed}/{other.total} ({other.pass_rate:.2f}) | "
            f"{delta:+.2f} |"
        )
    return "\n".join(lines)


def _label_table(
    baseline_labels: dict[str, int],
    improved_labels: dict[str, int],
) -> str:
    keys = sorted(set(baseline_labels) | set(improved_labels))
    if not keys:
        return "_No failure labels surfaced in either run._"
    lines = [
        "| Failure label | Baseline | Improved |",
        "|---|---:|---:|",
    ]
    for label in keys:
        lines.append(
            f"| `{label}` | {baseline_labels.get(label, 0)} | {improved_labels.get(label, 0)} |"
        )
    return "\n".join(lines)


def _failing_case_block(cases: list[CaseEvalResult]) -> str:
    failing = [c for c in cases if not c.passed]
    if not failing:
        return "_No failing cases in this run._"
    lines = []
    for case in failing:
        labels = ", ".join(f"`{label}`" for label in case.failure_labels) or "_(no labels)_"
        lines.append(
            f"- **`{case.case_id}`** ({case.risk_band}, "
            f"`{case.workflow}`) — labels: {labels}. "
            f"Trace: [`{case.trace_path}`]({case.trace_path})."
        )
    return "\n".join(lines)


def _operational_summary(report: EvalReport) -> dict[str, Any]:
    measured_by_band = (
        report.synthetic_latency_envelope.get("measured_ms", {}).get("samples_by_risk_band", {})
        if report.synthetic_latency_envelope
        else {}
    )
    return {
        "total_est_cost_usd": report.synthetic_cost_summary.get("total_est_cost_usd", 0.0),
        "case_count": report.case_count,
        "measured_by_band": measured_by_band,
    }


def _operational_block(baseline: EvalReport, improved: EvalReport) -> str:
    b = _operational_summary(baseline)
    i = _operational_summary(improved)
    lines = [
        "| Metric | Baseline | Improved |",
        "|---|---:|---:|",
        f"| Total est. cost (USD) | {b['total_est_cost_usd']} | {i['total_est_cost_usd']} |",
        f"| Cases counted | {b['case_count']} | {i['case_count']} |",
    ]
    bands = sorted(set(b["measured_by_band"]) | set(i["measured_by_band"]))
    for band in bands:
        b_band = b["measured_by_band"].get(band, {})
        i_band = i["measured_by_band"].get(band, {})
        lines.append(
            f"| `{band}` measured mean (ms) | "
            f"{b_band.get('mean_ms', '—')} | {i_band.get('mean_ms', '—')} |"
        )
    return "\n".join(lines)


def render_card(baseline: EvalReport, improved: EvalReport) -> str:
    """Render the markdown eval card from two validated reports."""

    workflows = sorted(
        {case.workflow for case in baseline.per_case}
        | {case.workflow for case in improved.per_case}
    )
    workflow_str = ", ".join(f"`{w}`" for w in workflows) or "_unknown_"

    grader_table = _grader_table(
        baseline.aggregate_grader_pass_rates,
        improved.aggregate_grader_pass_rates,
    )
    label_table = _label_table(baseline.failure_label_counts, improved.failure_label_counts)
    failing_block = _failing_case_block(baseline.per_case)
    improved_failing_block = _failing_case_block(improved.per_case)
    operational_block = _operational_block(baseline, improved)

    summary_table = (
        "| Field | Baseline | Improved |\n"
        "|---|---|---|\n"
        f"| Agent-system profile | `{baseline.agent_system_version}` | `{improved.agent_system_version}` |\n"
        f"| Dataset | `{baseline.dataset_path}` | `{improved.dataset_path}` |\n"
        f"| Cases | {baseline.case_count} | {improved.case_count} |\n"
        f"| Passed | {baseline.passed_case_count} | {improved.passed_case_count} |\n"
        f"| Failed | {baseline.failed_case_count} | {improved.failed_case_count} |\n"
        f"| Report version | `{baseline.version}` | `{improved.version}` |"
    )

    improved_failure_labels_in_baseline = sorted(baseline.failure_label_counts)
    fix_bullets = []
    if "POLICY_MISS" in improved_failure_labels_in_baseline:
        fix_bullets.append(
            "Restores the synthetic partner-fallback policy citation "
            "(`FL-PARTNER-FALLBACK-002`) on cases the baseline omitted."
        )
    if "TOOL_MISUSE" in improved_failure_labels_in_baseline:
        fix_bullets.append(
            "Calls `lookup_partner_config` even on healthy aggregator routes when "
            "an institution + partner are present (the baseline skipped this)."
        )
    if "UNSAFE_CUSTOMER_COMMS" in improved_failure_labels_in_baseline:
        fix_bullets.append(
            "Removes the baseline's real-time-data overpromise from customer-facing "
            "copy; the improved draft uses hedged language only."
        )
    if not fix_bullets:
        fix_bullets.append(
            "No baseline failures were surfaced by the offline graders, so no specific "
            "fixes are claimed. Add adversarial cases before claiming improvement."
        )

    fixes_block = "\n".join(f"- {bullet}" for bullet in fix_bullets)

    return f"""# Local Eval Card — Financial Links Vertical Slice

> {SYNTHETIC_DISCLAIMER}

## Summary

- **Workflow:** {workflow_str}
- **Profiles compared:** `{baseline.agent_system_version}` → `{improved.agent_system_version}`
- **Dataset:** `{baseline.dataset_path}`

{summary_table}

## Quality metrics

### Aggregate grader pass rates

{grader_table}

### Failure label counts

{label_table}

## What failed in baseline

{failing_block}

## What failed in improved

{improved_failing_block}

## What changed in improved profile

{fixes_block}

This is a synthetic deterministic change set; it demonstrates the eval
loop closing on planted failures. Do not infer pilot, production, or
regulatory acceptance from this delta — the baseline failures were
authored as targets for this lab.

## Operational metrics

{operational_block}

Cost is a deterministic `0.0` placeholder — the current Phase 3 runner
makes no model calls. Latency is wall-clock for the deterministic
runner only. Per-band targets in `configs/latency_budgets.yaml` are
**synthetic planning envelopes**, not production SLAs, partner
commitments, or regulatory thresholds.

## Launch posture

**{LAUNCH_POSTURE}**

Specifically: this lab still owes an `EvaluatorNode` catch-rate grader,
a regression loop that pins failing traces as future test cases, an
LLM-backed agent (so cost and latency become meaningful), redacted
evidence packs, and pilot-readiness review artifacts before any
launch-readiness recommendation could be made.
"""


def generate_eval_card(
    baseline_report: Path,
    improved_report: Path,
    out: Path,
) -> Path:
    baseline = _load_report(Path(baseline_report))
    improved = _load_report(Path(improved_report))
    _validate_pair(baseline, improved)

    markdown = render_card(baseline, improved)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a public-safe markdown eval card from two local "
            "before/after JSON eval reports."
        )
    )
    parser.add_argument("--baseline-report", required=True, type=Path)
    parser.add_argument("--improved-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    out_path = generate_eval_card(
        baseline_report=args.baseline_report,
        improved_report=args.improved_report,
        out=args.out,
    )
    print(f"OK: wrote eval card -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
