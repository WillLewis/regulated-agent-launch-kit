"""Tests for the ``llm_candidate_v2_2`` generalized residual profile (WIRED, NOT RUN).

The candidate-v2.1 run cleared its target (case_017) but the same
affirmative-timing-on-a-closed-gate failure recurred on case_010/012/024 — gate
types v2.1's missing-metadata-only control did not reach. v2.2 generalizes that
one control to EVERY closed-gate state. These tests lock in:

1. ``LLM_CANDIDATE_V2_2`` is registered, opt-in (not default), distinct.
2. v2.2 generalizes exactly the one control and nothing else (it equals v2.1 with
   that ban replaced); v2.1 is unchanged.
3. The generalized ban names every closed-gate trigger and still permits hedged
   timing on fully-healthy cases.
4. v2.2 preserves every other v2 control; the drift guard matches v2.1's wording.
5. The agent routes v2.2 through ``_build_llm_prompt_v2_2``.
6. The credentialed v2.2 targets gate on ``check-llm-env`` and the raw report is
   gitignored.

No real LLM call or credentials are involved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.agents.financial_links_reliability_agent as specialist_module
from app.agents.financial_links_reliability_agent import (
    _V2_1_MISSING_METADATA_BAN,
    _V2_2_CLOSED_GATE_BAN,
)
from app.agents.llm_adapter import LLMResponse
from app.agents.profiles import (
    DEFAULT_PROFILE,
    KNOWN_PROFILES,
    AgentSystemProfile,
)
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

# A distinctive marker present only in v2.2's generalized ban.
V2_2_MARKER = "No timing expectation on a closed gate"


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


def test_v2_2_registered_opt_in_distinct() -> None:
    assert AgentSystemProfile.LLM_CANDIDATE_V2_2.value == "llm_candidate_v2_2"
    assert "llm_candidate_v2_2" in KNOWN_PROFILES
    assert DEFAULT_PROFILE != AgentSystemProfile.LLM_CANDIDATE_V2_2
    distinct = {
        AgentSystemProfile.LLM_CANDIDATE_V2_1.value,
        AgentSystemProfile.LLM_CANDIDATE_V2_2.value,
    }
    assert len(distinct) == 2


def test_v2_2_generalizes_only_the_one_control() -> None:
    v21 = _build(specialist_module._build_llm_prompt_v2_1)
    v22 = _build(specialist_module._build_llm_prompt_v2_2)
    # v2.2 is exactly v2.1 with the single missing-metadata ban generalized.
    assert v22 == v21.replace(_V2_1_MISSING_METADATA_BAN, _V2_2_CLOSED_GATE_BAN, 1)
    assert V2_2_MARKER in v22
    assert V2_2_MARKER not in v21, "v2.1 must NOT carry the v2.2 generalized ban"


def test_v2_2_ban_names_every_closed_gate_trigger() -> None:
    v22 = _build(specialist_module._build_llm_prompt_v2_2)
    for trigger in (
        "institution_id or institution metadata is missing",
        "consent is insufficient / expired / revoked / unknown",
        "aggregator route is unavailable / degraded / blocked",
        "partner scope is disabled",
        "fallback_blocked",
    ):
        assert trigger in v22, f"v2.2 ban missing closed-gate trigger: {trigger!r}"
    # And it explicitly preserves hedged timing on fully-healthy cases.
    assert "hedged timing guidance is still allowed" in v22


def test_v2_2_preserves_all_v2_controls() -> None:
    v22 = _build(specialist_module._build_llm_prompt_v2_2)
    for marker in (
        "FORBIDDEN PHRASES",
        "M7 SEMANTIC BANS",
        "M7 STRUCTURAL CONTROLS",
        "Partner-scope decision table",
        "Operational-status overpromise",
    ):
        assert marker in v22, f"v2.2 dropped a v2 control: {marker!r}"


def test_drift_guard_constant_is_in_v2_1_prompt() -> None:
    v21 = _build(specialist_module._build_llm_prompt_v2_1)
    assert _V2_1_MISSING_METADATA_BAN in v21


def test_v2_1_unchanged_no_v2_2_text() -> None:
    v21 = _build(specialist_module._build_llm_prompt_v2_1)
    assert _V2_1_MISSING_METADATA_BAN in v21
    assert V2_2_MARKER not in v21


def test_agent_routes_v2_2_through_v2_2_builder(monkeypatch: pytest.MonkeyPatch) -> None:
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

    run_case(case, agent_system_version="llm_candidate_v2_1")
    assert V2_2_MARKER not in captured["last"]

    run_case(case, agent_system_version="llm_candidate_v2_2")
    assert V2_2_MARKER in captured["last"]
    assert "M7 SEMANTIC BANS" in captured["last"]


# --- Make wiring: credential-gated, raw report gitignored --------------------

def _target_block(target: str) -> tuple[str, str]:
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


def test_v2_2_eval_target_is_credential_gated() -> None:
    block, header = _target_block("eval-adversarial-v2-llm-v2-2")
    assert "check-llm-env" in header
    assert "--agent-system-version llm_candidate_v2_2" in block


def test_v2_2_decisions_target_is_credential_gated() -> None:
    _block, header = _target_block("semantic-model-decisions-adversarial-v2-llm-v2-2")
    assert "check-llm-env" in header


def test_v2_2_raw_report_is_gitignored() -> None:
    gi = GITIGNORE.read_text()
    assert "reports/llm_adversarial_v2_candidate_v2_2_eval.json" in gi
    assert "reports/llm_adversarial_v2_candidate_v2_2_semantic_replay_decisions.json" in gi
