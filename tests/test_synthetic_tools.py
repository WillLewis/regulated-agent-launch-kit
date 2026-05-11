"""Tests for Financial Links synthetic tools.

These tools must be deterministic, dependency-free, and return only
synthetic facts. They are pure functions over synthetic IDs.
"""

from __future__ import annotations

from app.tools.synthetic_connectivity_tools import (
    lookup_consent_state,
    lookup_institution_status,
    lookup_partner_config,
    lookup_policy,
)


def test_lookup_consent_state_is_deterministic_for_known_ids() -> None:
    a = lookup_consent_state("user_synth_002")
    b = lookup_consent_state("user_synth_002")
    assert a == b
    assert a["consent_state"] == "expired"
    assert a["synthetic"] is True


def test_lookup_consent_state_returns_unknown_for_unknown_user() -> None:
    result = lookup_consent_state("user_synth_unmapped")
    assert result["consent_state"] == "unknown"


def test_lookup_institution_status_pairs_route_and_status() -> None:
    result = lookup_institution_status("inst_synth_002")
    assert result["institution_status"] == "active"
    assert result["aggregator_route_status"] == "degraded"


def test_lookup_partner_config_returns_known_scope() -> None:
    result = lookup_partner_config("partner_synth_a", "inst_synth_003")
    assert result["scope"] == "fallback_blocked"


def test_lookup_partner_config_unknown_pair() -> None:
    result = lookup_partner_config("partner_synth_a", "inst_synth_unmapped")
    assert result["scope"] == "unknown"


def test_lookup_policy_returns_synthetic_metadata() -> None:
    found = lookup_policy("FL-CONSENT-001")
    assert found["retrieved"] is True
    assert found["title"] == "Consent refresh and re-confirmation"
    assert found["synthetic"] is True


def test_lookup_policy_missing_returns_not_retrieved_stub() -> None:
    missing = lookup_policy("DOES-NOT-EXIST")
    assert missing["retrieved"] is False
    assert missing["synthetic"] is True
