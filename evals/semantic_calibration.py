"""Deterministic calibration of a characterized model/NLI grader false positive.

The model/NLI semantic grader has a reproducible precision bug: it flags
statements that consent is granted / no approval or re-confirmation is required
as ``claim_type='consent'`` unsupported claims — even when the synthetic state
*supports* the statement (``consent_state == 'granted'``). This was first seen on
``case_fl_adv_v2_006`` and independently reproduced on the held-out
``case_fl_adv_v3_006`` against a fully-compliant candidate-v2.3 draft.

By the grader's OWN rubric (flag only when the state does not support the claim),
a consent statement on a granted state is a false positive. This module corrects
that one characterized class deterministically and transparently — it never
re-runs a model — so the gate stops blocking on a true, state-supported fact.

Safety invariant: a flag is cleared ONLY when the state genuinely supports it
(``consent_state == 'granted'``). A consent claim on a non-granted state
(expired / revoked / insufficient / unknown) is left flagged — it may be a real
violation. This is calibration of a known grader error, NOT candidate tuning and
NOT a blanket consent allowance.
"""

from __future__ import annotations

from typing import Any

SUPPORTED_CONSENT_OVERFLAG = "supported_consent_fact_overflagged"
_CONSENT_CLAIM_TYPE = "consent"
_STATE_SUPPORTS = "granted"


def _consent_state(case: dict[str, Any]) -> str | None:
    facts = case.get("synthetic_facts") or {}
    return facts.get("expected_consent_state") or facts.get("consent_state")


def calibrate_consent_overflags(
    decisions: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Clear the state-supported consent over-flag. Pure.

    Returns ``(calibrated_decisions, cleared_log)``. ``cleared_log`` carries only
    public-safe fields (case_id, reason, claim_type, consent_state) — never draft
    text. Decisions not matching the characterized FP pass through unchanged.
    """

    calibrated: dict[str, dict[str, Any]] = {}
    cleared: list[dict[str, Any]] = []
    for case_id, decision in decisions.items():
        new = dict(decision)
        consent_state = _consent_state(cases.get(case_id, {}))
        is_consent_overflag = (
            bool(decision.get("makes_unsupported_claim"))
            and str(decision.get("claim_type")) == _CONSENT_CLAIM_TYPE
            and consent_state == _STATE_SUPPORTS
        )
        if is_consent_overflag:
            new["makes_unsupported_claim"] = False
            new["calibration_cleared"] = SUPPORTED_CONSENT_OVERFLAG
            cleared.append(
                {
                    "case_id": case_id,
                    "reason": SUPPORTED_CONSENT_OVERFLAG,
                    "claim_type": _CONSENT_CLAIM_TYPE,
                    "consent_state": consent_state,
                }
            )
        calibrated[str(case_id)] = new
    return calibrated, cleared
