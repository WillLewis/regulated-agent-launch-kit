"""Tests for the opt-in adversarial LLM eval run path.

These tests lock in the same invariants the smoke-slice opt-in tests
enforce, but for the adversarial slice:

1. The opt-in Make targets ``eval-adversarial-llm`` and
   ``eval-card-adversarial-llm`` exist with the right dependency wiring.
2. No deterministic Make target depends on either target.
3. The README documents the credential-gated adversarial opt-in run.
4. PLAN.md records the first credentialed adversarial LLM signal and the
   deliberate grader-vs-prompt decision now in front of the lab.
5. No standard test outside this file requires the adversarial LLM artifacts.
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
    for target in (
        "eval-adversarial-llm:",
        "eval-card-adversarial-llm:",
        "eval-adversarial-llm-v1:",
        "eval-card-adversarial-llm-v1:",
    ):
        assert target in makefile, f"Makefile missing target {target!r}"


def test_eval_adversarial_llm_v1_depends_on_check_llm_env() -> None:
    makefile = MAKEFILE.read_text()
    match = re.search(
        r"^eval-adversarial-llm-v1:\s*([^\n]*)$", makefile, flags=re.MULTILINE
    )
    assert match is not None, "eval-adversarial-llm-v1 target not found"
    prereqs = match.group(1).split()
    assert "check-llm-env" in prereqs, (
        "eval-adversarial-llm-v1 must list check-llm-env as a prerequisite; "
        f"got {prereqs}"
    )


def test_eval_card_adversarial_llm_v1_compares_v0_to_v1() -> None:
    makefile = MAKEFILE.read_text()
    match = re.search(
        r"^eval-card-adversarial-llm-v1:\s*([^\n]*)$", makefile, flags=re.MULTILINE
    )
    assert match is not None, "eval-card-adversarial-llm-v1 target not found"
    prereqs = match.group(1).split()
    # The Before/After card target must depend on both LLM runs so
    # neither side is stale.
    assert "eval-adversarial-llm" in prereqs, (
        f"v1 card must depend on the v0 LLM eval (Before); got {prereqs}"
    )
    assert "eval-adversarial-llm-v1" in prereqs, (
        f"v1 card must depend on the v1 LLM eval (After); got {prereqs}"
    )

    # Recipe must wire Before/After labels and write the canonical card path.
    pattern = re.compile(
        r"^eval-card-adversarial-llm-v1:[^\n]*\n((?:\t[^\n]*\n)+)",
        re.MULTILINE,
    )
    body_match = pattern.search(makefile)
    assert body_match is not None, "eval-card-adversarial-llm-v1 recipe not found"
    body = body_match.group(1)
    assert "reports/llm_adversarial_eval.json" in body
    assert "reports/llm_adversarial_v1_eval.json" in body
    assert "--baseline-label Before" in body
    assert "--improved-label After" in body
    assert "reports/llm_adversarial_v1_vs_v0_card.md" in body


def test_eval_adversarial_llm_v1_runs_the_right_profile_and_paths() -> None:
    makefile = MAKEFILE.read_text()
    pattern = re.compile(
        r"^eval-adversarial-llm-v1:[^\n]*\n((?:\t[^\n]*\n)+)", re.MULTILINE
    )
    match = pattern.search(makefile)
    assert match is not None, "eval-adversarial-llm-v1 recipe not found"
    body = match.group(1)
    assert "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl" in body
    assert "traces/local/llm_adversarial_v1" in body
    assert "reports/llm_adversarial_v1_eval.json" in body
    assert "llm_candidate_v1" in body


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
    """The credential-free public proof loop must not pull in any of the
    opt-in adversarial LLM targets (v0 or v1)."""

    makefile = MAKEFILE.read_text()
    forbidden_prereqs = {
        "eval-adversarial-llm",
        "eval-card-adversarial-llm",
        "eval-adversarial-llm-v1",
        "eval-card-adversarial-llm-v1",
    }

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


def test_readme_documents_first_credentialed_run() -> None:
    readme = README.read_text()
    lower = readme.lower()
    assert "has not yet been evaluated" not in lower, (
        "README still says the LLM has not been evaluated; flip this now that "
        "the card is committed."
    )
    assert "First credentialed LLM run" in readme
    assert "6" in readme  # six-case slice
    assert "UNSAFE_CUSTOMER_COMMS" in readme
    # Post-grader-upgrade: the canonical worked example is case_fl_adv_v0_002
    # (runtime guardrail fires on hedged-but-negated language that the
    # offline negation-aware grader clears). The pre-upgrade "two failures
    # on cases _004 + _006" framing is gone.
    assert "case_fl_adv_v0_002" in readme, (
        "README first-run section must cite case_fl_adv_v0_002 as the "
        "canonical worked example of the runtime-vs-offline asymmetry"
    )
    assert "NOT READY FOR PILOT" in readme
    assert "no affirmative" in lower or "negation-aware" in lower

    overclaims = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    )
    section_marker = "#### First credentialed LLM run"
    assert section_marker in readme
    start = readme.index(section_marker)
    rest = readme[start + len(section_marker):]
    next_break = len(rest)
    for marker in ("\n## ", "\n#### ", "\n### "):
        idx = rest.find(marker)
        if idx != -1 and idx < next_break:
            next_break = idx
    section = rest[:next_break].lower()
    for forbidden in overclaims:
        assert forbidden not in section, (
            f"first-credentialed-run subsection contains overclaim: {forbidden!r}"
        )


def test_plan_marks_adversarial_llm_path_prepared_but_not_executed() -> None:
    """PLAN must still describe the opt-in adversarial LLM targets and call out
    that the smoke-slice path has not yet been executed."""

    plan = PLAN.read_text()
    lower = plan.lower()
    assert "eval-adversarial-llm" in plan
    assert "eval-card-adversarial-llm" in plan
    assert "smoke slice still un-run" in lower or "smoke-slice opt-in" in lower
    assert "credential" in lower or "anthropic_api_key" in lower


def test_plan_marks_adversarial_llm_run_executed() -> None:
    plan = PLAN.read_text()
    lower = plan.lower()
    assert "first credentialed run executed" in lower or "first credentialed run" in lower
    assert "negation-aware" in lower or "negation aware" in lower


# ---------------------------------------------------------------------------
# Standard suite must not require the adversarial LLM artifacts
# ---------------------------------------------------------------------------

# Paths that other tests must not depend on (they're produced only by
# a real LLM run).
_LLM_ADVERSARIAL_OUTPUT_PATHS: tuple[str, ...] = (
    "reports/llm_adversarial_eval.json",
    "reports/llm_adversarial_eval_card.md",
    "reports/llm_adversarial_v1_eval.json",
    "reports/llm_adversarial_v1_vs_v0_card.md",
    "traces/local/llm_adversarial",
    "traces/local/llm_adversarial_v1",
    # adversarial v1 (12-case) LLM candidate loop raw eval reports
    "reports/llm_adversarial_v1_candidate_v0_eval.json",
    "reports/llm_adversarial_v1_candidate_v1_eval.json",
)

def test_no_test_requires_generated_adversarial_llm_outputs() -> None:
    """No other test in the suite may depend on the LLM-only adversarial artifacts.

    ``tests/test_evidence_pack_llm.py`` is exempt because it builds its
    own fixtures in ``tmp_path`` and uses the ``traces/local/...`` path
    string solely to verify the pack script refuses raw-trace inputs —
    it never reads from the real on-disk location.
    """

    exempt = {
        Path(__file__).name,
        "test_evidence_pack_llm.py",
        # Builds its own fixtures + uses the raw-LLM path string only
        # to verify the card replaces it with a redacted-trace link.
        "test_eval_card_llm_trace_links.py",
        # Builds its own fixtures + uses the raw-LLM path string only
        # to verify the v1 pack assembler refuses raw-trace inputs.
        "test_evidence_pack_llm_v1.py",
        # Asserts the raw-LLM eval JSONs stay gitignored — references
        # the path strings only to assert non-tracking, never to read
        # the files.
        "test_llm_prompt_improvement_memo.py",
        # Asserts the committed LLM cards carry the runtime/offline
        # asymmetry note — references the card paths only for that
        # docs-consistency check.
        "test_unsupported_claim_consistency.py",
        # References the adversarial v1 candidate raw-trace/report path
        # strings only to assert they stay gitignored / untracked — never
        # reads the real on-disk artifacts.
        "test_adversarial_v1_dataset.py",
        # Builds its own tmp_path fixtures and uses the raw-LLM path
        # strings only to verify the v1 pack assembler abstracts drafts
        # and refuses raw-trace inputs.
        "test_evidence_pack_adversarial_v1_llm.py",
    }
    for test_file in TESTS_DIR.glob("**/*.py"):
        if test_file.name in exempt:
            continue
        content = test_file.read_text()
        for forbidden in _LLM_ADVERSARIAL_OUTPUT_PATHS:
            assert forbidden not in content, (
                f"{test_file.name} references {forbidden!r}; the standard "
                "suite must not depend on LLM-run-only artifacts."
            )


def test_adversarial_llm_card_is_committed_and_report_is_not() -> None:
    """The first credentialed adversarial LLM run lives as public-safe
    signal: the corrected card is tracked (no raw drafts, no raw trace
    links); the raw JSON eval report stays local-only because it
    embeds raw model `draft_excerpt` content. The public-safe view of
    the report is the redacted summary inside the LLM evidence pack."""

    import subprocess

    card = ROOT / "reports" / "llm_adversarial_eval_card.md"
    assert card.exists(), (
        "reports/llm_adversarial_eval_card.md must be committed; it is the "
        "lab's first credentialed signal on the adversarial slice."
    )

    # The card is tracked.
    tracked = subprocess.run(
        ["git", "ls-files", "reports/llm_adversarial_eval_card.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert tracked == "reports/llm_adversarial_eval_card.md"

    # The raw JSON report must NOT be tracked — it carries raw
    # `draft_excerpt` payloads. The redacted summary inside
    # evidence_packs/financial_links_llm_v0/ is the public-safe view.
    raw_tracked = subprocess.run(
        ["git", "ls-files", "reports/llm_adversarial_eval.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert raw_tracked == "", (
        "reports/llm_adversarial_eval.json must remain local-only — it "
        "embeds raw LLM draft text. Public-safe view: "
        "evidence_packs/financial_links_llm_v0/llm_candidate_eval.redacted.json."
    )

    body = card.read_text()
    assert "improved_v0" in body
    assert "llm_candidate_v0" in body
    assert "NOT READY FOR PILOT" in body
    assert "Reference" in body
    assert "Candidate" in body


def test_adversarial_llm_traces_stay_local_only() -> None:
    """Raw LLM traces are not committed (no redaction pass for them yet)."""

    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "traces/local/llm_adversarial"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    tracked = result.stdout.strip()
    assert tracked == "", (
        "raw LLM traces must remain local-only until a redaction pass exists; "
        f"git ls-files surfaced: {tracked!r}"
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
