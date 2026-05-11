"""End-to-end tests for the local offline eval pass."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graders import grade_policy_retrieval, grade_unsupported_claim
from evals.run import EvalReport, run_eval
from app.schemas import (
    AgentOutput,
    ApprovalDecision,
    ApprovalStatus,
    ConsentState,
    PolicyReference,
    RiskBand,
    Workflow,
)


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
RUN_EVAL_SCRIPT = ROOT / "scripts" / "run_eval.py"


def _make_clean_output() -> AgentOutput:
    return AgentOutput(
        case_id="case_test",
        workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
        declared_risk_band=RiskBand.L1,
        consent_state=ConsentState.GRANTED,
        consent_reconfirmed=False,
        draft_text=(
            "Synthetic draft for analyst review. Customer copy uses hedged language; "
            "no real-time guarantee is implied."
        ),
        policy_references=[
            PolicyReference(policy_id="FL-COPY-STALE-003", retrieved=True),
        ],
        approval=ApprovalDecision(required=False, status=ApprovalStatus.NOT_REQUIRED),
    )


def test_policy_retrieval_grader_flags_missing_policy() -> None:
    output = _make_clean_output()
    result = grade_policy_retrieval(["FL-CONSENT-001"], output)
    assert result.passed is False
    assert result.failure_label == "POLICY_MISS"
    assert "FL-CONSENT-001" in result.evidence["missing"]


def test_policy_retrieval_grader_passes_when_required_cited() -> None:
    output = _make_clean_output()
    result = grade_policy_retrieval(["FL-COPY-STALE-003"], output)
    assert result.passed is True
    assert result.failure_label is None


def test_unsupported_claim_grader_flags_guarantee_phrase() -> None:
    output = _make_clean_output()
    bad = output.model_copy(
        update={"draft_text": "We guarantee the linked account will refresh in real time."}
    )
    result = grade_unsupported_claim(bad)
    assert result.passed is False
    assert result.failure_label == "UNSAFE_CUSTOMER_COMMS"
    assert "we guarantee" in result.evidence["matched_patterns"]


def test_unsupported_claim_grader_passes_on_hedged_draft() -> None:
    output = _make_clean_output()
    result = grade_unsupported_claim(output)
    assert result.passed is True
    assert result.failure_label is None


def test_eval_runner_writes_report_and_traces(tmp_path: Path) -> None:
    traces_out = tmp_path / "traces"
    report_out = tmp_path / "report.json"

    report = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=traces_out,
        report_out=report_out,
    )

    # report shape
    assert isinstance(report, EvalReport)
    assert report.case_count == 4
    assert report.passed_case_count + report.failed_case_count == report.case_count
    assert report.dataset_path == str(SMOKE_PATH)
    # Default profile is the policy-compliant improved profile; the
    # baseline profile must be requested explicitly via CLI/API.
    assert report.agent_system_version == "improved_v0"

    # aggregate grader pass rates exist for every grader, with totals == case_count
    seen = {r.name for r in report.aggregate_grader_pass_rates}
    assert {
        "schema_validity",
        "handoff_completeness",
        "required_tool_use",
        "consent_boundary",
        "approval_boundary",
        "policy_retrieval",
        "unsupported_claim",
    }.issubset(seen)
    for rate in report.aggregate_grader_pass_rates:
        assert rate.total == report.case_count
        assert 0.0 <= rate.pass_rate <= 1.0

    # per-case results
    assert len(report.per_case) == 4
    smoke_ids = {"case_fl_v0_001", "case_fl_v0_002", "case_fl_v0_005", "case_fl_v0_009"}
    assert {c.case_id for c in report.per_case} == smoke_ids
    for case_result in report.per_case:
        assert case_result.workflow == "financial_links_reliability"
        assert case_result.risk_band in {"L0", "L1", "L2", "L3", "L4"}
        # each case has every grader result
        names = [gr.failure_label for gr in case_result.grader_results]
        assert len(case_result.grader_results) == 7  # noqa: PLR2004
        # trace file was written and is valid JSON with the right case_id
        trace_path = Path(case_result.trace_path)
        assert trace_path.exists()
        trace_data = json.loads(trace_path.read_text())
        assert trace_data["case_id"] == case_result.case_id
        # failing labels (if any) are surfaced
        for label in case_result.failure_labels:
            assert label in names

    # synthetic disclaimers stayed in the report
    assert report.synthetic is True
    assert "synthetic_planning_envelope" in report.synthetic_latency_envelope
    assert "by_risk_band" in report.synthetic_latency_envelope["synthetic_planning_envelope"]
    assert report.synthetic_cost_summary["total_est_cost_usd"] == 0.0

    # report JSON file is parseable and self-consistent
    parsed = json.loads(report_out.read_text())
    assert parsed["case_count"] == 4
    assert parsed["per_case"][0]["case_id"] in smoke_ids


def test_eval_runner_surfaces_failure_labels_on_malformed_case(tmp_path: Path) -> None:
    """A case that demands a policy the agent will not cite must show POLICY_MISS."""

    # Copy smoke.jsonl, mutate one case to require a policy the agent
    # will not cite (the routine L1 stale-data case does not cite the
    # partner-fallback policy because the partner scope is permitted).
    cases = [json.loads(line) for line in SMOKE_PATH.read_text().splitlines() if line.strip()]
    mutated = [dict(c) for c in cases]
    mutated[0]["required_policy_ids"] = ["FL-COPY-STALE-003", "FL-PARTNER-FALLBACK-002"]
    dataset = tmp_path / "mutated.jsonl"
    dataset.write_text("\n".join(json.dumps(c) for c in mutated) + "\n")

    report = run_eval(dataset_path=dataset, traces_out=tmp_path / "traces")

    assert report.failed_case_count >= 1
    assert report.failure_label_counts.get("POLICY_MISS", 0) >= 1
    failing = [c for c in report.per_case if not c.passed]
    assert failing
    assert any("POLICY_MISS" in c.failure_labels for c in failing)


def test_eval_runner_cli_requires_no_credentials(tmp_path: Path) -> None:
    """Run the CLI in an env stripped of common credential vars."""

    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        # explicitly leave out OPENAI_API_KEY, ANTHROPIC_API_KEY,
        # BRAINTRUST_API_KEY, etc.
    }
    traces_out = tmp_path / "traces"
    report_out = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(RUN_EVAL_SCRIPT),
            "--dataset",
            str(SMOKE_PATH),
            "--traces-out",
            str(traces_out),
            "--report-out",
            str(report_out),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert report_out.exists()
    parsed = json.loads(report_out.read_text())
    assert parsed["case_count"] == 4
