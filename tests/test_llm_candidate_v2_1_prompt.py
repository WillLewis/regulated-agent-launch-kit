"""Tests for the ``llm_candidate_v2_1`` residual-remediation profile (WIRED, NOT RUN).

The candidate-v2 run blocked on 3 residuals; the residual adjudication marked one
``candidate_actionable`` (``case_fl_adv_v2_017``, a conditional refresh-timing
expectation on a missing-institution case). v2.1 is v2's prompt with ONLY the
missing-metadata control tightened. These tests lock in:

1. ``LLM_CANDIDATE_V2_1`` is registered, opt-in (not default), distinct.
2. v2.1 tightens exactly the missing-metadata ban and nothing else (it equals v2
   with that single ban replaced); v2 is unchanged.
3. v2.1 preserves every other v2 control.
4. The drift-guard constant matches the v2 prompt's actual wording.
5. The agent routes v2.1 through ``_build_llm_prompt_v2_1``.
6. The credentialed v2.1 targets gate on ``check-llm-env`` and the raw report is
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
    _V2_MISSING_METADATA_BAN,
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


def test_v2_1_registered_opt_in_distinct() -> None:
    assert AgentSystemProfile.LLM_CANDIDATE_V2_1.value == "llm_candidate_v2_1"
    assert "llm_candidate_v2_1" in KNOWN_PROFILES
    assert DEFAULT_PROFILE != AgentSystemProfile.LLM_CANDIDATE_V2_1
    distinct = {
        AgentSystemProfile.LLM_CANDIDATE_V2.value,
        AgentSystemProfile.LLM_CANDIDATE_V2_1.value,
    }
    assert len(distinct) == 2


def test_v2_1_tightens_only_the_missing_metadata_ban() -> None:
    v2 = _build(specialist_module._build_llm_prompt_v2)
    v21 = _build(specialist_module._build_llm_prompt_v2_1)
    # v2.1 is exactly v2 with the single missing-metadata ban replaced.
    assert v21 == v2.replace(_V2_MISSING_METADATA_BAN, _V2_1_MISSING_METADATA_BAN, 1)
    # The tightened content is present in v2.1 and absent from v2.
    for marker in (
        "do NOT include any hypothetical or conditional timing",
        "Omit the customer-facing timing section ENTIRELY",
        "remediation cannot proceed until the missing identifier is provided",
    ):
        assert marker in v21, marker
        assert marker not in v2, f"v2 must NOT carry v2.1 text: {marker!r}"


def test_v2_1_preserves_all_v2_controls() -> None:
    v21 = _build(specialist_module._build_llm_prompt_v2_1)
    for marker in (
        "FORBIDDEN PHRASES",
        "M7 SEMANTIC BANS",
        "M7 STRUCTURAL CONTROLS",
        "Partner-scope decision table",
        "Operational-status overpromise",
    ):
        assert marker in v21, f"v2.1 dropped a v2 control: {marker!r}"


def test_drift_guard_constant_is_in_v2_prompt() -> None:
    """If v2's missing-metadata wording ever changes, _V2_MISSING_METADATA_BAN
    must be re-synced — otherwise v2.1 cannot tighten it. This guards that."""

    v2 = _build(specialist_module._build_llm_prompt_v2)
    assert _V2_MISSING_METADATA_BAN in v2


def test_v2_unchanged_still_has_original_ban() -> None:
    v2 = _build(specialist_module._build_llm_prompt_v2)
    assert _V2_MISSING_METADATA_BAN in v2
    assert "Omit the customer-facing timing section ENTIRELY" not in v2


def test_agent_routes_v2_1_through_v2_1_builder(monkeypatch: pytest.MonkeyPatch) -> None:
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

    run_case(case, agent_system_version="llm_candidate_v2")
    assert "Omit the customer-facing timing section ENTIRELY" not in captured["last"]

    run_case(case, agent_system_version="llm_candidate_v2_1")
    assert "Omit the customer-facing timing section ENTIRELY" in captured["last"]
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


def test_v2_1_eval_target_is_credential_gated() -> None:
    block, header = _target_block("eval-adversarial-v2-llm-v2-1")
    assert "check-llm-env" in header
    assert "--agent-system-version llm_candidate_v2_1" in block


def test_v2_1_decisions_target_is_credential_gated() -> None:
    _block, header = _target_block("semantic-model-decisions-adversarial-v2-llm-v2-1")
    assert "check-llm-env" in header


def test_v2_1_raw_report_is_gitignored() -> None:
    gi = GITIGNORE.read_text()
    assert "reports/llm_adversarial_v2_candidate_v2_1_eval.json" in gi
    assert "reports/llm_adversarial_v2_candidate_v2_1_semantic_replay_decisions.json" in gi
