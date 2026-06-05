"""Validate the adversarial v1 semantic regression seeds — on disk, no model.

These regression seeds pin model/NLI **semantic-only** UNSAFE_CUSTOMER_COMMS
failures. The failure mode is not reproducible by the deterministic eval runner
(the lexical grader cleared every draft), so this check does **not** replay them
through ``scripts/run_eval.py`` and never calls a model. Instead it asserts:

1. structural integrity (one record per semantic-only flag, unique IDs,
   replayable case-superset shape, ``pending_review``, semantic grader +
   UNSAFE_CUSTOMER_COMMS label, ``replayable_deterministically == False``);
2. **linkage** — the ``(source_case_id, source_agent_system_version)`` pairs in
   the seed file exactly match the semantic-only flags recorded in the public
   semantic audit summary (so seeds can't drift from the audit they cite);
3. **public safety** — no raw trace path, no model-decision rationale/evidence
   keys, no readiness overclaim.

Credential-free and deterministic.
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

from scripts.seed_semantic_regressions_adversarial_v1 import (  # noqa: E402
    DEFAULT_OUT,
    DEFAULT_SUMMARY,
    SEMANTIC_FAILURE_LABEL,
    SEMANTIC_GRADER,
    semantic_only_pairs,
)

# Tracked artifacts must never embed raw model output or raw trace locations.
FORBIDDEN_SUBSTRINGS: tuple[str, ...] = ("traces/local/llm_",)
FORBIDDEN_KEYS: tuple[str, ...] = ("rationale", "evidence_spans")
REQUIRED_CASE_FIELDS: frozenset[str] = frozenset(
    {
        "case_id",
        "dataset_id",
        "workflow",
        "risk_band",
        "consent_sensitive",
        "synthetic_facts",
        "expected_route",
        "required_tools",
        "required_policy_ids",
        "expected_approval",
        "expected_behavior",
        "prohibited_behavior",
        "synthetic",
    }
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _iter_keys(value: Any) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _iter_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def check(regressions_path: Path, summary_path: Path) -> list[str]:
    """Return a list of human-readable problems; empty means the seeds pass."""

    errors: list[str] = []
    if not regressions_path.exists():
        return [f"semantic regression file not found: {regressions_path}"]
    if not summary_path.exists():
        return [f"semantic audit summary not found: {summary_path}"]

    records = _load_jsonl(regressions_path)
    summary = json.loads(summary_path.read_text())

    # Linkage: seeds vs. the audit summary's semantic-only flags.
    expected_pairs = {
        (case_id, profile) for case_id, profile, _ in semantic_only_pairs(summary)
    }
    seed_pairs = {
        (str(r.get("source_case_id")), str(r.get("source_agent_system_version")))
        for r in records
    }
    if seed_pairs != expected_pairs:
        errors.append(
            "seed (source_case_id, profile) pairs do not match the audit "
            f"summary semantic-only flags: extra={sorted(seed_pairs - expected_pairs)}, "
            f"missing={sorted(expected_pairs - seed_pairs)}"
        )
    if len(records) != len(expected_pairs):
        errors.append(
            f"expected {len(expected_pairs)} record(s) (one per semantic-only "
            f"flag); got {len(records)}"
        )

    seen_ids: set[str] = set()
    for record in records:
        rid = record.get("regression_case_id", "<unknown>")
        if rid in seen_ids:
            errors.append(f"duplicate regression_case_id {rid!r}")
        seen_ids.add(rid)

        missing = REQUIRED_CASE_FIELDS - set(record)
        if missing:
            errors.append(f"{rid}: missing replayable case fields {sorted(missing)}")
        if record.get("workflow") != "financial_links_reliability":
            errors.append(f"{rid}: workflow must be financial_links_reliability")
        if record.get("synthetic") is not True:
            errors.append(f"{rid}: synthetic must be True")
        if record.get("review_status") != "pending_review":
            errors.append(
                f"{rid}: review_status must be 'pending_review' (untriaged seed)"
            )
        if record.get("grader") != SEMANTIC_GRADER:
            errors.append(f"{rid}: grader must be {SEMANTIC_GRADER!r}")
        if SEMANTIC_FAILURE_LABEL not in record.get("failure_labels", []):
            errors.append(f"{rid}: failure_labels must include {SEMANTIC_FAILURE_LABEL}")
        if record.get("replayable_deterministically") is not False:
            errors.append(
                f"{rid}: replayable_deterministically must be False — the failure "
                "is only detectable by the model/NLI semantic grader"
            )
        if "source_semantic_audit_summary" not in record:
            errors.append(f"{rid}: missing source_semantic_audit_summary linkage")
        if "trace_path" in record:
            errors.append(
                f"{rid}: must not carry a trace_path (raw trace paths are not "
                "shipped in tracked artifacts)"
            )
        for key in _iter_keys(record):
            if key in FORBIDDEN_KEYS:
                errors.append(
                    f"{rid}: must not embed model-decision key {key!r} "
                    "(raw rationale/evidence spans stay gitignored)"
                )

    blob = regressions_path.read_text()
    for needle in FORBIDDEN_SUBSTRINGS:
        if needle in blob:
            errors.append(f"file contains forbidden substring {needle!r}")

    return errors


def check_replay_report(regressions_path: Path, report_path: Path) -> list[str]:
    """Verify a credential-free replay report fired the semantic grader.

    Asserts that the offline ``unsupported_claim_semantic`` grader produced an
    ``UNSAFE_CUSTOMER_COMMS`` failure for **every** seeded case in the produced
    eval report (one per regression seed). This is the proof that the seeds
    replay — without any model call — through ``run_eval.py --semantic-decisions``.
    """

    errors: list[str] = []
    if not report_path.exists():
        return [f"replay report not found: {report_path}"]
    report = json.loads(report_path.read_text())

    names = [r.get("name") for r in report.get("aggregate_grader_pass_rates", [])]
    if SEMANTIC_GRADER not in names:
        return [
            f"replay report has no {SEMANTIC_GRADER!r} grader; run "
            "scripts/run_eval.py with --semantic-decisions <fixture>"
        ]
    idx = names.index(SEMANTIC_GRADER)

    seed_ids = {r["regression_case_id"] for r in _load_jsonl(regressions_path)}
    report_cases = {c.get("case_id"): c for c in report.get("per_case", [])}
    for case_id in sorted(seed_ids):
        case = report_cases.get(case_id)
        if case is None:
            errors.append(f"{case_id}: not present in replay report")
            continue
        results = case.get("grader_results", [])
        if idx >= len(results):
            errors.append(f"{case_id}: no {SEMANTIC_GRADER} result in report")
            continue
        result = results[idx]
        if result.get("passed"):
            errors.append(
                f"{case_id}: {SEMANTIC_GRADER} did not fire (passed=True); "
                f"expected a {SEMANTIC_FAILURE_LABEL} failure"
            )
        if result.get("failure_label") != SEMANTIC_FAILURE_LABEL:
            errors.append(
                f"{case_id}: {SEMANTIC_GRADER} failure_label="
                f"{result.get('failure_label')!r}; expected {SEMANTIC_FAILURE_LABEL}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the adversarial v1 semantic regression seeds and verify "
            "their linkage to the public semantic audit summary. With "
            "--replay-report, also verify the semantic grader fired on every "
            "seed in a credential-free replay report. No model call."
        )
    )
    parser.add_argument("--regressions", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--replay-report",
        type=Path,
        default=None,
        help=(
            "Optional path to a report produced by `run_eval.py "
            "--semantic-decisions <fixture>` on the regression slice. When "
            "given, assert the semantic grader fired UNSAFE_CUSTOMER_COMMS on "
            "every seed."
        ),
    )
    args = parser.parse_args(argv)

    errors = check(args.regressions, args.summary)
    if args.replay_report is not None:
        errors += check_replay_report(args.regressions, args.replay_report)
    if errors:
        print(f"INVALID: {args.regressions}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    records = _load_jsonl(args.regressions)
    replay_note = (
        " + semantic grader fired on every seed in the replay report"
        if args.replay_report is not None
        else ""
    )
    print(
        f"OK: {args.regressions} ({len(records)} semantic-only regression seed(s); "
        f"all pending_review; linked to the semantic audit summary{replay_note}; "
        "no model call)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
