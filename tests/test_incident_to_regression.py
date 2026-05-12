"""Tests for the incident-to-regression workflow.

Locks in the script's behavior, the shape of regression records, the
contents of the committed ``regressions_v0.jsonl`` fixture, and the
end-to-end pin: the improved profile must pass every regression the
baseline failed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.run import run_eval
from scripts.incident_to_regression import (
    REGRESSION_DATASET_ID,
    build_regression_record,
    write_record,
)


ROOT = Path(__file__).resolve().parents[1]
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
COMMITTED_REGRESSIONS = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "regressions_v0.jsonl"
)
INCIDENT_SCRIPT = ROOT / "scripts" / "incident_to_regression.py"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_dataset.py"


REGRESSION_REQUIRED_FIELDS: tuple[str, ...] = (
    "case_id",
    "regression_case_id",
    "source_case_id",
    "source_agent_system_version",
    "source_dataset_path",
    "source_report_path",
    "created_from_report",
    "dataset_id",
    "workflow",
    "risk_band",
    "case_type",
    "consent_sensitive",
    "synthetic_facts",
    "expected_route",
    "required_tools",
    "required_policy_ids",
    "expected_approval",
    "expected_behavior",
    "prohibited_behavior",
    "failure_labels",
    "trace_path",
    "review_status",
    "synthetic",
    "notes",
)


@pytest.fixture()
def baseline_v0_report(tmp_path: Path) -> Path:
    report_out = tmp_path / "baseline_v0.json"
    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp_path / "baseline_traces",
        report_out=report_out,
        agent_system_version="baseline_v0",
    )
    return report_out


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _source_case(case_id: str) -> dict:
    for case in _load_jsonl(FULL_V0_PATH):
        if case["case_id"] == case_id:
            return case
    raise AssertionError(f"case_id {case_id!r} not in v0 dataset")


# ---------------------------------------------------------------------------
# Pure builder
# ---------------------------------------------------------------------------

def test_build_regression_record_for_case_fl_v0_005(baseline_v0_report: Path) -> None:
    report = json.loads(baseline_v0_report.read_text())
    record = build_regression_record(
        report=report,
        case_id="case_fl_v0_005",
        source_case=_source_case("case_fl_v0_005"),
        review_status="pending_review",
        report_path=baseline_v0_report,
    )
    assert record["case_id"] == "case_fl_v0_005__regression_v0"
    assert record["regression_case_id"] == "case_fl_v0_005__regression_v0"
    assert record["source_case_id"] == "case_fl_v0_005"
    assert record["source_agent_system_version"] == "baseline_v0"
    assert "POLICY_MISS" in record["failure_labels"]
    assert record["review_status"] == "pending_review"
    assert record["dataset_id"] == REGRESSION_DATASET_ID
    assert record["workflow"] == "financial_links_reliability"
    assert record["synthetic"] is True
    assert "FL-PARTNER-FALLBACK-002" in record["required_policy_ids"]


def test_build_record_includes_every_required_field(baseline_v0_report: Path) -> None:
    report = json.loads(baseline_v0_report.read_text())
    record = build_regression_record(
        report=report,
        case_id="case_fl_v0_010",
        source_case=_source_case("case_fl_v0_010"),
        review_status="pending_review",
        report_path=baseline_v0_report,
    )
    missing = [f for f in REGRESSION_REQUIRED_FIELDS if f not in record]
    assert not missing, f"regression record missing fields: {missing}"
    assert record["trace_path"], "trace_path must be carried forward from the report"
    assert "case_fl_v0_010" in record["notes"]


def test_build_rejects_passing_case(baseline_v0_report: Path) -> None:
    report = json.loads(baseline_v0_report.read_text())
    with pytest.raises(SystemExit) as exc:
        build_regression_record(
            report=report,
            case_id="case_fl_v0_001",
            source_case=_source_case("case_fl_v0_001"),
            review_status="pending_review",
            report_path=baseline_v0_report,
        )
    assert "no failure_labels" in str(exc.value)


def test_build_rejects_unknown_case_id(baseline_v0_report: Path) -> None:
    report = json.loads(baseline_v0_report.read_text())
    with pytest.raises(SystemExit) as exc:
        build_regression_record(
            report=report,
            case_id="case_fl_v0_nope",
            source_case={"case_id": "case_fl_v0_nope"},
            review_status="pending_review",
            report_path=baseline_v0_report,
        )
    assert "not found in report" in str(exc.value)


# ---------------------------------------------------------------------------
# write_record / append dedup
# ---------------------------------------------------------------------------

def test_append_mode_dedupes_by_regression_case_id(
    baseline_v0_report: Path, tmp_path: Path
) -> None:
    report = json.loads(baseline_v0_report.read_text())
    record = build_regression_record(
        report=report,
        case_id="case_fl_v0_005",
        source_case=_source_case("case_fl_v0_005"),
        review_status="pending_review",
        report_path=baseline_v0_report,
    )

    out = tmp_path / "regressions.jsonl"
    first = write_record(out, record, append=True)
    second = write_record(out, record, append=True)
    assert first == "wrote"
    assert second == "skipped_duplicate"
    assert len(_load_jsonl(out)) == 1


def test_default_mode_overwrites(baseline_v0_report: Path, tmp_path: Path) -> None:
    report = json.loads(baseline_v0_report.read_text())
    record = build_regression_record(
        report=report,
        case_id="case_fl_v0_005",
        source_case=_source_case("case_fl_v0_005"),
        review_status="pending_review",
        report_path=baseline_v0_report,
    )

    out = tmp_path / "regressions.jsonl"
    write_record(out, record, append=False)
    write_record(out, record, append=False)
    assert len(_load_jsonl(out)) == 1


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

def test_cli_seeds_a_regression_record(
    baseline_v0_report: Path, tmp_path: Path
) -> None:
    out = tmp_path / "regressions.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(INCIDENT_SCRIPT),
            "--eval-report",
            str(baseline_v0_report),
            "--case-id",
            "case_fl_v0_005",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    records = _load_jsonl(out)
    assert len(records) == 1
    assert records[0]["regression_case_id"] == "case_fl_v0_005__regression_v0"


def test_cli_rejects_passing_case(baseline_v0_report: Path, tmp_path: Path) -> None:
    out = tmp_path / "regressions.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(INCIDENT_SCRIPT),
            "--eval-report",
            str(baseline_v0_report),
            "--case-id",
            "case_fl_v0_001",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "no failure_labels" in (result.stderr + result.stdout)
    assert not out.exists()


# ---------------------------------------------------------------------------
# Committed regressions_v0.jsonl fixture
# ---------------------------------------------------------------------------

def test_committed_regressions_exists_and_has_three_records() -> None:
    assert COMMITTED_REGRESSIONS.exists()
    records = _load_jsonl(COMMITTED_REGRESSIONS)
    assert len(records) == 3
    ids = {r["regression_case_id"] for r in records}
    assert ids == {
        "case_fl_v0_005__regression_v0",
        "case_fl_v0_006__regression_v0",
        "case_fl_v0_010__regression_v0",
    }


def test_committed_regressions_have_required_fields() -> None:
    for record in _load_jsonl(COMMITTED_REGRESSIONS):
        missing = [f for f in REGRESSION_REQUIRED_FIELDS if f not in record]
        assert not missing, (
            f"regression record {record.get('regression_case_id')} "
            f"missing fields: {missing}"
        )
        assert record["review_status"] == "pending_review"


def test_committed_regressions_have_no_duplicate_ids() -> None:
    records = _load_jsonl(COMMITTED_REGRESSIONS)
    ids = [r["regression_case_id"] for r in records]
    assert len(ids) == len(set(ids)), f"duplicate regression_case_ids: {ids}"


def test_committed_regressions_pass_dataset_validator() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(COMMITTED_REGRESSIONS)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_improved_profile_passes_all_committed_regressions(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=COMMITTED_REGRESSIONS,
        traces_out=tmp_path / "traces",
        agent_system_version="improved_v0",
    )
    assert report.failed_case_count == 0, [
        (c.case_id, c.failure_labels) for c in report.per_case if not c.passed
    ]
    assert report.failure_label_counts == {}


def test_baseline_profile_still_fails_all_committed_regressions(tmp_path: Path) -> None:
    """The pin should be tight: baseline replays the same failures we captured."""

    report = run_eval(
        dataset_path=COMMITTED_REGRESSIONS,
        traces_out=tmp_path / "traces",
        agent_system_version="baseline_v0",
    )
    assert report.failed_case_count == report.case_count
    # the captured labels should re-appear when the baseline replays them
    assert "POLICY_MISS" in report.failure_label_counts
