"""Convert a failing eval-report case into a synthetic regression record.

The output JSONL line is a *superset* of a regular case record: it
preserves the case schema that ``scripts/run_eval.py`` consumes (so the
regression file can be replayed against any agent profile) and adds
provenance fields — source case, source agent-system version, source
report, captured failure labels, the original trace path, and an
explicit ``review_status``.

Workflow:

- Load an eval report JSON produced by ``scripts/run_eval.py``.
- Find the per-case result by ``--case-id``.
- Refuse if that case has no failure labels (you don't seed regressions
  from passing cases).
- Look up the original case definition in the source dataset (defaults
  to the report's recorded ``dataset_path`` but can be overridden).
- Emit one JSONL line to ``--out``. ``--append`` adds to an existing
  file and skips records whose ``regression_case_id`` is already
  present (deterministic dedup); the default writes a single-line
  file fresh.

No external credentials are required.
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


VALID_REVIEW_STATUSES: tuple[str, ...] = ("pending_review", "approved", "rejected")
REGRESSION_DATASET_ID = "financial_links_regressions_v0"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"file not found: {path}")
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}: line {line_no}: invalid JSON ({exc})")
    return records


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"eval report not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: report must be a JSON object")
    for key in ("agent_system_version", "dataset_path", "per_case"):
        if key not in data:
            raise SystemExit(f"{path}: report missing required field {key!r}")
    return data


def build_regression_record(
    report: dict[str, Any],
    case_id: str,
    source_case: dict[str, Any],
    review_status: str,
    report_path: Path,
) -> dict[str, Any]:
    """Build a single regression-record dict from a failing report case."""

    per_case = next((c for c in report["per_case"] if c.get("case_id") == case_id), None)
    if per_case is None:
        raise SystemExit(f"case_id {case_id!r} not found in report")
    if not per_case.get("failure_labels"):
        raise SystemExit(
            f"case {case_id!r} has no failure_labels in the report — "
            "incident-to-regression only seeds from failing cases"
        )
    if source_case.get("case_id") != case_id:
        raise SystemExit(
            f"source_case.case_id {source_case.get('case_id')!r} does not match "
            f"--case-id {case_id!r}"
        )

    regression_case_id = f"{case_id}__regression_v0"
    notes = (
        f"Pinned from {report['agent_system_version']} failure on {case_id}. "
        f"Failure labels at capture: {sorted(per_case['failure_labels'])}."
    )

    record: dict[str, Any] = {
        # Case fields (kept compatible with scripts/run_eval.py so the
        # regression file is directly replayable).
        "case_id": regression_case_id,
        "dataset_id": REGRESSION_DATASET_ID,
        "workflow": source_case["workflow"],
        "risk_band": source_case["risk_band"],
        "case_type": f"regression__{source_case.get('case_type', 'unknown')}",
        "consent_sensitive": bool(source_case.get("consent_sensitive", False)),
        "synthetic_facts": dict(source_case.get("synthetic_facts", {})),
        "expected_route": source_case.get("expected_route", {}),
        "required_tools": list(source_case.get("required_tools", [])),
        "required_policy_ids": list(source_case.get("required_policy_ids", [])),
        "expected_approval": source_case.get("expected_approval", {}),
        "expected_behavior": list(source_case.get("expected_behavior", [])),
        "prohibited_behavior": list(source_case.get("prohibited_behavior", [])),
        "synthetic": True,
        # Regression-specific provenance.
        "regression_case_id": regression_case_id,
        "source_case_id": case_id,
        "source_agent_system_version": report["agent_system_version"],
        "source_dataset_path": report["dataset_path"],
        "source_report_path": str(report_path),
        "created_from_report": str(report_path),
        "failure_labels": list(per_case["failure_labels"]),
        "trace_path": per_case.get("trace_path"),
        "review_status": review_status,
        "notes": notes,
    }
    return record


def write_record(out_path: Path, record: dict[str, Any], *, append: bool) -> str:
    """Write the record. Returns ``"wrote"`` or ``"skipped_duplicate"``."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record)

    if append and out_path.exists():
        existing = _load_jsonl(out_path)
        existing_ids = {r.get("regression_case_id") for r in existing}
        if record["regression_case_id"] in existing_ids:
            return "skipped_duplicate"
        with out_path.open("a") as f:
            f.write(line + "\n")
        return "wrote"

    out_path.write_text(line + "\n")
    return "wrote"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed a synthetic regression record from a failing case in a "
            "local eval report."
        )
    )
    parser.add_argument("--eval-report", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--review-status",
        default="pending_review",
        choices=VALID_REVIEW_STATUSES,
        help="Default 'pending_review'.",
    )
    parser.add_argument(
        "--source-dataset",
        type=Path,
        default=None,
        help=(
            "Path to the source JSONL dataset for the original case. "
            "Defaults to the report's 'dataset_path' field."
        ),
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "Append to --out, deduping by regression_case_id. Without "
            "this flag the file is overwritten with a single record."
        ),
    )
    args = parser.parse_args(argv)

    report = _load_report(args.eval_report)
    source_dataset = args.source_dataset or Path(report["dataset_path"])
    source_cases = _load_jsonl(source_dataset)
    source_case = next(
        (c for c in source_cases if c.get("case_id") == args.case_id), None
    )
    if source_case is None:
        raise SystemExit(
            f"case_id {args.case_id!r} not found in source dataset {source_dataset}"
        )

    record = build_regression_record(
        report=report,
        case_id=args.case_id,
        source_case=source_case,
        review_status=args.review_status,
        report_path=args.eval_report,
    )
    outcome = write_record(args.out, record, append=args.append)
    if outcome == "skipped_duplicate":
        print(
            f"SKIP: regression_case_id {record['regression_case_id']!r} already "
            f"present in {args.out}"
        )
    else:
        print(
            f"OK: wrote regression {record['regression_case_id']!r} "
            f"(labels={record['failure_labels']}, review_status="
            f"{record['review_status']!r}) -> {args.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
