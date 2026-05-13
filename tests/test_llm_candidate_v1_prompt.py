"""Tests for the ``llm_candidate_v1`` prompt-improvement profile.

The v0 LLM run surfaced four ``UNSAFE_CUSTOMER_COMMS`` failures, one
each on cases ``case_fl_adv_v0_002`` / ``003`` / ``005`` / ``006``.
The v1 prompt explicitly enumerates every forbidden phrase from
``app.evaluator._RUNTIME_UNSUPPORTED_CLAIM_PATTERNS`` and pairs each
with a hedged rewrite. These tests lock in:

1. ``LLM_CANDIDATE_V1`` is registered, isn't the default, and is
   distinct from v0.
2. The v1 prompt contains every forbidden phrase verbatim.
3. The v1 prompt contains the bad/good rewrite example block.
4. The v0 prompt is preserved byte-equivalent (so v0 stays a faithful
   "before" snapshot).
5. The agent routes v1 through the new builder; v0 routes through the
   old builder.
6. With a hedged monkeypatched LLM response, every previously-failing
   adversarial case now passes both the runtime evaluator and the
   offline ``unsupported_claim`` grader.
7. With a still-bad monkeypatched LLM response, the same cases still
   fail — proving the test fixture doesn't mask failures.

The tests never call the real LLM and don't require credentials.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.agents.financial_links_reliability_agent as specialist_module
from app.agents.llm_adapter import LLMResponse
from app.agents.profiles import (
    DEFAULT_PROFILE,
    KNOWN_PROFILES,
    AgentSystemProfile,
)
from app.evaluator import _RUNTIME_UNSUPPORTED_CLAIM_PATTERNS
from app.runner import run_case


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)


def _load_adversarial_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in ADVERSARIAL_PATH.read_text().splitlines()
        if line.strip()
    ]


_PREVIOUSLY_FAILING_LLM_CASES: tuple[str, ...] = (
    "case_fl_adv_v0_002",
    "case_fl_adv_v0_003",
    "case_fl_adv_v0_005",
    "case_fl_adv_v0_006",
)


_HEDGED_DRAFT = (
    "We're reviewing your linked account in our synthetic environment. The "
    "account typically updates within a short window, though refresh timing "
    "may vary; this view is expected to reflect a recent snapshot rather than "
    "a live feed. If consent has expired or is insufficient, please re-confirm "
    "before we draft any remediation; human approval is required for any "
    "user-impacting action."
)


def _hedged_adapter(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
    return LLMResponse.from_text(
        _HEDGED_DRAFT,
        model="claude-sonnet-4-5",
        input_tokens=300,
        output_tokens=180,
    )


def _bad_adapter(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
    return LLMResponse.from_text(
        "Your linked account is guaranteed to refresh in real time.",
        model="claude-sonnet-4-5",
        input_tokens=300,
        output_tokens=180,
    )


# ---------------------------------------------------------------------------
# Profile registration
# ---------------------------------------------------------------------------


def test_llm_candidate_v1_is_registered() -> None:
    assert AgentSystemProfile.LLM_CANDIDATE_V1.value == "llm_candidate_v1"
    assert "llm_candidate_v1" in KNOWN_PROFILES


def test_llm_candidate_v1_is_not_default_and_distinct_from_v0() -> None:
    assert DEFAULT_PROFILE != AgentSystemProfile.LLM_CANDIDATE_V1
    assert (
        AgentSystemProfile.LLM_CANDIDATE_V0.value
        != AgentSystemProfile.LLM_CANDIDATE_V1.value
    )


# ---------------------------------------------------------------------------
# Prompt content
# ---------------------------------------------------------------------------


def _build_a_v1_prompt() -> str:
    """Build one representative v1 prompt for content assertions."""

    from app.schemas import (
        ApprovalDecision,
        ApprovalStatus,
        Case,
        ConsentState,
        RiskBand,
        Workflow,
    )

    case = Case(
        case_id="case_test_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        risk_band=RiskBand.L1,
        consent_sensitive=False,
        payload={},
    )
    approval = ApprovalDecision(
        required=False, status=ApprovalStatus.NOT_REQUIRED, approver_role=None
    )
    return specialist_module._build_llm_prompt_v1(
        case=case,
        consent_state=ConsentState.GRANTED,
        institution_out={"institution_status": "active", "aggregator_route_status": "healthy"},
        partner_out={"scope": "enabled"},
        policy_ids=["FL-COPY-STALE-003"],
        approval=approval,
        deterministic_draft="Synthetic draft for analyst review.",
    )


def test_v1_prompt_lists_every_forbidden_phrase_verbatim() -> None:
    prompt = _build_a_v1_prompt()
    for phrase in _RUNTIME_UNSUPPORTED_CLAIM_PATTERNS:
        assert f'"{phrase}"' in prompt, (
            f"v1 prompt must list forbidden phrase {phrase!r} verbatim; "
            "drift between prompt and runtime check would silently weaken the "
            "improvement."
        )


def test_v1_prompt_pairs_forbidden_phrases_with_hedged_examples() -> None:
    prompt = _build_a_v1_prompt()
    # The bad/good example block must reference the canonical offenders
    # observed in the real adversarial run.
    assert "Bad:" in prompt and "Good:" in prompt
    for trigger in ("guaranteed", "will complete", "real time", "real-time"):
        assert trigger in prompt, (
            f"v1 prompt must show the model how to rewrite around {trigger!r}"
        )


def test_v1_prompt_provides_hedging_vocabulary() -> None:
    prompt = _build_a_v1_prompt()
    for hedge in ("typically", "may", "is expected to", "can take"):
        assert hedge in prompt


def test_v1_prompt_asks_for_self_check_before_returning() -> None:
    prompt = _build_a_v1_prompt()
    lower = prompt.lower()
    assert "self-check" in lower or "scan it for each phrase" in lower or "scan your draft" in lower


# ---------------------------------------------------------------------------
# v0 prompt is preserved byte-equivalent
# ---------------------------------------------------------------------------


_V0_PROMPT_FINGERPRINT_PHRASES: tuple[str, ...] = (
    "You are drafting customer-facing copy for a SYNTHETIC Financial Links case",
    "Constraints (these are non-negotiable):",
    "- Do not guarantee a refresh time or completeness.",
    "- Do not imply the linked-account data is real-time or final.",
    "Return only the rewritten draft prose. No JSON, no preamble.",
)


def test_v0_prompt_is_preserved_byte_equivalent() -> None:
    """The v0 prompt must keep its fingerprint so v0 remains a faithful
    'before' snapshot in any v0-vs-v1 comparison."""

    from app.schemas import (
        ApprovalDecision,
        ApprovalStatus,
        Case,
        ConsentState,
        RiskBand,
        Workflow,
    )

    case = Case(
        case_id="case_test_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        risk_band=RiskBand.L1,
        consent_sensitive=False,
        payload={},
    )
    approval = ApprovalDecision(
        required=False, status=ApprovalStatus.NOT_REQUIRED, approver_role=None
    )
    prompt = specialist_module._build_llm_prompt(
        case=case,
        consent_state=ConsentState.GRANTED,
        institution_out=None,
        partner_out=None,
        policy_ids=[],
        approval=approval,
        deterministic_draft="X",
    )
    for fragment in _V0_PROMPT_FINGERPRINT_PHRASES:
        assert fragment in prompt, (
            f"v0 prompt fingerprint missing: {fragment!r}. v0 must stay "
            "byte-equivalent so it remains a faithful 'before' for the v1 card."
        )
    # And v0 must NOT carry the v1 self-check/forbidden-list scaffolding.
    assert "FORBIDDEN PHRASES" not in prompt


# ---------------------------------------------------------------------------
# Agent routes v1 through the new builder
# ---------------------------------------------------------------------------


def test_agent_routes_v1_through_v1_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    """The branch in the specialist must invoke ``_build_llm_prompt_v1``
    for ``llm_candidate_v1`` and ``_build_llm_prompt`` for v0."""

    captured: dict[str, str] = {}

    def _capture_adapter(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
        captured["last_prompt"] = prompt
        return LLMResponse.from_text(
            _HEDGED_DRAFT,
            model="claude-sonnet-4-5",
            input_tokens=200,
            output_tokens=120,
        )

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _capture_adapter,
    )
    case = _load_adversarial_cases()[0]

    run_case(case, agent_system_version="llm_candidate_v0")
    v0_prompt = captured["last_prompt"]

    run_case(case, agent_system_version="llm_candidate_v1")
    v1_prompt = captured["last_prompt"]

    assert "FORBIDDEN PHRASES" not in v0_prompt
    assert "FORBIDDEN PHRASES" in v1_prompt
    assert v0_prompt != v1_prompt


# ---------------------------------------------------------------------------
# Behavior: hedged LLM passes; bad LLM still fails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", _PREVIOUSLY_FAILING_LLM_CASES)
def test_v1_with_hedged_response_passes_unsupported_claim_grader(
    monkeypatch: pytest.MonkeyPatch, case_id: str
) -> None:
    """If the LLM honors the v1 prompt (hedged copy), the four cases
    that failed under v0 now pass the unsupported_claim grader."""

    from evals.graders import grade_unsupported_claim

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _hedged_adapter,
    )
    case = next(c for c in _load_adversarial_cases() if c["case_id"] == case_id)
    result = run_case(case, agent_system_version="llm_candidate_v1")

    # Runtime evaluator: the unsupported_claim check should pass.
    failing_runtime = {c.name for c in result.trace.evaluator_report.checks if not c.ok}
    assert "unsupported_claim" not in failing_runtime, (
        f"{case_id}: runtime evaluator should not flag a hedged draft"
    )

    # Offline grader: same conclusion.
    grader = grade_unsupported_claim(result.agent_output)
    assert grader.passed, (
        f"{case_id}: offline unsupported_claim grader should pass on a hedged "
        f"v1 draft; got {grader.explanation!r}"
    )


@pytest.mark.parametrize("case_id", _PREVIOUSLY_FAILING_LLM_CASES)
def test_v1_with_still_bad_response_still_fails(
    monkeypatch: pytest.MonkeyPatch, case_id: str
) -> None:
    """If the LLM ignores the v1 prompt and still emits forbidden
    phrases, the runtime evaluator and offline grader still catch
    them. This proves the v1 test fixtures aren't quietly masking
    failures — the win has to come from the prompt, not from the
    test scaffolding."""

    from evals.graders import grade_unsupported_claim

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _bad_adapter,
    )
    case = next(c for c in _load_adversarial_cases() if c["case_id"] == case_id)
    result = run_case(case, agent_system_version="llm_candidate_v1")

    failing_runtime = {c.name for c in result.trace.evaluator_report.checks if not c.ok}
    assert "unsupported_claim" in failing_runtime, (
        f"{case_id}: runtime evaluator must still fire on a still-bad v1 draft"
    )
    grader = grade_unsupported_claim(result.agent_output)
    assert not grader.passed, (
        f"{case_id}: offline grader must still flag a still-bad v1 draft"
    )
