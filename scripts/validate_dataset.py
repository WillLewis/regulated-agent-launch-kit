"""Synthetic-dataset structural validator.

This is intentionally **not** an eval runner. It performs deterministic,
credential-free shape checks on a hand-authored JSONL case file:

- required top-level fields present;
- `workflow == financial_links_reliability` (this script is currently
  Financial-Links-only — other workflows can be added later);
- `risk_band` is one of the values declared by ``app.schemas.RiskBand``;
- every ID in ``required_policy_ids`` resolves against the policy fixture
  at ``case_studies/financial_links_reliability/policies/connectivity_policies.yaml``;
- every name in ``required_tools`` resolves against a callable in
  ``app.tools.synthetic_connectivity_tools``.

It exits with a non-zero status and prints a clear, line-numbered error
report when invalid; it prints a single success summary otherwise.

This script is meant to be runnable in a clean checkout with no external
credentials and no network calls.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.schemas import RiskBand, Workflow  # noqa: E402
from app.tools import synthetic_connectivity_tools  # noqa: E402


POLICY_FIXTURE = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "policies"
    / "connectivity_policies.yaml"
)

REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "case_id",
    "dataset_id",
    "workflow",
    "risk_band",
    "case_type",
    "consent_sensitive",
    "synthetic_facts",
    "expected_route",
    "required_tools",
    "required_policy_ids",
    "expected_approval",
    "expected_behavior",
    "prohibited_behavior",
)

ALLOWED_RISK_BANDS: frozenset[str] = frozenset(band.value for band in RiskBand)
EXPECTED_WORKFLOW = Workflow.FINANCIAL_LINKS_RELIABILITY.value


def _known_policy_ids() -> set[str]:
    data = yaml.safe_load(POLICY_FIXTURE.read_text())
    return {policy["id"] for policy in data.get("policies", [])}


def _known_tool_names() -> set[str]:
    return {
        name
        for name, obj in inspect.getmembers(synthetic_connectivity_tools)
        if inspect.isfunction(obj) and not name.startswith("_")
    }


def _validate_case(
    case: dict[str, Any],
    line_no: int,
    known_policies: set[str],
    known_tools: set[str],
) -> list[str]:
    errors: list[str] = []
    prefix = f"line {line_no}"
    case_id = case.get("case_id", "<unknown>")

    missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in case]
    if missing:
        errors.append(f"{prefix} ({case_id}): missing required fields: {missing}")
        return errors

    if case["workflow"] != EXPECTED_WORKFLOW:
        errors.append(
            f"{prefix} ({case_id}): workflow must be {EXPECTED_WORKFLOW!r}, "
            f"got {case['workflow']!r}"
        )

    if case["risk_band"] not in ALLOWED_RISK_BANDS:
        errors.append(
            f"{prefix} ({case_id}): risk_band {case['risk_band']!r} "
            f"not in {sorted(ALLOWED_RISK_BANDS)}"
        )

    if not isinstance(case["consent_sensitive"], bool):
        errors.append(
            f"{prefix} ({case_id}): consent_sensitive must be bool, "
            f"got {type(case['consent_sensitive']).__name__}"
        )

    policy_ids = case.get("required_policy_ids", [])
    if not isinstance(policy_ids, list):
        errors.append(f"{prefix} ({case_id}): required_policy_ids must be a list")
    else:
        unknown = sorted(set(policy_ids) - known_policies)
        if unknown:
            errors.append(
                f"{prefix} ({case_id}): unknown policy IDs {unknown}; "
                f"known IDs: {sorted(known_policies)}"
            )

    tools = case.get("required_tools", [])
    if not isinstance(tools, list):
        errors.append(f"{prefix} ({case_id}): required_tools must be a list")
    else:
        unknown_tools = sorted(set(tools) - known_tools)
        if unknown_tools:
            errors.append(
                f"{prefix} ({case_id}): unknown tools {unknown_tools}; "
                f"available tools: {sorted(known_tools)}"
            )

    approval = case.get("expected_approval")
    if not isinstance(approval, dict) or "required" not in approval:
        errors.append(
            f"{prefix} ({case_id}): expected_approval must be a dict with a "
            f"'required' bool key"
        )

    return errors


def _iter_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append((line_no, json.loads(raw)))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"line {line_no}: invalid JSON ({exc})")
    return records


def validate(path: Path) -> list[str]:
    if not path.exists():
        return [f"dataset path does not exist: {path}"]

    if not POLICY_FIXTURE.exists():
        return [f"policy fixture missing: {POLICY_FIXTURE}"]

    known_policies = _known_policy_ids()
    known_tools = _known_tool_names()

    errors: list[str] = []
    seen_ids: set[str] = set()
    records = _iter_jsonl(path)
    if not records:
        return [f"{path}: dataset is empty"]

    for line_no, case in records:
        case_errors = _validate_case(case, line_no, known_policies, known_tools)
        errors.extend(case_errors)
        cid = case.get("case_id")
        if cid in seen_ids:
            errors.append(f"line {line_no}: duplicate case_id {cid!r}")
        elif isinstance(cid, str):
            seen_ids.add(cid)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a synthetic Financial Links JSONL dataset."
    )
    parser.add_argument("dataset", type=Path, help="Path to the JSONL dataset.")
    args = parser.parse_args(argv)

    errors = validate(args.dataset)
    if errors:
        print(f"INVALID: {args.dataset}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    record_count = len(_iter_jsonl(args.dataset))
    print(f"OK: {args.dataset} ({record_count} synthetic cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
