"""CLI: score a semantic-grader verdict file against the human-authored gold set.

Credential-free and pure on-disk: this NEVER calls the grader it measures. It
consumes a recorded verdict file (from the credentialed gold-pass, its
public-safe replay, or a demo fixture) and emits a reliability result JSON with
the confusion matrix, precision, RECALL, specificity, and per-slice breakdowns.

    uv run python scripts/score_grader_gold.py \
        --gold case_studies/financial_links_reliability/grader_validation/grader_gold.jsonl \
        --verdicts <verdicts.json> \
        --out reports/grader_gold_reliability.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.grader_gold_scorer import load_gold, load_verdicts, score  # noqa: E402

DEFAULT_GOLD = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "grader_validation"
    / "grader_gold.jsonl"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument(
        "--verdicts",
        type=Path,
        required=True,
        help="grader verdict JSON keyed by gold_id (gold-pass / replay / demo).",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--verdicts-source",
        default=None,
        help="provenance label for the report; defaults to the file's 'source'.",
    )
    args = parser.parse_args(argv)

    if not args.gold.exists():
        raise SystemExit(f"gold set not found: {args.gold}")
    if not args.verdicts.exists():
        raise SystemExit(
            f"verdicts file not found: {args.verdicts}\n"
            "  This scorer reads recorded verdicts; it does NOT call the grader.\n"
            "  Hint: run the credentialed gold-pass + replay (make grader-gold-pass\n"
            "  then make grader-gold-replay), or point --verdicts at the demo fixture\n"
            "  tests/fixtures/grader_gold/demo_grader_verdicts.json."
        )

    gold = load_gold(args.gold)
    verdicts = load_verdicts(args.verdicts)
    source = args.verdicts_source
    if source is None:
        try:
            source = json.loads(args.verdicts.read_text()).get("source", args.verdicts.name)
        except (json.JSONDecodeError, AttributeError):
            source = args.verdicts.name

    result = score(gold, verdicts, verdicts_source=str(source))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")

    m = result["metrics"]
    conf = result["confusion"]
    print(
        f"OK: scored {result['scored_count']} gold item(s) -> {args.out}\n"
        f"  confusion tp={conf['tp']} fp={conf['fp']} fn={conf['fn']} tn={conf['tn']}\n"
        f"  recall={m['recall']} (CI95 {m['recall_ci95']})  "
        f"precision={m['precision']}  specificity={m['specificity']}"
    )
    if conf["fn"]:
        missed = ", ".join(f["gold_id"] for f in result["false_negatives"])
        print(f"  MISSED {conf['fn']} known overpromise(s): {missed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
