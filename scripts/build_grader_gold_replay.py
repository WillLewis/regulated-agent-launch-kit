"""Strip a raw gold-pass decision file into a public-safe verdict fixture.

The raw output of ``scripts/run_grader_gold_pass.py`` embeds model
``rationale`` / ``evidence_spans`` that quote the synthetic drafts, so it stays
gitignored. This script keeps only the audited boolean verdict plus the
aggregate-safe ``confidence`` / ``claim_type`` and drops the draft-bearing
fields, producing a trackable verdict file that ``scripts/score_grader_gold.py``
can consume credential-free.

Public-safe by construction: no rationale, no evidence_spans, no draft text, no
raw trace path. A defense-in-depth assertion enforces this on the emitted file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERDICTS_VERSION = "grader_gold_verdicts_v0"
DRAFT_BEARING_KEYS = ("rationale", "evidence_spans")


def build_replay(raw: dict[str, Any], *, source_label: str) -> dict[str, Any]:
    src = raw.get("verdicts")
    if not isinstance(src, dict) or not src:
        raise SystemExit("raw decision file missing object field 'verdicts'")
    verdicts: dict[str, dict[str, Any]] = {}
    for gold_id, decision in src.items():
        if not isinstance(decision, dict):
            raise SystemExit(f"{gold_id}: decision is not an object")
        verdicts[str(gold_id)] = {
            "makes_unsupported_claim": bool(decision.get("makes_unsupported_claim")),
            "confidence": round(
                min(1.0, max(0.0, float(decision.get("confidence", 0.0) or 0.0))), 4
            ),
            "claim_type": str(decision.get("claim_type", "none")),
        }
    fixture = {
        "version": VERDICTS_VERSION,
        "synthetic": True,
        "source": source_label,
        "grader_adapter": raw.get("grader_adapter", "unknown"),
        "model": raw.get("model", "unknown"),
        "answer_key_withheld": bool(raw.get("answer_key_withheld", False)),
        "note": (
            "Public-safe verdict fixture re-keyed from the gitignored gold-pass "
            "raw decisions. Only the boolean verdict + aggregate confidence are "
            "carried; draft-quoting rationale/evidence_spans are dropped."
        ),
        "verdicts": verdicts,
    }
    _assert_public_safe(fixture)
    return fixture


def _assert_public_safe(fixture: dict[str, Any]) -> None:
    serialized = json.dumps(fixture)
    if "traces/local/" in serialized:
        raise SystemExit("verdict fixture must not reference a raw trace path")
    for gold_id, decision in fixture["verdicts"].items():
        for key in DRAFT_BEARING_KEYS:
            if key in decision:
                raise SystemExit(f"{gold_id}: verdict fixture must drop {key!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True, help="gitignored gold-pass output")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.raw.exists():
        raise SystemExit(
            f"raw decisions not found: {args.raw}\n"
            "  This strips an existing gold-pass file; it does NOT call the grader.\n"
            "  Hint: run `make grader-gold-pass` (credentialed) first."
        )
    raw = json.loads(args.raw.read_text())
    fixture = build_replay(raw, source_label=f"{raw.get('grader_adapter', 'grader')} gold-pass (replayed, public-safe)")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, indent=2) + "\n")
    flagged = sum(1 for d in fixture["verdicts"].values() if d["makes_unsupported_claim"])
    print(
        f"OK: wrote public-safe verdict fixture -> {args.out} "
        f"({len(fixture['verdicts'])} verdicts; {flagged} flagged)\n"
        f"  Next: make grader-reliability-report"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
