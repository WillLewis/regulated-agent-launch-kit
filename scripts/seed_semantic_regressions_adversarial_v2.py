"""Seed synthetic regression records from the adversarial v2 model/NLI audit.

Mirrors ``scripts/seed_semantic_regressions_adversarial_v1.py`` for the broader
24-case adversarial v2 slice. The credentialed M7 run's model/NLI semantic audit
flagged 14 customer-facing drafts as ``UNSAFE_CUSTOMER_COMMS`` that the lexical
``unsupported_claim`` grader cleared — a *lexical blind spot*. This script pins
each of those **semantic-only** failures as a ``pending_review`` regression seed.

Inputs — all on-disk, credential-free, no model call:

- the public-safe v2 semantic audit summary JSON (the authoritative source of
  which ``(case_id, profile)`` pairs were semantic-only flags);
- the adversarial v2 dataset (for the replayable case-superset fields).

The genuinely-generic ``semantic_only_pairs`` extractor is reused from the v1
seeder so the seed/check stay linked to the same public-summary contract. No raw
model draft text, rationale, evidence spans, or raw trace paths are read or
emitted — only synthetic case-superset fields and public summary linkage.
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
    semantic_only_pairs,
)

REGRESSION_DATASET_ID = "financial_links_regressions_semantic_adversarial_v2"
SEMANTIC_GRADER = "unsupported_claim_semantic"
SEMANTIC_FAILURE_LABEL = "UNSAFE_CUSTOMER_COMMS"
REGRESSION_SUFFIX = "semantic_regression_v2"

DEFAULT_SUMMARY = (
    REPO_ROOT / "reports" / "llm_adversarial_v2_semantic_audit_summary.json"
)
DEFAULT_DATASET = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v2.jsonl"
)
DEFAULT_OUT = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "regressions_semantic_adversarial_v2.jsonl"
)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(
            f"{label} not found: {path}\n"
            "  Hint: this seeder reads on-disk artifacts only; generate the v2 "
            "semantic audit summary first with "
            "`make semantic-audit-summary-adversarial-v2-llm` (on-disk, no creds)."
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected a JSON object")
    return data


def _load_dataset(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"dataset not found: {path}")
    cases: dict[str, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: line {line_no}: invalid JSON ({exc})")
        cases[str(record.get("case_id", ""))] = record
    return cases


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_record(
    *,
    case_id: str,
    profile: str,
    risk_band_at_audit: str,
    source_case: dict[str, Any],
    dataset_path: str,
    summary_path: str,
) -> dict[str, Any]:
    regression_case_id = f"{case_id}__{profile}__{REGRESSION_SUFFIX}"
    return {
        # Replayable case-superset (copied from the synthetic source case so the
        # file passes scripts/validate_dataset.py and the semantic-decision
        # replay can consume it directly).
        "case_id": regression_case_id,
        "dataset_id": REGRESSION_DATASET_ID,
        "workflow": source_case["workflow"],
        "risk_band": source_case["risk_band"],
        "case_type": f"semantic_regression__{source_case.get('case_type', 'unknown')}",
        "consent_sensitive": bool(source_case.get("consent_sensitive", False)),
        "synthetic_facts": dict(source_case.get("synthetic_facts", {})),
        "expected_route": source_case.get("expected_route", {}),
        "required_tools": list(source_case.get("required_tools", [])),
        "required_policy_ids": list(source_case.get("required_policy_ids", [])),
        "expected_approval": source_case.get("expected_approval", {}),
        "expected_behavior": list(source_case.get("expected_behavior", [])),
        "prohibited_behavior": list(source_case.get("prohibited_behavior", [])),
        "category_tags": list(source_case.get("category_tags", [])),
        "synthetic": True,
        # Semantic-regression provenance (linked to the PUBLIC summary only).
        "regression_case_id": regression_case_id,
        "source_case_id": case_id,
        "source_agent_system_version": profile,
        "source_dataset_path": dataset_path,
        "detected_by": "model_nli_semantic_audit",
        "grader": SEMANTIC_GRADER,
        "failure_labels": [SEMANTIC_FAILURE_LABEL],
        "source_semantic_audit_summary": summary_path,
        "risk_band_at_audit": risk_band_at_audit,
        "replayable_deterministically": False,
        "review_status": "pending_review",
        "notes": (
            f"Pinned from the adversarial v2 model/NLI semantic audit (M7 "
            f"credentialed run): profile {profile} produced a draft on {case_id} "
            f"that the model/NLI unsupported-claim grader flagged as "
            f"{SEMANTIC_FAILURE_LABEL} while the lexical unsupported_claim grader "
            "cleared it (a lexical blind spot). Replay requires a semantic-decision "
            "fixture or a fresh model/NLI audit input; the on-disk check verifies "
            "shape + linkage to the public semantic audit summary rather than "
            "re-running any model. Synthetic; no raw draft text is stored."
        ),
    }


def seed(
    *,
    summary_path: Path,
    dataset_path: Path,
    out: Path,
) -> list[dict[str, Any]]:
    summary = _load_json(summary_path, "semantic audit summary")
    cases = _load_dataset(dataset_path)
    pairs = semantic_only_pairs(summary)
    if not pairs:
        raise SystemExit(
            f"{summary_path}: no semantic-only flags found in the audit summary; "
            "nothing to seed."
        )

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    summary_path_str = _relative(summary_path)
    dataset_path_str = _relative(dataset_path)
    for case_id, profile, risk_band in pairs:
        source_case = cases.get(case_id)
        if source_case is None:
            raise SystemExit(
                f"case_id {case_id!r} from the audit summary is not in the "
                f"source dataset {dataset_path}"
            )
        record = build_record(
            case_id=case_id,
            profile=profile,
            risk_band_at_audit=risk_band,
            source_case=source_case,
            dataset_path=dataset_path_str,
            summary_path=summary_path_str,
        )
        if record["regression_case_id"] in seen_ids:
            raise SystemExit(
                f"duplicate regression_case_id {record['regression_case_id']!r}"
            )
        seen_ids.add(record["regression_case_id"])
        records.append(record)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(rec) for rec in records) + "\n")
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed pending_review regression records from the adversarial v2 "
            "model/NLI semantic audit summary. On-disk only; no model call."
        )
    )
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    records = seed(summary_path=args.summary, dataset_path=args.dataset, out=args.out)
    print(
        f"OK: wrote {len(records)} pending_review semantic regression seed(s) -> "
        f"{args.out} (linked to {_relative(args.summary)}; no model call)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
