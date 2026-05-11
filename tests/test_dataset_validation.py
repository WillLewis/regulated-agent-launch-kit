"""Dataset validation tests for the Financial Links v0 slice.

These assertions are intentionally narrow: they confirm shape, the
required-mix coverage promised by the dataset card, and that the
validator script rejects malformed input. They do not run the agent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
CARD_PATH = ROOT / "case_studies" / "financial_links_reliability" / "dataset_card.md"
VALIDATOR = ROOT / "scripts" / "validate_dataset.py"


def _load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture(scope="module")
def cases_v0() -> list[dict[str, Any]]:
    return _load(DATA_PATH)


@pytest.fixture(scope="module")
def smoke_cases() -> list[dict[str, Any]]:
    return _load(SMOKE_PATH)


def _run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cases_v0_validates() -> None:
    result = _run_validator(DATA_PATH)
    assert result.returncode == 0, result.stderr


def test_smoke_validates() -> None:
    result = _run_validator(SMOKE_PATH)
    assert result.returncode == 0, result.stderr


def test_cases_v0_size_is_in_range(cases_v0: list[dict[str, Any]]) -> None:
    assert 8 <= len(cases_v0) <= 12, f"v0 should hold 8–12 cases, has {len(cases_v0)}"


def test_case_ids_are_unique(cases_v0: list[dict[str, Any]]) -> None:
    ids = [case["case_id"] for case in cases_v0]
    assert len(ids) == len(set(ids))


def test_smoke_ids_subset_of_full(
    cases_v0: list[dict[str, Any]], smoke_cases: list[dict[str, Any]]
) -> None:
    full_ids = {case["case_id"] for case in cases_v0}
    smoke_ids = {case["case_id"] for case in smoke_cases}
    assert smoke_ids.issubset(full_ids)


def test_required_failure_labels_are_covered(cases_v0: list[dict[str, Any]]) -> None:
    labels = {case["failure_label_if_mishandled"] for case in cases_v0}
    for required in (
        "CONSENT_BOUNDARY_VIOLATION",
        "TOOL_MISUSE",
        "POLICY_MISS",
        "MISSED_ESCALATION",
        "UNSAFE_CUSTOMER_COMMS",
    ):
        assert required in labels, f"v0 is missing a case for {required}"


def test_required_case_types_are_covered(cases_v0: list[dict[str, Any]]) -> None:
    types = {case["case_type"] for case in cases_v0}
    # routine stale-data, consent (expired/revoked/insufficient),
    # partner fallback blocked at L2 and L3, institution unavailable,
    # missing-info payload, adversarial.
    assert "routine_stale_data" in types
    assert any(t.startswith("consent_") or "consent" in t for t in types)
    assert "partner_fallback_blocked" in types
    assert "partner_fallback_blocked_high_risk" in types
    assert any("institution" in t for t in types)
    assert any("missing_info" in t for t in types)
    assert "adversarial_force_completion" in types


def test_dataset_card_has_no_todo_placeholders() -> None:
    card = CARD_PATH.read_text()
    # The card should describe the v0 dataset; leftover scaffolding TODOs are not allowed.
    assert "TODO" not in card, "dataset card still contains TODO placeholders"


def test_validator_fails_on_malformed_dataset(tmp_path: Path) -> None:
    bad = tmp_path / "bad_cases.jsonl"
    # workflow is wrong, risk_band is unknown, required_tools references a missing tool,
    # required_policy_ids references a missing policy. The validator should reject it.
    payload = {
        "case_id": "case_bad_001",
        "dataset_id": "financial_links_reliability_v0",
        "workflow": "not_a_workflow",
        "risk_band": "L9",
        "case_type": "bogus",
        "consent_sensitive": False,
        "synthetic_facts": {},
        "expected_route": {"specialist_agent": "FinancialLinksReliabilityAgent"},
        "required_tools": ["lookup_consent_state", "nonexistent_tool"],
        "required_policy_ids": ["FL-DOES-NOT-EXIST"],
        "expected_approval": {"required": False},
        "expected_behavior": [],
        "prohibited_behavior": [],
    }
    bad.write_text(json.dumps(payload) + "\n")

    result = _run_validator(bad)
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "workflow" in combined
    assert "risk_band" in combined
    assert "nonexistent_tool" in combined or "unknown tools" in combined
    assert "FL-DOES-NOT-EXIST" in combined or "unknown policy" in combined


def test_validator_fails_on_duplicate_case_ids(tmp_path: Path) -> None:
    bad = tmp_path / "dup_cases.jsonl"
    case = {
        "case_id": "case_dup_001",
        "dataset_id": "financial_links_reliability_v0",
        "workflow": "financial_links_reliability",
        "risk_band": "L1",
        "case_type": "routine_stale_data",
        "consent_sensitive": False,
        "synthetic_facts": {"user_id": "user_synth_001"},
        "expected_route": {"specialist_agent": "FinancialLinksReliabilityAgent"},
        "required_tools": ["lookup_consent_state"],
        "required_policy_ids": ["FL-COPY-STALE-003"],
        "expected_approval": {"required": False},
        "expected_behavior": [],
        "prohibited_behavior": [],
    }
    bad.write_text(json.dumps(case) + "\n" + json.dumps(case) + "\n")

    result = _run_validator(bad)
    assert result.returncode != 0
    assert "duplicate" in (result.stderr + result.stdout).lower()
