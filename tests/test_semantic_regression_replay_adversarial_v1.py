"""Tests for the credential-free replay of the semantic regression seeds.

A tracked ``SemanticDecision`` fixture
(``regressions_semantic_adversarial_v1_decisions.json``) makes the 3 model/NLI
semantic-only seeds replayable with **no model call**: feeding it to
``run_eval.py --semantic-decisions`` with the deterministic ``improved_v0``
profile fires the offline ``unsupported_claim_semantic`` grader
(``UNSAFE_CUSTOMER_COMMS``) on every seed.

These tests are credential-free and hermetic (run_eval writes into ``tmp_path``).
They never call a model and never read the gitignored candidate reports, raw
traces, or raw decision files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.run import run_eval
from scripts.build_semantic_replay_fixture_adversarial_v1 import build_fixture
from scripts.check_semantic_regressions_adversarial_v1 import check_replay_report


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "case_studies" / "financial_links_reliability" / "evals"
REGRESSIONS = EVALS / "regressions_semantic_adversarial_v1.jsonl"
FIXTURE = EVALS / "regressions_semantic_adversarial_v1_decisions.json"
SUMMARY = ROOT / "reports" / "llm_adversarial_v1_semantic_audit_summary.json"
MAKEFILE = ROOT / "Makefile"
REPLAY_PROFILE = "improved_v0"
SEMANTIC_GRADER = "unsupported_claim_semantic"


def _seed_ids() -> set[str]:
    return {
        json.loads(line)["regression_case_id"]
        for line in REGRESSIONS.read_text().splitlines()
        if line.strip()
    }


def _semantic_rate(report) -> object:
    return next(
        r for r in report.aggregate_grader_pass_rates if r.name == SEMANTIC_GRADER
    )


def _semantic_results_by_case(report) -> dict[str, object]:
    names = [r.name for r in report.aggregate_grader_pass_rates]
    idx = names.index(SEMANTIC_GRADER)
    return {case.case_id: case.grader_results[idx] for case in report.per_case}


# --- Fixture shape + public safety -------------------------------------------

def test_fixture_exists_and_covers_exactly_the_seeds() -> None:
    assert FIXTURE.exists(), f"missing replay fixture: {FIXTURE}"
    fixture = json.loads(FIXTURE.read_text())
    assert fixture["replay_profile"] == REPLAY_PROFILE
    decisions = fixture["decisions"][REPLAY_PROFILE]
    assert set(decisions) == _seed_ids(), "fixture keys must match the seed IDs exactly"


def test_fixture_decisions_pin_unsupported_claim_true() -> None:
    decisions = json.loads(FIXTURE.read_text())["decisions"][REPLAY_PROFILE]
    for case_id, d in decisions.items():
        assert d["makes_unsupported_claim"] is True, case_id


def test_fixture_is_public_safe() -> None:
    blob = FIXTURE.read_text()
    assert "traces/local/llm_" not in blob
    decisions = json.loads(blob)["decisions"][REPLAY_PROFILE]
    for case_id, d in decisions.items():
        # No raw draft spans; aggregate-only.
        assert d["evidence_spans"] == [], case_id
        # rationale is an authored provenance string, not raw draft text.
        assert "rationale" in d and isinstance(d["rationale"], str)


# --- Credential-free replay fires the offline semantic grader ----------------

def test_replay_fires_semantic_grader_on_all_seeds(tmp_path: Path) -> None:
    report = run_eval(
        dataset_path=REGRESSIONS,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version=REPLAY_PROFILE,
        semantic_decisions_path=FIXTURE,
    )
    rate = _semantic_rate(report)
    assert rate.total == 3
    assert rate.passed == 0, "every seeded case must fire the semantic grader"

    for case_id, result in _semantic_results_by_case(report).items():
        assert result.passed is False, case_id
        assert result.failure_label == "UNSAFE_CUSTOMER_COMMS", case_id


def test_replay_check_function_passes_on_written_report(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    run_eval(
        dataset_path=REGRESSIONS,
        traces_out=tmp_path / "traces",
        report_out=report_path,
        agent_system_version=REPLAY_PROFILE,
        semantic_decisions_path=FIXTURE,
    )
    assert check_replay_report(REGRESSIONS, report_path) == []


def test_replay_check_has_teeth_when_grader_did_not_fire(tmp_path: Path) -> None:
    """If the semantic grader did not fire (e.g. report produced without the
    fixture), the replay check must report problems."""

    report_path = tmp_path / "report_no_fixture.json"
    run_eval(
        dataset_path=REGRESSIONS,
        traces_out=tmp_path / "traces",
        report_out=report_path,
        agent_system_version=REPLAY_PROFILE,
        # no semantic_decisions_path -> no unsupported_claim_semantic grader
    )
    errors = check_replay_report(REGRESSIONS, report_path)
    assert errors, "replay check must fail when the semantic grader is absent"


# --- Evaluator / grader separation -------------------------------------------

def test_semantic_lane_is_opt_in_and_separate_from_default_path(tmp_path: Path) -> None:
    """The semantic grader is an OFFLINE, opt-in lane fed only by
    --semantic-decisions. Without the fixture the default eval path is
    unchanged (no unsupported_claim_semantic), and the runtime-evaluator
    catch-rate grader remains a distinct offline grader either way."""

    without = run_eval(
        dataset_path=REGRESSIONS,
        traces_out=tmp_path / "t1",
        report_out=tmp_path / "r1.json",
        agent_system_version=REPLAY_PROFILE,
    )
    without_names = {r.name for r in without.aggregate_grader_pass_rates}
    assert SEMANTIC_GRADER not in without_names

    with_fixture = run_eval(
        dataset_path=REGRESSIONS,
        traces_out=tmp_path / "t2",
        report_out=tmp_path / "r2.json",
        agent_system_version=REPLAY_PROFILE,
        semantic_decisions_path=FIXTURE,
    )
    with_names = {r.name for r in with_fixture.aggregate_grader_pass_rates}
    # The offline semantic grader and the offline runtime-evaluator catch-rate
    # grader coexist as distinct graders — the runtime EvaluatorNode is never
    # fed the semantic decision.
    assert SEMANTIC_GRADER in with_names
    assert "evaluator_catch_rate" in with_names
    assert SEMANTIC_GRADER != "evaluator_catch_rate"


# --- Fixture builder honesty + determinism -----------------------------------

def test_build_fixture_is_deterministic_and_matches_committed(tmp_path: Path) -> None:
    built = build_fixture(
        regressions_path=REGRESSIONS,
        summary_path=SUMMARY,
        replay_profile=REPLAY_PROFILE,
    )
    committed = json.loads(FIXTURE.read_text())
    assert built["decisions"] == committed["decisions"]


def test_build_fixture_refuses_non_summary_flag(tmp_path: Path) -> None:
    """The builder must not fabricate a fixture for a case that is not a
    semantic-only flag in the audit summary."""

    records = [
        json.loads(line)
        for line in REGRESSIONS.read_text().splitlines()
        if line.strip()
    ]
    records[0]["source_case_id"] = "case_fl_adv_v1_001"  # not a semantic-only flag
    bad = tmp_path / "bad_regressions.jsonl"
    bad.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    with pytest.raises(SystemExit, match="not a semantic-only flag"):
        build_fixture(regressions_path=bad, summary_path=SUMMARY, replay_profile=REPLAY_PROFILE)


# --- Makefile wiring ----------------------------------------------------------

def _target_block(target: str) -> str:
    lines = MAKEFILE.read_text().splitlines()
    header = f"{target}:"
    start = next((i for i, ln in enumerate(lines) if ln.startswith(header)), None)
    assert start is not None, f"Makefile target {target!r} not found"
    block = [lines[start]]
    for ln in lines[start + 1 :]:
        if not ln.strip() or not ln[0].isspace():
            break
        block.append(ln)
    return "\n".join(block)


def test_replay_target_is_credential_free() -> None:
    block = _target_block("regression-replay-adversarial-v1-semantic")
    # Uses the deterministic profile + the tracked fixture.
    assert "scripts/run_eval.py" in block
    assert "--agent-system-version improved_v0" in block
    assert "--semantic-decisions" in block
    assert "regressions_semantic_adversarial_v1_decisions.json" in block
    assert "--replay-report" in block
    # No credentials, no candidate profile, no model-decision generation.
    assert "check-llm-env" not in block
    assert "generate_semantic_decisions" not in block
    assert "llm_candidate_v" not in block


def test_seed_target_also_builds_the_replay_fixture() -> None:
    block = _target_block("regression-seed-adversarial-v1-semantic")
    assert "scripts/build_semantic_replay_fixture_adversarial_v1.py" in block
    assert "regressions_semantic_adversarial_v1_decisions.json" in block
