"""Tests for the full v0 dataset before/after eval card.

The smoke slice has only 4 cases and one planted failure, which is not
enough to show the eval loop's value. These tests run the generator
against the full 10-case dataset and lock in the failure-label coverage
the v0 baseline is supposed to surface.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.run import run_eval
from scripts.generate_eval_card import (
    LAUNCH_POSTURE,
    generate_eval_card,
)


ROOT = Path(__file__).resolve().parents[1]
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
MAKEFILE = ROOT / "Makefile"


@pytest.fixture()
def v0_paired_reports(tmp_path: Path) -> tuple[Path, Path]:
    baseline_report = tmp_path / "baseline_v0.json"
    improved_report = tmp_path / "improved_v0.json"
    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline_report,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=improved_report,
        agent_system_version="improved_v0",
    )
    return baseline_report, improved_report


def test_makefile_has_v0_targets() -> None:
    makefile = MAKEFILE.read_text()
    for target in ("eval-v0-baseline:", "eval-v0-improved:", "eval-card-v0:"):
        assert target in makefile, f"Makefile missing target {target!r}"
    # eval-card-v0 must chain the two underlying eval targets so the
    # card is regenerable from a single command.
    assert "eval-card-v0: eval-v0-baseline eval-v0-improved" in makefile


def test_makefile_v0_targets_point_at_canonical_paths() -> None:
    makefile = MAKEFILE.read_text()
    for fragment in (
        "case_studies/financial_links_reliability/data/cases_v0.jsonl",
        "traces/local/baseline_v0",
        "traces/local/improved_v0",
        "reports/baseline_v0_eval.json",
        "reports/improved_v0_eval.json",
        "reports/v0_eval_card.md",
    ):
        assert fragment in makefile, f"Makefile missing path {fragment!r}"


def test_v0_card_surfaces_all_planted_baseline_labels(
    v0_paired_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = v0_paired_reports
    out = tmp_path / "v0_card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()

    for label in ("POLICY_MISS", "TOOL_MISUSE", "UNSAFE_CUSTOMER_COMMS"):
        assert label in markdown, (
            f"v0 eval card is missing planted baseline label {label!r}"
        )


def test_v0_card_keeps_not_ready_for_pilot_posture(
    v0_paired_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = v0_paired_reports
    out = tmp_path / "v0_card.md"
    generate_eval_card(baseline, improved, out)
    assert "NOT READY FOR PILOT" in out.read_text()
    assert LAUNCH_POSTURE in out.read_text()


def test_v0_card_does_not_overclaim_pilot_or_production_readiness(
    v0_paired_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    baseline, improved = v0_paired_reports
    out = tmp_path / "v0_card.md"
    generate_eval_card(baseline, improved, out)
    lower = out.read_text().lower()

    # Same narrow positive-claim list as the smoke card test: "ready
    # for pilot" / "ready for production" are intentionally NOT here
    # because the card legitimately says "NOT READY FOR PILOT".
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"v0 eval card must not claim {phrase!r}"


def test_v0_card_shows_three_failing_cases_in_baseline(
    v0_paired_reports: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    """Specifically the cases case_fl_v0_005, case_fl_v0_006, case_fl_v0_010."""

    baseline, improved = v0_paired_reports
    out = tmp_path / "v0_card.md"
    generate_eval_card(baseline, improved, out)
    markdown = out.read_text()

    for case_id in ("case_fl_v0_005", "case_fl_v0_006", "case_fl_v0_010"):
        assert case_id in markdown, f"v0 card missing failing baseline case {case_id!r}"
