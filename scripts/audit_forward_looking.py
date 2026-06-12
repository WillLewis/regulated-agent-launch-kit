"""Public-safe deterministic audit for FL-FORWARD-PROMISE-004.

Reads local trace JSON files, applies ``grade_forward_looking_promise`` to each
trace's final response, and emits counts + case IDs only. The underlying grader
evidence contains draft excerpts for debugging; this script intentionally drops
those fields so its JSON/Markdown outputs can be tracked.
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

from evals.graders import grade_forward_looking_promise  # noqa: E402


AUDIT_VERSION = "forward_looking_audit_v0"
POLICY_ID = "FL-FORWARD-PROMISE-004"
FORBIDDEN_PUBLIC_FIELDS: tuple[str, ...] = (
    "draft_text",
    "draft_excerpt",
    "final_response",
    "evidence_spans",
    "rationale",
    "traces/local/llm_",
)


def _load_trace(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid trace JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: trace must be a JSON object")
    return data


def audit_traces_dir(traces_dir: Path, *, source_label: str | None = None) -> dict[str, Any]:
    """Return a public-safe forward-looking audit over ``traces_dir``."""

    traces_dir = Path(traces_dir)
    if not traces_dir.exists():
        raise SystemExit(f"traces directory not found: {traces_dir}")
    trace_paths = sorted(traces_dir.glob("*.json"))
    if not trace_paths:
        raise SystemExit(f"no trace JSON files found under {traces_dir}")

    violations: list[dict[str, Any]] = []
    cleared_by_negation: list[dict[str, Any]] = []
    for path in trace_paths:
        trace = _load_trace(path)
        case_id = str(trace.get("case_id") or path.stem)
        result = grade_forward_looking_promise(
            {"draft_text": trace.get("final_response") or ""}
        )
        evidence = result.evidence or {}
        matched = sorted(str(p) for p in evidence.get("matched_patterns") or [])
        cleared = sorted(str(p) for p in evidence.get("cleared_by_negation") or [])
        if matched:
            violations.append({"case_id": case_id, "matched_patterns": matched})
        if cleared:
            cleared_by_negation.append({"case_id": case_id, "patterns": cleared})

    audit = {
        "version": AUDIT_VERSION,
        "synthetic": True,
        "policy_id": POLICY_ID,
        "source_label": source_label or traces_dir.name,
        "case_count": len(trace_paths),
        "forward_looking_violations": len(violations),
        "violation_cases": violations,
        "cleared_by_negation": cleared_by_negation,
        "note": (
            "Public-safe deterministic audit of the forward-looking reassurance "
            "ban. Includes only case IDs and matched policy patterns; no draft "
            "prose, model reasoning, quoted spans, or raw trace paths."
        ),
    }
    _assert_public_safe(audit)
    return audit


def _assert_public_safe(value: dict[str, Any] | str) -> None:
    text = value if isinstance(value, str) else json.dumps(value)
    leaked = [needle for needle in FORBIDDEN_PUBLIC_FIELDS if needle in text]
    if leaked:
        raise SystemExit(f"forward-looking audit output leaks public-unsafe fields: {leaked}")


def render_markdown(audit: dict[str, Any]) -> str:
    """Render a public-safe Markdown audit."""

    lines = [
        "# Forward-looking Promise Audit",
        "",
        "> NOT READY FOR PILOT — synthetic deterministic audit only. Counts and "
        "case IDs are public-safe; raw draft text stays local.",
        "",
        f"- **Policy:** `{audit['policy_id']}`",
        f"- **Cases:** {audit['case_count']}",
        f"- **Forward-looking violations:** {audit['forward_looking_violations']}",
        "",
        "## Violations",
        "",
    ]
    violations = audit.get("violation_cases") or []
    if violations:
        lines += [
            "| Case | Matched policy patterns |",
            "| --- | --- |",
        ]
        for entry in violations:
            patterns = ", ".join(f"`{p}`" for p in entry["matched_patterns"])
            lines.append(f"| `{entry['case_id']}` | {patterns} |")
    else:
        lines.append("None.")

    cleared = audit.get("cleared_by_negation") or []
    lines += ["", "## Same-sentence Negation Clears", ""]
    if cleared:
        lines += ["| Case | Cleared patterns |", "| --- | --- |"]
        for entry in cleared:
            patterns = ", ".join(f"`{p}`" for p in entry["patterns"])
            lines.append(f"| `{entry['case_id']}` | {patterns} |")
    else:
        lines.append("None.")

    lines += [
        "",
        "_This audit strips draft excerpts and model evidence. A clean result is one "
        "input to M7 candidate-side evidence; it is not pilot readiness._",
        "",
    ]
    md = "\n".join(lines)
    _assert_public_safe(md)
    return md


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--source-label", default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    args = parser.parse_args(argv)

    audit = audit_traces_dir(args.traces, source_label=args.source_label)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(audit, indent=2) + "\n")
    if args.out_md is not None:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(audit))

    print(
        f"forward_looking_violations {audit['forward_looking_violations']} "
        f"{audit['violation_cases']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
