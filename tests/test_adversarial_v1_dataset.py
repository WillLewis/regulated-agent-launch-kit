"""Tests for the expanded Financial Links adversarial v1 slice.

``case_studies/financial_links_reliability/evals/adversarial_v1.jsonl``
is a 12-case synthetic stress slice that expands beyond the original
6-case adversarial v0. These tests lock in:

1. The file exists, has exactly 12 cases, and validates with
   ``scripts/validate_dataset.py``.
2. ``case_id`` values are unique and disjoint from v0.
3. ``dataset_id`` is ``financial_links_reliability_adversarial_v1``.
4. Required category coverage (paraphrased overpromise, safe negated
   calibration, cross-sentence disclaimer trap, consent pressure,
   policy citation trap, missing-info hallucination) is present via
   ``category_tags`` on each case.
5. Required failure-label coverage includes ``UNSAFE_CUSTOMER_COMMS``,
   ``CONSENT_BOUNDARY_VIOLATION``, ``POLICY_MISS``, ``TOOL_MISUSE``.
6. The deterministic ``improved_v0`` profile passes all 12 cases.
7. The deterministic ``baseline_v0`` profile fails at least 3 cases
   across at least 2 distinct failure labels.
8. The adversarial v1 LLM candidate loop is wired as opt-in and
   credential-gated (eval/card/semantic-decision/redaction/evidence
   targets), but README / PLAN do not claim a credentialed run has
   actually been executed against adversarial v1.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_V1_PATH = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v1.jsonl"
)
ADVERSARIAL_V0_PATH = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v0.jsonl"
)
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_dataset.py"
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"

EXPECTED_DATASET_ID = "financial_links_reliability_adversarial_v1"
EXPECTED_CASE_COUNT = 12

REQUIRED_FAILURE_LABELS: frozenset[str] = frozenset(
    {
        "UNSAFE_CUSTOMER_COMMS",
        "CONSENT_BOUNDARY_VIOLATION",
        "POLICY_MISS",
        "TOOL_MISUSE",
    }
)

REQUIRED_CATEGORY_TAGS: frozenset[str] = frozenset(
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

# Specific paraphrased-overpromise patterns that must be represented at
# least once across the slice. The task explicitly enumerates these.
REQUIRED_PARAPHRASE_HINTS: tuple[str, ...] = (
    "always current",
    "updates instantly",
    "refreshes without delay",
    "certain to reconnect",
)

# Specific safe negated / hedged calibration patterns that must show up.
REQUIRED_SAFE_NEGATION_HINTS: tuple[str, ...] = (
    "not guaranteed",
    "cannot guarantee",
    "may not reflect current status",
    "not real-time",
)


def _load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in ADVERSARIAL_V1_PATH.read_text().splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def cases() -> list[dict]:
    return _load_cases()


# ---------------------------------------------------------------------------
# Shape + validator
# ---------------------------------------------------------------------------


def test_adversarial_v1_file_exists() -> None:
    assert ADVERSARIAL_V1_PATH.exists(), (
        f"missing dataset: {ADVERSARIAL_V1_PATH.relative_to(ROOT)}"
    )


def test_adversarial_v1_has_exactly_12_cases(cases: list[dict]) -> None:
    assert len(cases) == EXPECTED_CASE_COUNT, (
        f"adversarial v1 must have exactly {EXPECTED_CASE_COUNT} cases; "
        f"got {len(cases)}"
    )


def test_adversarial_v1_dataset_id_is_v1(cases: list[dict]) -> None:
    for case in cases:
        assert case["dataset_id"] == EXPECTED_DATASET_ID, (
            f"case {case['case_id']!r} has wrong dataset_id "
            f"{case['dataset_id']!r}; expected {EXPECTED_DATASET_ID!r}"
        )


def test_adversarial_v1_case_ids_are_unique(cases: list[dict]) -> None:
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids)), (
        f"adversarial v1 contains duplicate case_id values: {ids}"
    )


def test_adversarial_v1_case_ids_disjoint_from_v0() -> None:
    v0_ids = {
        json.loads(line)["case_id"]
        for line in ADVERSARIAL_V0_PATH.read_text().splitlines()
        if line.strip()
    }
    v1_ids = {case["case_id"] for case in _load_cases()}
    overlap = v0_ids & v1_ids
    assert not overlap, (
        f"adversarial v1 case_ids overlap with adversarial v0: {sorted(overlap)}"
    )


def test_adversarial_v1_case_ids_follow_v1_naming(cases: list[dict]) -> None:
    for case in cases:
        cid = case["case_id"]
        assert cid.startswith("case_fl_adv_v1_"), (
            f"case_id {cid!r} should start with 'case_fl_adv_v1_'"
        )


def test_adversarial_v1_passes_validate_dataset_script() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(ADVERSARIAL_V1_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"validate_dataset.py rejected adversarial v1:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Category coverage
# ---------------------------------------------------------------------------


def test_adversarial_v1_every_case_carries_category_tags(cases: list[dict]) -> None:
    for case in cases:
        tags = case.get("category_tags")
        assert isinstance(tags, list) and tags, (
            f"case {case['case_id']!r} must carry a non-empty category_tags list"
        )


def test_adversarial_v1_covers_required_categories(cases: list[dict]) -> None:
    seen: set[str] = set()
    for case in cases:
        seen.update(case.get("category_tags") or [])
    missing = REQUIRED_CATEGORY_TAGS - seen
    assert not missing, (
        f"adversarial v1 missing required category tags: {sorted(missing)}; "
        f"present: {sorted(seen)}"
    )


def test_adversarial_v1_includes_each_paraphrase_hint(cases: list[dict]) -> None:
    """Each of the four enumerated paraphrased-overpromise phrases must
    appear in at least one case (in summary or partner_request)."""

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
            f"adversarial v1 missing paraphrased-overpromise hint {hint!r}"
        )


def test_adversarial_v1_includes_each_safe_negation_hint(cases: list[dict]) -> None:
    """Each of the four enumerated safe-negated / hedged phrases must
    appear in at least one case (in summary, partner_request, or
    expected_behavior bullets) for grader calibration."""

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
            f"adversarial v1 missing safe-negation calibration hint {hint!r}"
        )


def test_adversarial_v1_has_explicit_cross_sentence_traps(cases: list[dict]) -> None:
    """At least two cases must carry the cross_sentence_disclaimer_trap tag."""

    matches = [
        case
        for case in cases
        if "cross_sentence_disclaimer_trap" in (case.get("category_tags") or [])
    ]
    assert len(matches) >= 2, (
        "adversarial v1 must include at least two cross-sentence "
        "disclaimer trap cases (hedged sentence followed by an "
        f"affirmative overpromise); got {len(matches)}"
    )


# ---------------------------------------------------------------------------
# Failure-label coverage
# ---------------------------------------------------------------------------


def test_adversarial_v1_covers_required_failure_labels(cases: list[dict]) -> None:
    labels = {
        case.get("failure_label_if_mishandled")
        for case in cases
        if case.get("failure_label_if_mishandled")
    }
    missing = REQUIRED_FAILURE_LABELS - labels
    assert not missing, (
        f"adversarial v1 missing required failure_label_if_mishandled values: "
        f"{sorted(missing)}; present: {sorted(labels)}"
    )


# ---------------------------------------------------------------------------
# Deterministic baseline / improved expectations
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def baseline_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    from evals.run import run_eval

    out = tmp_path_factory.mktemp("adv_v1_baseline")
    report = run_eval(
        dataset_path=ADVERSARIAL_V1_PATH,
        traces_out=out / "traces",
        report_out=out / "report.json",
        agent_system_version="baseline_v0",
    )
    return report.model_dump(mode="json")


@pytest.fixture(scope="module")
def improved_report(tmp_path_factory: pytest.TempPathFactory) -> dict:
    from evals.run import run_eval

    out = tmp_path_factory.mktemp("adv_v1_improved")
    report = run_eval(
        dataset_path=ADVERSARIAL_V1_PATH,
        traces_out=out / "traces",
        report_out=out / "report.json",
        agent_system_version="improved_v0",
    )
    return report.model_dump(mode="json")


def test_improved_v0_passes_all_adversarial_v1_cases(improved_report: dict) -> None:
    assert improved_report["case_count"] == EXPECTED_CASE_COUNT
    assert improved_report["passed_case_count"] == EXPECTED_CASE_COUNT, (
        "improved_v0 must pass every adversarial v1 case; got "
        f"{improved_report['passed_case_count']} / {EXPECTED_CASE_COUNT}"
    )
    assert improved_report["failed_case_count"] == 0
    assert improved_report["failure_label_counts"] == {}, (
        f"improved_v0 surfaced unexpected failure labels: "
        f"{improved_report['failure_label_counts']}"
    )


def test_baseline_v0_fails_at_least_3_cases_across_2_labels(
    baseline_report: dict,
) -> None:
    failed = baseline_report["failed_case_count"]
    assert failed >= 3, (
        "baseline_v0 must fail at least 3 adversarial v1 cases (planted "
        f"weaknesses); got {failed} failures"
    )
    labels = {
        label
        for label, count in baseline_report["failure_label_counts"].items()
        if count
    }
    assert len(labels) >= 2, (
        "baseline_v0 must surface at least 2 distinct failure labels on "
        f"adversarial v1; got {sorted(labels)}"
    )


# ---------------------------------------------------------------------------
# README / PLAN must not claim an LLM v1 run on adversarial_v1
# ---------------------------------------------------------------------------


def test_readme_does_not_claim_llm_run_on_adversarial_v1() -> None:
    lower = README.read_text().lower()
    forbidden = (
        "credentialed run on adversarial_v1",
        "llm candidate evaluated on adversarial v1",
        "adversarial_v1 credentialed run",
        "llm run on adversarial_v1",
        "adversarial v1 credentialed llm run",
    )
    for phrase in forbidden:
        assert phrase not in lower, (
            f"README must not claim an LLM run on adversarial_v1: {phrase!r}"
        )


def test_plan_does_not_claim_llm_run_on_adversarial_v1() -> None:
    lower = PLAN.read_text().lower()
    forbidden = (
        "credentialed run on adversarial_v1",
        "llm candidate evaluated on adversarial v1",
        "adversarial_v1 credentialed run",
        "llm run on adversarial_v1",
        "adversarial v1 credentialed llm run",
    )
    for phrase in forbidden:
        assert phrase not in lower, (
            f"PLAN must not claim an LLM run on adversarial_v1: {phrase!r}"
        )


# ---------------------------------------------------------------------------
# Adversarial v1 LLM candidate loop: opt-in, credential-gated, isolated
# ---------------------------------------------------------------------------

# Credentialed targets that must gate on check-llm-env (they call the model).
_CREDENTIALED_V1_LLM_TARGETS: tuple[str, ...] = (
    "eval-adversarial-v1-llm-v0",
    "eval-adversarial-v1-llm-v1",
    "semantic-model-decisions-adversarial-v1-llm-v0",
    "semantic-model-decisions-adversarial-v1-llm-v1",
)

# Every adversarial v1 LLM target (credentialed + on-disk-only).
_ALL_V1_LLM_TARGETS: tuple[str, ...] = _CREDENTIALED_V1_LLM_TARGETS + (
    "eval-card-adversarial-v1-llm",
    "redact-adversarial-v1-llm",
    "evidence-pack-adversarial-v1-llm",
)


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


def test_adversarial_v1_llm_targets_exist() -> None:
    """The adversarial v1 slice now has an opt-in, credential-gated LLM
    candidate loop. Replaces the earlier 'no adversarial v1 LLM target'
    invariant now that the loop is intentionally wired."""

    makefile = (ROOT / "Makefile").read_text()
    for target in _ALL_V1_LLM_TARGETS:
        assert f"{target}:" in makefile, (
            f"Makefile missing adversarial v1 LLM target {target!r}"
        )


def test_credentialed_v1_llm_targets_gate_on_check_llm_env() -> None:
    """No silent fallback: every target that calls the model must depend on
    the check-llm-env preflight."""

    makefile = (ROOT / "Makefile").read_text()
    for target in _CREDENTIALED_V1_LLM_TARGETS:
        prereqs = _make_prereqs(makefile, target)
        assert "check-llm-env" in prereqs, (
            f"{target} must list check-llm-env as a prerequisite; got {prereqs}"
        )


def test_on_disk_v1_llm_targets_do_not_gate_on_check_llm_env() -> None:
    """Redaction + evidence packaging operate on on-disk artifacts only and
    must NOT require credentials."""

    makefile = (ROOT / "Makefile").read_text()
    for target in ("redact-adversarial-v1-llm", "evidence-pack-adversarial-v1-llm"):
        prereqs = _make_prereqs(makefile, target)
        assert "check-llm-env" not in prereqs, (
            f"{target} is on-disk-only and must not depend on check-llm-env; "
            f"got {prereqs}"
        )


def test_eval_card_adversarial_v1_llm_compares_both_candidates() -> None:
    makefile = (ROOT / "Makefile").read_text()
    prereqs = _make_prereqs(makefile, "eval-card-adversarial-v1-llm")
    assert "eval-adversarial-v1-llm-v0" in prereqs
    assert "eval-adversarial-v1-llm-v1" in prereqs

    body = _make_recipe(makefile, "eval-card-adversarial-v1-llm")
    assert "reports/llm_adversarial_v1_candidate_v0_eval.json" in body
    assert "reports/llm_adversarial_v1_candidate_v1_eval.json" in body
    assert "--baseline-label Before" in body
    assert "--improved-label After" in body
    assert "reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md" in body


def test_adversarial_v1_llm_eval_targets_run_right_profiles_and_paths() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target, profile, traces, report in (
        (
            "eval-adversarial-v1-llm-v0",
            "llm_candidate_v0",
            "traces/local/llm_adversarial_v1_candidate_v0",
            "reports/llm_adversarial_v1_candidate_v0_eval.json",
        ),
        (
            "eval-adversarial-v1-llm-v1",
            "llm_candidate_v1",
            "traces/local/llm_adversarial_v1_candidate_v1",
            "reports/llm_adversarial_v1_candidate_v1_eval.json",
        ),
    ):
        body = _make_recipe(makefile, target)
        assert (
            "case_studies/financial_links_reliability/evals/adversarial_v1.jsonl"
            in body
        )
        assert traces in body
        assert report in body
        assert profile in body


def test_semantic_decision_v1_llm_targets_target_the_candidate_reports() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target, report, out in (
        (
            "semantic-model-decisions-adversarial-v1-llm-v0",
            "reports/llm_adversarial_v1_candidate_v0_eval.json",
            "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json",
        ),
        (
            "semantic-model-decisions-adversarial-v1-llm-v1",
            "reports/llm_adversarial_v1_candidate_v1_eval.json",
            "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json",
        ),
    ):
        body = _make_recipe(makefile, target)
        assert "scripts/generate_semantic_decisions.py" in body
        assert report in body
        assert out in body


def test_no_deterministic_target_depends_on_adversarial_v1_llm_targets() -> None:
    """The credential-free public proof loop (including the deterministic and
    fixture-backed adversarial v1 surfaces) must not pull in any opt-in
    adversarial v1 LLM target."""

    makefile = (ROOT / "Makefile").read_text()
    deterministic_targets = (
        "test:",
        "scaffold-test:",
        "dataset-test:",
        "dataset-test-adversarial:",
        "dataset-test-adversarial-v1:",
        "eval-adversarial-v1-baseline:",
        "eval-adversarial-v1-improved:",
        "eval-card-adversarial-v1:",
        "eval-adversarial-v1-baseline-semantic:",
        "eval-adversarial-v1-improved-semantic:",
        "semantic-reporting-surface:",
        "lint:",
    )
    forbidden = set(_ALL_V1_LLM_TARGETS)
    for target in deterministic_targets:
        match = re.search(
            rf"^{re.escape(target)}\s*([^\n]*)$", makefile, flags=re.MULTILINE
        )
        if match is None:
            continue
        prereqs = set(match.group(1).split())
        leaked = prereqs & forbidden
        assert not leaked, (
            f"deterministic Make target {target} depends on adversarial v1 LLM "
            f"target(s) {leaked}; the public proof loop must not require "
            "credentials."
        )


def test_adversarial_v1_llm_raw_artifacts_are_gitignored() -> None:
    """Raw candidate eval reports embed raw model draft text and the
    model/NLI decision JSON is a credentialed local artifact; all must be
    gitignored. The public-safe view is the redacted evidence pack."""

    gitignored = (
        "reports/llm_adversarial_v1_candidate_v0_eval.json",
        "reports/llm_adversarial_v1_candidate_v1_eval.json",
        "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json",
        "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json",
        "traces/local/llm_adversarial_v1_candidate_v0/case_fl_adv_v1_001.json",
        "traces/local/llm_adversarial_v1_candidate_v1/case_fl_adv_v1_001.json",
    )
    for path in gitignored:
        check = subprocess.run(
            ["git", "check-ignore", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert check.returncode == 0 and check.stdout.strip() == path, (
            f"{path} must be gitignored (raw LLM / credentialed artifact); "
            f"git check-ignore returned rc={check.returncode!r} "
            f"out={check.stdout.strip()!r}"
        )
        tracked = subprocess.run(
            ["git", "ls-files", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert tracked == "", f"{path} must not be tracked"
