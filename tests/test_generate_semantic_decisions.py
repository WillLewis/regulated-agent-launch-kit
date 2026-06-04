"""Tests for generating SemanticDecision files with the model/NLI adapter CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evals.graders import SemanticDecision
from evals.run import load_semantic_decisions, run_eval
from evals.semantic_model_adapter import SemanticAdapterResponse
from scripts.generate_semantic_decisions import generate_semantic_decision_file


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_V1 = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v1.jsonl"
)
SCRIPT = ROOT / "scripts" / "generate_semantic_decisions.py"


def _case_ids() -> list[str]:
    return [
        json.loads(line)["case_id"]
        for line in ADVERSARIAL_V1.read_text().splitlines()
        if line.strip()
    ]


def _fake_decision_fn(
    prompt: str,
    *,
    model: str | None = None,
    timeout_s: float = 30.0,
    max_tokens: int = 512,
) -> SemanticAdapterResponse:
    makes_claim = "always current" in prompt or "updates instantly" in prompt
    return SemanticAdapterResponse(
        decision=SemanticDecision(
            makes_unsupported_claim=makes_claim,
            claim_type="freshness" if makes_claim else "none",
            confidence=0.88,
            rationale=(
                "Fake adapter saw paraphrased overpromise pressure."
                if makes_claim
                else "Fake adapter saw no unsupported claim."
            ),
            evidence_spans=["always current"] if makes_claim else [],
            calibration="affirmative_overpromise" if makes_claim else "safe_hedge",
        ),
        input_tokens=10,
        output_tokens=5,
        model=model or "fake-semantic-model",
        est_cost_usd=0.000105,
        cost_estimation_note="rate_used",
    )


def test_generate_semantic_decision_file_writes_fixture_compatible_json(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "baseline_report.json"
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "traces",
        report_out=report_path,
        agent_system_version="baseline_v0",
    )
    out = tmp_path / "semantic_decisions.json"

    payload = generate_semantic_decision_file(
        dataset_path=ADVERSARIAL_V1,
        eval_report_path=report_path,
        out=out,
        model="fake-semantic-model",
        decision_fn=_fake_decision_fn,
    )

    assert out.exists()
    assert payload["version"] == "semantic_model_decisions_v0"
    assert payload["adapter"] == "anthropic_nli_semantic_v0"
    assert payload["profile"] == "baseline_v0"
    assert payload["summary"]["case_count"] == 12
    assert payload["summary"]["total_est_cost_usd"] > 0

    decisions = load_semantic_decisions(
        out,
        profile="baseline_v0",
        expected_case_ids=_case_ids(),
    )
    assert set(decisions) == set(_case_ids())
    assert decisions["case_fl_adv_v1_001"].makes_unsupported_claim is True


def test_generated_decisions_can_drive_semantic_eval_lane(tmp_path: Path) -> None:
    report_path = tmp_path / "baseline_report.json"
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "source_traces",
        report_out=report_path,
        agent_system_version="baseline_v0",
    )
    decisions_path = tmp_path / "semantic_decisions.json"
    generate_semantic_decision_file(
        dataset_path=ADVERSARIAL_V1,
        eval_report_path=report_path,
        out=decisions_path,
        decision_fn=_fake_decision_fn,
    )

    semantic_report = run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "semantic_traces",
        report_out=tmp_path / "semantic_report.json",
        agent_system_version="baseline_v0",
        semantic_decisions_path=decisions_path,
    )

    names = [rate.name for rate in semantic_report.aggregate_grader_pass_rates]
    assert "unsupported_claim_semantic" in names
    semantic_rate = next(
        rate
        for rate in semantic_report.aggregate_grader_pass_rates
        if rate.name == "unsupported_claim_semantic"
    )
    assert semantic_rate.total == 12
    assert semantic_rate.passed < 12


def test_generate_semantic_decisions_cli_help_is_local_only() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--eval-report" in result.stdout
    assert "--max-tokens" in result.stdout


def test_gitignore_excludes_model_semantic_outputs() -> None:
    gitignore = (ROOT / ".gitignore").read_text()

    assert "reports/semantic_model_decisions/" in gitignore
    assert "reports/*_semantic_model_eval.json" in gitignore
    assert "traces/local/*_semantic_model/" in gitignore
