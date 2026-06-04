"""Tests for the optional fixture-backed semantic eval lane.

The default eval runner remains the credential-free eight-grader path.
When a SemanticDecision fixture file is explicitly supplied, the runner
adds one extra grader row: ``unsupported_claim_semantic``. No model calls
are made; the fixture file is local JSON.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.run import load_semantic_decisions, run_eval


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_V1 = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v1.jsonl"
)
SEMANTIC_DECISIONS = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v1_semantic_decisions.json"
)
RUN_EVAL_SCRIPT = ROOT / "scripts" / "run_eval.py"


def _case_ids() -> list[str]:
    return [
        json.loads(line)["case_id"]
        for line in ADVERSARIAL_V1.read_text().splitlines()
        if line.strip()
    ]


def _rate(report, name: str):
    return next(r for r in report.aggregate_grader_pass_rates if r.name == name)


def test_semantic_decision_fixture_covers_both_profiles() -> None:
    case_ids = _case_ids()

    baseline = load_semantic_decisions(
        SEMANTIC_DECISIONS,
        profile="baseline_v0",
        expected_case_ids=case_ids,
    )
    improved = load_semantic_decisions(
        SEMANTIC_DECISIONS,
        profile="improved_v0",
        expected_case_ids=case_ids,
    )

    assert set(baseline) == set(case_ids)
    assert set(improved) == set(case_ids)
    assert sum(d.makes_unsupported_claim for d in baseline.values()) == 5
    assert sum(d.makes_unsupported_claim for d in improved.values()) == 0


def test_default_eval_report_shape_does_not_include_semantic_lane(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="improved_v0",
    )

    names = [r.name for r in report.aggregate_grader_pass_rates]
    assert "unsupported_claim_semantic" not in names
    assert len(report.per_case[0].grader_results) == 8

    parsed = json.loads((tmp_path / "report.json").read_text())
    parsed_names = [r["name"] for r in parsed["aggregate_grader_pass_rates"]]
    assert "unsupported_claim_semantic" not in parsed_names


def test_opt_in_semantic_lane_adds_ninth_grader_for_improved(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="improved_v0",
        semantic_decisions_path=SEMANTIC_DECISIONS,
    )

    names = [r.name for r in report.aggregate_grader_pass_rates]
    assert "unsupported_claim_semantic" in names
    assert len(report.per_case[0].grader_results) == 9
    semantic = _rate(report, "unsupported_claim_semantic")
    assert semantic.total == 12
    assert semantic.passed == 12
    assert semantic.pass_rate == 1.0
    assert report.passed_case_count == 12

    first_semantic = report.per_case[0].grader_results[7]
    assert first_semantic.evidence["grader_type"] == "semantic_fixture"


def test_opt_in_semantic_lane_surfaces_baseline_semantic_failures(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="baseline_v0",
        semantic_decisions_path=SEMANTIC_DECISIONS,
    )

    semantic = _rate(report, "unsupported_claim_semantic")
    assert semantic.total == 12
    assert semantic.passed == 7
    assert semantic.pass_rate == pytest.approx(7 / 12)

    case_001 = next(c for c in report.per_case if c.case_id == "case_fl_adv_v1_001")
    semantic_result = case_001.grader_results[7]
    assert semantic_result.failure_label == "UNSAFE_CUSTOMER_COMMS"
    assert semantic_result.evidence["grader_type"] == "semantic_fixture"
    assert semantic_result.evidence["calibration"] == "affirmative_overpromise"


def test_cli_accepts_semantic_decisions_fixture(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    traces_path = tmp_path / "traces"
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_EVAL_SCRIPT),
            "--dataset",
            str(ADVERSARIAL_V1),
            "--traces-out",
            str(traces_path),
            "--report-out",
            str(report_path),
            "--agent-system-version",
            "improved_v0",
            "--semantic-decisions",
            str(SEMANTIC_DECISIONS),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    parsed = json.loads(report_path.read_text())
    names = [r["name"] for r in parsed["aggregate_grader_pass_rates"]]
    assert "unsupported_claim_semantic" in names
    assert len(parsed["per_case"][0]["grader_results"]) == 9


def test_missing_case_decision_rejected(tmp_path: Path) -> None:
    fixture = json.loads(SEMANTIC_DECISIONS.read_text())
    fixture["decisions"]["improved_v0"].pop("case_fl_adv_v1_012")
    bad_path = tmp_path / "missing.json"
    bad_path.write_text(json.dumps(fixture))

    with pytest.raises(SystemExit) as exc:
        load_semantic_decisions(
            bad_path,
            profile="improved_v0",
            expected_case_ids=_case_ids(),
        )
    assert "missing semantic decisions" in str(exc.value)


def test_unknown_profile_decisions_rejected() -> None:
    with pytest.raises(SystemExit) as exc:
        load_semantic_decisions(
            SEMANTIC_DECISIONS,
            profile="llm_candidate_v1",
            expected_case_ids=_case_ids(),
        )
    assert "no semantic decisions for profile" in str(exc.value)

