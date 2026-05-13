"""Tests for the opt-in adversarial LLM eval run path.

These tests lock in the same invariants the smoke-slice opt-in tests
enforce, but for the adversarial slice:

1. The opt-in Make targets ``eval-adversarial-llm`` and
   ``eval-card-adversarial-llm`` exist with the right dependency wiring.
2. No deterministic Make target depends on either target.
3. The README documents the credential-gated adversarial opt-in run.
4. PLAN.md says the adversarial LLM run path is prepared / not executed.
5. No standard test requires the adversarial LLM run artifacts to exist
   on disk.
6. ``scripts/generate_eval_card.py`` accepts ``--baseline-label`` /
   ``--improved-label`` without breaking the existing deterministic cards.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from evals.run import run_eval
from scripts.generate_eval_card import generate_eval_card, render_card


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"
SCRIPTS = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"
GENERATOR_SCRIPT = SCRIPTS / "generate_eval_card.py"
ADVERSARIAL_PATH = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v0.jsonl"
)


# ---------------------------------------------------------------------------
# Makefile wiring
# ---------------------------------------------------------------------------

def test_makefile_has_adversarial_llm_targets() -> None:
    makefile = MAKEFILE.read_text()
    for target in ("eval-adversarial-llm:", "eval-card-adversarial-llm:"):
        assert target in makefile, f"Makefile missing target {target!r}"


def test_eval_adversarial_llm_depends_on_check_llm_env() -> None:
    """The preflight gate must run before any credentialed eval invocation."""

    makefile = MAKEFILE.read_text()
    match = re.search(r"^eval-adversarial-llm:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
    assert match is not None, "eval-adversarial-llm target not found"
    prereqs = match.group(1).split()
    assert "check-llm-env" in prereqs, (
        "eval-adversarial-llm must list check-llm-env as a prerequisite; "
        f"got {prereqs}"
    )


def test_eval_card_adversarial_llm_depends_on_both_adversarial_evals() -> None:
    makefile = MAKEFILE.read_text()
    match = re.search(
        r"^eval-card-adversarial-llm:\s*([^\n]*)$", makefile, flags=re.MULTILINE
    )
    assert match is not None, "eval-card-adversarial-llm target not found"
    prereqs = match.group(1).split()
    assert "eval-adversarial-improved" in prereqs, (
        "eval-card-adversarial-llm must list eval-adversarial-improved as a "
        f"prerequisite; got {prereqs}"
    )
    assert "eval-adversarial-llm" in prereqs, (
        "eval-card-adversarial-llm must list eval-adversarial-llm as a "
        f"prerequisite; got {prereqs}"
    )


def test_eval_adversarial_llm_runs_the_right_profile_and_paths() -> None:
    """The new target must run llm_candidate_v0 against the adversarial slice
    and write the expected report/trace destinations."""

    makefile = MAKEFILE.read_text()
    # Extract the body of the eval-adversarial-llm target (recipe lines until
    # the next blank line or the next target).
    pattern = re.compile(
        r"^eval-adversarial-llm:[^\n]*\n((?:\t[^\n]*\n)+)", re.MULTILINE
    )
    match = pattern.search(makefile)
    assert match is not None, "eval-adversarial-llm recipe not found"
    body = match.group(1)
    assert "scripts/run_eval.py" in body
    assert (
        "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl"
        in body
    )
    assert "traces/local/llm_adversarial" in body
    assert "reports/llm_adversarial_eval.json" in body
    assert "llm_candidate_v0" in body


def test_eval_card_adversarial_llm_uses_improved_v0_as_reference() -> None:
    """The card target should compare improved_v0 (reference) vs
    llm_candidate_v0 (candidate)."""

    makefile = MAKEFILE.read_text()
    pattern = re.compile(
        r"^eval-card-adversarial-llm:[^\n]*\n((?:\t[^\n]*\n)+)", re.MULTILINE
    )
    match = pattern.search(makefile)
    assert match is not None, "eval-card-adversarial-llm recipe not found"
    body = match.group(1)
    assert "reports/improved_adversarial_eval.json" in body, (
        "card target must use improved_v0 as the reference profile report"
    )
    assert "reports/llm_adversarial_eval.json" in body, (
        "card target must use the llm_candidate_v0 adversarial report"
    )
    assert "reports/llm_adversarial_eval_card.md" in body, (
        "card target must write reports/llm_adversarial_eval_card.md"
    )


_DETERMINISTIC_TARGETS: tuple[str, ...] = (
    "test:",
    "scaffold-test:",
    "dataset-test:",
    "dataset-test-adversarial:",
    "eval-smoke:",
    "eval-smoke-baseline:",
    "eval-smoke-improved:",
    "eval-card-smoke:",
    "eval-v0-baseline:",
    "eval-v0-improved:",
    "eval-card-v0:",
    "regression-seed-v0:",
    "regression-check-v0:",
    "redact-v0:",
    "evidence-pack-v0:",
    "eval-adversarial-baseline:",
    "eval-adversarial-improved:",
    "eval-card-adversarial:",
    "lint:",
)


def test_no_deterministic_target_depends_on_adversarial_llm_targets() -> None:
    """The credential-free public proof loop must not pull in either of the
    new opt-in adversarial LLM targets."""

    makefile = MAKEFILE.read_text()
    forbidden_prereqs = {"eval-adversarial-llm", "eval-card-adversarial-llm"}

    for target in _DETERMINISTIC_TARGETS:
        pattern = rf"^{re.escape(target)}\s*([^\n]*)$"
        match = re.search(pattern, makefile, flags=re.MULTILINE)
        if match is None:
            continue
        prereqs = set(match.group(1).split())
        leaked = prereqs & forbidden_prereqs
        assert not leaked, (
            f"deterministic Make target {target} depends on adversarial LLM "
            f"target(s) {leaked}; the public proof loop must not require "
            "credentials."
        )


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

def test_readme_documents_adversarial_llm_opt_in() -> None:
    readme = README.read_text()
    lower = readme.lower()
    for fragment in (
        "make check-llm-env",
        "make eval-adversarial-llm",
        "make eval-card-adversarial-llm",
        "ANTHROPIC_API_KEY",
    ):
        assert fragment in readme, (
            f"README missing adversarial opt-in instruction: {fragment!r}"
        )
    # The adversarial opt-in section must be credential-gated and explicitly
    # decoupled from the deterministic proof loop.
    assert "opt-in" in lower
    assert "credential" in lower
    assert "no silent fallback" in lower
    # The README must continue to disclose that the LLM has not yet been
    # evaluated on this slice until the card is in-repo.
    assert "has not yet been evaluated" in lower or "not yet been evaluated" in lower

    # And the newly-added opt-in subsection itself must not contain affirmative
    # safety / readiness / regulatory claims. We isolate the section so the
    # broader README's *disclaimer* uses of these words (e.g. "regulatory" in
    # "no regulatory claim is made") are not flagged.
    section_marker = "#### Optional adversarial LLM run"
    assert section_marker in readme, (
        "README must contain a dedicated adversarial LLM opt-in subsection"
    )
    start = readme.index(section_marker)
    # The next `## ` or `#### ` heading closes the section.
    rest = readme[start + len(section_marker):]
    next_break = len(rest)
    for marker in ("\n## ", "\n#### ", "\n### "):
        idx = rest.find(marker)
        if idx != -1 and idx < next_break:
            next_break = idx
    section = rest[:next_break].lower()
    for forbidden_phrase in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "regulatory compliance",
        "regulatory-compliant",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden_phrase not in section, (
            "README adversarial LLM opt-in section contains overclaim phrase: "
            f"{forbidden_phrase!r}"
        )


def test_plan_marks_adversarial_llm_path_prepared_but_not_executed() -> None:
    plan = PLAN.read_text()
    lower = plan.lower()
    # The opt-in adversarial LLM targets must be named in PLAN.
    assert "eval-adversarial-llm" in plan
    assert "eval-card-adversarial-llm" in plan
    # The path must be described as prepared but not executed.
    assert "prepared" in lower
    assert "not yet executed" in lower or "not executed" in lower
    # The recommended next step is to run the credentialed eval and interpret.
    assert "credential" in lower or "anthropic_api_key" in lower


# ---------------------------------------------------------------------------
# Standard suite must not require the adversarial LLM artifacts
# ---------------------------------------------------------------------------

# Paths that other tests must not depend on (they're produced only by
# a real LLM run).
_LLM_ADVERSARIAL_OUTPUT_PATHS: tuple[str, ...] = (
    "reports/llm_adversarial_eval.json",
    "reports/llm_adversarial_eval_card.md",
    "traces/local/llm_adversarial",
)

# Paths that must NEVER be tracked by git — they embed raw LLM draft
# text and are republished only through the redacted evidence pack at
# evidence_packs/financial_links_llm_v0/. The corrected card
# (reports/llm_adversarial_eval_card.md) is intentionally NOT in this
# list: it has no raw payloads and carries the LLM-aware disclaimer.
_RAW_LLM_ADVERSARIAL_PATHS: tuple[str, ...] = (
    "reports/llm_adversarial_eval.json",
    "traces/local/llm_adversarial",
)


def test_no_test_requires_generated_adversarial_llm_outputs() -> None:
    """No other test in the suite may depend on the LLM-only adversarial artifacts.

    ``tests/test_evidence_pack_llm.py`` is exempt because it builds its
    own fixtures in ``tmp_path`` and uses the ``traces/local/...`` path
    string solely to verify the pack script refuses raw-trace inputs —
    it never reads from the real on-disk location.
    """

    exempt = {Path(__file__).name, "test_evidence_pack_llm.py"}
    for test_file in TESTS_DIR.glob("**/*.py"):
        if test_file.name in exempt:
            continue
        content = test_file.read_text()
        for forbidden in _LLM_ADVERSARIAL_OUTPUT_PATHS:
            assert forbidden not in content, (
                f"{test_file.name} references {forbidden!r}; the standard "
                "suite must not depend on LLM-run-only artifacts."
            )


def test_raw_llm_adversarial_outputs_are_not_committed() -> None:
    """Raw LLM-adversarial outputs may never be tracked by git.

    The opt-in LLM path produces real model traces under
    ``traces/local/llm_adversarial/`` and a JSON eval report at
    ``reports/llm_adversarial_eval.json`` that embeds raw ``draft_text``
    / ``draft_excerpt`` content. Both are treated as raw evidence and
    are gitignored. They must be republished only through the redacted
    pack at ``evidence_packs/financial_links_llm_v0/``. ``git ls-files``
    is the source of truth for tracking state.

    The corrected card (``reports/llm_adversarial_eval_card.md``) is
    explicitly NOT in scope — it carries no raw payloads and is allowed
    to be tracked publicly with its LLM-aware disclaimer.
    """

    import subprocess

    # ``git ls-files`` on a directory path returns all files tracked
    # under it. Use ``traces/local/llm_adversarial`` (no trailing
    # ``/*``) so the check catches anything inside without depending on
    # shell expansion.
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", *_RAW_LLM_ADVERSARIAL_PATHS],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], (
        "git is tracking raw LLM-adversarial outputs that embed raw model "
        "draft text. Untrack them with `git rm --cached` and rely on the "
        f"redacted evidence pack instead. Tracked: {tracked}"
    )


# ---------------------------------------------------------------------------
# Card-generator label args
# ---------------------------------------------------------------------------

def test_card_generator_cli_accepts_baseline_and_improved_labels() -> None:
    """The CLI must expose ``--baseline-label`` / ``--improved-label``."""

    result = subprocess.run(
        [sys.executable, str(GENERATOR_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert "--baseline-label" in combined
    assert "--improved-label" in combined


def test_card_generator_labels_default_to_baseline_and_improved(tmp_path: Path) -> None:
    """Default behavior must preserve the existing card text exactly so the
    deterministic card tests stay green."""

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
    out = tmp_path / "card.md"
    generate_eval_card(baseline_report, improved_report, out)
    rendered = out.read_text()

    # Default columns + section headings keep the legacy strings.
    assert "| Field | Baseline | Improved |" in rendered
    assert "| Grader | Baseline | Improved | Δ pass rate |" in rendered
    assert "## What failed in baseline" in rendered
    assert "## What failed in improved" in rendered
    assert "## What changed in improved profile" in rendered


def test_card_generator_custom_labels_are_threaded_through(tmp_path: Path) -> None:
    """Passing custom labels must rewrite the column headers and section headings
    consistently — used by the new eval-card-adversarial-llm target so the card
    reads as reference (improved_v0) vs candidate (llm_candidate_v0)."""

    baseline_report = tmp_path / "improved_ref.json"
    improved_report = tmp_path / "improved_cand.json"
    # We can't run llm_candidate_v0 in the standard suite (no credentials), so
    # we exercise the label plumbing using two deterministic profiles that
    # differ — improved_v0 against baseline_v0 is sufficient.
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "ref_traces",
        report_out=baseline_report,
        agent_system_version="improved_v0",
    )
    run_eval(
        dataset_path=ADVERSARIAL_PATH,
        traces_out=tmp_path / "cand_traces",
        report_out=improved_report,
        agent_system_version="baseline_v0",
    )
    out = tmp_path / "card.md"
    generate_eval_card(
        baseline_report,
        improved_report,
        out,
        baseline_label="Reference",
        improved_label="Candidate",
    )
    rendered = out.read_text()

    assert "| Field | Reference | Candidate |" in rendered
    assert "| Grader | Reference | Candidate | Δ pass rate |" in rendered
    assert "## What failed in reference" in rendered
    assert "## What failed in candidate" in rendered
    assert "## What changed in candidate profile" in rendered
    # The "Baseline EVALUATOR_MISS" / "Improved EVALUATOR_MISS" line must
    # follow the labels too.
    assert "**Reference `EVALUATOR_MISS`:**" in rendered
    assert "**Candidate `EVALUATOR_MISS`:**" in rendered
    # And we must NOT carry forward the deterministic baseline_v0 -> improved_v0
    # fix-bullet text when the profile pair is not that canonical pair.
    forbidden_bullets = (
        "Restores the synthetic partner-fallback policy citation",
        "Calls `lookup_partner_config` even on healthy aggregator routes",
        "Removes the baseline's real-time-data overpromise",
    )
    for bullet in forbidden_bullets:
        assert bullet not in rendered, (
            f"non-canonical pair card contains canonical fix bullet: {bullet!r}"
        )


def test_render_card_signature_accepts_label_kwargs() -> None:
    """The public render_card function must accept label kwargs so other
    scripts and tests can render cards programmatically with custom labels."""

    import inspect

    sig = inspect.signature(render_card)
    assert "baseline_label" in sig.parameters
    assert "improved_label" in sig.parameters
    # Defaults must preserve "Baseline" / "Improved".
    assert sig.parameters["baseline_label"].default == "Baseline"
    assert sig.parameters["improved_label"].default == "Improved"
