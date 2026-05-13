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

from evals.graders import evaluator_catchable_categories  # noqa: E402
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

LLM_SYNTHETIC_DISCLAIMER = (
    "This card is generated from synthetic local eval runs. Identifiers, "
    "policies, partner configurations, and risk bands are fabricated for "
    "this lab. No production-readiness, regulatory, partner, or "
    "model-safety claim is made by this document. At least one profile "
    "compared here calls a real LLM via the credential-gated "
    "`llm_candidate_v0` path; only `draft_text` is model-generated — "
    "tool calls, policy citations, approval boundary, and prohibited-"
    "action avoidance remain deterministic."
)


LLM_PROFILE_PREFIX = "llm_"


def _is_llm_profile(agent_system_version: str) -> bool:
    """True when the named profile routes draft text through the LLM adapter.

    The convention is that any profile whose ``agent_system_version`` starts
    with ``llm_`` is credential-gated and calls an external model (see
    ``app/agents/llm_adapter.py``). Today that's ``llm_candidate_v0``; future
    LLM profiles must keep the prefix so this check stays correct without
    edits.
    """

    return bool(agent_system_version) and agent_system_version.startswith(
        LLM_PROFILE_PREFIX
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
    baseline_label: str = "Baseline",
    improved_label: str = "Improved",
) -> str:
    improved_by_name = {rate.name: rate for rate in improved_rates}
    lines = [
        f"| Grader | {baseline_label} | {improved_label} | Δ pass rate |",
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
    baseline_label: str = "Baseline",
    improved_label: str = "Improved",
) -> str:
    keys = sorted(set(baseline_labels) | set(improved_labels))
    if not keys:
        return "_No failure labels surfaced in either run._"
    lines = [
        f"| Failure label | {baseline_label} | {improved_label} |",
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


def _operational_block(
    baseline: EvalReport,
    improved: EvalReport,
    baseline_label: str = "Baseline",
    improved_label: str = "Improved",
) -> str:
    b = _operational_summary(baseline)
    i = _operational_summary(improved)
    lines = [
        f"| Metric | {baseline_label} | {improved_label} |",
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


def _load_regressions(regressions_path: Path | None) -> list[dict[str, Any]]:
    if regressions_path is None:
        return []
    if not regressions_path.exists():
        raise SystemExit(f"regressions file not found: {regressions_path}")
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(regressions_path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{regressions_path}: line {line_no}: invalid JSON ({exc})")
    return records


def _regression_seeds_block(regressions: list[dict[str, Any]]) -> str:
    if not regressions:
        return "_No regression seeds linked into this card._"
    lines = [
        "| Regression case | Source case | Labels at capture | Source profile | Review status |",
        "|---|---|---|---|---|",
    ]
    for record in regressions:
        labels = ", ".join(f"`{label}`" for label in record.get("failure_labels", [])) or "_(none)_"
        lines.append(
            f"| `{record.get('regression_case_id', record.get('case_id', '?'))}` "
            f"| `{record.get('source_case_id', '?')}` "
            f"| {labels} "
            f"| `{record.get('source_agent_system_version', '?')}` "
            f"| `{record.get('review_status', 'pending_review')}` |"
        )
    return "\n".join(lines)


def _catch_rate_block(
    baseline: EvalReport,
    improved: EvalReport,
    baseline_label: str = "Baseline",
    improved_label: str = "Improved",
) -> str:
    """Render the runtime evaluator catch-rate subsection."""

    def _rate(report: EvalReport) -> str:
        for rate in report.aggregate_grader_pass_rates:
            if rate.name == "evaluator_catch_rate":
                return f"{rate.passed}/{rate.total} ({rate.pass_rate:.2f})"
        return "_not measured_"

    scope = evaluator_catchable_categories()
    scope_lines = "\n".join(
        f"- `{label}` → runtime check(s): "
        + ", ".join(f"`{name}`" for name in sorted(checks))
        for label, checks in sorted(scope.items())
    )
    baseline_miss = baseline.failure_label_counts.get("EVALUATOR_MISS", 0)
    improved_miss = improved.failure_label_counts.get("EVALUATOR_MISS", 0)
    miss_line = (
        f"**{baseline_label} `EVALUATOR_MISS`:** {baseline_miss} · "
        f"**{improved_label} `EVALUATOR_MISS`:** {improved_miss}"
    )
    return (
        "The runtime evaluator (`app/evaluator.py`) should catch failures in a "
        "small, explicit set of categories. The catch-rate grader compares "
        "offline grader failures against the runtime evaluator's own checks for "
        "those categories. Architectural failures (`TOOL_MISUSE`, "
        "`HANDOFF_CONTEXT_LOSS`, `SCHEMA_VIOLATION`) are intentionally out of "
        "scope — they describe the multi-agent system, not what the evaluator "
        "could plausibly inspect on a single draft.\n\n"
        "**Catchable categories:**\n"
        f"{scope_lines}\n\n"
        f"**Catch-rate:** {baseline_label.lower()} {_rate(baseline)} · "
        f"{improved_label.lower()} {_rate(improved)}\n\n"
        f"{miss_line}"
    )


def render_card(
    baseline: EvalReport,
    improved: EvalReport,
    regressions: list[dict[str, Any]] | None = None,
    baseline_label: str = "Baseline",
    improved_label: str = "Improved",
) -> str:
    """Render the markdown eval card from two validated reports.

    ``regressions`` is an optional list of regression-seed records (see
    ``scripts/incident_to_regression.py``); when present, a small
    "Regression Seeds" section is rendered alongside the quality
    metrics.

    ``baseline_label`` / ``improved_label`` control the column-header and
    section-heading text. Defaults are ``"Baseline"`` and ``"Improved"`` so
    every existing card target renders byte-equivalent output. Pass e.g.
    ``"Reference"`` / ``"Candidate"`` for an LLM-candidate comparison card
    where neither side is the deliberately-weak baseline.
    """

    workflows = sorted(
        {case.workflow for case in baseline.per_case}
        | {case.workflow for case in improved.per_case}
    )
    workflow_str = ", ".join(f"`{w}`" for w in workflows) or "_unknown_"

    grader_table = _grader_table(
        baseline.aggregate_grader_pass_rates,
        improved.aggregate_grader_pass_rates,
        baseline_label=baseline_label,
        improved_label=improved_label,
    )
    label_table = _label_table(
        baseline.failure_label_counts,
        improved.failure_label_counts,
        baseline_label=baseline_label,
        improved_label=improved_label,
    )
    failing_block = _failing_case_block(baseline.per_case)
    improved_failing_block = _failing_case_block(improved.per_case)
    operational_block = _operational_block(
        baseline,
        improved,
        baseline_label=baseline_label,
        improved_label=improved_label,
    )

    summary_table = (
        f"| Field | {baseline_label} | {improved_label} |\n"
        "|---|---|---|\n"
        f"| Agent-system profile | `{baseline.agent_system_version}` | `{improved.agent_system_version}` |\n"
        f"| Dataset | `{baseline.dataset_path}` | `{improved.dataset_path}` |\n"
        f"| Cases | {baseline.case_count} | {improved.case_count} |\n"
        f"| Passed | {baseline.passed_case_count} | {improved.passed_case_count} |\n"
        f"| Failed | {baseline.failed_case_count} | {improved.failed_case_count} |\n"
        f"| Report version | `{baseline.version}` | `{improved.version}` |"
    )

    # The deterministic fix-bullet block describes the *known* deltas between
    # the canonical baseline_v0 (deliberately weak) and improved_v0
    # (policy-compliant) profiles. For any other profile pair — e.g. an LLM
    # candidate compared against improved_v0 — those specific deltas do not
    # apply, so we emit a generic, non-overclaiming note instead.
    deterministic_pair = (
        baseline.agent_system_version == "baseline_v0"
        and improved.agent_system_version == "improved_v0"
    )
    fix_bullets: list[str] = []
    if deterministic_pair:
        improved_failure_labels_in_baseline = sorted(baseline.failure_label_counts)
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
        if "EVALUATOR_MISS" in improved_failure_labels_in_baseline:
            fix_bullets.append(
                "Closes runtime evaluator gaps the baseline left open — the offline "
                "catch-rate grader was firing `EVALUATOR_MISS` on the baseline and "
                "the improved profile clears it."
            )
        if not fix_bullets:
            fix_bullets.append(
                "No baseline failures were surfaced by the offline graders, so no specific "
                "fixes are claimed. Add adversarial cases before claiming improvement."
            )
    else:
        fix_bullets.append(
            f"`{improved.agent_system_version}` produced its own draft text on the same "
            "deterministic decision graph as "
            f"`{baseline.agent_system_version}`; specific behavioral deltas surface in the "
            "failure-label and grader tables above. No claim is made about model safety, "
            "pilot readiness, or production behavior from this card."
        )

    fixes_block = "\n".join(f"- {bullet}" for bullet in fix_bullets)

    catch_rate_block = _catch_rate_block(
        baseline,
        improved,
        baseline_label=baseline_label,
        improved_label=improved_label,
    )
    regression_block = _regression_seeds_block(regressions or [])

    llm_in_play = _is_llm_profile(baseline.agent_system_version) or _is_llm_profile(
        improved.agent_system_version
    )
    top_disclaimer = (
        LLM_SYNTHETIC_DISCLAIMER if llm_in_play else SYNTHETIC_DISCLAIMER
    )
    operational_rider = (
        (
            "Cost is currently surfaced as `0.0` because the `llm_candidate_v0`\n"
            "adapter does not yet capture `response.usage` tokens — capturing real\n"
            "cost is a tracked follow-up. Latency is wall-clock end-to-end for the\n"
            "graph node path, which now includes a real LLM call on at least one\n"
            "profile. Per-band targets in `configs/latency_budgets.yaml` are\n"
            "**synthetic planning envelopes**, not production SLAs, partner\n"
            "commitments, or regulatory thresholds."
        )
        if llm_in_play
        else (
            "Cost is a deterministic `0.0` placeholder — the current Phase 3 runner\n"
            "makes no model calls. Latency is wall-clock for the deterministic\n"
            "runner only. Per-band targets in `configs/latency_budgets.yaml` are\n"
            "**synthetic planning envelopes**, not production SLAs, partner\n"
            "commitments, or regulatory thresholds."
        )
    )
    launch_posture_rider = (
        (
            "Specifically: this card compares an LLM-backed profile against the\n"
            "deterministic reference on a single synthetic adversarial slice. It\n"
            "owes: LLM cost capture, a redacted evidence pack covering the LLM\n"
            "traces, pinned regression seeds for any new model failures, and\n"
            "pilot-readiness review artifacts before any launch-readiness\n"
            "recommendation could be made."
        )
        if llm_in_play
        else (
            "Specifically: this lab still owes an `EvaluatorNode` catch-rate grader,\n"
            "a regression loop that pins failing traces as future test cases, an\n"
            "LLM-backed agent (so cost and latency become meaningful), redacted\n"
            "evidence packs, and pilot-readiness review artifacts before any\n"
            "launch-readiness recommendation could be made."
        )
    )

    closing_paragraph = (
        "This is a synthetic deterministic change set; it demonstrates the eval\n"
        "loop closing on planted failures. Do not infer pilot, production, or\n"
        "regulatory acceptance from this delta — the baseline failures were\n"
        "authored as targets for this lab."
        if deterministic_pair
        else (
            "This card compares two profiles on the same synthetic dataset. The\n"
            f"`{improved.agent_system_version}` profile is positioned as the candidate; "
            f"`{baseline.agent_system_version}` is the reference. No model-safety,\n"
            "pilot-readiness, or production-readiness claim is made by this document."
        )
    )

    return f"""# Local Eval Card — Financial Links Vertical Slice

> {top_disclaimer}

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

### Runtime evaluator catch-rate

{catch_rate_block}

## Regression seeds

{regression_block}

## What failed in {baseline_label.lower()}

{failing_block}

## What failed in {improved_label.lower()}

{improved_failing_block}

## What changed in {improved_label.lower()} profile

{fixes_block}

{closing_paragraph}

## Operational metrics

{operational_block}

{operational_rider}

## Launch posture

**{LAUNCH_POSTURE}**

{launch_posture_rider}
"""


def generate_eval_card(
    baseline_report: Path,
    improved_report: Path,
    out: Path,
    regressions: Path | None = None,
    baseline_label: str = "Baseline",
    improved_label: str = "Improved",
) -> Path:
    baseline = _load_report(Path(baseline_report))
    improved = _load_report(Path(improved_report))
    _validate_pair(baseline, improved)
    regression_records = _load_regressions(Path(regressions) if regressions else None)

    markdown = render_card(
        baseline,
        improved,
        regression_records,
        baseline_label=baseline_label,
        improved_label=improved_label,
    )
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
    parser.add_argument(
        "--regressions",
        type=Path,
        default=None,
        help=(
            "Optional path to a regressions_v0.jsonl file. If supplied "
            "the card gets a 'Regression Seeds' section listing the "
            "linked records."
        ),
    )
    parser.add_argument(
        "--baseline-label",
        default="Baseline",
        help=(
            "Column-header / section-heading label for the first report. "
            "Defaults to 'Baseline' so the existing deterministic cards "
            "render byte-equivalent output. Use e.g. 'Reference' when "
            "neither profile is the deliberately-weak baseline."
        ),
    )
    parser.add_argument(
        "--improved-label",
        default="Improved",
        help=(
            "Column-header / section-heading label for the second report. "
            "Defaults to 'Improved'. Use e.g. 'Candidate' for an LLM "
            "candidate comparison card."
        ),
    )
    args = parser.parse_args(argv)

    out_path = generate_eval_card(
        baseline_report=args.baseline_report,
        improved_report=args.improved_report,
        out=args.out,
        regressions=args.regressions,
        baseline_label=args.baseline_label,
        improved_label=args.improved_label,
    )
    print(f"OK: wrote eval card -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
