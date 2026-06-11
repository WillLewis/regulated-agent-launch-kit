"""CLI: render a public-safe grader-reliability report from a scorer result JSON.

Consumes the JSON emitted by ``scripts/score_grader_gold.py`` and writes a
Markdown report. The report carries only metrics, gold_ids, reason codes, and
difficulty — never draft text, model rationale, or evidence spans — so it is
public-safe regardless of whether the underlying verdicts came from a real
credentialed pass.

The centerpiece is an honest "what a clean gate does and does not prove"
section, derived from the measured recall: a screen that misses overpromises
cannot turn a clean gate into a safety claim.
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


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _ci(ci: list[float] | None) -> str:
    if not ci:
        return ""
    return f" (95% CI {ci[0] * 100:.0f}–{ci[1] * 100:.0f}%)"


def _clean_gate_section(result: dict[str, Any]) -> list[str]:
    m = result["metrics"]
    conf = result["confusion"]
    recall = m["recall"]
    pos = result["gold_positive_count"]
    fn = conf["fn"]
    lines = ["## What a clean gate does and does not prove", ""]
    if recall is None:
        lines.append(
            "- Recall is undefined (no known-bad drafts scored), so this set "
            "cannot speak to what a clean gate proves."
        )
        return lines
    if fn == 0:
        lines += [
            f"- On this set the grader caught **all {pos}** known overpromises "
            f"(recall {_pct(recall)}{_ci(m['recall_ci95'])}).",
            "- A clean gate is therefore **consistent with** safety on this "
            "synthetic slice — but the wide small-N interval means it is **not "
            "proof**. The lower CI bound is the honest floor on detection.",
            "- It says nothing about claim types or phrasings absent from the "
            "gold set; expand the set before treating a clean gate as strong "
            "evidence.",
        ]
    else:
        miss_rate = fn / pos if pos else 0.0
        lines += [
            f"- The grader **missed {fn} of {pos}** known overpromises "
            f"(recall {_pct(recall)}{_ci(m['recall_ci95'])}).",
            f"- A clean gate does **NOT** prove the drafts are safe: on labeled "
            f"data this grader lets roughly **{miss_rate * 100:.0f}%** of "
            "unsupported claims through undetected.",
            "- Treat a clean gate as a **weak screen**, not evidence of safety. "
            "Every missed case below is an overpromise that would pass the gate "
            "looking green.",
        ]
    return lines


def _table(rows: list[dict[str, str]], headers: tuple[str, ...], keys: tuple[str, ...]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(f"`{row[k]}`" if k == "gold_id" else row[k] for k in keys) + " |")
    return out


def render(result: dict[str, Any]) -> str:
    m = result["metrics"]
    conf = result["confusion"]
    is_demo = "DEMO" in str(result.get("verdicts_source", "")).upper() or (
        "illustrative" in str(result.get("verdicts_source", "")).lower()
    )

    lines: list[str] = [
        "# Semantic Grader Reliability — Financial Links Gold Set",
        "",
        "> NOT READY FOR PILOT — synthetic vertical slice. This measures the "
        "model/NLI semantic **grader** against a human-authored gold set whose "
        "labels are independent of the grader. It is a reliability check on the "
        "measurement instrument, not a safety or readiness claim about the agent.",
        "",
    ]
    if is_demo:
        lines += [
            "> ⚠️ **DEMO RUN — synthetic illustrative verdicts, NOT a real grader "
            "measurement.** Numbers below exist only to demonstrate the harness "
            "end-to-end without credentials. A real measurement requires the "
            "credentialed gold-pass.",
            "",
        ]
    lines += [
        f"- **Verdicts source:** {result['verdicts_source']}",
        f"- **Scored items:** {result['scored_count']} "
        f"({result['gold_positive_count']} known-bad, "
        f"{result['gold_negative_count']} known-safe)",
        f"- **Positive class:** {result['positive_class']}",
        "",
        "## Headline",
        "",
        f"- **Recall (caught overpromises): {_pct(m['recall'])}**{_ci(m['recall_ci95'])} "
        "— the safety-critical metric.",
        f"- Precision (flags that were right): {_pct(m['precision'])}{_ci(m['precision_ci95'])}",
        f"- Specificity (safe drafts left alone): {_pct(m['specificity'])}",
        f"- Accuracy: {_pct(m['accuracy'])}  |  F1: {_pct(m['f1'])}",
        "",
        "## Confusion matrix",
        "",
        "| | grader flags | grader clean |",
        "| --- | --- | --- |",
        f"| **gold: unsupported claim** | {conf['tp']} (caught) | "
        f"{conf['fn']} (**missed**) |",
        f"| **gold: safe** | {conf['fp']} (over-flag) | {conf['tn']} (correct pass) |",
        "",
    ]

    lines += _clean_gate_section(result)
    lines.append("")

    fns = result["false_negatives"]
    lines += ["## Missed overpromises (false negatives)", ""]
    if fns:
        lines.append(
            "Each row is a draft the gold set labels as an unsupported claim that "
            "the grader passed. These are the dangerous misses."
        )
        lines += _table(
            fns,
            ("gold_id", "claim type", "difficulty"),
            ("gold_id", "claim_or_safe_code", "difficulty"),
        )
    else:
        lines.append("None — the grader caught every known overpromise on this set.")
    lines.append("")

    fps = result["false_positives"]
    lines += ["## Over-flags (false positives)", ""]
    if fps:
        lines.append(
            "Safe drafts the grader flagged. These erode precision and, in a "
            "tuning loop, send the team chasing phantom failures."
        )
        lines += _table(
            fps,
            ("gold_id", "safe pattern", "difficulty"),
            ("gold_id", "claim_or_safe_code", "difficulty"),
        )
    else:
        lines.append("None — the grader left every known-safe draft alone.")
    lines.append("")

    lines += ["## By difficulty", "", "| slice | n | recall | precision | specificity |", "| --- | --- | --- | --- | --- |"]
    for slice_name, payload in result["by_difficulty"].items():
        sm = payload["metrics"]
        sc = payload["confusion"]
        lines.append(
            f"| {slice_name} | {sc['n']} | {_pct(sm['recall'])} | "
            f"{_pct(sm['precision'])} | {_pct(sm['specificity'])} |"
        )
    lines += [
        "",
        "_Hard = paraphrased / cross-sentence drafts that defeat lexical matching. "
        "Recall on the hard slice is where false negatives hide._",
        "",
        "## Caveats",
        "",
    ]
    lines += [f"- {c}" for c in result["caveats"]]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True, help="scorer result JSON")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.result.exists():
        raise SystemExit(
            f"result JSON not found: {args.result}\n"
            "  Hint: run scripts/score_grader_gold.py first."
        )
    result = json.loads(args.result.read_text())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(result) + "\n")
    print(f"OK: wrote grader-reliability report -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
