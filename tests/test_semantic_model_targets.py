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

    # The opt-in model/NLI adapter and the credentialed baseline/improved lane
    # remain documented as opt-in.
    assert "opt-in model/NLI adapter" in readme
    assert "make semantic-model-decisions-adversarial-v1-baseline" in readme
    # The candidate-draft model/NLI audit has now been executed once and is
    # reported only from a tracked, aggregate-only summary.
    assert "reports/llm_adversarial_v1_semantic_audit_summary.md" in readme
    assert "lexical blind spot" in readme.lower()
    # Raw model-decision/report/trace outputs stay gitignored local artifacts.
    assert "generated model-decision/report/trace outputs are gitignored" in plan
    # PLAN records the executed candidate audit, not just a prepared adapter.
    assert (
        "Model/NLI semantic audit of the adversarial v1 LLM candidate drafts" in plan
    )
    assert "lexical blind spot" in plan.lower()


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


def test_llm_semantic_decision_targets_do_not_rerun_candidate_evals() -> None:
    """The adversarial v1 LLM semantic-decision targets must judge drafts
    already on disk. They must NOT depend on the candidate eval targets, which
    would re-call the candidate model and overwrite the very drafts the
    decisions are made against."""

    makefile = _makefile()
    for prof in ("v0", "v1"):
        target = f"semantic-model-decisions-adversarial-v1-llm-{prof}"
        # Only check-llm-env is a prerequisite — never the candidate eval target.
        assert f"\n{target}: check-llm-env\n" in makefile, target
        assert (
            f"{target}: check-llm-env eval-adversarial-v1-llm-{prof}" not in makefile
        ), f"{target} must not depend on the candidate eval (would rerun it)"

        block = _target_block(target)
        # The recipe judges the on-disk report; it must not re-run the agent.
        assert "scripts/run_eval.py" not in block
        assert f"--agent-system-version llm_candidate_{prof}" not in block
        assert "scripts/generate_semantic_decisions.py" in block
        assert f"reports/llm_adversarial_v1_candidate_{prof}_eval.json" in block
        # It guards for the existing report + traces instead of regenerating.
        assert "not found" in block
        assert f"traces/local/llm_adversarial_v1_candidate_{prof}" in block


def test_llm_semantic_audit_summary_target_is_on_disk_only() -> None:
    block = _target_block("semantic-audit-summary-adversarial-v1-llm")
    assert "scripts/summarize_semantic_audit_adversarial_v1_llm.py" in block
    assert "reports/llm_adversarial_v1_semantic_audit_summary.json" in block
    assert "reports/llm_adversarial_v1_semantic_audit_summary.md" in block
    # No model call, no candidate rerun, no credentials needed.
    assert "scripts/run_eval.py" not in block
    assert "--agent-system-version" not in block
    assert "check-llm-env" not in block


def test_semantic_audit_summary_is_trackable_but_decisions_are_not() -> None:
    # The aggregate audit summary is a public artifact (not gitignored).
    summary = subprocess.run(
        [
            "git",
            "check-ignore",
            "reports/llm_adversarial_v1_semantic_audit_summary.json",
            "reports/llm_adversarial_v1_semantic_audit_summary.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # check-ignore exits 1 when NONE of the paths are ignored.
    assert summary.returncode == 1, (
        f"semantic audit summary must be trackable, got ignored: {summary.stdout}"
    )

    # The raw model/NLI decision files stay gitignored.
    decisions = subprocess.run(
        [
            "git",
            "check-ignore",
            "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json",
            "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert decisions.returncode == 0
    assert "adversarial_v1_llm_candidate_v0.json" in decisions.stdout
    assert "adversarial_v1_llm_candidate_v1.json" in decisions.stdout
