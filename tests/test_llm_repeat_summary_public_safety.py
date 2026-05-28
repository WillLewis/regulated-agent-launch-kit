"""Public-safety invariants for the credentialed repeat-run summary.

The repeat-run capture is opt-in and costs real Anthropic tokens. Once
captured, the aggregated public-safe summary at
``reports/llm_repeat_summary.{md,json}`` may be tracked. These tests
lock in:

1. README says the credentialed repeat-run was executed (not just
   "harness landed"), and only if the public-safe summary md exists.
2. PLAN no longer says credentialed repeat runs are "not yet executed".
3. The committed summary files contain no raw draft text and no raw
   trace paths (``traces/local/llm_*``, ``reports/llm_repeats/.../run_*``,
   ``draft_text``, ``draft_excerpt``).
4. The v1 evidence pack manifest indexes the public-safe repeat-run
   summary; the pack-side ``repeat_run_summary.md`` carries
   NOT READY FOR PILOT and avoids overclaims.
5. Raw repeat outputs under ``reports/llm_repeats/`` remain gitignored
   and untracked.
6. All public-facing surfaces (README, PLAN, memo, pack README, pack
   repeat-summary md) carry NOT READY FOR PILOT and avoid production /
   model-safety / regulatory claims.

These tests do not call the LLM.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"
MEMO = ROOT / "reports" / "llm_prompt_improvement_memo.md"
SUMMARY_MD = ROOT / "reports" / "llm_repeat_summary.md"
SUMMARY_JSON = ROOT / "reports" / "llm_repeat_summary.json"
PACK_DIR = ROOT / "evidence_packs" / "financial_links_llm_v1"
PACK_MANIFEST = PACK_DIR / "manifest.json"
PACK_README = PACK_DIR / "README.md"
PACK_SUMMARY_MD = PACK_DIR / "repeat_run_summary.md"
PACK_SUMMARY_JSON = PACK_DIR / "repeat_run_summary.json"


FORBIDDEN_RAW_SUBSTRINGS: tuple[str, ...] = (
    "traces/local/llm_",
    "draft_text",
    "draft_excerpt",
    "RAW MODEL OUTPUT",
)


# Narrow forbidden list: only positive-claim phrases that cannot
# legitimately appear inside a "this does NOT prove …" disclaimer.
# `regulatory compliant`, `partner endorsed`, etc. show up inside
# explicit negations in the memo and pack README, so they're omitted.
FORBIDDEN_OVERCLAIMS: tuple[str, ...] = (
    "production ready",
    "production-ready",
    "pilot ready",
    "pilot-ready",
    "model is safe",
    "safe to deploy",
)


# ---------------------------------------------------------------------------
# Summary file content gates
# ---------------------------------------------------------------------------


def test_summary_md_exists_and_carries_not_ready_posture() -> None:
    assert SUMMARY_MD.exists(), (
        "reports/llm_repeat_summary.md must exist once `make "
        "repeat-adversarial-llm-summary` has been executed"
    )
    text = SUMMARY_MD.read_text()
    assert "NOT READY FOR PILOT" in text


def test_summary_md_has_no_raw_paths_or_draft_text() -> None:
    text = SUMMARY_MD.read_text()
    for needle in FORBIDDEN_RAW_SUBSTRINGS:
        assert needle not in text, (
            f"reports/llm_repeat_summary.md leaks {needle!r}; the "
            "aggregator must strip it before the summary is tracked"
        )
    # And no per-run path under reports/llm_repeats/.../run_*
    import re

    leaks = re.findall(r"reports/llm_repeats/[^\s\"`]*?/run_\d+", text)
    assert not leaks, (
        f"reports/llm_repeat_summary.md leaks raw repeat-run paths: {leaks}"
    )


def test_summary_md_avoids_overclaims() -> None:
    lower = SUMMARY_MD.read_text().lower()
    for phrase in FORBIDDEN_OVERCLAIMS:
        assert phrase not in lower, (
            f"reports/llm_repeat_summary.md must not claim {phrase!r}"
        )


def test_summary_json_exists_and_is_not_ready_for_pilot() -> None:
    assert SUMMARY_JSON.exists()
    payload = json.loads(SUMMARY_JSON.read_text())
    assert payload.get("not_ready_for_pilot") is True
    assert payload.get("synthetic") is True
    assert payload.get("run_count", 0) >= 2


def test_summary_json_has_no_raw_paths_or_draft_text() -> None:
    text = SUMMARY_JSON.read_text()
    for needle in FORBIDDEN_RAW_SUBSTRINGS:
        assert needle not in text, (
            f"reports/llm_repeat_summary.json leaks {needle!r}"
        )
    import re

    leaks = re.findall(r"reports/llm_repeats/[^\s\"`]*?/run_\d+", text)
    assert not leaks, (
        f"reports/llm_repeat_summary.json leaks raw repeat-run paths: {leaks}"
    )


# ---------------------------------------------------------------------------
# README must reflect "credentialed repeat-run executed" only when the
# summary file actually exists
# ---------------------------------------------------------------------------


def test_readme_does_not_claim_capture_yet_to_be_executed() -> None:
    text = README.read_text().lower()
    forbidden_stale = (
        "harness landed; not yet executed",
        "no credentialed repeat-run capture has been executed yet",
        "credentialed repeat-runs have not been executed",
        "repeat-run capture is not yet executed",
        "not yet executed",
    )
    for phrase in forbidden_stale:
        assert phrase not in text, (
            f"README has stale repeat-run wording: {phrase!r}"
        )


def test_readme_marks_repeat_run_executed_when_summary_exists() -> None:
    if not SUMMARY_MD.exists():
        pytest.skip("repeat-run summary not built yet; the README claim is gated on it")
    lower = README.read_text().lower()
    assert (
        "credentialed repeat-run executed" in lower
        or "credentialed repeat-run capture has now been executed" in lower
    ), (
        "README must explicitly say the credentialed repeat-run was "
        "executed once the public-safe summary exists"
    )
    # README must link to the public-safe summary file (or the json sibling).
    text = README.read_text()
    assert "reports/llm_repeat_summary.md" in text
    # And carry the launch posture.
    assert "NOT READY FOR PILOT" in text


# ---------------------------------------------------------------------------
# PLAN must drop the "not yet executed" framing
# ---------------------------------------------------------------------------


def test_plan_no_longer_says_credentialed_repeat_runs_not_executed() -> None:
    text = PLAN.read_text().lower()
    forbidden_stale = (
        "credentialed repeat runs not yet executed",
        "no credentialed repeat-run capture has been executed yet",
        "credentialed repeat-runs have not been executed",
        "harness landed (code/test only)",
    )
    for phrase in forbidden_stale:
        assert phrase not in text, (
            f"PLAN has stale repeat-run wording: {phrase!r}"
        )


def test_plan_reports_credentialed_repeat_capture_executed() -> None:
    if not SUMMARY_MD.exists():
        pytest.skip("repeat-run summary not built yet")
    lower = PLAN.read_text().lower()
    assert "credentialed repeat-run capture" in lower
    assert "executed" in lower
    # PLAN row should name both candidate profiles.
    assert "llm_candidate_v0" in lower
    assert "llm_candidate_v1" in lower


# ---------------------------------------------------------------------------
# Memo must carry the repeat-run addendum and stay non-overclaiming
# ---------------------------------------------------------------------------


def test_memo_has_repeat_run_variance_addendum() -> None:
    text = MEMO.read_text()
    assert "Repeat-run variance" in text or "repeat-run variance" in text.lower()
    # Memo must cite per-profile run counts and the headline metrics.
    lower = text.lower()
    assert "n=5" in lower or "5 runs" in lower or "runs × " in lower
    assert "UNSAFE_CUSTOMER_COMMS" in text
    assert "EVALUATOR_MISS" in text
    assert "NOT READY FOR PILOT" in text


def test_memo_does_not_overclaim() -> None:
    lower = MEMO.read_text().lower()
    for phrase in FORBIDDEN_OVERCLAIMS:
        assert phrase not in lower, f"memo must not claim {phrase!r}"


# ---------------------------------------------------------------------------
# Evidence pack must include and index the public-safe repeat-run summary
# ---------------------------------------------------------------------------


def test_evidence_pack_includes_repeat_run_summary_files() -> None:
    if not PACK_DIR.exists():
        pytest.skip("v1 evidence pack not built locally")
    assert PACK_SUMMARY_MD.exists(), (
        "evidence pack must include repeat_run_summary.md"
    )
    assert PACK_SUMMARY_JSON.exists(), (
        "evidence pack must include repeat_run_summary.json"
    )


def test_evidence_pack_manifest_indexes_repeat_run_summary() -> None:
    if not PACK_MANIFEST.exists():
        pytest.skip("v1 evidence pack manifest not built locally")
    manifest = json.loads(PACK_MANIFEST.read_text())
    paths = {entry["path"] for entry in manifest["files"]}
    assert "repeat_run_summary.md" in paths, (
        "evidence pack manifest must index repeat_run_summary.md"
    )
    assert "repeat_run_summary.json" in paths, (
        "evidence pack manifest must index repeat_run_summary.json"
    )


def test_evidence_pack_readme_describes_repeat_summary() -> None:
    if not PACK_README.exists():
        pytest.skip("v1 evidence pack README not built locally")
    text = PACK_README.read_text()
    assert "repeat_run_summary.md" in text
    assert "repeat_run_summary.json" in text


def test_evidence_pack_repeat_summary_is_public_safe() -> None:
    if not PACK_SUMMARY_MD.exists():
        pytest.skip("pack-side repeat-run summary not present")
    text = PACK_SUMMARY_MD.read_text()
    assert "NOT READY FOR PILOT" in text
    for needle in FORBIDDEN_RAW_SUBSTRINGS:
        assert needle not in text, (
            f"pack repeat_run_summary.md leaks {needle!r}"
        )
    lower = text.lower()
    for phrase in FORBIDDEN_OVERCLAIMS:
        assert phrase not in lower, (
            f"pack repeat_run_summary.md must not claim {phrase!r}"
        )


# ---------------------------------------------------------------------------
# Raw repeat outputs remain untracked
# ---------------------------------------------------------------------------


def test_raw_repeat_outputs_remain_untracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "reports/llm_repeats/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], (
        "raw per-run repeat outputs must remain local; git is tracking: "
        f"{tracked}"
    )


def test_gitignore_excludes_raw_repeat_tree() -> None:
    text = (ROOT / ".gitignore").read_text()
    assert "reports/llm_repeats/" in text, (
        ".gitignore must exclude reports/llm_repeats/ so raw per-run "
        "eval reports and traces never get tracked"
    )


# ---------------------------------------------------------------------------
# Tracked markdown must not embed raw repeat-run path templates
# ---------------------------------------------------------------------------


_FORBIDDEN_MARKDOWN_PATH_TEMPLATES: tuple[str, ...] = (
    "reports/llm_repeats/adversarial/",
    "run_<i>",
    "run_*/eval_report",
)


def test_tracked_markdown_avoids_raw_repeat_run_path_templates() -> None:
    """Public Markdown should not embed raw per-run path templates like
    ``reports/llm_repeats/adversarial/<profile>/<ts>/run_<i>/``. The
    repeat-run output directory is gitignored; tracked docs should refer
    to it abstractly so the path layout can change without doc drift
    and so casual readers do not see implementation paths."""

    tracked = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    leaks: list[tuple[str, str]] = []
    for rel in tracked:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text()
        for needle in _FORBIDDEN_MARKDOWN_PATH_TEMPLATES:
            if needle in text:
                leaks.append((rel, needle))
    assert not leaks, (
        "tracked markdown embeds raw repeat-run path templates; replace "
        "with abstract wording (e.g. 'gitignored repeat-run output "
        f"directory'). Hits: {leaks}"
    )
