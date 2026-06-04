"""Tests for the fixture-backed semantic HTML reporting surface."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.run import run_eval
from scripts.render_semantic_reporting_surface import (
    SEMANTIC_GRADER_NAME,
    render_reporting_surface,
)


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
RENDER_SCRIPT = ROOT / "scripts" / "render_semantic_reporting_surface.py"


@pytest.fixture()
def semantic_reports(tmp_path: Path) -> tuple[Path, Path]:
    baseline = tmp_path / "baseline.json"
    improved = tmp_path / "improved.json"
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline,
        agent_system_version="baseline_v0",
        semantic_decisions_path=SEMANTIC_DECISIONS,
    )
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "improved_traces",
        report_out=improved,
        agent_system_version="improved_v0",
        semantic_decisions_path=SEMANTIC_DECISIONS,
    )
    return baseline, improved


def test_render_reporting_surface_contains_required_sections(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        out=out,
    )

    html = out.read_text()
    assert "Fixture-Backed Semantic Reporting Surface" in html
    assert "Semantic Unsupported-Claim Lane" in html
    assert SEMANTIC_GRADER_NAME in html
    assert "NOT READY FOR PILOT" in html
    assert "semantic_fixture" in html


def test_render_reporting_surface_shows_case_level_adversarial_v1_evidence(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        out=out,
    )

    html = out.read_text()
    assert "case_fl_adv_v1_001" in html
    assert "case_fl_adv_v1_008" in html
    assert "paraphrased_overpromise" in html
    assert "cross_sentence_disclaimer_trap" in html
    assert "affirmative_overpromise" in html


def test_render_reporting_surface_is_public_safe(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        out=out,
    )

    lowered = out.read_text().lower()
    assert "traces/local/llm_" not in lowered
    assert "reports/llm_repeats/" not in lowered
    forbidden_phrases = [
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "regulatory compliant",
        "regulatory-compliant",
        "model safety claim",
    ]
    assert not any(phrase in lowered for phrase in forbidden_phrases)


def test_renderer_rejects_reports_without_semantic_lane(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    improved = tmp_path / "improved.json"
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "improved_traces",
        report_out=improved,
        agent_system_version="improved_v0",
    )

    with pytest.raises(SystemExit) as exc:
        render_reporting_surface(
            dataset_path=ADVERSARIAL_V1,
            baseline_report_path=baseline,
            improved_report_path=improved,
            out=tmp_path / "surface.html",
        )
    assert "does not include 'unsupported_claim_semantic'" in str(exc.value)


def test_renderer_cli_writes_html(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    result = subprocess.run(
        [
            sys.executable,
            str(RENDER_SCRIPT),
            "--dataset",
            str(ADVERSARIAL_V1),
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
    assert "OK: wrote semantic reporting surface" in result.stdout
    assert out.exists()
    assert "Fixture-Backed Semantic Reporting Surface" in out.read_text()


def test_makefile_exposes_semantic_reporting_surface_target() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "semantic-reporting-surface:" in makefile
    assert "scripts/render_semantic_reporting_surface.py" in makefile
    assert "reports/adversarial_v1_semantic_reporting_surface.html" in makefile


def test_generated_semantic_reports_have_expected_fixture_counts(
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    baseline_report = json.loads(baseline.read_text())
    improved_report = json.loads(improved.read_text())

    def rate(report: dict[str, object]) -> dict[str, object]:
        rates = report["aggregate_grader_pass_rates"]
        assert isinstance(rates, list)
        return next(r for r in rates if r["name"] == SEMANTIC_GRADER_NAME)

    assert rate(baseline_report)["passed"] == 7
    assert rate(improved_report)["passed"] == 12
