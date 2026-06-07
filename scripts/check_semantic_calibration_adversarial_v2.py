"""Validate the credential-free grader-calibration fixtures for the 4 M7 over-flags.

Two checks, both credential-free and model-free:

1. **Coverage** — the calibration dataset must cover *exactly* the 4
   ``grader_calibration_review`` findings in the M7 adjudication (no more, no
   fewer; the ``needs_human_review`` finding must be absent). Every record must
   declare ``expected_semantic_claim: false``.

2. **Replay (optional)** — given the report from
   ``run_eval.py --semantic-decisions`` over the calibration dataset, assert the
   offline ``unsupported_claim_semantic`` lane is present and CLEARED every
   calibration case (zero ``UNSAFE_CUSTOMER_COMMS``). That proves the safe/hedged
   cases are representable as non-claims in the offline lane.

Exits non-zero on any mismatch. Reads no raw candidate report, decision file, or
trace, and makes no model/LLM call.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = REPO_ROOT / "case_studies" / "financial_links_reliability" / "evals"
DEFAULT_ADJUDICATION = (
    REPO_ROOT / "reports" / "llm_adversarial_v2_semantic_adjudication.json"
)
DEFAULT_DATASET = EVALS_DIR / "calibration_semantic_adversarial_v2.jsonl"

GRADER_CALIBRATION_REVIEW = "grader_calibration_review"
SEMANTIC_GRADER = "unsupported_claim_semantic"
SEMANTIC_FAILURE_LABEL = "UNSAFE_CUSTOMER_COMMS"


def _adjudication_pairs(path: Path) -> set[tuple[str, str]]:
    payload = json.loads(path.read_text())
    return {
        (str(f["case_id"]), str(f["profile"]))
        for f in payload.get("findings", [])
        if f.get("adjudication_status") == GRADER_CALIBRATION_REVIEW
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def check_coverage(*, adjudication: Path, dataset: Path) -> list[dict[str, Any]]:
    if not adjudication.exists():
        raise SystemExit(f"adjudication not found: {adjudication}")
    if not dataset.exists():
        raise SystemExit(
            f"calibration dataset not found: {dataset}\n"
            "  Hint: run `make calibration-seed-adversarial-v2-semantic` first."
        )
    expected = _adjudication_pairs(adjudication)
    records = _load_jsonl(dataset)
    got = {
        (str(r.get("source_case_id")), str(r.get("source_agent_system_version")))
        for r in records
    }
    if got != expected:
        raise SystemExit(
            "calibration coverage mismatch vs adjudication grader_calibration_review:\n"
            f"  missing from fixtures: {sorted(expected - got)}\n"
            f"  unexpected in fixtures: {sorted(got - expected)}"
        )
    for r in records:
        if r.get("expected_semantic_claim") is not False:
            raise SystemExit(
                f"{r.get('case_id')}: calibration record must set "
                f"expected_semantic_claim=false"
            )
        if r.get("adjudication_status") != GRADER_CALIBRATION_REVIEW:
            raise SystemExit(
                f"{r.get('case_id')}: calibration record must be "
                f"adjudication_status={GRADER_CALIBRATION_REVIEW!r}"
            )
    return records


def check_replay(*, dataset: Path, replay_report: Path) -> None:
    """Assert the offline semantic lane cleared every calibration case."""

    if not replay_report.exists():
        raise SystemExit(f"replay report not found: {replay_report}")
    report = json.loads(replay_report.read_text())

    grader_names = [
        str(rate["name"]) for rate in report.get("aggregate_grader_pass_rates", [])
    ]
    if SEMANTIC_GRADER not in grader_names:
        raise SystemExit(
            f"{replay_report}: the {SEMANTIC_GRADER!r} lane is absent — the "
            "replay must run run_eval with --semantic-decisions so the offline "
            "semantic grader is exercised (fail closed)."
        )
    idx = grader_names.index(SEMANTIC_GRADER)

    dataset_case_ids = {str(r["case_id"]) for r in _load_jsonl(dataset)}
    seen: set[str] = set()
    flagged: list[str] = []
    for case in report.get("per_case", []):
        case_id = str(case.get("case_id"))
        if case_id not in dataset_case_ids:
            continue
        seen.add(case_id)
        results = case.get("grader_results", [])
        if len(results) != len(grader_names):
            raise SystemExit(
                f"{case_id}: grader_results count {len(results)} != grader-name "
                f"count {len(grader_names)}"
            )
        result = results[idx]
        if not result.get("passed") or result.get("failure_label") == SEMANTIC_FAILURE_LABEL:
            flagged.append(case_id)

    missing = dataset_case_ids - seen
    if missing:
        raise SystemExit(
            f"{replay_report}: calibration cases missing from the report: "
            f"{sorted(missing)}"
        )
    if flagged:
        raise SystemExit(
            "calibration replay FAILED: the offline semantic grader still flagged "
            f"these supposed-safe cases as {SEMANTIC_FAILURE_LABEL}: {sorted(flagged)}.\n"
            "  A grader-calibration fixture must clear (non-claim) every case."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the grader-calibration fixtures cover exactly the 4 "
            "grader_calibration_review findings and (optionally) that the offline "
            "semantic lane clears them. Credential-free; no model call."
        )
    )
    parser.add_argument("--adjudication", type=Path, default=DEFAULT_ADJUDICATION)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--replay-report",
        type=Path,
        default=None,
        help=(
            "Optional run_eval --semantic-decisions report over the calibration "
            "dataset. When supplied, asserts the semantic lane cleared every case."
        ),
    )
    args = parser.parse_args(argv)

    records = check_coverage(adjudication=args.adjudication, dataset=args.dataset)
    msg = f"OK: calibration fixtures cover exactly {len(records)} grader_calibration_review finding(s)"
    if args.replay_report is not None:
        check_replay(dataset=args.dataset, replay_report=args.replay_report)
        msg += "; offline semantic lane CLEARED all of them (non-claim)"
    print(msg + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
