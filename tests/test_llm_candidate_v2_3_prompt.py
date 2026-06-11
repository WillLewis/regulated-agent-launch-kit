"""Tests for the ``llm_candidate_v2_3`` universal forward-looking-ban profile (WIRED, NOT RUN).

The re-grounding adjudication resolved all 8 hardened-gate flags to
candidate_actionable under the 2026-06-11 decision to ban forward-looking
reassurance (policy FL-FORWARD-PROMISE-004). v2.2 banned forward-looking timing
only on CLOSED gates (and allowed it on healthy cases), and its hedging vocab /
good example actively taught the banned language. v2.3 makes the ban UNIVERSAL
and removes the contradictory guidance. These tests lock in:

1. ``LLM_CANDIDATE_V2_3`` is registered, opt-in (not default), distinct.
2. v2.3 = v2.2 with EXACTLY the three guarded replacements and nothing else.
3. The new ban is universal (no healthy carve-out) and names the banned forms.
4. v2.3 removes the contradictory hedging vocab + good example.
5. v2.3 preserves every other v2 control.
6. The agent routes v2.3 through ``_build_llm_prompt_v2_3``; v2.2 is unchanged.
7. The credentialed v2.3 targets gate on ``check-llm-env`` and raw reports are
   gitignored.

No real LLM call or credentials are involved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import app.agents.financial_links_reliability_agent as specialist_module
from app.agents.financial_links_reliability_agent import (
    _V2_2_CLOSED_GATE_BAN,
    _V2_3_FORWARD_LOOKING_BAN,
    _V2_3_GOOD_TIMING_EXAMPLE,
    _V2_3_HEDGING_VOCAB,
    _V2_GOOD_TIMING_EXAMPLE,
    _V2_HEDGING_VOCAB,
)
from app.agents.llm_adapter import LLMResponse
from app.agents.profiles import DEFAULT_PROFILE, KNOWN_PROFILES, AgentSystemProfile
from app.schemas import (
    ApprovalDecision,
    ApprovalStatus,
    Case,
    ConsentState,
    RiskBand,
    Workflow,
)
from app.runner import run_case

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"
ADVERSARIAL_V0 = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)

V2_3_MARKER = "No forward-looking reassurance, in ANY state"


def _build(builder):
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
    return builder(
        case=case,
        consent_state=ConsentState.GRANTED,
        institution_out=None,
        partner_out=None,
        policy_ids=["FL-COPY-STALE-003"],
        approval=approval,
        deterministic_draft="Synthetic draft for analyst review.",
    )


def test_v2_3_registered_opt_in_distinct() -> None:
    assert AgentSystemProfile.LLM_CANDIDATE_V2_3.value == "llm_candidate_v2_3"
    assert "llm_candidate_v2_3" in KNOWN_PROFILES
    assert DEFAULT_PROFILE != AgentSystemProfile.LLM_CANDIDATE_V2_3


def test_v2_3_is_v2_2_with_exactly_three_replacements() -> None:
    v22 = _build(specialist_module._build_llm_prompt_v2_2)
    v23 = _build(specialist_module._build_llm_prompt_v2_3)
    expected = v22
    for old, new in (
        (_V2_2_CLOSED_GATE_BAN, _V2_3_FORWARD_LOOKING_BAN),
        (_V2_HEDGING_VOCAB, _V2_3_HEDGING_VOCAB),
        (_V2_GOOD_TIMING_EXAMPLE, _V2_3_GOOD_TIMING_EXAMPLE),
    ):
        expected = expected.replace(old, new, 1)
    assert v23 == expected
    assert V2_3_MARKER in v23
    assert V2_3_MARKER not in v22, "v2.2 must NOT carry the v2.3 universal ban"


def test_v2_3_ban_is_universal_no_healthy_carveout() -> None:
    v23 = _build(specialist_module._build_llm_prompt_v2_3)
    assert "neither on closed gates NOR on fully healthy cases" in v23
    # The v2.2 healthy-case allowance must be gone.
    assert "hedged timing guidance is still allowed" not in v23
    # Names the banned forms and the permitted escape hatch.
    for marker in (
        "expected to refresh / update / stabilize / proceed / continue",
        "anticipated to proceed / continue",
        "within a typical / short window",
        "a NEGATED future is allowed",
    ):
        assert marker in v23, f"v2.3 ban missing: {marker!r}"


def test_v2_3_removes_contradictory_guidance() -> None:
    v23 = _build(specialist_module._build_llm_prompt_v2_3)
    # The old hedging vocab recommended "is expected to" / "is anticipated to".
    assert _V2_HEDGING_VOCAB not in v23
    assert 'Prefer hedged verbs and qualifiers: "typically", "may", "is expected to"' not in v23
    # The old good example used a banned phrase.
    assert _V2_GOOD_TIMING_EXAMPLE not in v23
    # The replacement good example must not reintroduce a banned forward phrase.
    assert "within a short window; refresh timing may vary" not in v23


def test_v2_3_preserves_all_other_v2_controls() -> None:
    v23 = _build(specialist_module._build_llm_prompt_v2_3)
    for marker in (
        "FORBIDDEN PHRASES",
        "M7 SEMANTIC BANS",
        "M7 STRUCTURAL CONTROLS",
        "Partner-scope decision table",
        "Operational-status overpromise",
        "Consent gate is absolute",
    ):
        assert marker in v23, f"v2.3 dropped a v2 control: {marker!r}"


def test_v2_2_unchanged_no_v2_3_text() -> None:
    v22 = _build(specialist_module._build_llm_prompt_v2_2)
    assert V2_3_MARKER not in v22
    assert _V2_2_CLOSED_GATE_BAN in v22  # v2.2 still carries its own ban


def test_agent_routes_v2_3_through_v2_3_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def _capture(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
        captured["last"] = prompt
        return LLMResponse.from_text(
            "Synthetic hedged draft; data may currently be delayed.",
            model="claude-sonnet-4-5",
            input_tokens=200,
            output_tokens=120,
        )

    monkeypatch.setattr(
        specialist_module._llm_adapter, "generate_financial_links_draft", _capture
    )
    case = json.loads(ADVERSARIAL_V0.read_text().splitlines()[0])

    run_case(case, agent_system_version="llm_candidate_v2_2")
    assert V2_3_MARKER not in captured["last"]

    run_case(case, agent_system_version="llm_candidate_v2_3")
    assert V2_3_MARKER in captured["last"]


def test_v2_3_credentialed_targets_gate_on_env_and_gitignore_raw() -> None:
    makefile = MAKEFILE.read_text()
    gitignore = GITIGNORE.read_text()
    for target in (
        "eval-adversarial-v2-llm-v2-3",
        "semantic-model-decisions-adversarial-v2-llm-v2-3",
        "eval-adversarial-v3-llm-v2-3",
    ):
        m = re.search(rf"^{re.escape(target)}:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
        assert m is not None, f"missing Make target {target!r}"
        assert "check-llm-env" in m.group(1).split(), f"{target} must gate on check-llm-env"
    # Raw v2.3 eval reports stay gitignored.
    assert "llm_adversarial_v2_candidate_v2_3_eval.json" in gitignore
    assert "llm_adversarial_v3_candidate_v2_3_eval.json" in gitignore
