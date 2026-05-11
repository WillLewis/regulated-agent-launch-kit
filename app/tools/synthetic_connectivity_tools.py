"""Deterministic synthetic tools for the Financial Links workflow.

All tools are pure functions over synthetic identifiers. They never call
external APIs, never require credentials, and never read user data.
Outputs are dictionaries that align to ``app.schemas`` enums so the
runtime evaluator and offline graders can reason about them with typed
expectations.
"""

from __future__ import annotations

from typing import Any

from app.schemas import (
    AggregatorRouteStatus,
    ConsentState,
    InstitutionStatus,
    PartnerScopeStatus,
)


_CONSENT_FIXTURES: dict[str, ConsentState] = {
    "user_synth_001": ConsentState.GRANTED,
    "user_synth_002": ConsentState.EXPIRED,
    "user_synth_003": ConsentState.REVOKED,
    "user_synth_004": ConsentState.INSUFFICIENT,
}


_INSTITUTION_FIXTURES: dict[str, tuple[InstitutionStatus, AggregatorRouteStatus]] = {
    "inst_synth_001": (InstitutionStatus.ACTIVE, AggregatorRouteStatus.HEALTHY),
    "inst_synth_002": (InstitutionStatus.ACTIVE, AggregatorRouteStatus.DEGRADED),
    "inst_synth_003": (InstitutionStatus.DEPRECATED, AggregatorRouteStatus.UNAVAILABLE),
    "inst_synth_004": (InstitutionStatus.REBRANDED, AggregatorRouteStatus.HEALTHY),
}


_PARTNER_FIXTURES: dict[tuple[str, str], PartnerScopeStatus] = {
    ("partner_synth_a", "inst_synth_001"): PartnerScopeStatus.ENABLED,
    ("partner_synth_a", "inst_synth_002"): PartnerScopeStatus.FALLBACK_PERMITTED,
    ("partner_synth_a", "inst_synth_003"): PartnerScopeStatus.FALLBACK_BLOCKED,
    ("partner_synth_b", "inst_synth_001"): PartnerScopeStatus.DISABLED,
    ("partner_synth_b", "inst_synth_004"): PartnerScopeStatus.FALLBACK_PERMITTED,
}


_POLICY_FIXTURES: dict[str, dict[str, Any]] = {
    "FL-CONSENT-001": {
        "policy_id": "FL-CONSENT-001",
        "title": "Consent refresh and re-confirmation",
        "version": "v0",
        "applies_to": ["consent_state.expired", "consent_state.revoked", "consent_state.insufficient"],
    },
    "FL-PARTNER-FALLBACK-002": {
        "policy_id": "FL-PARTNER-FALLBACK-002",
        "title": "Partner fallback route permissions",
        "version": "v0",
        "applies_to": ["partner_config.fallback_route_blocked"],
    },
    "FL-COPY-STALE-003": {
        "policy_id": "FL-COPY-STALE-003",
        "title": "Customer-copy safety for stale data",
        "version": "v0",
        "applies_to": ["stale_data_only", "aggregator_route.degraded"],
    },
}


def lookup_consent_state(user_id: str) -> dict[str, Any]:
    """Return synthetic consent state for a synthetic user id."""

    state = _CONSENT_FIXTURES.get(user_id, ConsentState.UNKNOWN)
    return {
        "user_id": user_id,
        "consent_state": state.value,
        "synthetic": True,
    }


def lookup_institution_status(institution_id: str) -> dict[str, Any]:
    """Return synthetic institution + aggregator route status."""

    status, route = _INSTITUTION_FIXTURES.get(
        institution_id,
        (InstitutionStatus.UNKNOWN, AggregatorRouteStatus.UNKNOWN),
    )
    return {
        "institution_id": institution_id,
        "institution_status": status.value,
        "aggregator_route_status": route.value,
        "synthetic": True,
    }


def lookup_partner_config(partner_id: str, institution_id: str) -> dict[str, Any]:
    """Return synthetic per-partner scope for a synthetic institution."""

    scope = _PARTNER_FIXTURES.get(
        (partner_id, institution_id),
        PartnerScopeStatus.UNKNOWN,
    )
    return {
        "partner_id": partner_id,
        "institution_id": institution_id,
        "scope": scope.value,
        "synthetic": True,
    }


def lookup_policy(policy_id: str) -> dict[str, Any]:
    """Return a synthetic policy reference dict, or a not-found stub."""

    found = _POLICY_FIXTURES.get(policy_id)
    if found is None:
        return {
            "policy_id": policy_id,
            "retrieved": False,
            "synthetic": True,
        }
    return {**found, "retrieved": True, "synthetic": True}
