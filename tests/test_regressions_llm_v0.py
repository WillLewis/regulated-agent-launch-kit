"""Tests for the pinned LLM-failure regression seed file.

``case_studies/financial_links_reliability/evals/regressions_llm_v0.jsonl``
captures the first real model failures observed against the adversarial
slice when running the opt-in ``llm_candidate_v0`` profile. The four
records pin the failing cases as ``pending_review`` regression seeds.

These tests lock in:

1. The file exists in the canonical location.
2. It contains exactly four records — one per failing adversarial case.
3. Every record is ``pending_review`` (review hasn't happened yet).
4. Every record's provenance is ``llm_candidate_v0`` and carries the
   ``UNSAFE_CUSTOMER_COMMS`` failure label.
5. The set of source case IDs matches the documented LLM failures
   (``case_fl_adv_v0_002`` / ``003`` / ``005`` / ``006``).
6. The file is structurally distinct from the deterministic
   ``regressions_v0.jsonl`` (no shared regression case IDs).
7. Each record carries enough case-superset fields to be replayed
   directly through ``scripts/run_eval.py``.

The tests do NOT call the LLM and do not require ``ANTHROPIC_API_KEY``.
They only read the committed JSONL.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS_LLM = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "regressions_llm_v0.jsonl"
)
REGRESSIONS_DETERMINISTIC = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "regressions_v0.jsonl"
)


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


EXPECTED_SOURCE_CASE_IDS: frozenset[str] = frozenset(
    {
        "case_fl_adv_v0_002",
        "case_fl_adv_v0_003",
        "case_fl_adv_v0_005",
        "case_fl_adv_v0_006",
    }
)


def test_regressions_llm_v0_file_exists() -> None:
    assert REGRESSIONS_LLM.exists(), (
        f"missing pinned LLM-regression seed file: {REGRESSIONS_LLM}"
    )


def test_regressions_llm_v0_has_exactly_four_records() -> None:
    records = _load_jsonl(REGRESSIONS_LLM)
    assert len(records) == 4, (
        "regressions_llm_v0.jsonl must contain exactly 4 pinned LLM failures; "
        f"got {len(records)}"
    )


def test_every_record_is_pending_review() -> None:
    records = _load_jsonl(REGRESSIONS_LLM)
    for record in records:
        assert record["review_status"] == "pending_review", (
            f"{record['regression_case_id']}: review_status is "
            f"{record['review_status']!r}; expected 'pending_review' "
            "(these are the first real LLM failures — they haven't been "
            "triaged yet)"
        )


def test_every_record_provenance_is_llm_candidate_v0() -> None:
    records = _load_jsonl(REGRESSIONS_LLM)
    for record in records:
        assert record["source_agent_system_version"] == "llm_candidate_v0", (
            f"{record['regression_case_id']}: source profile is "
            f"{record['source_agent_system_version']!r}; expected "
            "'llm_candidate_v0'. Deterministic baselines belong in "
            "regressions_v0.jsonl, not the LLM file."
        )


def test_every_record_carries_unsafe_customer_comms_label() -> None:
    records = _load_jsonl(REGRESSIONS_LLM)
    for record in records:
        assert "UNSAFE_CUSTOMER_COMMS" in record["failure_labels"], (
            f"{record['regression_case_id']}: failure_labels lack "
            "UNSAFE_CUSTOMER_COMMS; that's the failure mode the LLM "
            "tripped on this slice."
        )


def test_source_case_ids_match_documented_llm_failures() -> None:
    records = _load_jsonl(REGRESSIONS_LLM)
    seen = {record["source_case_id"] for record in records}
    assert seen == EXPECTED_SOURCE_CASE_IDS, (
        f"source case-id set mismatch: extra={seen - EXPECTED_SOURCE_CASE_IDS}, "
        f"missing={EXPECTED_SOURCE_CASE_IDS - seen}"
    )


def test_llm_regression_records_have_replayable_case_shape() -> None:
    """Each record must be a case-superset so scripts/run_eval.py can
    consume the file directly without special-casing."""

    required = {
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
    records = _load_jsonl(REGRESSIONS_LLM)
    for record in records:
        missing = required - set(record)
        assert not missing, (
            f"{record.get('regression_case_id', '<unknown>')}: regression "
            f"record missing replayable case fields: {sorted(missing)}"
        )
        assert record["workflow"] == "financial_links_reliability"
        assert record["synthetic"] is True


def test_llm_regression_file_is_distinct_from_deterministic() -> None:
    """The two regression files must not share regression_case_ids — they
    pin failures from different source datasets and different agent
    profiles."""

    if not REGRESSIONS_DETERMINISTIC.exists():
        # Deterministic regressions file is optional for this assertion;
        # the LLM file's standalone shape is what matters.
        return

    llm_ids = {r["regression_case_id"] for r in _load_jsonl(REGRESSIONS_LLM)}
    det_ids = {r["regression_case_id"] for r in _load_jsonl(REGRESSIONS_DETERMINISTIC)}
    overlap = llm_ids & det_ids
    assert not overlap, (
        "regressions_llm_v0.jsonl shares regression_case_ids with "
        f"regressions_v0.jsonl: {sorted(overlap)}. These pin different "
        "kinds of failures — keep them disjoint."
    )
