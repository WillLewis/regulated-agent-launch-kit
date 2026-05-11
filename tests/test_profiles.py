"""Baseline-vs-improved agent-system profile tests.

These tests anchor the honest failing-baseline / improved-pass narrative
the eval loop relies on. They are intentionally tied to specific
deliberately-weak behaviors in the baseline profile (skipped
partner-config on healthy routes, omitted FL-PARTNER-FALLBACK-002
citation, planted real-time overpromise). If a future improvement to
the baseline changes those targets, the dataset and these tests must
move together.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.agents.profiles import (
    DEFAULT_PROFILE,
    KNOWN_PROFILES,
    AgentSystemProfile,
    normalize_profile,
)
from app.runner import run_case
from evals.run import run_eval


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
RUN_EVAL_SCRIPT = ROOT / "scripts" / "run_eval.py"


def test_profile_enum_lists_baseline_and_improved() -> None:
    assert AgentSystemProfile.BASELINE_V0.value == "baseline_v0"
    assert AgentSystemProfile.IMPROVED_V0.value == "improved_v0"
    assert "baseline_v0" in KNOWN_PROFILES
    assert "improved_v0" in KNOWN_PROFILES
    assert DEFAULT_PROFILE == AgentSystemProfile.IMPROVED_V0


def test_normalize_profile_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        normalize_profile("not_a_real_profile")


def test_baseline_smoke_eval_has_at_least_one_failure(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        agent_system_version="baseline_v0",
    )
    assert report.agent_system_version == "baseline_v0"
    assert report.failed_case_count >= 1, report.model_dump()
    assert report.failure_label_counts, "baseline smoke run should surface ≥1 failure label"


def test_baseline_full_v0_has_three_failures_across_two_labels(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp_path / "traces",
        agent_system_version="baseline_v0",
    )
    failing_cases = [c for c in report.per_case if not c.passed]
    distinct_labels = {label for case in failing_cases for label in case.failure_labels}

    assert report.failed_case_count >= 3, (
        f"expected ≥3 failing cases for baseline_v0 on v0; got "
        f"{report.failed_case_count}: {[c.case_id for c in failing_cases]}"
    )
    assert len(distinct_labels) >= 2, (
        f"expected ≥2 distinct failure labels for baseline_v0 on v0; got "
        f"{sorted(distinct_labels)}"
    )


def test_improved_smoke_eval_passes(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        agent_system_version="improved_v0",
    )
    assert report.agent_system_version == "improved_v0"
    assert report.failed_case_count == 0, [
        (c.case_id, c.failure_labels) for c in report.per_case if not c.passed
    ]
    assert report.failure_label_counts == {}


def test_report_records_agent_system_version_on_traces(tmp_path: Path) -> None:
    """Every per-case trace JSON should reflect the requested profile."""

    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "traces",
        agent_system_version="baseline_v0",
    )
    for case in report.per_case:
        trace = json.loads(Path(case.trace_path).read_text())
        assert trace["agent_system_version"] == "baseline_v0"


def test_run_eval_cli_accepts_agent_system_version(tmp_path: Path) -> None:
    report_out = tmp_path / "baseline.json"
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_EVAL_SCRIPT),
            "--dataset",
            str(SMOKE_PATH),
            "--traces-out",
            str(tmp_path / "traces"),
            "--report-out",
            str(report_out),
            "--agent-system-version",
            "baseline_v0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    parsed = json.loads(report_out.read_text())
    assert parsed["agent_system_version"] == "baseline_v0"
    assert parsed["failed_case_count"] >= 1


def test_run_eval_cli_rejects_unknown_profile(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_EVAL_SCRIPT),
            "--dataset",
            str(SMOKE_PATH),
            "--traces-out",
            str(tmp_path / "traces"),
            "--report-out",
            str(tmp_path / "report.json"),
            "--agent-system-version",
            "bogus_v0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "bogus_v0" in result.stderr or "invalid choice" in result.stderr


def test_baseline_profile_is_deterministic(tmp_path: Path) -> None:
    """Same case + same profile → identical agent output (modulo trace_id)."""

    case_dict = next(
        json.loads(line) for line in SMOKE_PATH.read_text().splitlines() if line.strip()
    )
    first = run_case(case_dict, agent_system_version="baseline_v0")
    second = run_case(case_dict, agent_system_version="baseline_v0")
    assert first.agent_output.model_dump() == second.agent_output.model_dump()


def test_run_case_default_is_improved_profile() -> None:
    case_dict = next(
        json.loads(line) for line in SMOKE_PATH.read_text().splitlines() if line.strip()
    )
    result = run_case(case_dict)
    assert result.trace.agent_system_version == "improved_v0"


def test_baseline_vs_improved_diverge_on_partner_fallback_case(tmp_path: Path) -> None:
    """case_fl_v0_005 (L2 partner_fallback_blocked) is the canonical baseline failure.

    Baseline omits FL-PARTNER-FALLBACK-002 → POLICY_MISS;
    improved still cites it → pass.
    """

    case_dict = next(
        json.loads(line)
        for line in FULL_V0_PATH.read_text().splitlines()
        if line.strip() and json.loads(line)["case_id"] == "case_fl_v0_005"
    )
    baseline_cited = {
        ref.policy_id
        for ref in run_case(case_dict, agent_system_version="baseline_v0").agent_output.policy_references
    }
    improved_cited = {
        ref.policy_id
        for ref in run_case(case_dict, agent_system_version="improved_v0").agent_output.policy_references
    }
    assert "FL-PARTNER-FALLBACK-002" not in baseline_cited
    assert "FL-PARTNER-FALLBACK-002" in improved_cited
