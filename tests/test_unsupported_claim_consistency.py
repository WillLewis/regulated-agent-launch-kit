"""Lock in the post-grader-upgrade public-surface consistency.

The offline ``grade_unsupported_claim`` grader is negation-aware; the
runtime ``unsupported_claim_check`` stays a conservative substring
guardrail. Code and tests reflect this. These tests lock the
**documentation surfaces** (README, PLAN, evaluator docstring, eval
cards) so they cannot drift back to the pre-upgrade story.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.run import EvalReport, run_eval
from scripts.generate_eval_card import (
    LLM_RUNTIME_OFFLINE_ASYMMETRY_NOTE,
    render_card,
)


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"
EVALUATOR = ROOT / "app" / "evaluator.py"
SMOKE_PATH = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "smoke.jsonl"
ADVERSARIAL_PATH = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v0.jsonl"
)


# ---------------------------------------------------------------------------
# README: pre-upgrade phrases must be gone
# ---------------------------------------------------------------------------


def _first_credentialed_run_section(readme_text: str) -> str:
    """Return the body of the README's '#### First credentialed LLM run'
    subsection so the test scopes its assertions to that block."""

    marker = "#### First credentialed LLM run"
    start = readme_text.find(marker)
    assert start != -1, "README must contain the 'First credentialed LLM run' subsection"
    rest = readme_text[start:]
    # Section ends at the next `## `, `### `, or `#### ` heading.
    end = len(rest)
    for delim in ("\n## ", "\n### ", "\n#### "):
        idx = rest.find(delim, len(marker))
        if idx != -1 and idx < end:
            end = idx
    return rest[:end]


def test_readme_first_run_section_no_longer_claims_grader_does_not_parse_negation() -> None:
    section = _first_credentialed_run_section(README.read_text())
    assert "the grader does not parse negation" not in section, (
        "README's 'First credentialed LLM run' section still tells the "
        "pre-upgrade story. The grader is now negation-aware."
    )
    # And the close paraphrase the prior wording also used.
    assert "negation-blindness" not in section, (
        "README first-run section must not describe the offline grader as "
        "negation-blind any longer."
    )


def test_readme_first_run_section_does_not_claim_v0_failed_on_004_and_006() -> None:
    """The previous 4/2-with-failures-on-cases-004-and-006 framing is
    pre-upgrade. The regraded report shows zero affirmative
    UNSAFE_CUSTOMER_COMMS failures; the runtime guardrail's one
    remaining flag is on case_fl_adv_v0_002."""

    section = _first_credentialed_run_section(README.read_text())
    for stale_case in ("case_fl_adv_v0_004", "case_fl_adv_v0_006"):
        assert stale_case not in section, (
            f"README first-run section still cites {stale_case!r} as a v0 "
            "UNSAFE_CUSTOMER_COMMS failure. Under the negation-aware grader "
            "neither v0 nor v1 emits an affirmative failure on this slice."
        )


def test_readme_first_run_section_uses_post_upgrade_framing() -> None:
    section = _first_credentialed_run_section(README.read_text()).lower()
    # Some post-upgrade signal must be present.
    assert "negation-aware" in section
    assert "case_fl_adv_v0_002" in section
    assert "cleared_by_negation" in section
    assert "not ready for pilot" in section


# ---------------------------------------------------------------------------
# PLAN: the recommended-next row must not still recommend the now-done work
# ---------------------------------------------------------------------------


def test_plan_no_longer_recommends_making_grader_negation_aware() -> None:
    plan = PLAN.read_text()
    lower = plan.lower()

    # The stale row marker.
    assert "next recommended phase — deliberate grader-vs-prompt decision" not in lower, (
        "PLAN.md still carries the pre-upgrade 'deliberate grader-vs-prompt "
        "decision' row. The negation-aware grader path has been taken; "
        "replace the row with the actual next recommended step."
    )

    # The specific stale recommendation phrasing.
    stale_recommendations = (
        "refine the grader to be negation-aware",
        "(1) refine the grader to be negation-aware",
    )
    for phrase in stale_recommendations:
        assert phrase not in lower, (
            f"PLAN.md still recommends the now-completed grader upgrade "
            f"({phrase!r}). Replace with the next real step."
        )


def test_plan_recommends_repeat_run_variance_or_nli_grader_next() -> None:
    """The new recommended-next row must point at one of the two
    forward steps the memo flagged as the real remaining work."""

    lower = PLAN.read_text().lower()
    assert (
        "repeat" in lower and ("variance" in lower or "repeat-run" in lower)
    ) or "nli" in lower, (
        "PLAN.md must recommend repeat-run variance measurement (or an "
        "NLI-style grader experiment) as the next phase now that the "
        "negation-aware grader has landed."
    )


# ---------------------------------------------------------------------------
# Runtime evaluator docstring
# ---------------------------------------------------------------------------


def test_evaluator_docstring_no_longer_says_runtime_mirror() -> None:
    text = EVALUATOR.read_text()
    assert "Runtime mirror of ``evals.graders.grade_unsupported_claim``" not in text, (
        "app/evaluator.py::unsupported_claim_check docstring still calls "
        "itself a 'Runtime mirror' of the offline grader. After the "
        "negation-aware upgrade the two are deliberately asymmetric; "
        "update the docstring."
    )


def test_evaluator_docstring_describes_asymmetry_and_test_link() -> None:
    text = EVALUATOR.read_text()
    # Some honest framing of the asymmetry must be present.
    assert "conservative substring guardrail" in text.lower()
    # And the asymmetry test must be referenced so a future reader can
    # find what locks the contract.
    assert "test_runtime_evaluator_remains_conservative_on_negated_phrasing" in text


# ---------------------------------------------------------------------------
# Generated LLM cards include the asymmetry note; deterministic cards do not
# ---------------------------------------------------------------------------


@pytest.fixture()
def deterministic_pair(tmp_path: Path) -> tuple[EvalReport, EvalReport]:
    baseline = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "b",
        report_out=tmp_path / "b.json",
        agent_system_version="baseline_v0",
    )
    improved = run_eval(
        dataset_path=SMOKE_PATH,
        traces_out=tmp_path / "i",
        report_out=tmp_path / "i.json",
        agent_system_version="improved_v0",
    )
    return baseline, improved


def _llm_shape_pair(
    reference: EvalReport,
) -> tuple[EvalReport, EvalReport]:
    """Relabel a deterministic report's agent_system_version to make it
    LLM-shape for asymmetry-block rendering. The card branch we're
    testing only inspects ``agent_system_version``."""

    before = reference.model_copy(update={"agent_system_version": "llm_candidate_v0"})
    after = reference.model_copy(update={"agent_system_version": "llm_candidate_v1"})
    return before, after


def test_deterministic_card_omits_llm_asymmetry_note(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    baseline, improved = deterministic_pair
    text = render_card(baseline, improved)
    assert LLM_RUNTIME_OFFLINE_ASYMMETRY_NOTE not in text, (
        "Deterministic cards must not carry the LLM-only asymmetry note."
    )
    # And the headline phrase that's specific to the note must be absent.
    assert "Why a case can be marked failed with zero failure labels" not in text


def test_llm_paired_card_includes_asymmetry_note(
    deterministic_pair: tuple[EvalReport, EvalReport],
) -> None:
    reference, _ = deterministic_pair
    before, after = _llm_shape_pair(reference)
    text = render_card(before, after, baseline_label="Before", improved_label="After")
    assert LLM_RUNTIME_OFFLINE_ASYMMETRY_NOTE in text, (
        "Cards comparing any llm_* profile must include the "
        "runtime/offline asymmetry explainer near the failing-case "
        "section."
    )
    # The note must mention the field a reviewer should inspect.
    assert "cleared_by_negation" in text


def test_committed_llm_cards_carry_asymmetry_note() -> None:
    """Belt-and-braces: the two tracked LLM cards on disk must have the
    note. This catches the case where the cards drift away from the
    generator (e.g. someone hand-edits them)."""

    for rel in (
        "reports/llm_adversarial_eval_card.md",
        "reports/llm_adversarial_v1_vs_v0_card.md",
    ):
        path = ROOT / rel
        text = path.read_text()
        assert LLM_RUNTIME_OFFLINE_ASYMMETRY_NOTE in text, (
            f"{rel} is missing the runtime/offline asymmetry note. "
            "Regenerate with `make eval-card-adversarial-llm` "
            "(credentialed) or by re-running scripts/generate_eval_card.py "
            "against the existing on-disk reports."
        )
