"""Tests for the synthetic trace redaction script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from evals.run import run_eval
from scripts.redact_trace import redact


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "configs" / "redaction_policy.yaml"
REDACT_SCRIPT = ROOT / "scripts" / "redact_trace.py"
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"


def _policy() -> dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text())


@pytest.fixture(scope="module")
def baseline_trace_005(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Generate a fresh baseline v0 trace for case_fl_v0_005."""

    tmp = tmp_path_factory.mktemp("baseline_v0")
    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp,
        agent_system_version="baseline_v0",
    )
    return json.loads((tmp / "case_fl_v0_005.json").read_text())


# ---------------------------------------------------------------------------
# Preserved diagnostic fields
# ---------------------------------------------------------------------------

DIAGNOSTIC_TOP_LEVEL: tuple[str, ...] = (
    "trace_id",
    "case_id",
    "workflow",
    "risk_band",
    "agent_system_version",
    "specialist_path",
    "tool_calls",
    "evaluator_report",
    "approval",
    "grader_results",
    "failure_labels",
    "latency_ms",
    "est_cost_usd",
)


def test_redaction_preserves_diagnostic_top_level_fields(
    baseline_trace_005: dict[str, Any],
) -> None:
    redacted, _ = redact(baseline_trace_005, _policy())
    for field in DIAGNOSTIC_TOP_LEVEL:
        assert field in redacted, f"redacted trace dropped diagnostic field {field!r}"

    # tool sequence preserved (and non-empty for case_fl_v0_005)
    tools = [tc["tool"] for tc in redacted["tool_calls"]]
    assert tools, "tool_calls must survive redaction"
    assert "lookup_partner_config" in tools

    # evaluator check names preserved
    check_names = {c["name"] for c in redacted["evaluator_report"]["checks"]}
    assert "policy_citation" in check_names

    # approval decision preserved
    assert redacted["approval"]["required"] is True

    # failure labels preserved
    assert "POLICY_MISS" in redacted["failure_labels"]


# ---------------------------------------------------------------------------
# Removed / abstracted fields
# ---------------------------------------------------------------------------

def test_redaction_removes_user_partner_institution_ids(
    baseline_trace_005: dict[str, Any],
) -> None:
    redacted, report = redact(baseline_trace_005, _policy())

    # handoff route_context loses the IDs but the wrapper dict stays.
    route_context = redacted["handoff"]["route_context"]
    assert "institution_id" not in route_context
    assert "partner_id" not in route_context

    # every tool call has had its identifier args / outputs stripped.
    for tool_call in redacted["tool_calls"]:
        for forbidden in ("user_id", "institution_id", "partner_id"):
            assert forbidden not in tool_call["arguments"], tool_call
            assert forbidden not in tool_call["output"], tool_call

    # the report records what got removed.
    assert report["summary"]["removed_count"] > 0
    assert any("institution_id" in path for path in report["removed_paths"])
    assert any("user_id" in path for path in report["removed_paths"])


def test_redaction_abstracts_draft_text_and_excerpts(
    baseline_trace_005: dict[str, Any],
) -> None:
    redacted, report = redact(baseline_trace_005, _policy())

    assert redacted["final_response"] == "<draft_text_abstracted>"
    assert any(path.endswith(".final_response") for path in report["abstracted_paths"])
    # draft_excerpt under evaluator_report and grader_results is abstracted too.
    for check in redacted["evaluator_report"]["checks"]:
        if "draft_excerpt" in check.get("metadata", {}):
            assert check["metadata"]["draft_excerpt"] == "<draft_text_abstracted>"


# ---------------------------------------------------------------------------
# Redaction report categories
# ---------------------------------------------------------------------------

def test_report_lists_all_required_categories(baseline_trace_005: dict[str, Any]) -> None:
    _, report = redact(baseline_trace_005, _policy())

    for key in (
        "version",
        "synthetic",
        "policy_version",
        "removed_paths",
        "abstracted_paths",
        "preserved_top_level_fields",
        "preserve_fields_missing",
        "uncovered_top_level_fields",
        "summary",
    ):
        assert key in report, f"redaction report missing field {key!r}"

    assert report["synthetic"] is True
    assert report["policy_version"] == _policy()["version"]


def test_redacted_v0_trace_has_no_uncovered_top_level_fields(
    baseline_trace_005: dict[str, Any],
) -> None:
    """The committed policy should classify every top-level key in the v0 trace.

    If the trace schema grows, this test fires so the policy stays in sync.
    """

    _, report = redact(baseline_trace_005, _policy())
    assert report["uncovered_top_level_fields"] == [], report["uncovered_top_level_fields"]


def test_redacted_v0_trace_has_no_preserve_missing(
    baseline_trace_005: dict[str, Any],
) -> None:
    _, report = redact(baseline_trace_005, _policy())
    assert report["preserve_fields_missing"] == [], report["preserve_fields_missing"]


def test_report_summary_counts_match_path_lists(baseline_trace_005: dict[str, Any]) -> None:
    _, report = redact(baseline_trace_005, _policy())
    assert report["summary"]["removed_count"] == len(report["removed_paths"])
    assert report["summary"]["abstracted_count"] == len(report["abstracted_paths"])
    assert report["summary"]["preserved_count"] == len(report["preserved_top_level_fields"])
    assert report["summary"]["uncovered_count"] == len(report["uncovered_top_level_fields"])
    assert report["summary"]["preserve_missing_count"] == len(
        report["preserve_fields_missing"]
    )


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------

def test_cli_writes_redacted_file_and_report(tmp_path: Path) -> None:
    """Generate a baseline trace and redact it via the CLI."""

    eval_dir = tmp_path / "baseline_v0"
    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=eval_dir,
        agent_system_version="baseline_v0",
    )
    trace_path = eval_dir / "case_fl_v0_005.json"

    out = tmp_path / "case_fl_v0_005.redacted.json"
    report_out = tmp_path / "case_fl_v0_005.redaction_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(REDACT_SCRIPT),
            "--input",
            str(trace_path),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(out),
            "--report-out",
            str(report_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    assert report_out.exists()

    redacted = json.loads(out.read_text())
    assert redacted["case_id"] == "case_fl_v0_005"
    assert redacted["final_response"] == "<draft_text_abstracted>"

    report = json.loads(report_out.read_text())
    assert report["version"] == "redaction_report_v0"


def test_cli_rejects_missing_input(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REDACT_SCRIPT),
            "--input",
            str(tmp_path / "does_not_exist.json"),
            "--policy",
            str(POLICY_PATH),
            "--output",
            str(tmp_path / "out.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "trace not found" in result.stderr
