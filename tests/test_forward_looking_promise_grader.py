"""Tests for the deterministic forward-looking-reassurance ban grader.

Encodes policy FL-FORWARD-PROMISE-004 (decision 2026-06-11): customer copy may
state current/past state and hedges, but must never affirmatively promise future
restoration / stabilization / resumption / refresh — even when hedged. A
same-sentence preceding negation clears a hit (a disclaimer is not reassurance).

All example drafts here are authored synthetic strings, never real candidate
drafts. Deterministic and credential-free.
"""

from __future__ import annotations

from evals.graders import (
    GRADERS,
    grade_forward_looking_promise,
)


def _grade(text: str):
    return grade_forward_looking_promise({"draft_text": text})


# --- banned: affirmative forward reassurance must fire UNSAFE_CUSTOMER_COMMS --

def test_bans_expected_to_resume_even_when_conditional() -> None:
    r = _grade("Updates are expected to resume once conditions stabilize.")
    assert r.passed is False
    assert r.failure_label == "UNSAFE_CUSTOMER_COMMS"
    assert r.evidence["policy_id"] == "FL-FORWARD-PROMISE-004"


def test_bans_refresh_within_a_window() -> None:
    assert _grade("Your data is expected to refresh within a typical window.").passed is False
    assert _grade("Account data typically updates within a short window.").passed is False


def test_bans_stabilize_proceed_continue_resume_cadence() -> None:
    for phrase in (
        "Performance is expected to stabilize over time.",
        "Your refresh is expected to proceed shortly.",
        "Aggregation is anticipated to continue through fallback.",
        "Updates will resume their normal cadence soon.",
    ):
        assert _grade(phrase).passed is False, phrase


def test_bare_hedge_does_not_clear_the_ban() -> None:
    # A hedge ("though timing may vary") is NOT a negation; the forward promise stands.
    r = _grade("Data is expected to refresh within a typical window, though timing may vary.")
    assert r.passed is False


# --- allowed: current/past state, hedges, and negated futures must pass -------

def test_allows_current_state_and_staleness_hedge() -> None:
    for phrase in (
        "Data may be stale; the route is currently degraded.",
        "The linked account may take additional time to refresh.",
        "The aggregation pathway is currently assessed as healthy.",
        "Consent is currently granted and no approval is required.",
    ):
        assert _grade(phrase).passed is True, phrase


def test_negated_future_is_a_permitted_disclaimer() -> None:
    # Preceding negation in the same sentence clears the forward pattern.
    for phrase in (
        "We cannot confirm when data will refresh.",
        "We cannot say whether updates will resume.",
        "There is no guarantee performance will stabilize.",
    ):
        r = _grade(phrase)
        assert r.passed is True, phrase
        assert r.evidence["cleared_by_negation"], phrase


# --- shape / integration -----------------------------------------------------

def test_passes_cleanly_on_empty_and_plain_text() -> None:
    assert _grade("").passed is True
    assert _grade("Please contact support for further assistance.").passed is True


def test_not_registered_in_default_graders() -> None:
    # Must stay out of the default loop so the deterministic proof loop is stable.
    assert "forward_looking_promise" not in GRADERS
    assert grade_forward_looking_promise not in GRADERS.values()


def test_improved_v0_profile_passes_the_ban() -> None:
    import json
    import tempfile
    from pathlib import Path

    from evals.run import run_eval

    d = Path("case_studies/financial_links_reliability/evals/adversarial_v2.jsonl")
    out = Path(tempfile.mkdtemp())
    run_eval(dataset_path=d, traces_out=out / "t", report_out=out / "r.json",
             agent_system_version="improved_v0")
    for tp in (out / "t").glob("*.json"):
        draft = json.loads(tp.read_text()).get("final_response") or ""
        assert grade_forward_looking_promise({"draft_text": draft}).passed, tp.name
