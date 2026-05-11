"""Tests for the local before/after eval-card generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.run import run_eval

import scripts.generate_eval_card as generator
from scripts.generate_eval_card import (
    LAUNCH_POSTURE,
    SYNTHETIC_DISCLAIMER,
    generate_eval_card,
)


ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
GENERATOR_SCRIPT = ROOT / "scripts" / "generate_eval_card.py"


@pytest.fixture()
def baseline_and_improved_reports(tmp_path: Path) -> tuple[Path, Path]:
    """Run both profiles once per test that needs paired reports."""

    baseline_report = tmp_path / "baseline.json"
    improved_report = tmp_path / "improved.json"
    run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline_report,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=improved_report,
        agent_system_version="improved_v0",
    )
    return baseline_report, improved_report


def test_card_names_both_profiles(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    out = tmp_path / "card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()
    assert "baseline_v0" in markdown
    assert "improved_v0" in markdown
    # the title and synthetic disclaimer must both be present
    assert "Local Eval Card" in markdown
    assert SYNTHETIC_DISCLAIMER in markdown


def test_card_includes_failure_labels_from_baseline(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    baseline_data = json.loads(baseline.read_text())
    assert baseline_data["failure_label_counts"], (
        "baseline_v0 must surface at least one failure label for the card test"
    )

    out = tmp_path / "card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()

    for label in baseline_data["failure_label_counts"]:
        assert label in markdown, f"card missing label {label!r}"


def test_card_includes_trace_paths_for_failing_cases(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    baseline_data = json.loads(baseline.read_text())

    out = tmp_path / "card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()

    failing = [c for c in baseline_data["per_case"] if not c["passed"]]
    assert failing, "baseline_v0 must have at least one failing case"
    for case in failing:
        assert case["case_id"] in markdown
        assert case["trace_path"] in markdown


def test_card_carries_synthetic_no_production_language(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    out = tmp_path / "card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()
    lower = markdown.lower()

    assert "synthetic" in lower
    assert "no production-readiness" in lower or "no production" in lower

    # Narrow positive-claim list. "ready for pilot" / "ready for production"
    # are intentionally NOT in this list because the card includes the legit
    # phrase "NOT READY FOR PILOT" — guarding against unambiguous overclaims
    # is enough here.
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"eval card must not claim {phrase!r}"


def test_card_includes_launch_posture(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    out = tmp_path / "card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()
    assert "NOT READY FOR PILOT" in markdown
    assert LAUNCH_POSTURE in markdown


def test_generator_rejects_missing_baseline(tmp_path: Path) -> None:
    improved = tmp_path / "improved.json"
    run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=improved,
        agent_system_version="improved_v0",
    )
    with pytest.raises(SystemExit) as exc:
        generate_eval_card(tmp_path / "does_not_exist.json", improved, tmp_path / "card.md")
    assert "report not found" in str(exc.value)


def test_generator_rejects_malformed_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not really json")
    good = tmp_path / "improved.json"
    run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=good,
        agent_system_version="improved_v0",
    )
    with pytest.raises(SystemExit) as exc:
        generate_eval_card(bad, good, tmp_path / "card.md")
    assert "invalid JSON" in str(exc.value)


def test_generator_rejects_wrong_shape(tmp_path: Path) -> None:
    not_a_report = tmp_path / "wrong.json"
    not_a_report.write_text(json.dumps({"hello": "world"}))
    good = tmp_path / "improved.json"
    run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=good,
        agent_system_version="improved_v0",
    )
    with pytest.raises(SystemExit) as exc:
        generate_eval_card(not_a_report, good, tmp_path / "card.md")
    assert "EvalReport" in str(exc.value)


def test_generator_rejects_same_profile_on_both_sides(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    # pass the improved report twice — both sides have agent_system_version "improved_v0"
    with pytest.raises(SystemExit) as exc:
        generate_eval_card(improved, improved, tmp_path / "card.md")
    assert "same agent_system_version" in str(exc.value)


def test_generator_rejects_dataset_mismatch(tmp_path: Path) -> None:
    """If the two reports were run against different datasets, refuse."""

    full_v0 = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
    baseline = tmp_path / "baseline.json"
    improved = tmp_path / "improved.json"
    run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "b",
        report_out=baseline,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=full_v0,
        traces_out=tmp_path / "i",
        report_out=improved,
        agent_system_version="improved_v0",
    )
    with pytest.raises(SystemExit) as exc:
        generate_eval_card(baseline, improved, tmp_path / "card.md")
    assert "different datasets" in str(exc.value)


def test_cli_writes_card_file(
    baseline_and_improved_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = baseline_and_improved_reports
    out = tmp_path / "card.md"
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_SCRIPT),
            "--baseline-report",
            str(baseline),
            "--improved-report",
            str(improved),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    assert "Local Eval Card" in out.read_text()


def test_module_exposes_constants() -> None:
    """Make sure the generator's public constants stay importable for downstream tooling."""

    assert isinstance(generator.LAUNCH_POSTURE, str)
    assert isinstance(generator.SYNTHETIC_DISCLAIMER, str)
    assert "NOT READY FOR PILOT" in generator.LAUNCH_POSTURE
