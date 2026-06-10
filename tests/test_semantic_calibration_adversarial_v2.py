"""Tests for the credential-free grader-calibration fixtures (4 M7 over-flags).

The M7 adjudication marked 4 findings ``grader_calibration_review``. These
fixtures represent exactly those 4 as NON-claims so the offline semantic lane
clears them — the mirror of the regression replay (which proves the lane FIRES on
the 14). These tests lock in:

1. The fixtures cover exactly the 5 ``grader_calibration_review`` findings (the 4
   original over-flags + the candidate-v2 residual case_006); the
   ``needs_human_review`` finding is excluded.
2. Every calibration decision is a non-claim (``makes_unsupported_claim: false``,
   empty ``evidence_spans``); the fixtures carry no raw draft text or trace path.
3. The offline-replay check has teeth (passes when the lane clears all 4, fails
   closed when the lane is absent or still flags a case).
4. The default ``GRADERS`` / eval pipeline is not polluted with the semantic lane.
5. The Make targets are credential-free.

No credentials or model calls are involved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_semantic_calibration_adversarial_v2 import (
    CALIBRATION_DATASET_ID,
    REPLAY_PROFILE,
    _assert_no_forbidden_keys,
    build_fixtures,
)
from scripts.check_semantic_calibration_adversarial_v2 import (
    SEMANTIC_GRADER,
    check_coverage,
    check_replay,
)


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"
EVALS = ROOT / "case_studies" / "financial_links_reliability" / "evals"
ADJUDICATION = ROOT / "reports" / "llm_adversarial_v2_semantic_adjudication.json"
RESIDUAL_ADJUDICATION = (
    ROOT / "reports" / "llm_adversarial_v2_candidate_v2_residual_adjudication.json"
)
SEEDS = EVALS / "regressions_semantic_adversarial_v2.jsonl"
SOURCE_DATASET = EVALS / "adversarial_v2.jsonl"
DATASET = EVALS / "calibration_semantic_adversarial_v2.jsonl"
DECISIONS = EVALS / "calibration_semantic_adversarial_v2_decisions.json"

# The 4 original grader_calibration_review over-flags + the candidate-v2 residual
# adjudication's tool-verified-fact over-flag (case_006).
EXPECTED_5 = {
    ("case_fl_adv_v2_010", "llm_candidate_v0"),
    ("case_fl_adv_v2_014", "llm_candidate_v0"),
    ("case_fl_adv_v2_023", "llm_candidate_v0"),
    ("case_fl_adv_v2_012", "llm_candidate_v1"),
    ("case_fl_adv_v2_006", "llm_candidate_v2"),
}
# needs_human_review findings from BOTH adjudications must be excluded.
NEEDS_HUMAN_REVIEW = {
    ("case_fl_adv_v2_024", "llm_candidate_v1"),
    ("case_fl_adv_v2_024", "llm_candidate_v2"),
}

FORBIDDEN = ("draft_text", "draft_excerpt", "final_response", "traces/local/llm_")


# --- Coverage of exactly the 5 grader_calibration_review findings -------------

def test_committed_fixtures_cover_exactly_the_5() -> None:
    records = check_coverage(
        adjudication=ADJUDICATION,
        dataset=DATASET,
        residual_adjudication=RESIDUAL_ADJUDICATION,
    )
    got = {
        (r["source_case_id"], r["source_agent_system_version"]) for r in records
    }
    assert got == EXPECTED_5
    assert not (got & NEEDS_HUMAN_REVIEW), "needs_human_review must be excluded"


def test_builder_covers_exactly_the_5_across_adjudications() -> None:
    dataset_records, decisions_fixture = build_fixtures(
        adjudication_path=ADJUDICATION,
        seeds_path=SEEDS,
        residual_adjudication_path=RESIDUAL_ADJUDICATION,
        dataset_path=SOURCE_DATASET,
    )
    got = {
        (r["source_case_id"], r["source_agent_system_version"]) for r in dataset_records
    }
    assert got == EXPECTED_5
    assert ("case_fl_adv_v2_006", "llm_candidate_v2") in got, "residual case_006 missing"
    assert decisions_fixture["dataset_id"] == CALIBRATION_DATASET_ID
    decisions = decisions_fixture["decisions"][REPLAY_PROFILE]
    assert len(decisions) == 5


# --- Non-claim representation + public safety ---------------------------------

def test_all_calibration_decisions_are_non_claims() -> None:
    fixture = json.loads(DECISIONS.read_text())
    decisions = fixture["decisions"][REPLAY_PROFILE]
    assert len(decisions) == 5
    for cid, d in decisions.items():
        assert d["makes_unsupported_claim"] is False, cid
        assert d["evidence_spans"] == [], cid


def test_calibration_fixtures_are_public_safe() -> None:
    for path in (DATASET, DECISIONS):
        blob = path.read_text()
        for token in FORBIDDEN:
            assert token not in blob, f"{path.name} leaked {token!r}"


def test_builder_guard_rejects_populated_evidence_spans() -> None:
    with pytest.raises(SystemExit, match="evidence_spans must be empty"):
        _assert_no_forbidden_keys(
            {"decisions": {"x": {"evidence_spans": ["a raw span"]}}},
            label="probe",
        )
    with pytest.raises(SystemExit, match="draft-bearing key"):
        _assert_no_forbidden_keys({"draft_text": "leak"}, label="probe")


# --- The replay check has teeth ----------------------------------------------

def _calibration_case_ids() -> list[str]:
    return [json.loads(line)["case_id"] for line in DATASET.read_text().splitlines() if line.strip()]


def _synthetic_report(*, flagged: set[str] | None = None, include_lane: bool = True) -> dict:
    flagged = flagged or set()
    names = [
        "schema_validity",
        "unsupported_claim",
        "unsupported_claim_semantic",
        "evaluator_catch_rate",
    ]
    if not include_lane:
        names.remove("unsupported_claim_semantic")
    per_case = []
    for cid in _calibration_case_ids():
        results = []
        for n in names:
            if n == "unsupported_claim_semantic" and cid in flagged:
                results.append({"passed": False, "failure_label": "UNSAFE_CUSTOMER_COMMS"})
            else:
                results.append({"passed": True, "failure_label": None})
        per_case.append({"case_id": cid, "grader_results": results})
    return {
        "aggregate_grader_pass_rates": [{"name": n} for n in names],
        "per_case": per_case,
    }


def test_replay_check_passes_when_lane_clears_all(tmp_path: Path) -> None:
    report = tmp_path / "rep.json"
    report.write_text(json.dumps(_synthetic_report()))
    # Should not raise.
    check_replay(dataset=DATASET, replay_report=report)


def test_replay_check_fails_when_a_case_is_still_flagged(tmp_path: Path) -> None:
    flagged = {_calibration_case_ids()[0]}
    report = tmp_path / "rep.json"
    report.write_text(json.dumps(_synthetic_report(flagged=flagged)))
    with pytest.raises(SystemExit, match="still flagged"):
        check_replay(dataset=DATASET, replay_report=report)


def test_replay_check_fails_closed_when_lane_absent(tmp_path: Path) -> None:
    report = tmp_path / "rep.json"
    report.write_text(json.dumps(_synthetic_report(include_lane=False)))
    with pytest.raises(SystemExit, match=f"{SEMANTIC_GRADER!r} lane is absent"):
        check_replay(dataset=DATASET, replay_report=report)


# --- No default-grader pollution ---------------------------------------------

def test_semantic_grader_not_in_default_pipeline() -> None:
    from evals.graders import GRADERS
    from evals.run import _GRADER_NAMES

    assert SEMANTIC_GRADER not in GRADERS
    assert SEMANTIC_GRADER not in _GRADER_NAMES


# --- Make wiring credential-free ---------------------------------------------

def _target_block(target: str) -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(f"{target}:")), None)
    assert start is not None, f"Makefile target {target!r} not found"
    block = [lines[start]]
    for ln in lines[start + 1 :]:
        if not ln.strip() or not ln[0].isspace():
            break
        block.append(ln)
    return "\n".join(block)


def test_calibration_targets_are_credential_free() -> None:
    for target in (
        "calibration-seed-adversarial-v2-semantic",
        "calibration-replay-adversarial-v2-semantic",
    ):
        block = _target_block(target)
        for forbidden in (
            "check-llm-env",
            "check_llm_env",
            "generate_semantic_decisions",
            "--agent-system-version llm_candidate",
        ):
            assert forbidden not in block, f"{target} wires credentialed step {forbidden!r}"
    # The replay uses the deterministic improved_v0 vehicle + the tracked fixture.
    replay = _target_block("calibration-replay-adversarial-v2-semantic")
    assert "--agent-system-version improved_v0" in replay
    assert "--semantic-decisions" in replay


def test_calibration_replay_report_is_gitignored() -> None:
    gi = GITIGNORE.read_text()
    assert "reports/calibration_semantic_adversarial_v2_eval.json" in gi
    assert "traces/local/calibration_semantic_adversarial_v2/" in gi
