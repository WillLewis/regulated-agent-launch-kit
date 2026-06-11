"""Credentialed pass: run the model/NLI semantic grader over the gold drafts.

This is the ONE credentialed step in the grader-validation loop (~$0.30–0.60 of
tokens). It is WIRED BUT NOT RUN by default: ``make grader-gold-pass`` gates on
``check-llm-env`` and the raw output path is gitignored. Do not run it without
an explicit decision to spend.

Fairness / independence design
------------------------------
The grader is given the synthetic **operational context** (consent / route /
institution / partner state) it needs to judge whether a claim is supported —
but NOT the gold label and NOT any expected/prohibited-behavior answer key. The
gold ``category_tags`` are also withheld because some of them (e.g.
"paraphrased_overpromise") would leak the label. This measures the grader's
independent discrimination, not its ability to copy an answer key.

The raw output embeds model ``rationale`` / ``evidence_spans`` that quote the
draft, so it stays gitignored. ``scripts/build_grader_gold_replay.py`` strips
those to a public-safe verdict fixture for scoring.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.semantic_model_adapter import (  # noqa: E402
    SEMANTIC_ADAPTER_NAME,
    SemanticAdapterResponse,
    build_semantic_prompt,
    generate_semantic_decision,
)

RAW_FILE_VERSION = "grader_gold_raw_decisions_v0"
DEFAULT_GOLD = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "grader_validation"
    / "grader_gold.jsonl"
)


def _grader_input_record(gold_row: dict[str, Any]) -> dict[str, Any]:
    """Build the answer-key-free record handed to the shared grader prompt.

    Only the neutral synthetic connectivity state (consent / route / institution
    / partner / missing_ids) is carried, under ``synthetic_facts`` where
    ``build_semantic_prompt`` reads it. The gold label, claim_or_safe_code, and
    category tags are withheld. build_semantic_prompt enforces the same firewall,
    so this is defense in depth."""

    return {
        "case_id": gold_row["gold_id"],
        "synthetic_facts": dict(gold_row.get("synthetic_context") or {}),
    }


def run_grader_gold_pass(
    gold_rows: list[dict[str, Any]],
    *,
    decision_fn: Callable[..., SemanticAdapterResponse] = generate_semantic_decision,
    model: str | None = None,
    timeout_s: float = 30.0,
    client: Any | None = None,
) -> dict[str, Any]:
    """Judge each gold draft with the model/NLI grader. ``decision_fn`` is
    injectable so tests can run this with a fake client (no credentials)."""

    verdicts: dict[str, dict[str, Any]] = {}
    total_in = total_out = 0
    total_cost = 0.0
    resolved_model = model or "(unset)"
    for row in gold_rows:
        gold_id = str(row.get("gold_id", ""))
        if not gold_id:
            raise SystemExit("gold row missing gold_id")
        prompt = build_semantic_prompt(_grader_input_record(row), row["draft_text"])
        kwargs: dict[str, Any] = {"model": model, "timeout_s": timeout_s}
        if client is not None:
            kwargs["client"] = client
        response = decision_fn(prompt, **kwargs)
        verdicts[gold_id] = response.decision.model_dump(mode="json")
        total_in += response.input_tokens
        total_out += response.output_tokens
        total_cost += response.est_cost_usd
        resolved_model = response.model

    flagged = sum(1 for d in verdicts.values() if d.get("makes_unsupported_claim"))
    return {
        "version": RAW_FILE_VERSION,
        "synthetic": True,
        "gold_set": "financial_links_reliability_grader_gold",
        "grader_adapter": SEMANTIC_ADAPTER_NAME,
        "model": resolved_model,
        "answer_key_withheld": True,
        "note": (
            "Raw model/NLI verdicts over the gold drafts. Grader given synthetic "
            "operational context only — no gold label, no expected/prohibited "
            "answer key. Embeds draft-quoting rationale/evidence_spans; KEEP "
            "GITIGNORED. Strip to public-safe via build_grader_gold_replay.py."
        ),
        "usage": {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "est_cost_usd": round(total_cost, 4),
        },
        "flagged_count": flagged,
        "verdicts": verdicts,
    }


def _load_gold_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, required=True, help="raw output (gitignored)")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    args = parser.parse_args(argv)

    if not args.gold.exists():
        raise SystemExit(f"gold set not found: {args.gold}")

    output = run_grader_gold_pass(
        _load_gold_rows(args.gold), model=args.model, timeout_s=args.timeout_s
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    usage = output["usage"]
    print(
        f"OK: judged {len(output['verdicts'])} gold draft(s) -> {args.out} "
        f"(GITIGNORED)\n"
        f"  flagged makes_unsupported_claim=true: {output['flagged_count']}\n"
        f"  tokens in/out {usage['input_tokens']}/{usage['output_tokens']} "
        f"| est ${usage['est_cost_usd']}\n"
        f"  Next: make grader-gold-replay  (strip to public-safe verdicts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
