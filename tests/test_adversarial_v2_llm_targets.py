"""Tests for the M7b opt-in adversarial v2 LLM + semantic-gate wiring.

These are **credential-free**: they verify the Makefile wiring (credentialed
targets gate on check-llm-env; on-disk targets do not; raw artifacts gitignored;
no deterministic target depends on the LLM targets) and the credential-free
semantic-gate pipeline (replay builder + run_eval improved_v0 + check_semantic_gate)
end-to-end using a synthetic decision file. No model is called and no
credentials are required.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_semantic_replay_adversarial_v2_llm import build_replay_fixture

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"
ADVERSARIAL_V2 = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v2.jsonl"
)

_CREDENTIALED_V2_TARGETS = (
    "eval-adversarial-v2-llm-v0",
    "eval-adversarial-v2-llm-v1",
    "semantic-model-decisions-adversarial-v2-llm-v0",
    "semantic-model-decisions-adversarial-v2-llm-v1",
)
_ONDISK_V2_TARGETS = (
    "semantic-audit-summary-adversarial-v2-llm",
    "semantic-gate-adversarial-v2-llm",
)
_ALL_V2_LLM_TARGETS = _CREDENTIALED_V2_TARGETS + _ONDISK_V2_TARGETS + (
    "eval-card-adversarial-v2-llm",
)


def _makefile() -> str:
    return MAKEFILE.read_text()


def _make_prereqs(makefile: str, target: str) -> list[str]:
    match = re.search(rf"^{re.escape(target)}:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
    assert match is not None, f"Make target {target!r} not found"
    return match.group(1).split()


def _make_recipe(makefile: str, target: str) -> str:
    pattern = re.compile(rf"^{re.escape(target)}:[^\n]*\n((?:\t[^\n]*\n)+)", re.MULTILINE)
    match = pattern.search(makefile)
    assert match is not None, f"recipe for {target!r} not found"
    return match.group(1)


# --- Target existence + credential gating ------------------------------------


def test_all_v2_llm_targets_exist() -> None:
    makefile = _makefile()
    for target in _ALL_V2_LLM_TARGETS:
        assert f"{target}:" in makefile, f"Makefile missing v2 LLM target {target!r}"


def test_credentialed_v2_targets_gate_on_check_llm_env() -> None:
    makefile = _makefile()
    for target in _CREDENTIALED_V2_TARGETS:
        prereqs = _make_prereqs(makefile, target)
        assert "check-llm-env" in prereqs, (
            f"{target} must depend on check-llm-env (no silent fallback); got {prereqs}"
        )


def test_ondisk_v2_targets_do_not_gate_on_check_llm_env() -> None:
    """The summary aggregation and the semantic gate operate on on-disk
    artifacts only and must NOT require credentials."""

    makefile = _makefile()
    for target in _ONDISK_V2_TARGETS:
        prereqs = _make_prereqs(makefile, target)
        assert "check-llm-env" not in prereqs, (
            f"{target} is on-disk-only and must not depend on check-llm-env; got {prereqs}"
        )
        recipe = _make_recipe(makefile, target)
        assert "check-llm-env" not in recipe


def test_v2_eval_targets_run_right_profiles_and_gitignored_paths() -> None:
    makefile = _makefile()
    for target, profile, traces, report in (
        (
            "eval-adversarial-v2-llm-v0",
            "llm_candidate_v0",
            "traces/local/llm_adversarial_v2_candidate_v0",
            "reports/llm_adversarial_v2_candidate_v0_eval.json",
        ),
        (
            "eval-adversarial-v2-llm-v1",
            "llm_candidate_v1",
            "traces/local/llm_adversarial_v2_candidate_v1",
            "reports/llm_adversarial_v2_candidate_v1_eval.json",
        ),
    ):
        recipe = _make_recipe(makefile, target)
        assert "case_studies/financial_links_reliability/evals/adversarial_v2.jsonl" in recipe
        assert f"--agent-system-version {profile}" in recipe
        assert traces in recipe
        assert report in recipe


def test_v2_card_compares_both_candidates() -> None:
    makefile = _makefile()
    prereqs = _make_prereqs(makefile, "eval-card-adversarial-v2-llm")
    assert "eval-adversarial-v2-llm-v0" in prereqs
    assert "eval-adversarial-v2-llm-v1" in prereqs
    recipe = _make_recipe(makefile, "eval-card-adversarial-v2-llm")
    assert "reports/llm_adversarial_v2_candidate_v0_eval.json" in recipe
    assert "reports/llm_adversarial_v2_candidate_v1_eval.json" in recipe
    assert "reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md" in recipe


def test_v2_semantic_decision_targets_judge_on_disk_without_rerun() -> None:
    """The semantic-decision targets must NOT depend on the candidate eval
    targets (that would re-run the candidate and overwrite the audited drafts)."""

    makefile = _makefile()
    for target, report, out in (
        (
            "semantic-model-decisions-adversarial-v2-llm-v0",
            "reports/llm_adversarial_v2_candidate_v0_eval.json",
            "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json",
        ),
        (
            "semantic-model-decisions-adversarial-v2-llm-v1",
            "reports/llm_adversarial_v2_candidate_v1_eval.json",
            "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json",
        ),
    ):
        prereqs = _make_prereqs(makefile, target)
        assert prereqs == ["check-llm-env"], (
            f"{target} must depend ONLY on check-llm-env (no candidate rerun); got {prereqs}"
        )
        recipe = _make_recipe(makefile, target)
        assert "scripts/generate_semantic_decisions.py" in recipe
        assert f"--eval-report {report}" in recipe
        assert out in recipe


def test_v2_summary_target_aggregates_v2_paths() -> None:
    recipe = _make_recipe(_makefile(), "semantic-audit-summary-adversarial-v2-llm")
    assert "scripts/summarize_semantic_audit_adversarial_v1_llm.py" in recipe
    assert "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json" in recipe
    assert "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json" in recipe
    assert "reports/llm_adversarial_v2_semantic_audit_summary.json" in recipe
    assert "reports/llm_adversarial_v2_semantic_audit_summary.md" in recipe


def test_v2_gate_target_builds_replay_then_runs_eval_then_gates() -> None:
    recipe = _make_recipe(_makefile(), "semantic-gate-adversarial-v2-llm")
    build_idx = recipe.index("scripts/build_semantic_replay_adversarial_v2_llm.py")
    eval_idx = recipe.index("scripts/run_eval.py")
    gate_idx = recipe.index("scripts/check_semantic_gate.py")
    assert build_idx < eval_idx < gate_idx, "gate must build replay, run eval, then gate"
    # Credential-free vehicle, not the candidate: the only agent-system-version
    # in the recipe is the deterministic improved_v0.
    assert "--agent-system-version improved_v0" in recipe
    assert "--agent-system-version llm_candidate" not in recipe
    assert "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json" in recipe


def test_no_deterministic_target_depends_on_v2_llm_targets() -> None:
    makefile = _makefile()
    deterministic_targets = (
        "test:",
        "lint:",
        "dataset-test-adversarial-v2:",
        "eval-adversarial-v2-baseline:",
        "eval-adversarial-v2-improved:",
        "eval-card-adversarial-v2:",
        "semantic-gate-adversarial-v1-regressions:",
        "regression-replay-adversarial-v1-semantic:",
    )
    forbidden = set(_ALL_V2_LLM_TARGETS)
    for target in deterministic_targets:
        match = re.search(rf"^{re.escape(target)}\s*([^\n]*)$", makefile, flags=re.MULTILINE)
        if match is None:
            continue
        leaked = set(match.group(1).split()) & forbidden
        assert not leaked, f"deterministic target {target} depends on v2 LLM target(s) {leaked}"


# --- gitignore: raw artifacts ignored, public artifacts tracked --------------


def _is_ignored(path: str) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", path], cwd=ROOT, check=False
        ).returncode
        == 0
    )


def test_v2_raw_llm_artifacts_are_gitignored() -> None:
    for path in (
        "reports/llm_adversarial_v2_candidate_v0_eval.json",
        "reports/llm_adversarial_v2_candidate_v1_eval.json",
        "traces/local/llm_adversarial_v2_candidate_v0/case_fl_adv_v2_001.json",
        "traces/local/llm_adversarial_v2_candidate_v1/case_fl_adv_v2_001.json",
        "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json",
        "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json",
        "reports/llm_adversarial_v2_candidate_v1_semantic_replay_decisions.json",
        "reports/llm_adversarial_v2_candidate_v1_semantic_model_eval.json",
        "traces/local/llm_adversarial_v2_candidate_v1_semantic_model/case_fl_adv_v2_001.json",
    ):
        assert _is_ignored(path), f"raw/regenerable artifact must be gitignored: {path}"


def test_v2_public_artifacts_are_not_gitignored() -> None:
    for path in (
        "reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md",
        "reports/llm_adversarial_v2_semantic_audit_summary.json",
        "reports/llm_adversarial_v2_semantic_audit_summary.md",
    ):
        assert not _is_ignored(path), f"public artifact must be trackable: {path}"


# --- Replay builder: public-safe re-keying -----------------------------------

RAW_SPAN = "RAW_DRAFT_SPAN_the_data_is_real_time_once_linked"


def _raw_decisions(flagged_case_ids: set[str], case_ids: list[str]) -> dict:
    return {
        "version": "semantic_model_decisions_v0",
        "synthetic": True,
        "adapter": "anthropic_nli_semantic_v0",
        "profile": "llm_candidate_v1",
        "decisions": {
            "llm_candidate_v1": {
                cid: {
                    "makes_unsupported_claim": cid in flagged_case_ids,
                    "claim_type": "freshness" if cid in flagged_case_ids else "none",
                    "confidence": 0.91,
                    # Draft-bearing fields that MUST be dropped by the builder.
                    "rationale": f"model quoted: {RAW_SPAN}",
                    "evidence_spans": [RAW_SPAN] if cid in flagged_case_ids else [],
                    "calibration": "affirmative_overpromise" if cid in flagged_case_ids else "safe_hedge",
                }
                for cid in case_ids
            }
        },
    }


def _v2_case_ids() -> list[str]:
    return [json.loads(line)["case_id"] for line in ADVERSARIAL_V2.read_text().splitlines() if line.strip()]


def test_builder_rekeys_under_improved_v0_and_preserves_verdicts() -> None:
    case_ids = _v2_case_ids()
    flagged = {case_ids[0], case_ids[3]}
    fixture = build_replay_fixture(_raw_decisions(flagged, case_ids))
    assert fixture["replay_profile"] == "improved_v0"
    decisions = fixture["decisions"]["improved_v0"]
    assert set(decisions) == set(case_ids)
    for cid, d in decisions.items():
        assert d["makes_unsupported_claim"] is (cid in flagged)


def test_builder_strips_draft_bearing_fields() -> None:
    case_ids = _v2_case_ids()
    fixture = build_replay_fixture(_raw_decisions({case_ids[0]}, case_ids))
    blob = json.dumps(fixture)
    assert RAW_SPAN not in blob, "builder leaked a raw draft span"
    for d in fixture["decisions"]["improved_v0"].values():
        assert d["evidence_spans"] == []
        assert RAW_SPAN not in d["rationale"]
        # rationale is the authored provenance string, not the source quote.
        assert "Replayed model/NLI semantic verdict" in d["rationale"]


def test_builder_assert_public_safe_rejects_nonempty_evidence_spans() -> None:
    """The public-safety guard must reject a fixture that somehow carried a
    non-empty evidence_spans (defense-in-depth against a future builder bug)."""

    from scripts.build_semantic_replay_adversarial_v2_llm import _assert_public_safe

    bad = {"decisions": {"improved_v0": {"c1": {"evidence_spans": ["x"]}}}}
    with pytest.raises(SystemExit, match="evidence_spans"):
        _assert_public_safe(bad)


def test_builder_assert_public_safe_rejects_non_provenance_rationale() -> None:
    """A decision whose rationale was copied from the raw (draft-quoting) model
    decision — rather than the authored provenance string — must be rejected."""

    from scripts.build_semantic_replay_adversarial_v2_llm import _assert_public_safe

    leaked = {
        "decisions": {
            "improved_v0": {
                "c1": {"evidence_spans": [], "rationale": f"model quoted: {RAW_SPAN}"}
            }
        }
    }
    with pytest.raises(SystemExit, match="provenance"):
        _assert_public_safe(leaked)


# --- Credential-free gate pipeline end-to-end --------------------------------


def _build_run_gate(raw_decisions: dict, tmp_path: Path) -> int:
    from evals.run import run_eval

    raw = tmp_path / "raw_decisions.json"
    raw.write_text(json.dumps(raw_decisions))
    replay = tmp_path / "replay.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_semantic_replay_adversarial_v2_llm.py"),
            "--decisions",
            str(raw),
            "--out",
            str(replay),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rc.returncode == 0, rc.stderr
    assert RAW_SPAN not in replay.read_text()
    run_eval(
        dataset_path=ADVERSARIAL_V2,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="improved_v0",
        semantic_decisions_path=replay,
    )
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_semantic_gate.py"),
            "--report",
            str(tmp_path / "report.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).returncode


def test_gate_pipeline_passes_on_clean_candidate(tmp_path: Path) -> None:
    case_ids = _v2_case_ids()
    assert _build_run_gate(_raw_decisions(set(), case_ids), tmp_path) == 0


def test_gate_pipeline_blocks_on_flagged_candidate(tmp_path: Path) -> None:
    case_ids = _v2_case_ids()
    flagged = {case_ids[2], case_ids[7]}
    assert _build_run_gate(_raw_decisions(flagged, case_ids), tmp_path) == 1
