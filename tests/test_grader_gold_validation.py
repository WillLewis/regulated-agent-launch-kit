"""Contract tests for the human-authored semantic-grader gold set.

The gold labels in ``grader_gold.jsonl`` are intentionally independent of the
model/NLI semantic grader. These tests only validate shape and coverage; they
must not call or calibrate the grader being measured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = (
    ROOT / "case_studies" / "financial_links_reliability" / "grader_validation"
)
SCORED_PATH = VALIDATION_DIR / "grader_gold.jsonl"
BORDERLINE_PATH = VALIDATION_DIR / "grader_gold_borderline.jsonl"

BAD_REASON_CODES = {
    "unsupported_operational_status_claim",
    "implied_future_refresh_despite_gate",
    "unsupported_resolution_or_restoration_promise",
    "unsupported_continuity_claim_disabled_scope",
    "unsupported_refresh_timeframe_missing_metadata",
    "unsupported_auto_completion_promise_missing_partner",
}
SAFE_REASON_CODES = {
    "safe_hedged_negation",
    "safe_snapshot_not_live_hedge",
    "flagged_span_is_required_consent_gate",
    "benign_conditional_followup_commitment",
    "safe_degraded_disclosure",
}
KNOWN_OVERFLAG_SAFE_CODES = {
    "flagged_span_is_required_consent_gate",
    "safe_snapshot_not_live_hedge",
    "benign_conditional_followup_commitment",
    "safe_hedged_negation",
}
CONTEXT_ENUMS = {
    "consent_state": {"granted", "expired", "revoked", "insufficient", "unknown"},
    "institution_status": {"active", "deprecated", "rebranded", "unknown"},
    "aggregator_route_status": {"healthy", "degraded", "unavailable", "unknown"},
    "partner_scope": {"enabled", "fallback_permitted", "fallback_blocked", "disabled", None},
}
OBVIOUS_BANNED_PHRASES = {
    "updates instantly",
    "always current",
    "always up to date",
    "guaranteed",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_grader_gold_files_parse() -> None:
    assert len(_load_jsonl(SCORED_PATH)) == 28
    assert len(_load_jsonl(BORDERLINE_PATH)) >= 1


def test_grader_gold_scored_shape_and_context_enums() -> None:
    rows = _load_jsonl(SCORED_PATH)
    expected_ids = [f"gold_fl_{idx:03d}" for idx in range(1, 29)]
    assert [row["gold_id"] for row in rows] == expected_ids

    for row in rows:
        assert row["provenance"] == "human_authored"
        assert isinstance(row["draft_text"], str) and row["draft_text"].strip()
        assert isinstance(row["makes_unsupported_claim"], bool)
        assert row["difficulty"] in {"easy", "hard"}
        assert isinstance(row["category_tags"], list) and row["category_tags"]
        assert row["label_basis"].count(".") == 1
        assert row["label_basis"].endswith(".")
        assert not any(token in row["gold_id"] for token in ("true", "false", "bad", "good"))

        context = row["synthetic_context"]
        assert set(context) == {
            "consent_state",
            "institution_status",
            "aggregator_route_status",
            "partner_scope",
            "missing_ids",
        }
        for field, allowed in CONTEXT_ENUMS.items():
            assert context[field] in allowed
        assert isinstance(context["missing_ids"], list)


def test_grader_gold_is_balanced_and_covers_reason_codes() -> None:
    rows = _load_jsonl(SCORED_PATH)
    bad = [row for row in rows if row["makes_unsupported_claim"] is True]
    safe = [row for row in rows if row["makes_unsupported_claim"] is False]

    assert len(bad) == 14
    assert len(safe) == 14
    assert {row["claim_or_safe_code"] for row in bad} >= BAD_REASON_CODES
    assert {row["claim_or_safe_code"] for row in safe} >= SAFE_REASON_CODES
    assert KNOWN_OVERFLAG_SAFE_CODES <= {row["claim_or_safe_code"] for row in safe}


def test_grader_gold_has_hard_paraphrase_and_cross_sentence_coverage() -> None:
    rows = _load_jsonl(SCORED_PATH)
    hard_bad = [
        row
        for row in rows
        if row["makes_unsupported_claim"] is True and row["difficulty"] == "hard"
    ]
    hard_good = [
        row
        for row in rows
        if row["makes_unsupported_claim"] is False and row["difficulty"] == "hard"
    ]
    hard_bad_without_obvious_phrases = [
        row
        for row in hard_bad
        if not any(
            phrase in row["draft_text"].lower()
            for phrase in OBVIOUS_BANNED_PHRASES
        )
    ]
    cross_sentence_bad = [
        row for row in hard_bad if "cross_sentence" in row["category_tags"]
    ]

    assert len(hard_bad_without_obvious_phrases) >= 4
    assert len(cross_sentence_bad) >= 2
    assert len(hard_good) >= 3


def test_borderline_file_is_documented_but_unscored() -> None:
    rows = _load_jsonl(BORDERLINE_PATH)
    for row in rows:
        assert row["provenance"] == "human_authored"
        assert "makes_unsupported_claim" not in row
        assert isinstance(row["possible_claim_or_safe_codes"], list)
        assert row["borderline_reason"].endswith(".")
        assert row["why_not_scored"].endswith(".")
