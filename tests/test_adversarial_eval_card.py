"""Tests for the adversarial slice before/after eval-card target.

These tests build the card from a fresh in-process run so they don't
depend on a previously-committed report file. They lock in: the
Makefile target name, the card's profile naming, the expected
adversarial failure labels, the NOT READY FOR PILOT posture, the lack
of positive overclaim phrases, and that README points readers at both
the adversarial dataset and the card while making clear no LLM eval
has yet been run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from evals.run import run_eval
from scripts.generate_eval_card import LAUNCH_POSTURE, generate_eval_card


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)
MAKEFILE = ROOT / "Makefile"
README = ROOT / "README.md"


@pytest.fixture()
def adversarial_card(tmp_path: Path) -> Path:
    """Build a fresh adversarial card from in-process baseline+improved runs."""

    baseline_report = tmp_path / "baseline_adversarial.json"
    improved_report = tmp_path / "improved_adversarial.json"
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline_report,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "improved_traces",
        report_out=improved_report,
        agent_system_version="improved_v0",
    )
    out = tmp_path / "adversarial_eval_card.md"
    generate_eval_card(baseline_report, improved_report, out)
    return out


# ---------------------------------------------------------------------------
# Makefile wiring
# ---------------------------------------------------------------------------

def test_makefile_has_eval_card_adversarial_target() -> None:
    makefile = MAKEFILE.read_text()
    assert "eval-card-adversarial:" in makefile


def test_eval_card_adversarial_depends_on_both_adversarial_evals() -> None:
    makefile = MAKEFILE.read_text()
    match = re.search(
        r"^eval-card-adversarial:\s*([^\n]*)$", makefile, flags=re.MULTILINE
    )
    assert match is not None, "eval-card-adversarial target not found"
    prereqs = match.group(1).split()
    assert "eval-adversarial-baseline" in prereqs
    assert "eval-adversarial-improved" in prereqs


def test_eval_card_adversarial_writes_canonical_card_path() -> None:
    makefile = MAKEFILE.read_text()
    match = re.search(
        r"^eval-card-adversarial:[^\n]*\n((?:\t[^\n]*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    recipe = match.group(1)
    assert "reports/adversarial_eval_card.md" in recipe
    assert "reports/baseline_adversarial_eval.json" in recipe
    assert "reports/improved_adversarial_eval.json" in recipe


# ---------------------------------------------------------------------------
# Card content
# ---------------------------------------------------------------------------

def test_card_names_both_profiles(adversarial_card: Path) -> None:
    text = adversarial_card.read_text()
    assert "baseline_v0" in text
    assert "improved_v0" in text


def test_card_surfaces_expected_adversarial_failure_labels(
    adversarial_card: Path,
) -> None:
    text = adversarial_card.read_text()
    for label in ("TOOL_MISUSE", "UNSAFE_CUSTOMER_COMMS", "POLICY_MISS"):
        assert label in text, f"adversarial card missing label {label!r}"


def test_card_keeps_not_ready_for_pilot_posture(adversarial_card: Path) -> None:
    text = adversarial_card.read_text()
    assert "NOT READY FOR PILOT" in text
    assert LAUNCH_POSTURE in text


def test_card_does_not_claim_pilot_or_production_readiness(
    adversarial_card: Path,
) -> None:
    lower = adversarial_card.read_text().lower()
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"adversarial card must not claim {phrase!r}"


def test_card_lists_failing_baseline_case_ids(adversarial_card: Path) -> None:
    text = adversarial_card.read_text()
    for case_id in ("case_fl_adv_v0_002", "case_fl_adv_v0_004", "case_fl_adv_v0_006"):
        assert case_id in text, f"adversarial card missing failing case {case_id!r}"


# ---------------------------------------------------------------------------
# README links + LLM-not-evaluated posture
# ---------------------------------------------------------------------------

def test_readme_links_to_adversarial_dataset_and_card() -> None:
    readme = README.read_text()
    assert (
        "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl" in readme
    )
    assert "reports/adversarial_eval_card.md" in readme


def test_readme_states_llm_profile_not_yet_evaluated() -> None:
    """README must make clear that no LLM eval result is in-repo."""

    readme = README.read_text()
    lower = readme.lower()
    # Accept any of a few honest framings of the same fact.
    candidates = (
        "has not yet been evaluated",
        "not yet been evaluated",
        "no llm eval result is in-repo",
        "no llm eval result is in repo",
        "nothing about llm behavior on adversarial cases is being",
    )
    assert any(c in lower for c in candidates), (
        f"README must state the LLM profile has not been evaluated yet; "
        f"none of {candidates!r} found"
    )


def test_readme_summarizes_adversarial_baseline_vs_improved() -> None:
    readme = README.read_text()
    # baseline 3 passed / 3 failed; improved 6 passed / 0 failed on 6 cases.
    for fragment in ("| 6 | 6 |", "| 3 | 6 |", "| 3 | 0 |"):
        assert fragment in readme, (
            f"README adversarial summary missing expected table row {fragment!r}"
        )
    # All three baseline labels are named.
    for label in ("TOOL_MISUSE", "UNSAFE_CUSTOMER_COMMS", "POLICY_MISS"):
        assert label in readme, (
            f"README adversarial summary missing failure label {label!r}"
        )
