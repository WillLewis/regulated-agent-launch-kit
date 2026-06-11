"""Make-wiring tests for the M7d grader-reliability targets.

Locks in the credential posture: only ``grader-gold-pass`` may spend tokens;
the scorer / replay / report / demo targets must be credential-free.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"

CREDENTIAL_FREE = (
    "grader-gold-score-demo",
    "grader-gold-replay",
    "grader-reliability-report",
)


def _prereqs(makefile: str, target: str) -> list[str]:
    match = re.search(rf"^{re.escape(target)}:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
    assert match is not None, f"target {target!r} not found"
    return match.group(1).split()


def _recipe(makefile: str, target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}:[^\n]*\n((?:\t[^\n]*\n)+)", makefile, flags=re.MULTILINE
    )
    assert match is not None, f"recipe for {target!r} not found"
    return match.group(1)


def test_all_grader_gold_targets_exist() -> None:
    makefile = MAKEFILE.read_text()
    for target in (
        "grader-gold-score-demo",
        "grader-gold-pass",
        "grader-gold-replay",
        "grader-reliability-report",
    ):
        assert f"{target}:" in makefile, f"missing Make target {target!r}"


def test_only_the_pass_is_credentialed() -> None:
    makefile = MAKEFILE.read_text()
    assert "check-llm-env" in _prereqs(makefile, "grader-gold-pass")
    for target in CREDENTIAL_FREE:
        assert "check-llm-env" not in _prereqs(makefile, target), (
            f"{target} must be credential-free"
        )
        recipe = _recipe(makefile, target).lower()
        assert "check-llm-env" not in recipe
        # These targets read recorded verdicts; they must not call the live grader.
        assert "run_grader_gold_pass" not in recipe


def test_demo_target_uses_the_tracked_demo_fixture() -> None:
    recipe = _recipe(MAKEFILE.read_text(), "grader-gold-score-demo")
    assert "tests/fixtures/grader_gold/demo_grader_verdicts.json" in recipe


def test_pass_writes_to_gitignored_raw_path() -> None:
    recipe = _recipe(MAKEFILE.read_text(), "grader-gold-pass")
    assert "reports/grader_gold/raw_decisions.json" in recipe
    gitignore = GITIGNORE.read_text()
    assert "reports/grader_gold/" in gitignore


def test_real_report_path_is_trackable_but_demo_is_ignored() -> None:
    gitignore = GITIGNORE.read_text()
    # demo outputs ignored
    assert "reports/grader_gold_reliability_demo.json" in gitignore
    assert "reports/grader_gold_reliability_demo.md" in gitignore
    # the real report is NOT pinned as ignored (so it can be committed)
    real_ignored = re.search(
        r"^reports/grader_gold_reliability\.md$", gitignore, flags=re.MULTILINE
    )
    assert real_ignored is None, "real reliability report must stay trackable"
