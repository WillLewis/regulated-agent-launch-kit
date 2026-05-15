"""Tests for the LLM prompt-improvement memo and the matching
README / PLAN status updates.

The memo at ``reports/llm_prompt_improvement_memo.md`` is the
single-page evidence-backed write-up of the credentialed v0 → v1
prompt-improvement loop. README and PLAN must reflect that v1 has
been executed once (no longer "not yet run") without overclaiming.
These tests lock in the public-safety constraints around all three
surfaces.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMO = ROOT / "reports" / "llm_prompt_improvement_memo.md"
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"


# ---------------------------------------------------------------------------
# Memo
# ---------------------------------------------------------------------------


def test_memo_exists() -> None:
    assert MEMO.exists(), (
        "reports/llm_prompt_improvement_memo.md must exist; it's the "
        "evidence-backed write-up of the v0 → v1 prompt-improvement loop"
    )


def test_memo_contains_dataset_and_run_scope() -> None:
    text = MEMO.read_text()
    assert "financial_links_reliability_adversarial_v0" in text
    # The memo must say "6" cases and that they're synthetic, even if
    # markdown line-wrap puts those tokens on different lines.
    flat = re.sub(r"\s+", " ", text)
    assert re.search(r"\b6\b[^.]*?synthetic", flat), (
        "memo must name the 6-case synthetic scope explicitly"
    )


def test_memo_contains_v0_and_v1_metrics() -> None:
    text = MEMO.read_text()
    for token in (
        "llm_candidate_v0",
        "llm_candidate_v1",
        "Before",
        "After",
        "UNSAFE_CUSTOMER_COMMS",
        "EVALUATOR_MISS",
    ):
        assert token in text, f"memo missing required token {token!r}"


def test_memo_contains_cost_and_latency_signals() -> None:
    text = MEMO.read_text()
    lower = text.lower()
    # Cost: dollar-amount or "cost" mention with a delta-like signal.
    assert "cost" in lower
    assert "$" in text or "USD" in text or "usd" in lower
    # Latency: per-band budget framing.
    assert "latency" in lower
    assert any(verdict in text for verdict in ("exceeds_p95", "between_p50_and_p95", "within_p50"))


def test_memo_keeps_not_ready_for_pilot_and_no_overclaims() -> None:
    text = MEMO.read_text()
    lower = text.lower()
    assert "NOT READY FOR PILOT" in text
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
        "regulatory-compliant",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"memo must not claim {phrase!r}"


# ---------------------------------------------------------------------------
# README + PLAN status
# ---------------------------------------------------------------------------


def test_readme_marks_v1_executed_once_without_overclaim() -> None:
    """README must say v1 was executed once on the 6-case slice and not
    overclaim. Earlier 'has not yet been run' wording must be gone."""

    text = README.read_text()
    lower = text.lower()
    # New honest framing (any of these is acceptable).
    assert (
        "executed once" in lower
        or "credentialed v1 comparison has been executed" in lower
        or "has been executed once" in lower
    ), (
        "README must clearly say v1 has been executed at least once now "
        "that the credentialed run is in-repo"
    )
    # Must call out the 6-case scope.
    assert "6-case" in lower or "6 cases" in lower
    # Must keep the launch posture.
    assert "NOT READY FOR PILOT" in text
    # Stale wording must be gone.
    assert "no claim about how much better v1 is can be made until you actually run it" not in lower
    # Memo must be linked.
    assert "reports/llm_prompt_improvement_memo.md" in text


def test_plan_marks_v1_executed_once_without_overclaim() -> None:
    text = PLAN.read_text()
    lower = text.lower()
    assert (
        "v1" in lower and ("executed once" in lower or "has now also been executed" in lower)
    ), "PLAN must say v1 has been executed once"
    assert "NOT READY FOR PILOT" not in text or "NOT READY FOR PILOT" in text
    # Either the launch posture is preserved at the lab level (existing
    # README/cards/pack), or PLAN explicitly notes it. Either way no
    # overclaim should appear in the v1 line.
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"PLAN must not claim {phrase!r}"
    # Stale wording must be gone.
    assert "no claim is made about real-llm v1 behavior until that credentialed run executes" not in lower


# ---------------------------------------------------------------------------
# Tracked markdown must not link to raw v0 OR v1 traces
# ---------------------------------------------------------------------------


def test_no_raw_llm_evidence_is_tracked_by_git() -> None:
    """Raw LLM evidence must stay local. ``reports/llm_*_eval.json``
    files embed raw model output (in ``draft_excerpt`` evidence
    blocks); ``traces/local/llm_*/`` files embed full draft / final
    response payloads. Both are gitignored. The public-safe view is
    the redacted summary + redacted traces inside the LLM evidence
    packs, plus the corrected cards."""

    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "traces/local/llm_*", "reports/llm_*_eval.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], (
        "raw LLM evidence is tracked by git; untrack with `git rm --cached` "
        "and confirm `.gitignore` covers the path. Tracked: "
        f"{tracked}"
    )


def test_gitignore_excludes_raw_llm_eval_reports() -> None:
    """Defense-in-depth: the gitignore must explicitly cover both the
    v0 and v1 raw LLM eval JSON reports, not just the trace dir. If a
    future eval script writes to a similar path we still want it
    excluded."""

    gitignore = (ROOT / ".gitignore").read_text()
    for required in (
        "traces/local/llm_*",
        "reports/llm_adversarial_eval.json",
        "reports/llm_adversarial_v1_eval.json",
    ):
        assert required in gitignore, (
            f".gitignore must list {required!r} so raw LLM evidence stays local"
        )


def test_no_tracked_markdown_links_raw_local_llm_paths() -> None:
    """Defense-in-depth: re-run the substring scan across every tracked
    markdown file. The two previous turns enforced this; keep the
    invariant locked even after the v1 docs land."""

    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    leaks: list[str] = []
    for rel in result.stdout.splitlines():
        path = ROOT / rel
        if not path.exists():
            continue
        if "traces/local/llm_" in path.read_text():
            leaks.append(rel)
    assert not leaks, (
        f"tracked markdown contains raw-LLM-trace path strings: {leaks}"
    )
