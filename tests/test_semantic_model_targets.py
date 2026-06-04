"""Policy tests for opt-in model/NLI semantic-grader targets."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_SEMANTIC_TARGETS = {
    "semantic-model-decisions-adversarial-v1-baseline",
    "semantic-model-decisions-adversarial-v1-improved",
    "eval-adversarial-v1-baseline-semantic-model",
    "eval-adversarial-v1-improved-semantic-model",
    "semantic-model-reporting-surface",
}


def _makefile() -> str:
    return (ROOT / "Makefile").read_text()


def _target_block(target: str) -> str:
    text = _makefile()
    marker = f"\n{target}:"
    start = text.index(marker) + 1
    tail = text[start + len(target) + 1 :]
    next_target = tail.find("\n\n")
    if next_target == -1:
        return text[start:]
    return text[start : start + len(target) + 1 + next_target]


def test_makefile_has_model_semantic_targets() -> None:
    makefile = _makefile()

    for target in MODEL_SEMANTIC_TARGETS:
        assert f"{target}:" in makefile
    assert "scripts/generate_semantic_decisions.py" in makefile
    assert "reports/semantic_model_decisions/adversarial_v1_baseline.json" in makefile
    assert "reports/adversarial_v1_semantic_model_reporting_surface.html" in makefile


def test_model_semantic_decision_targets_are_credential_gated() -> None:
    assert (
        "semantic-model-decisions-adversarial-v1-baseline: "
        "check-llm-env eval-adversarial-v1-baseline"
    ) in _makefile()
    assert (
        "semantic-model-decisions-adversarial-v1-improved: "
        "check-llm-env eval-adversarial-v1-improved"
    ) in _makefile()


def test_deterministic_targets_do_not_depend_on_model_semantic_targets() -> None:
    deterministic_targets = [
        "test",
        "eval-adversarial-v1-baseline",
        "eval-adversarial-v1-improved",
        "eval-card-adversarial-v1",
        "eval-adversarial-v1-baseline-semantic",
        "eval-adversarial-v1-improved-semantic",
        "semantic-reporting-surface",
    ]
    for target in deterministic_targets:
        block = _target_block(target)
        assert "semantic-model-decisions" not in block
        assert "semantic-model-reporting-surface" not in block


def test_gitignore_excludes_model_semantic_generated_artifacts() -> None:
    gitignore = (ROOT / ".gitignore").read_text()

    assert "reports/semantic_model_decisions/" in gitignore
    assert "reports/*_semantic_model_eval.json" in gitignore
    assert "reports/*semantic_model_reporting_surface.html" in gitignore
    assert "traces/local/*_semantic_model/" in gitignore


def test_readme_and_plan_document_model_semantic_path_as_opt_in() -> None:
    readme = (ROOT / "README.md").read_text()
    plan = (ROOT / "PLAN.md").read_text()

    assert "opt-in model/NLI adapter" in readme
    assert "make semantic-model-decisions-adversarial-v1-baseline" in readme
    assert "No credentialed model/NLI semantic run has been executed" in readme
    assert "model adapter prepared, not executed" in plan
    assert "generated model-decision/report/trace outputs are gitignored" in plan


def test_no_model_semantic_outputs_are_tracked() -> None:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "reports/semantic_model_decisions/*",
            "reports/*_semantic_model_eval.json",
            "reports/*semantic_model_reporting_surface.html",
            "traces/local/*_semantic_model/*",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""
