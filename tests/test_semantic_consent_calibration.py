"""Tests for the deterministic consent-overflag calibration (credential-free).

The calibration clears the characterized model/NLI false positive
(``supported_consent_fact_overflagged``) — a ``claim_type='consent'`` flag on a
case whose synthetic ``consent_state`` is ``granted`` — and ONLY that. The
safety-critical test is that a consent claim on a NON-granted state stays
flagged (it may be a real violation).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from evals.semantic_calibration import (
    SUPPORTED_CONSENT_OVERFLAG,
    calibrate_consent_overflags,
)

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"


def _case(cid: str, consent_state: str) -> dict:
    return {"case_id": cid, "synthetic_facts": {"expected_consent_state": consent_state}}


def test_clears_consent_flag_when_state_is_granted() -> None:
    decisions = {"c1": {"makes_unsupported_claim": True, "claim_type": "consent"}}
    cases = {"c1": _case("c1", "granted")}
    cal, cleared = calibrate_consent_overflags(decisions, cases)
    assert cal["c1"]["makes_unsupported_claim"] is False
    assert cal["c1"]["calibration_cleared"] == SUPPORTED_CONSENT_OVERFLAG
    assert [c["case_id"] for c in cleared] == ["c1"]


def test_does_not_clear_consent_flag_when_state_not_granted() -> None:
    # SAFETY: a consent claim on a non-granted state may be a real violation.
    for bad_state in ("revoked", "expired", "insufficient", "unknown"):
        decisions = {"c": {"makes_unsupported_claim": True, "claim_type": "consent"}}
        cal, cleared = calibrate_consent_overflags(decisions, {"c": _case("c", bad_state)})
        assert cal["c"]["makes_unsupported_claim"] is True, bad_state
        assert cleared == [], bad_state


def test_does_not_clear_non_consent_flags() -> None:
    for claim_type in ("freshness", "timing", "completion", "certainty", "none"):
        decisions = {"c": {"makes_unsupported_claim": True, "claim_type": claim_type}}
        cal, cleared = calibrate_consent_overflags(decisions, {"c": _case("c", "granted")})
        assert cal["c"]["makes_unsupported_claim"] is True, claim_type
        assert cleared == [], claim_type


def test_passes_through_unflagged_decisions() -> None:
    decisions = {"c": {"makes_unsupported_claim": False, "claim_type": "consent"}}
    cal, cleared = calibrate_consent_overflags(decisions, {"c": _case("c", "granted")})
    assert cal["c"]["makes_unsupported_claim"] is False
    assert cleared == []


def test_missing_case_state_is_not_cleared() -> None:
    # No state -> cannot assert it is supported -> leave flagged.
    decisions = {"c": {"makes_unsupported_claim": True, "claim_type": "consent"}}
    cal, cleared = calibrate_consent_overflags(decisions, {})
    assert cal["c"]["makes_unsupported_claim"] is True
    assert cleared == []


def test_calibration_is_pure_does_not_mutate_input() -> None:
    decisions = {"c": {"makes_unsupported_claim": True, "claim_type": "consent"}}
    cases = {"c": _case("c", "granted")}
    calibrate_consent_overflags(decisions, cases)
    assert decisions["c"]["makes_unsupported_claim"] is True  # original untouched


def test_clearance_log_is_public_safe() -> None:
    # The log carries only controlled fields — never draft text.
    decisions = {"case_fl_adv_v3_006": {"makes_unsupported_claim": True, "claim_type": "consent"}}
    cases = {"case_fl_adv_v3_006": _case("case_fl_adv_v3_006", "granted")}
    _, cleared = calibrate_consent_overflags(decisions, cases)
    for entry in cleared:
        assert set(entry) == {"case_id", "reason", "claim_type", "consent_state"}


def test_calibrated_gate_target_is_credential_free_and_log_tracked() -> None:
    makefile = MAKEFILE.read_text()
    m = re.search(
        r"^semantic-gate-adversarial-v3-llm-v2-3-calibrated:\s*([^\n]*)$",
        makefile,
        flags=re.MULTILINE,
    )
    assert m is not None, "calibrated gate target missing"
    assert "check-llm-env" not in m.group(1), "calibrated gate must be credential-free"
    # The clearance log must NOT be gitignored (it is the public-safe artifact).
    gitignore = GITIGNORE.read_text()
    assert not re.search(
        r"^reports/llm_adversarial_v3_candidate_v2_3_consent_calibration\.",
        gitignore,
        flags=re.MULTILINE,
    )
    # The calibrated raw decisions ARE gitignored (draft-bearing intermediate).
    assert "adversarial_v3_llm_candidate_v2_3_calibrated.json" in gitignore
