"""Tests for the optional ``llm_candidate_v0`` agent-system profile.

The deterministic ``baseline_v0`` / ``improved_v0`` proof loop must not
change. The LLM profile must be reachable through the existing CLIs,
must refuse to run without credentials, and — when an adapter is
monkeypatched in — must preserve every deterministic decision the
runtime evaluator and offline graders inspect.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import app.agents.financial_links_reliability_agent as specialist_module
from app.agents import llm_adapter
from app.agents.llm_adapter import LLMAdapterConfigError, LLMResponse
from app.agents.profiles import (
    DEFAULT_PROFILE,
    KNOWN_PROFILES,
    AgentSystemProfile,
)
from app.runner import run_case
from evals.run import run_eval


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
MAKEFILE = ROOT / "Makefile"


def _load_case(case_id: str) -> dict:
    for raw in FULL_V0_PATH.read_text().splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        if record["case_id"] == case_id:
            return record
    raise AssertionError(f"case_id {case_id!r} not in v0 dataset")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_llm_profile_is_registered() -> None:
    assert AgentSystemProfile.LLM_CANDIDATE_V0.value == "llm_candidate_v0"
    assert "llm_candidate_v0" in KNOWN_PROFILES


def test_llm_profile_is_not_default() -> None:
    assert DEFAULT_PROFILE == AgentSystemProfile.IMPROVED_V0
    assert DEFAULT_PROFILE.value != "llm_candidate_v0"


# ---------------------------------------------------------------------------
# Deterministic profiles must stay untouched
# ---------------------------------------------------------------------------

def test_improved_v0_output_unchanged_on_case_fl_v0_005() -> None:
    """Snapshot of the deterministic improved profile on a representative case.

    The exact draft text, policy citation set, tool calls, and approval
    decision must not drift when the LLM profile is added.
    """

    case = _load_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="improved_v0")
    output = result.agent_output

    # Policy citations
    cited = {ref.policy_id for ref in output.policy_references}
    assert cited == {"FL-PARTNER-FALLBACK-002", "FL-COPY-STALE-003"}

    # Tools called (in order)
    tools = [tc.tool for tc in output.tool_calls]
    assert tools == [
        "lookup_consent_state",
        "lookup_institution_status",
        "lookup_partner_config",
        "lookup_policy",
        "lookup_policy",
    ]

    # Approval decision
    assert output.approval.required is True
    assert output.approval.approver_role == "partner_support_analyst"

    # Draft is the deterministic compose_draft output and does NOT
    # contain LLM-style hedges or guarantees.
    assert "Synthetic draft for analyst review." in output.draft_text
    assert "real-time" not in output.draft_text.lower() or (
        # the deterministic copy uses "no real-time guarantee is implied"
        "no real-time guarantee is implied" in output.draft_text
    )


def test_baseline_v0_still_fails_on_case_fl_v0_005() -> None:
    """The planted POLICY_MISS must still surface on baseline."""

    case = _load_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="baseline_v0")
    cited = {ref.policy_id for ref in result.agent_output.policy_references}
    assert "FL-PARTNER-FALLBACK-002" not in cited


# ---------------------------------------------------------------------------
# LLM profile without credentials must fail loudly
# ---------------------------------------------------------------------------

def test_llm_profile_raises_config_error_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    case = _load_case("case_fl_v0_005")
    with pytest.raises(LLMAdapterConfigError) as exc:
        run_case(case, agent_system_version="llm_candidate_v0")
    assert "ANTHROPIC_API_KEY" in str(exc.value)


def test_llm_adapter_directly_raises_on_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMAdapterConfigError):
        llm_adapter.generate_financial_links_draft("anything")


# ---------------------------------------------------------------------------
# LLM profile with a monkeypatched adapter
# ---------------------------------------------------------------------------

_FAKE_DRAFT = (
    "Synthetic LLM draft: please re-confirm consent before any remediation. "
    "We do not guarantee a refresh time and the linked account is not real time."
)
# Fixed synthetic token counts so cost-aggregation tests are deterministic.
_FAKE_INPUT_TOKENS = 250
_FAKE_OUTPUT_TOKENS = 120
_FAKE_MODEL = "claude-sonnet-4-5"


def _fake_adapter(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
    """Return a fixed LLMResponse so tests are deterministic across runs.

    Use ``LLMResponse.from_text`` so the rate-table lookup runs against
    the real ``configs/llm_cost_rates.yaml`` and exercises the same
    cost-estimation codepath as a credentialed run.
    """

    return LLMResponse.from_text(
        _FAKE_DRAFT,
        model=_FAKE_MODEL,
        input_tokens=_FAKE_INPUT_TOKENS,
        output_tokens=_FAKE_OUTPUT_TOKENS,
    )


def test_llm_profile_with_fake_adapter_produces_agent_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Monkeypatch the adapter so we never need a real API key."""

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _fake_adapter,
    )
    case = _load_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="llm_candidate_v0")
    output = result.agent_output

    # Draft is the LLM output, not the deterministic draft.
    assert output.draft_text == _FAKE_DRAFT

    # All deterministic decisions match what improved_v0 does for this case.
    cited = {ref.policy_id for ref in output.policy_references}
    assert cited == {"FL-PARTNER-FALLBACK-002", "FL-COPY-STALE-003"}

    tools = [tc.tool for tc in output.tool_calls]
    assert tools == [
        "lookup_consent_state",
        "lookup_institution_status",
        "lookup_partner_config",
        "lookup_policy",
        "lookup_policy",
    ]

    assert output.approval.required is True
    assert output.approval.approver_role == "partner_support_analyst"

    # The trace from the graph-backed runner records the LLM profile.
    assert result.trace.agent_system_version == "llm_candidate_v0"
    # Evaluator still ran end-to-end.
    assert result.trace.evaluator_report is not None
    assert result.trace.evaluator_report.checks


