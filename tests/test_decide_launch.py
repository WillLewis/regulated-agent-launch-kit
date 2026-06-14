"""Tests for the launch-decision I/O and rendering layer."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.schemas import LaunchDecision, LaunchVerdict
from evals.launch_decision import decide
from scripts.decide_launch import load_inputs, main


ROOT = Path(__file__).resolve().parents[1]
GATES_PATH = ROOT / "configs" / "launch_gates.yaml"


def _load_gates() -> dict:
    return yaml.safe_load(GATES_PATH.read_text())


def _gate(decision: LaunchDecision, gate_id: str):
    return next(result for result in decision.gate_results if result.gate_id == gate_id)


def test_real_committed_artifacts_compute_current_do_not_pilot_verdict() -> None:
    gates_config = _load_gates()
    inputs = load_inputs(gates_config, gates_path=GATES_PATH)

    decision = decide(gates_config, **inputs)

    assert decision.verdict is LaunchVerdict.DO_NOT_PILOT
    assert "dnp_semantic_unsupported_claim_l3" in decision.blockers
    semantic_gate = _gate(decision, "dnp_semantic_unsupported_claim_l3")
    assert "case_fl_adv_v1_010" in semantic_gate.evidence["case_ids"]
    assert "NOT READY FOR PILOT" in decision.posture_line


def test_load_inputs_uses_tracked_artifacts_only() -> None:
    inputs = load_inputs(_load_gates(), gates_path=GATES_PATH)
    digest_paths = set(inputs["inputs_digest"])

    assert all("regression_semantic_adversarial" not in path for path in digest_paths)

    regression_paths = sorted(
        path
        for path in digest_paths
        if path.startswith("reports/regression") and path.endswith("_eval.json")
    )
    assert regression_paths
    assert len(inputs["regression_runs"]) == len(regression_paths)
    assert all(path.startswith("reports/regression") for path in regression_paths)
    assert all(path.endswith("_eval.json") for path in regression_paths)


def test_cli_writes_round_trippable_json_and_public_safe_markdown(tmp_path: Path) -> None:
    out_json = tmp_path / "launch_decision.json"
    out_md = tmp_path / "launch_decision.md"

    rc = main(
        [
            "--gates",
            str(GATES_PATH),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )

    assert rc == 0
    assert out_json.exists()
    assert out_md.exists()

    data = json.loads(out_json.read_text())
    decision = LaunchDecision.model_validate(data)
    assert decision.verdict is LaunchVerdict.DO_NOT_PILOT

    markdown = out_md.read_text()
    lower_markdown = markdown.lower()
    assert decision.posture_line in markdown
    assert "synthetic" in lower_markdown
    assert "no production-readiness" in lower_markdown
    assert "regulatory-compliance" in lower_markdown

    forbidden_overclaims = [
        "production ready",
        "pilot ready",
        "regulatory compliant",
        "approved for production",
    ]
    for phrase in forbidden_overclaims:
        assert phrase not in lower_markdown
