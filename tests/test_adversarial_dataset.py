"""Tests for the adversarial Financial Links v0 slice.

The adversarial slice exists to stress an LLM-backed candidate
profile. The deterministic public proof loop must still close on it:
``improved_v0`` should pass every adversarial case, and ``baseline_v0``
should fail a non-empty subset (so the slice doubles as a smoke test
for the planted baseline weaknesses).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from evals.run import run_eval


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)
FULL_V0_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
)
DATASET_CARD = ROOT / "case_studies" / "financial_links_reliability" / "dataset_card.md"
MAKEFILE = ROOT / "Makefile"
VALIDATOR_SCRIPT = ROOT / "scripts" / "validate_dataset.py"


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture(scope="module")
def adversarial_cases() -> list[dict]:
    return _load_jsonl(ADVERSARIAL_PATH)


# ---------------------------------------------------------------------------
# File shape + validator
# ---------------------------------------------------------------------------

def test_adversarial_jsonl_exists_and_is_sized_in_range(
    adversarial_cases: list[dict],
) -> None:
    assert ADVERSARIAL_PATH.exists()
    assert 5 <= len(adversarial_cases) <= 8, (
        f"adversarial slice should hold 5–8 cases, has {len(adversarial_cases)}"
    )


def test_adversarial_jsonl_passes_dataset_validator() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_SCRIPT), str(ADVERSARIAL_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_adversarial_case_ids_are_unique(adversarial_cases: list[dict]) -> None:
    ids = [c["case_id"] for c in adversarial_cases]
    assert len(ids) == len(set(ids)), f"duplicate adversarial case_ids: {ids}"


def test_adversarial_case_ids_do_not_collide_with_v0(
    adversarial_cases: list[dict],
) -> None:
    v0_ids = {c["case_id"] for c in _load_jsonl(FULL_V0_PATH)}
    adv_ids = {c["case_id"] for c in adversarial_cases}
    overlap = v0_ids & adv_ids
    assert not overlap, f"adversarial case_ids collide with v0: {overlap}"


def test_adversarial_records_carry_synthetic_marker(
    adversarial_cases: list[dict],
) -> None:
    for case in adversarial_cases:
        assert case.get("synthetic") is True, case["case_id"]
        assert case["dataset_id"] == "financial_links_reliability_adversarial_v0"
        assert case["workflow"] == "financial_links_reliability"


# ---------------------------------------------------------------------------
# Required mix + labels
# ---------------------------------------------------------------------------

_REQUIRED_CASE_TYPE_FRAGMENTS: tuple[str, ...] = (
    "force_completion",        # partner pressure to force completion
    "guaranteed_refresh",      # guaranteed refresh timing
    "hide_uncertainty",        # hide uncertainty / policy limits
    "fallback_on_blocked",     # fallback despite blocked partner
    "missing_info",            # missing-info hallucination
    "policy_citation_trap",    # policy citation trap
)


def test_required_adversarial_case_types_present(
    adversarial_cases: list[dict],
) -> None:
    case_types = [c["case_type"] for c in adversarial_cases]
    for fragment in _REQUIRED_CASE_TYPE_FRAGMENTS:
        assert any(fragment in ct for ct in case_types), (
            f"adversarial slice missing case type fragment {fragment!r}; "
            f"got {case_types}"
        )


_REQUIRED_LABELS: tuple[str, ...] = (
    "CONSENT_BOUNDARY_VIOLATION",
    "UNSAFE_CUSTOMER_COMMS",
    "POLICY_MISS",
    "TOOL_MISUSE",
)


def test_required_failure_labels_are_represented(
    adversarial_cases: list[dict],
) -> None:
    labels = {c["failure_label_if_mishandled"] for c in adversarial_cases}
    for required in _REQUIRED_LABELS:
        assert required in labels, (
            f"adversarial slice missing failure label {required!r}; got {sorted(labels)}"
        )


def test_every_case_carries_partner_request_or_explicit_summary(
    adversarial_cases: list[dict],
) -> None:
    """Adversarial cases need an LLM-pressure hook in synthetic_facts."""

    for case in adversarial_cases:
        facts = case["synthetic_facts"]
        has_pressure = "partner_request" in facts or "summary" in facts
        assert has_pressure, (
            f"adversarial case {case['case_id']!r} must carry a partner_request or summary"
        )


# ---------------------------------------------------------------------------
# Behavioral deltas
# ---------------------------------------------------------------------------

def test_improved_v0_passes_every_adversarial_case(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "improved_adversarial",
        agent_system_version="improved_v0",
    )
    assert report.failed_case_count == 0, [
        (c.case_id, c.failure_labels) for c in report.per_case if not c.passed
    ]
    assert report.failure_label_counts == {}


def test_baseline_v0_fails_at_least_one_adversarial_case(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "baseline_adversarial",
        agent_system_version="baseline_v0",
    )
    assert report.failed_case_count >= 1, (
        "baseline_v0 should still fail at least one adversarial case "
        f"(planted weaknesses); report.failure_label_counts={report.failure_label_counts}"
    )


def test_baseline_failures_span_multiple_labels(tmp_path: Path) -> None:
    """Adversarial slice should surface more than one planted label class on baseline."""

    report = run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "baseline_adversarial_labels",
        agent_system_version="baseline_v0",
    )
    assert len(report.failure_label_counts) >= 2, (
        f"baseline should fail with ≥2 distinct labels on the adversarial slice; "
        f"got {report.failure_label_counts}"
    )


# ---------------------------------------------------------------------------
# Makefile wiring
# ---------------------------------------------------------------------------

def test_makefile_has_adversarial_targets() -> None:
    makefile = MAKEFILE.read_text()
    for target in (
        "dataset-test-adversarial:",
        "eval-adversarial-baseline:",
        "eval-adversarial-improved:",
    ):
        assert target in makefile, f"Makefile missing target {target!r}"


def test_makefile_adversarial_targets_use_canonical_paths() -> None:
    makefile = MAKEFILE.read_text()
    for fragment in (
        "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl",
        "traces/local/baseline_adversarial",
        "traces/local/improved_adversarial",
        "reports/baseline_adversarial_eval.json",
        "reports/improved_adversarial_eval.json",
    ):
        assert fragment in makefile, f"Makefile missing path {fragment!r}"


def test_no_default_make_target_uses_llm_profile_on_adversarial() -> None:
    """The adversarial slice has no opt-in LLM target wired by default."""

    makefile = MAKEFILE.read_text()
    # Find the adversarial-improved recipe and confirm it requests improved_v0,
    # not llm_candidate_v0.
    match = re.search(
        r"^eval-adversarial-improved:[^\n]*\n((?:\t[^\n]*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    recipe = match.group(1)
    assert "improved_v0" in recipe
    assert "llm_candidate_v0" not in recipe


# ---------------------------------------------------------------------------
# Dataset card mentions the slice
# ---------------------------------------------------------------------------

def test_dataset_card_documents_adversarial_slice() -> None:
    card = DATASET_CARD.read_text()
    assert "Adversarial v0 slice" in card
    assert "adversarial_v0.jsonl" in card
    for fragment in _REQUIRED_CASE_TYPE_FRAGMENTS:
        assert fragment in card, (
            f"dataset card missing adversarial case-type fragment {fragment!r}"
        )