def test_llm_profile_threads_estimated_cost_into_agent_output_and_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cost-capture gap is closed: agent output + trace + report all
    carry a non-zero est_cost_usd derived from the rate table."""

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _fake_adapter,
    )
    case = _load_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="llm_candidate_v0")

    # Agent output carries the token counts and the resolved model.
    output = result.agent_output
    assert output.llm_input_tokens == _FAKE_INPUT_TOKENS
    assert output.llm_output_tokens == _FAKE_OUTPUT_TOKENS
    assert output.llm_model == _FAKE_MODEL
    assert output.llm_cost_estimation_note == "rate_used"

    # Expected cost: 250 * 3.0 / 1e6 + 120 * 15.0 / 1e6 = 0.00075 + 0.0018 = 0.00255
    expected = round(
        (_FAKE_INPUT_TOKENS * 3.0 + _FAKE_OUTPUT_TOKENS * 15.0) / 1_000_000, 6
    )
    assert output.est_cost_usd == expected, (
        f"agent output cost mismatch: expected {expected}, got {output.est_cost_usd}"
    )
    # The trace must mirror the agent's cost — no hardcoded 0.0 leaks.
    assert result.trace.est_cost_usd == expected


def test_llm_profile_eval_report_aggregates_cost(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A full smoke-slice run with the LLM profile aggregates per-case
    cost into synthetic_cost_summary.total_est_cost_usd."""

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _fake_adapter,
    )
    report_path = tmp_path / "report.json"
    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        report_out=report_path,
        agent_system_version="llm_candidate_v0",
    )

    per_case_costs = [c.est_cost_usd for c in report.per_case]
    assert all(c > 0.0 for c in per_case_costs), (
        f"every llm_candidate_v0 case must report a non-zero est_cost_usd; "
        f"got {per_case_costs}"
    )
    expected_total = round(sum(per_case_costs), 6)
    summary_total = report.synthetic_cost_summary["total_est_cost_usd"]
    assert summary_total == expected_total, (
        f"synthetic_cost_summary total mismatch: expected {expected_total}, "
        f"got {summary_total}"
    )
    assert summary_total > 0.0
    cost_note = report.synthetic_cost_summary["note"]
    assert "credential-gated LLM trace metadata" in cost_note
    assert "deterministic 0.0 placeholder" not in cost_note
    latency_note = report.synthetic_latency_envelope["measured_ms"]["note"]
    assert "including credential-gated LLM" in latency_note
    assert "deterministic runner only" not in latency_note


def test_deterministic_profile_still_reports_zero_cost(tmp_path: Path) -> None:
    """The cost path must not leak into the deterministic proof loop."""

    report_path = tmp_path / "report.json"
    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        report_out=report_path,
        agent_system_version="improved_v0",
    )
    assert all(c.est_cost_usd == 0.0 for c in report.per_case)
    assert report.synthetic_cost_summary["total_est_cost_usd"] == 0.0
    assert "deterministic 0.0 placeholder" in report.synthetic_cost_summary["note"]


def test_llm_profile_trace_preserves_graph_node_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _fake_adapter,
    )
    case = _load_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="llm_candidate_v0")

    # case_fl_v0_005 requires approval → HumanApprovalNode is on the path.
    path = result.trace.specialist_path
    assert "HumanApprovalNode" in path
    assert path.index("EvaluatorNode") < path.index("HumanApprovalNode")
    assert path.index("HumanApprovalNode") < path.index("FinalResponseComposer")


