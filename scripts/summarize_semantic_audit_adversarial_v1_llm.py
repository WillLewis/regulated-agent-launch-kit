"""Write the public-safe model/NLI semantic audit summary for the adversarial
v1 LLM candidate comparison.

This script consumes artifacts **already on disk** — the two candidate eval
reports and the two model/NLI ``SemanticDecision`` files — and emits an
aggregate-only JSON + Markdown summary. It makes no model or network call and
needs no credentials.

The raw decision files quote draft spans (``rationale`` / ``evidence_spans``)
and are gitignored; this summary copies only counts, enum histograms, synthetic
case IDs/risk bands, confidence ranges, and list-price cost estimates. The
output is therefore safe to track and to ship inside the evidence pack.
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

from evals.semantic_audit import (  # noqa: E402
    build_semantic_audit_summary,
    render_markdown,
)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(
            f"{label} not found: {path}\n"
            "  Hint: generate the model/NLI decision files first with "
            "`make semantic-model-decisions-adversarial-v1-llm-v0` and "
            "`...-llm-v1` (credentialed), which judge the drafts already on disk."
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected a JSON object")
    return data


def summarize(
    *,
    report_v0: Path,
    report_v1: Path,
    decisions_v0: Path,
    decisions_v1: Path,
    out_json: Path,
    out_md: Path,
) -> dict[str, Any]:
    inputs = [
        (
            _load_json(report_v0, "report-v0"),
            _load_json(decisions_v0, "decisions-v0"),
            str(decisions_v0),
        ),
        (
            _load_json(report_v1, "report-v1"),
            _load_json(decisions_v1, "decisions-v1"),
            str(decisions_v1),
        ),
    ]
    try:
        summary = build_semantic_audit_summary(inputs)
    except ValueError as exc:
        raise SystemExit(f"cannot build semantic audit summary: {exc}") from exc

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2))
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(summary))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate the opt-in model/NLI semantic decisions for the "
            "adversarial v1 LLM candidate comparison into a public-safe "
            "summary. Reads existing reports + decision files only; no model "
            "call, no credentials."
        )
    )
    parser.add_argument("--report-v0", type=Path, required=True)
    parser.add_argument("--report-v1", type=Path, required=True)
    parser.add_argument("--decisions-v0", type=Path, required=True)
    parser.add_argument("--decisions-v1", type=Path, required=True)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports" / "llm_adversarial_v1_semantic_audit_summary.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=REPO_ROOT / "reports" / "llm_adversarial_v1_semantic_audit_summary.md",
    )
    args = parser.parse_args(argv)

    summary = summarize(
        report_v0=args.report_v0,
        report_v1=args.report_v1,
        decisions_v0=args.decisions_v0,
        decisions_v1=args.decisions_v1,
        out_json=args.out_json,
        out_md=args.out_md,
    )
    totals = summary["totals"]
    print(
        "OK: wrote semantic audit summary -> "
        f"{args.out_json} and {args.out_md} "
        f"(semantic UNSAFE_CUSTOMER_COMMS={totals['total_semantic_unsafe_customer_comms']}, "
        f"lexical-blind-spot={totals['total_semantic_only_flags']}, "
        f"est_cost_usd={totals['total_semantic_judge_cost_usd']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
