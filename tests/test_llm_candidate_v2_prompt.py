"""Tests for the ``llm_candidate_v2`` M7 remediation profile (WIRED, NOT RUN).

The M7 adjudication marked 9 findings ``candidate_actionable`` across 6 distinct
reason codes. v2's prompt encodes one semantic ban per reason code plus the
failure-analysis structural controls, while preserving every v1 lexical control
(so the v0→v1 win is not regressed). These tests lock in:

1. ``LLM_CANDIDATE_V2`` is registered, opt-in (not default), distinct from v0/v1.
2. The v2 prompt covers every adjudicated ``candidate_actionable`` reason code
   and the structural controls, and frames the bans as *semantic*.
3. The v2 prompt keeps the v1 forbidden-phrase + hedging scaffolding.
4. v0/v1 prompts are unchanged; deterministic/default profiles never call the LLM.
5. The agent routes v2 through ``_build_llm_prompt_v2``.
6. The credentialed v2 Make targets gate on ``check-llm-env`` and the raw v2
   report stays gitignored.

No real LLM call or credentials are involved.
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
ADJUDICATION = ROOT / "reports" / "llm_adversarial_v2_semantic_adjudication.json"
ADVERSARIAL_V0 = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)

# Each adjudicated candidate_actionable reason code -> a distinctive marker the
# v2 prompt must carry. If the adjudication introduces a new candidate_actionable
# reason code, test_v2_prompt_covers_every_candidate_actionable_reason fails until
# the prompt is extended — preventing silent drift.
REASON_CODE_TO_MARKER = {
    "unsupported_operational_status_claim": "Operational-status overpromise",
    "unsupported_resolution_or_restoration_promise": "Resolution/restoration promise",
    "implied_future_refresh_despite_gate": "Implied future refresh despite a gate",
    "unsupported_continuity_claim_disabled_scope": "Disabled-scope continuity",
    "unsupported_refresh_timeframe_missing_metadata": "Missing-metadata refresh/timeframe",
    "unsupported_auto_completion_promise_missing_partner": "Missing-partner auto-completion",
}

STRUCTURAL_MARKERS = (
    "Same-clause hedging",
    "No inferred identifiers",
    "Consent gate is absolute",
    "Partner-scope decision table",
    "Cite ALL applicable policies",
    "Separate the axes",
)


def _build_prompt(builder, *, partner_scope: str = "disabled") -> str:
    case = Case(
        case_id="case_test_001",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        risk_band=RiskBand.L2,
        consent_sensitive=True,
        payload={},
    )
    approval = ApprovalDecision(
        required=True, status=ApprovalStatus.PENDING, approver_role="partner_support_analyst"
    )
    return builder(
        case=case,
        consent_state=ConsentState.INSUFFICIENT,
        institution_out={"institution_status": "active", "aggregator_route_status": "degraded"},
        partner_out={"scope": partner_scope},
        policy_ids=["FL-CONSENT-001", "FL-COPY-STALE-003"],
        approval=approval,
        deterministic_draft="Synthetic draft for analyst review.",
    )


# --- Profile registration ----------------------------------------------------

def test_llm_candidate_v2_is_registered() -> None:
    assert AgentSystemProfile.LLM_CANDIDATE_V2.value == "llm_candidate_v2"
    assert "llm_candidate_v2" in KNOWN_PROFILES


def test_llm_candidate_v2_is_opt_in_and_distinct() -> None:
    assert DEFAULT_PROFILE != AgentSystemProfile.LLM_CANDIDATE_V2
    assert DEFAULT_PROFILE.value == "improved_v0"
    distinct = {
        AgentSystemProfile.LLM_CANDIDATE_V0.value,
        AgentSystemProfile.LLM_CANDIDATE_V1.value,
        AgentSystemProfile.LLM_CANDIDATE_V2.value,
    }
    assert len(distinct) == 3


# --- v2 prompt content -------------------------------------------------------

def test_v2_prompt_covers_every_candidate_actionable_reason() -> None:
    # The set of candidate_actionable reason codes the adjudication actually
    # produced must equal the set the v2 prompt addresses.
    adj = json.loads(ADJUDICATION.read_text())
    actionable_codes = {
        f["public_reason_code"]
        for f in adj["findings"]
        if f["adjudication_status"] == "candidate_actionable"
    }
    assert actionable_codes == set(REASON_CODE_TO_MARKER), (
        "v2 prompt reason-code coverage drifted from the adjudication: "
        f"adjudication={sorted(actionable_codes)} prompt={sorted(REASON_CODE_TO_MARKER)}"
    )
    prompt = _build_prompt(specialist_module._build_llm_prompt_v2)
    assert "M7 SEMANTIC BANS" in prompt
    for code, marker in REASON_CODE_TO_MARKER.items():
        assert marker in prompt, f"v2 prompt missing control for {code!r} ({marker!r})"


def test_v2_prompt_includes_structural_controls() -> None:
    prompt = _build_prompt(specialist_module._build_llm_prompt_v2)
    assert "M7 STRUCTURAL CONTROLS" in prompt
    for marker in STRUCTURAL_MARKERS:
        assert marker in prompt, f"v2 prompt missing structural control {marker!r}"
    # Partner-scope decision table enumerates the scope states.
    for scope in ("fallback_blocked", "disabled", "fallback_permitted"):
        assert scope in prompt


def test_v2_prompt_is_semantic_not_just_substring() -> None:
    prompt = _build_prompt(specialist_module._build_llm_prompt_v2)
    lower = prompt.lower()
    assert "judge the meaning" in lower
    assert "paraphrase" in lower


def test_v2_prompt_preserves_v1_lexical_controls() -> None:
    """v2 must not regress the v0->v1 lexical win: forbidden phrases + hedging."""

    prompt = _build_prompt(specialist_module._build_llm_prompt_v2)
    assert "FORBIDDEN PHRASES" in prompt
    for phrase in _RUNTIME_UNSUPPORTED_CLAIM_PATTERNS:
        assert f'"{phrase}"' in prompt, f"v2 dropped forbidden phrase {phrase!r}"
    for hedge in ("typically", "may", "is expected to", "can take"):
        assert hedge in prompt


def test_v2_prompt_asks_for_self_check() -> None:
    prompt = _build_prompt(specialist_module._build_llm_prompt_v2)
    lower = prompt.lower()
    assert "self-check" in lower and "m7 semantic bans" in lower


# --- v0/v1 unchanged; deterministic profiles never call the LLM --------------

def test_v0_and_v1_prompts_do_not_carry_v2_scaffolding() -> None:
    v0 = _build_prompt(specialist_module._build_llm_prompt)
    v1 = _build_prompt(specialist_module._build_llm_prompt_v1)
    assert "FORBIDDEN PHRASES" not in v0
    assert "M7 SEMANTIC BANS" not in v0
    # v1 has the forbidden-phrase scaffolding but NOT the M7 remediation block.
    assert "FORBIDDEN PHRASES" in v1
    assert "M7 SEMANTIC BANS" not in v1
    assert "M7 STRUCTURAL CONTROLS" not in v1


def test_agent_routes_v2_through_v2_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def _capture(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
        captured["last"] = prompt
        return LLMResponse.from_text(
            "Synthetic hedged draft; refresh timing may vary.",
            model="claude-sonnet-4-5",
            input_tokens=200,
            output_tokens=120,
        )

    monkeypatch.setattr(
        specialist_module._llm_adapter, "generate_financial_links_draft", _capture
    )
    case = json.loads(ADVERSARIAL_V0.read_text().splitlines()[0])

    run_case(case, agent_system_version="llm_candidate_v1")
    assert "M7 SEMANTIC BANS" not in captured["last"]

    run_case(case, agent_system_version="llm_candidate_v2")
    assert "M7 SEMANTIC BANS" in captured["last"]
    assert "M7 STRUCTURAL CONTROLS" in captured["last"]


def test_deterministic_profiles_never_call_the_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """improved_v0 / baseline_v0 must not touch the LLM adapter — adding v2
    changes nothing about the default/deterministic path."""

    def _boom(prompt: str, **kwargs):  # noqa: ARG001
        raise AssertionError("deterministic profile must not call the LLM adapter")

    monkeypatch.setattr(
        specialist_module._llm_adapter, "generate_financial_links_draft", _boom
    )
    case = json.loads(ADVERSARIAL_V0.read_text().splitlines()[0])
    for profile in ("improved_v0", "baseline_v0"):
        result = run_case(case, agent_system_version=profile)
        assert result.agent_output.draft_text  # produced a deterministic draft


# --- Make wiring: credential-gated, raw artifacts gitignored -----------------

def _target_block(target: str) -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(f"{target}:")), None)
    assert start is not None, f"Makefile target {target!r} not found"
    header = lines[start]
    block = [header]
    for ln in lines[start + 1 :]:
        if not ln.strip() or not ln[0].isspace():
            break
        block.append(ln)
    return "\n".join(block), header


def test_v2_eval_target_is_credential_gated() -> None:
    block, header = _target_block("eval-adversarial-v2-llm-v2")
    assert "check-llm-env" in header, "v2 eval target must depend on check-llm-env"
    assert "--agent-system-version llm_candidate_v2" in block


def test_v2_semantic_decisions_target_is_credential_gated() -> None:
    _block, header = _target_block("semantic-model-decisions-adversarial-v2-llm-v2")
    assert "check-llm-env" in header


def test_v2_raw_report_is_gitignored() -> None:
    gi = GITIGNORE.read_text()
    assert "reports/llm_adversarial_v2_candidate_v2_eval.json" in gi
    assert "reports/llm_adversarial_v2_candidate_v2_semantic_replay_decisions.json" in gi


def test_no_readiness_overclaim_in_profile_docs() -> None:
    src = (ROOT / "app" / "agents" / "profiles.py").read_text().lower()
    for forbidden in ("production ready", "production-ready", "pilot ready", "pilot-ready"):
        assert forbidden not in src
