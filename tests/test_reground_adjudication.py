"""Tests for the M7 re-grounding adjudication (public-safe, credential-free)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_reground_adjudication_adversarial_v2 import (
    ADJUDICATIONS,
    _DRAFT_FRAGMENT_GUARD,
    build_payload,
    render_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
VALID_VERDICTS = {"candidate_actionable", "grader_calibration_review", "needs_human_review"}
EXPECTED_FLAGS = {
    "case_fl_adv_v2_017", "case_fl_adv_v2_006", "case_fl_adv_v2_002",
    "case_fl_adv_v2_005", "case_fl_adv_v2_012", "case_fl_adv_v2_013",
    "case_fl_adv_v2_015", "case_fl_adv_v2_024",
}


def test_covers_every_hardened_gate_flag() -> None:
    assert {a["case_id"] for a in ADJUDICATIONS} == EXPECTED_FLAGS


def test_verdict_vocabulary_and_counts() -> None:
    payload = build_payload()
    for row in payload["adjudications"]:
        assert row["verdict"] in VALID_VERDICTS
        assert row["reason_code"]
        assert row["basis"]
    # Resolved under the 2026-06-11 forward-looking ban: all 8 are actionable.
    assert payload["counts_by_verdict"] == {"candidate_actionable": 8}
    assert all(r["deterministic_ban_confirmed"] for r in payload["adjudications"])


def test_output_is_public_safe_no_draft_fragments() -> None:
    payload = build_payload()
    md = render_markdown(payload)
    blob = (json.dumps(payload) + md).lower()
    for frag in _DRAFT_FRAGMENT_GUARD:
        assert frag.lower() not in blob, f"draft fragment leaked: {frag!r}"
    # belt-and-suspenders: no trace path / evidence span key
    assert "traces/local/" not in blob
    assert "evidence_span" not in blob


def test_key_finding_names_the_forward_looking_decision() -> None:
    payload = build_payload()
    assert "forward-looking" in payload["key_finding"].lower()
    # The policy decision + its deterministic enforcer must be recorded.
    assert payload["policy_decision"]["policy_id"] == "FL-FORWARD-PROMISE-004"
    assert "grade_forward_looking_promise" in payload["policy_decision"]["enforced_by"]
    # The 006 consent over-flag is preserved as a grader-calibration note.
    assert any(n["case_id"] == "case_fl_adv_v2_006" for n in payload["grader_calibration_notes"])


def test_artifact_is_tracked_not_gitignored() -> None:
    # the public-safe adjudication report is meant to be committed
    gi = (ROOT / ".gitignore").read_text()
    assert "llm_adversarial_v2_reground_adjudication" not in gi