def test_llm_profile_runtime_evaluator_runs_against_llm_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the LLM produces unsafe copy, the runtime evaluator must catch it."""

    def _bad_adapter(prompt: str, **kwargs) -> LLMResponse:  # noqa: ARG001
        return LLMResponse.from_text(
            "We guarantee the linked account will refresh in real time.",
            model=_FAKE_MODEL,
            input_tokens=_FAKE_INPUT_TOKENS,
            output_tokens=_FAKE_OUTPUT_TOKENS,
        )

    monkeypatch.setattr(
        specialist_module._llm_adapter,
        "generate_financial_links_draft",
        _bad_adapter,
    )
    case = _load_case("case_fl_v0_005")
    result = run_case(case, agent_system_version="llm_candidate_v0")

    failing = {c.name for c in result.trace.evaluator_report.checks if not c.ok}
    assert "unsupported_claim" in failing


def test_run_eval_with_llm_profile_no_credentials_fails_cleanly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """run_eval over the smoke slice with LLM profile and no creds must raise loudly."""

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMAdapterConfigError):
        run_eval(
            dataset_path=SMOKE_PATH,
            traces_out=tmp_path / "traces",
            agent_system_version="llm_candidate_v0",
        )


def test_run_eval_cli_with_llm_profile_no_credentials_exits_nonzero(
    tmp_path: Path,
) -> None:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}  # strip ANTHROPIC_API_KEY
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_eval.py"),
            "--dataset",
            str(SMOKE_PATH),
            "--traces-out",
            str(tmp_path / "traces"),
            "--report-out",
            str(tmp_path / "report.json"),
            "--agent-system-version",
            "llm_candidate_v0",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    assert "anthropic_api_key" in combined or "llm_candidate_v0" in combined


def test_run_case_cli_accepts_llm_profile_as_choice() -> None:
    """The CLI must list llm_candidate_v0 as a valid --agent-system-version choice."""

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_case.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "llm_candidate_v0" in result.stdout


# ---------------------------------------------------------------------------
# Make targets must NOT use the LLM profile
# ---------------------------------------------------------------------------

def test_deterministic_makefile_recipes_do_not_invoke_llm_profile() -> None:
    """Any ``llm_candidate_*`` profile may only be invoked inside opt-in
    LLM targets.

    The deterministic public proof loop must never request an LLM
    profile by name. The targets that legitimately do are
    ``eval-smoke-llm``, ``eval-adversarial-llm``, and
    ``eval-adversarial-llm-v1`` (plus the ``check-llm-env`` preflight,
    whose recipe doesn't name the profile; the card-rendering targets
    reference report paths but do not invoke an LLM profile directly).
    """

    import re

    makefile = MAKEFILE.read_text()

    # Split on blank-line-followed-by-target-name boundaries by walking
    # lines and grouping by current target.
    current: str | None = None
    target_recipes: dict[str, list[str]] = {}
    for line in makefile.splitlines():
        if not line.startswith(("\t", " ", "#")) and ":" in line:
            head = line.split(":", 1)[0].strip()
            if re.match(r"^[A-Za-z0-9_\-]+$", head):
                current = head
                target_recipes.setdefault(current, [])
                continue
        if current is not None and line.startswith("\t"):
            target_recipes[current].append(line)

    allowed = {
        "eval-smoke-llm",
        "eval-card-llm-smoke",
        "eval-adversarial-llm",
        "eval-card-adversarial-llm",
        "eval-adversarial-llm-v1",
        "eval-card-adversarial-llm-v1",
        # Credentialed repeat-run capture (opt-in, gated by check-llm-env).
        "repeat-adversarial-llm-v0",
        "repeat-adversarial-llm-v1",
        # Opt-in adversarial v1 (12-case) LLM candidate evidence loop
        # (gated by check-llm-env; never in CI).
        "eval-adversarial-v1-llm-v0",
        "eval-adversarial-v1-llm-v1",
        "eval-card-adversarial-v1-llm",
        "semantic-model-decisions-adversarial-v1-llm-v0",
        "semantic-model-decisions-adversarial-v1-llm-v1",
    }

    llm_profile_token = re.compile(r"llm_candidate_v\d+")

    def _is_invocation(step: str) -> bool:
        """Skip @echo / printf documentation lines; only real recipe lines count."""

        stripped = step.lstrip("\t").lstrip()
        if stripped.startswith("@echo") or stripped.startswith("echo "):
            return False
        if stripped.startswith("@printf") or stripped.startswith("printf "):
            return False
        return bool(llm_profile_token.search(step))

    offenders = {
        target: [step for step in recipe if _is_invocation(step)]
        for target, recipe in target_recipes.items()
        if target not in allowed
        and any(_is_invocation(step) for step in recipe)
    }
    assert not offenders, (
        f"deterministic Make targets must not invoke any llm_candidate_v* "
        f"profile; found offenders: {sorted(offenders)}"
    )
