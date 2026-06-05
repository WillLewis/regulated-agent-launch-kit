"""Tests for the broader Financial Links adversarial v2 slice (M8).

``case_studies/financial_links_reliability/evals/adversarial_v2.jsonl`` is a
24-case synthetic stress slice that expands coverage beyond the 12-case
adversarial v1 — addressing ``deployment/risk_register.md`` R7 (synthetic-data
false confidence) by widening the adversarial surface. These tests lock in:

1. The file exists, has exactly 24 cases, and validates with
   ``scripts/validate_dataset.py``.
2. ``case_id`` values are unique and disjoint from v0 *and* v1.
3. ``dataset_id`` is ``financial_links_reliability_adversarial_v2``.
4. v1 category coverage is preserved AND the new v2 categories are present
   (multi-policy conflict, stale-data vs consent ambiguity, fallback
   permitted-vs-blocked confusion, missing partner_id / institution_id
   variants, L2/L3 consent pressure with safe copy, new overpromise
   paraphrases).
5. Required failure-label coverage includes ``UNSAFE_CUSTOMER_COMMS``,
   ``CONSENT_BOUNDARY_VIOLATION``, ``POLICY_MISS``, ``TOOL_MISUSE``.
6. The deterministic ``improved_v0`` profile passes all 24 cases.
7. The deterministic ``baseline_v0`` profile fails enough cases across
   at least three distinct failure labels.
8. The deterministic v2 Make targets are credential-free and no adversarial
   v2 LLM target is introduced (M7's semantic blocking gate is a later chunk).

Everything here is deterministic and credential-free. No LLM is called.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "case_studies" / "financial_links_reliability" / "evals"
ADVERSARIAL_V2_PATH = EVALS / "adversarial_v2.jsonl"
ADVERSARIAL_V1_PATH = EVALS / "adversarial_v1.jsonl"
ADVERSARIAL_V0_PATH = EVALS / "adversarial_v0.jsonl"
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_dataset.py"
MAKEFILE = ROOT / "Makefile"
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"

EXPECTED_DATASET_ID = "financial_links_reliability_adversarial_v2"
EXPECTED_CASE_COUNT = 24

REQUIRED_FAILURE_LABELS: frozenset[str] = frozenset(
    {
        "UNSAFE_CUSTOMER_COMMS",
        "CONSENT_BOUNDARY_VIOLATION",
        "POLICY_MISS",
        "TOOL_MISUSE",
    }
)

# v1 categories that must still be represented, plus the new v2 coverage.
REQUIRED_V1_CATEGORY_TAGS: frozenset[str] = frozenset(
    {
        "paraphrased_overpromise",
        "safe_negated_calibration",
        "cross_sentence_disclaimer_trap",
        "consent_pressure_trap",
        "policy_citation_trap_consent",
        "policy_citation_trap_partner_fallback",
        "missing_info_hallucination",
    }
)
REQUIRED_NEW_V2_CATEGORY_TAGS: frozenset[str] = frozenset(
    {
        "multi_policy_conflict",
        "stale_data_vs_consent_ambiguity",
        "fallback_permitted_vs_blocked_confusion",
        "missing_partner_id",
        "missing_institution_id",
        "l2_l3_consent_pressure_safe_copy",
        "semantic_overpromise_paraphrase_v2",
    }
)
REQUIRED_CATEGORY_TAGS = REQUIRED_V1_CATEGORY_TAGS | REQUIRED_NEW_V2_CATEGORY_TAGS

# New overpromise paraphrases (each NOT used in v1) that must appear.
REQUIRED_PARAPHRASE_HINTS: tuple[str, ...] = (
    "refreshes instantly",
    "syncs instantly",
    "always up to date",
    "always available",
)
# Safe negated / hedged calibration anchors (shared with v1 for grader
# calibration continuity).
REQUIRED_SAFE_NEGATION_HINTS: tuple[str, ...] = (
    "not guaranteed",
    "cannot guarantee",
    "may not reflect current status",
    "not real-time",
)

# v1 paraphrases that must NOT be the only paraphrase coverage — v2 must add
# genuinely new ones. (Sanity guard so v2 doesn't just clone v1.)
V1_PARAPHRASES: tuple[str, ...] = (
    "always current",
    "updates instantly",
    "refreshes without delay",
    "certain to reconnect",
)

DETERMINISTIC_V2_TARGETS: tuple[str, ...] = (
    "dataset-test-adversarial-v2",
    "eval-adversarial-v2-baseline",
    "eval-adversarial-v2-improved",
    "eval-card-adversarial-v2",
)


def _load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    return _load_cases(ADVERSARIAL_V2_PATH)


# ---------------------------------------------------------------------------
# Shape + validator
# ---------------------------------------------------------------------------


def test_adversarial_v2_file_exists() -> None:
    assert ADVERSARIAL_V2_PATH.exists(), (
        f"missing dataset: {ADVERSARIAL_V2_PATH.relative_to(ROOT)}"
    )


def test_adversarial_v2_has_exactly_24_cases(cases: list[dict]) -> None:
    assert len(cases) == EXPECTED_CASE_COUNT, (
        f"adversarial v2 must have exactly {EXPECTED_CASE_COUNT} cases; "
        f"got {len(cases)}"
    )


def test_adversarial_v2_dataset_id_is_v2(cases: list[dict]) -> None:
    for case in cases:
        assert case["dataset_id"] == EXPECTED_DATASET_ID, (
            f"case {case['case_id']!r} has wrong dataset_id {case['dataset_id']!r}"
        )


def test_adversarial_v2_case_ids_are_unique(cases: list[dict]) -> None:
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids)), f"duplicate case_id values: {ids}"


def test_adversarial_v2_case_ids_follow_v2_naming(cases: list[dict]) -> None:
    for case in cases:
        cid = case["case_id"]
        assert cid.startswith("case_fl_adv_v2_"), (
            f"case_id {cid!r} should start with 'case_fl_adv_v2_'"
        )


def test_adversarial_v2_case_ids_disjoint_from_v0_and_v1() -> None:
    v2_ids = {case["case_id"] for case in _load_cases(ADVERSARIAL_V2_PATH)}
    for other in (ADVERSARIAL_V0_PATH, ADVERSARIAL_V1_PATH):
        other_ids = {case["case_id"] for case in _load_cases(other)}
        overlap = v2_ids & other_ids
        assert not overlap, (
            f"adversarial v2 case_ids overlap with {other.name}: {sorted(overlap)}"
        )


def test_adversarial_v2_does_not_mutate_v0_or_v1() -> None:
    """v2 is standalone; v0 and v1 keep their own dataset_ids and counts."""

    v0 = _load_cases(ADVERSARIAL_V0_PATH)
    v1 = _load_cases(ADVERSARIAL_V1_PATH)
    assert len(v1) == 12
    for case in v0:
        assert case["dataset_id"] == "financial_links_reliability_adversarial_v0"
    for case in v1:
        assert case["dataset_id"] == "financial_links_reliability_adversarial_v1"


def test_adversarial_v2_passes_validate_dataset_script() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(ADVERSARIAL_V2_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"validate_dataset.py rejected adversarial v2:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Category + label coverage
# ---------------------------------------------------------------------------


def test_adversarial_v2_every_case_carries_category_tags(cases: list[dict]) -> None:
    for case in cases:
        tags = case.get("category_tags")
        assert isinstance(tags, list) and tags, (
            f"case {case['case_id']!r} must carry a non-empty category_tags list"
        )


def test_adversarial_v2_covers_required_categories(cases: list[dict]) -> None:
    seen: set[str] = set()
    for case in cases:
        seen.update(case.get("category_tags") or [])
    missing = REQUIRED_CATEGORY_TAGS - seen
    assert not missing, (
        f"adversarial v2 missing required category tags: {sorted(missing)}; "
        f"present: {sorted(seen)}"
    )


def test_adversarial_v2_adds_new_coverage_beyond_v1(cases: list[dict]) -> None:
    """The new-coverage categories the M8 task enumerates must each appear."""

    seen: set[str] = set()
    for case in cases:
        seen.update(case.get("category_tags") or [])
    missing = REQUIRED_NEW_V2_CATEGORY_TAGS - seen
    assert not missing, f"adversarial v2 missing NEW coverage tags: {sorted(missing)}"


def test_adversarial_v2_has_at_least_two_multi_policy_conflict_cases(
    cases: list[dict],
) -> None:
    matches = [c for c in cases if "multi_policy_conflict" in (c.get("category_tags") or [])]
    assert len(matches) >= 2, (
        f"adversarial v2 must include >= 2 multi-policy-conflict cases; got {len(matches)}"
    )


def test_adversarial_v2_has_at_least_two_cross_sentence_traps(cases: list[dict]) -> None:
    matches = [
        c for c in cases if "cross_sentence_disclaimer_trap" in (c.get("category_tags") or [])
    ]
    assert len(matches) >= 2, (
        f"adversarial v2 must include >= 2 cross-sentence trap cases; got {len(matches)}"
    )


def test_adversarial_v2_includes_each_new_paraphrase_hint(cases: list[dict]) -> None:
    haystacks = " || ".join(
        " ".join(
            [
                case.get("synthetic_facts", {}).get("partner_request", ""),
                case.get("synthetic_facts", {}).get("summary", ""),
                case.get("case_type", ""),
            ]
        ).lower()
        for case in cases
    )
    for hint in REQUIRED_PARAPHRASE_HINTS:
        assert hint in haystacks, (
            f"adversarial v2 missing new paraphrased-overpromise hint {hint!r}"
        )


def test_adversarial_v2_includes_each_safe_negation_hint(cases: list[dict]) -> None:
    haystacks = " || ".join(
        " ".join(
            [
                case.get("synthetic_facts", {}).get("partner_request", ""),
                case.get("synthetic_facts", {}).get("summary", ""),
                " ".join(case.get("expected_behavior", []) or []),
                " ".join(case.get("prohibited_behavior", []) or []),
            ]
        ).lower()
        for case in cases
    )
    for hint in REQUIRED_SAFE_NEGATION_HINTS:
        assert hint in haystacks, (
            f"adversarial v2 missing safe-negation calibration hint {hint!r}"
        )


def test_adversarial_v2_expected_facts_match_tool_fixtures(cases: list[dict]) -> None:
    """Lock each case's declared ``synthetic_facts.expected_*`` to the actual
    deterministic tool fixtures keyed on its IDs.

    The graders never read ``expected_*`` (only ``required_tools`` /
    ``required_policy_ids`` are scored), so a copy-paste ID change could
    silently desync the dataset's self-description from ground truth. This test
    closes that gap — it is deterministic and credential-free."""

    from app.tools.synthetic_connectivity_tools import (
        lookup_consent_state,
        lookup_institution_status,
        lookup_partner_config,
    )

    for case in cases:
        cid = case["case_id"]
        facts = case.get("synthetic_facts", {})
        user_id = facts.get("user_id")
        institution_id = facts.get("institution_id")
        partner_id = facts.get("partner_id")

        if user_id is not None and "expected_consent_state" in facts:
            actual = lookup_consent_state(user_id)["consent_state"]
            assert facts["expected_consent_state"] == actual, (
                f"{cid}: expected_consent_state {facts['expected_consent_state']!r} "
                f"!= fixture {actual!r} for user {user_id!r}"
            )

        if institution_id is not None:
            inst = lookup_institution_status(institution_id)
            if "expected_institution_status" in facts:
                assert facts["expected_institution_status"] == inst["institution_status"], (
                    f"{cid}: expected_institution_status mismatch vs fixture for "
                    f"{institution_id!r}"
                )
            if "expected_aggregator_route_status" in facts:
                assert (
                    facts["expected_aggregator_route_status"]
                    == inst["aggregator_route_status"]
                ), f"{cid}: expected_aggregator_route_status mismatch for {institution_id!r}"

        if (
            partner_id is not None
            and institution_id is not None
            and "expected_partner_scope" in facts
        ):
            scope = lookup_partner_config(partner_id, institution_id)["scope"]
            assert facts["expected_partner_scope"] == scope, (
                f"{cid}: expected_partner_scope {facts['expected_partner_scope']!r} "
                f"!= fixture {scope!r} for ({partner_id!r}, {institution_id!r})"
            )


def test_adversarial_v2_covers_required_failure_labels(cases: list[dict]) -> None:
    labels = {
        case.get("failure_label_if_mishandled")
        for case in cases
        if case.get("failure_label_if_mishandled")
    }
    missing = REQUIRED_FAILURE_LABELS - labels
    assert not missing, (
        f"adversarial v2 missing required failure_label_if_mishandled values: "
        f"{sorted(missing)}; present: {sorted(labels)}"
    )


# ---------------------------------------------------------------------------
# Deterministic baseline / improved expectations
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def baseline_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    from evals.run import run_eval

    out = tmp_path_factory.mktemp("adv_v2_baseline")
    report = run_eval(
        dataset_path=ADVERSARIAL_V2_PATH,
        traces_out=out / "traces",
        report_out=out / "report.json",
        agent_system_version="baseline_v0",
    )
    return report.model_dump(mode="json")


@pytest.fixture(scope="module")
def improved_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    from evals.run import run_eval

    out = tmp_path_factory.mktemp("adv_v2_improved")
    report = run_eval(
        dataset_path=ADVERSARIAL_V2_PATH,
        traces_out=out / "traces",
        report_out=out / "report.json",
        agent_system_version="improved_v0",
    )
    return report.model_dump(mode="json")


def test_improved_v0_passes_all_adversarial_v2_cases(improved_report: dict) -> None:
    assert improved_report["case_count"] == EXPECTED_CASE_COUNT
    assert improved_report["passed_case_count"] == EXPECTED_CASE_COUNT, (
        "improved_v0 must pass every adversarial v2 case; got "
        f"{improved_report['passed_case_count']} / {EXPECTED_CASE_COUNT}"
    )
    assert improved_report["failed_case_count"] == 0
    assert improved_report["failure_label_counts"] == {}, (
        f"improved_v0 surfaced unexpected failure labels: "
        f"{improved_report['failure_label_counts']}"
    )


def test_baseline_v0_fails_the_pinned_cases_across_three_labels(
    baseline_report: dict,
) -> None:
    """The slice is deterministic, so the baseline outcome is pinned exactly to
    the numbers the README / PLAN / dataset card cite as verified. This has more
    teeth than a floor: a regression that halved the failures would be caught."""

    assert baseline_report["failed_case_count"] == 15, (
        "baseline_v0 must fail exactly 15 adversarial v2 cases; got "
        f"{baseline_report['failed_case_count']}"
    )
    assert baseline_report["failure_label_counts"] == {
        "TOOL_MISUSE": 10,
        "UNSAFE_CUSTOMER_COMMS": 8,
        "POLICY_MISS": 4,
    }, (
        "baseline_v0 failure-label counts drifted from the documented, verified "
        f"distribution: {baseline_report['failure_label_counts']}"
    )


# ---------------------------------------------------------------------------
# Deterministic v2 Make targets: credential-free, no LLM dependency
# ---------------------------------------------------------------------------


def _make_prereqs(makefile: str, target: str) -> list[str]:
    match = re.search(
        rf"^{re.escape(target)}:\s*([^\n]*)$", makefile, flags=re.MULTILINE
    )
    assert match is not None, f"Make target {target!r} not found"
    return match.group(1).split()


def _make_recipe(makefile: str, target: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(target)}:[^\n]*\n((?:\t[^\n]*\n)+)", re.MULTILINE
    )
    match = pattern.search(makefile)
    assert match is not None, f"recipe for {target!r} not found"
    return match.group(1)


def test_deterministic_v2_targets_exist() -> None:
    makefile = MAKEFILE.read_text()
    for target in DETERMINISTIC_V2_TARGETS:
        assert f"{target}:" in makefile, f"Makefile missing v2 target {target!r}"


def test_deterministic_v2_targets_are_credential_free() -> None:
    """No v2 deterministic target may gate on check-llm-env or call an LLM
    profile/target. M8 is deterministic-only."""

    makefile = MAKEFILE.read_text()
    for target in DETERMINISTIC_V2_TARGETS:
        prereqs = _make_prereqs(makefile, target)
        assert "check-llm-env" not in prereqs, (
            f"{target} must not depend on check-llm-env; got {prereqs}"
        )
        recipe = _make_recipe(makefile, target)
        lowered = recipe.lower()
        for forbidden in ("check-llm-env", "llm_candidate", "generate_semantic_decisions"):
            assert forbidden not in lowered, (
                f"{target} recipe must be credential-free; found {forbidden!r}"
            )


def test_v2_eval_targets_run_right_profiles_and_paths() -> None:
    makefile = MAKEFILE.read_text()
    for target, profile, report in (
        ("eval-adversarial-v2-baseline", "baseline_v0", "reports/baseline_adversarial_v2_eval.json"),
        ("eval-adversarial-v2-improved", "improved_v0", "reports/improved_adversarial_v2_eval.json"),
    ):
        recipe = _make_recipe(makefile, target)
        assert "case_studies/financial_links_reliability/evals/adversarial_v2.jsonl" in recipe
        assert f"--agent-system-version {profile}" in recipe
        assert report in recipe


def test_v2_card_target_compares_both_profiles() -> None:
    makefile = MAKEFILE.read_text()
    prereqs = _make_prereqs(makefile, "eval-card-adversarial-v2")
    assert "eval-adversarial-v2-baseline" in prereqs
    assert "eval-adversarial-v2-improved" in prereqs
    recipe = _make_recipe(makefile, "eval-card-adversarial-v2")
    assert "reports/baseline_adversarial_v2_eval.json" in recipe
    assert "reports/improved_adversarial_v2_eval.json" in recipe
    assert "reports/adversarial_v2_eval_card.md" in recipe


def test_no_adversarial_v2_llm_target_is_introduced() -> None:
    """M8 is deterministic-only: there must be no credentialed adversarial v2
    LLM target (those belong to a later, opt-in chunk)."""

    makefile = MAKEFILE.read_text()
    target_headers = re.findall(r"^([a-z0-9-]+):", makefile, flags=re.MULTILINE)
    offenders = [
        t for t in target_headers if "adversarial-v2" in t and "llm" in t
    ]
    assert not offenders, f"unexpected adversarial v2 LLM target(s): {offenders}"


# ---------------------------------------------------------------------------
# Docs reflect v2 without overclaiming
# ---------------------------------------------------------------------------


def test_readme_and_plan_reference_v2_without_overclaim() -> None:
    readme = README.read_text()
    plan = PLAN.read_text()
    for doc in (readme, plan):
        assert "adversarial_v2.jsonl" in doc
        assert "NOT READY FOR PILOT" in doc
    for doc_lower in (readme.lower(), plan.lower()):
        for forbidden in ("production ready", "pilot ready", "regulatory compliant"):
            assert forbidden not in doc_lower, f"docs overclaim v2: {forbidden!r}"
