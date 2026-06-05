"""Tests for the adversarial v1 model/NLI semantic-only regression seeds.

``case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl``
pins the THREE semantic-only ``UNSAFE_CUSTOMER_COMMS`` failures the model/NLI
audit surfaced — drafts the lexical grader cleared (a lexical blind spot). These
seeds are ``pending_review`` and are sourced from the public semantic audit
summary, never from raw model decisions.

These tests are credential-free and read only committed/on-disk artifacts. They
never call a model, never replay through ``scripts/run_eval.py``, and never read
the gitignored candidate reports, raw traces, or raw decision files.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.check_semantic_regressions_adversarial_v1 import check
from scripts.seed_semantic_regressions_adversarial_v1 import seed, semantic_only_pairs


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "case_studies" / "financial_links_reliability" / "evals"
REGRESSIONS_SEMANTIC = EVALS / "regressions_semantic_adversarial_v1.jsonl"
REGRESSIONS_V0 = EVALS / "regressions_v0.jsonl"
REGRESSIONS_LLM_V0 = EVALS / "regressions_llm_v0.jsonl"
DATASET = EVALS / "adversarial_v1.jsonl"
SUMMARY = ROOT / "reports" / "llm_adversarial_v1_semantic_audit_summary.json"
MAKEFILE = ROOT / "Makefile"

EXPECTED_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("case_fl_adv_v1_010", "llm_candidate_v0"),
        ("case_fl_adv_v1_006", "llm_candidate_v1"),
        ("case_fl_adv_v1_012", "llm_candidate_v1"),
    }
)


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _records() -> list[dict]:
    return _load_jsonl(REGRESSIONS_SEMANTIC)


def test_file_exists() -> None:
    assert REGRESSIONS_SEMANTIC.exists(), (
        f"missing semantic regression seed file: {REGRESSIONS_SEMANTIC}"
    )


def test_has_exactly_three_records_with_unique_ids() -> None:
    records = _records()
    assert len(records) == 3, f"expected exactly 3 seeds; got {len(records)}"
    ids = [r["regression_case_id"] for r in records]
    assert len(set(ids)) == 3, f"regression_case_ids not unique: {ids}"


def test_source_case_profile_pairs_match_expected() -> None:
    pairs = {
        (r["source_case_id"], r["source_agent_system_version"]) for r in _records()
    }
    assert pairs == EXPECTED_PAIRS, (
        f"pair mismatch: extra={pairs - EXPECTED_PAIRS}, "
        f"missing={EXPECTED_PAIRS - pairs}"
    )


def test_pairs_are_linked_to_the_audit_summary() -> None:
    """The seeded (case, profile) pairs must exactly equal the audit summary's
    semantic-only flags — the seeds cannot drift from the audit they cite."""

    summary = json.loads(SUMMARY.read_text())
    summary_pairs = {(c, p) for c, p, _ in semantic_only_pairs(summary)}
    assert summary_pairs == EXPECTED_PAIRS
    seed_pairs = {
        (r["source_case_id"], r["source_agent_system_version"]) for r in _records()
    }
    assert seed_pairs == summary_pairs


def test_every_record_is_pending_review() -> None:
    for r in _records():
        assert r["review_status"] == "pending_review", (
            f"{r['regression_case_id']}: review_status is {r['review_status']!r}"
        )


def test_every_record_carries_semantic_grader_and_label() -> None:
    for r in _records():
        assert r["grader"] == "unsupported_claim_semantic", r["regression_case_id"]
        assert "UNSAFE_CUSTOMER_COMMS" in r["failure_labels"], r["regression_case_id"]
        assert r["detected_by"] == "model_nli_semantic_audit", r["regression_case_id"]


def test_records_are_not_deterministically_replayable() -> None:
    """The failure is only detectable by the model/NLI grader, so the seeds must
    advertise that a deterministic eval replay will not reproduce them."""

    for r in _records():
        assert r["replayable_deterministically"] is False, r["regression_case_id"]


def test_records_have_replayable_case_superset_shape() -> None:
    required = {
        "case_id",
        "dataset_id",
        "workflow",
        "risk_band",
        "consent_sensitive",
        "synthetic_facts",
        "expected_route",
        "required_tools",
        "required_policy_ids",
        "expected_approval",
        "expected_behavior",
        "prohibited_behavior",
        "synthetic",
    }
    for r in _records():
        missing = required - set(r)
        assert not missing, f"{r['regression_case_id']}: missing {sorted(missing)}"
        assert r["workflow"] == "financial_links_reliability"
        assert r["synthetic"] is True


def test_records_link_to_public_summary_only() -> None:
    for r in _records():
        assert (
            r["source_semantic_audit_summary"]
            == "reports/llm_adversarial_v1_semantic_audit_summary.json"
        ), r["regression_case_id"]


def test_no_raw_draft_text_or_raw_trace_paths() -> None:
    blob = REGRESSIONS_SEMANTIC.read_text()
    # No raw trace path, no model-decision draft-bearing fields anywhere.
    assert "traces/local/llm_" not in blob
    for r in _records():
        assert "trace_path" not in r, (
            f"{r['regression_case_id']}: must not carry a raw trace_path"
        )

        def _keys(value: object):
            if isinstance(value, dict):
                for k, v in value.items():
                    yield k
                    yield from _keys(v)
            elif isinstance(value, list):
                for item in value:
                    yield from _keys(item)

        leaked = {k for k in _keys(r) if k in ("rationale", "evidence_spans")}
        assert not leaked, f"{r['regression_case_id']}: leaked decision keys {leaked}"


def test_distinct_from_other_regression_files() -> None:
    semantic_ids = {r["regression_case_id"] for r in _records()}
    for other in (REGRESSIONS_V0, REGRESSIONS_LLM_V0):
        if not other.exists():
            continue
        other_ids = {r["regression_case_id"] for r in _load_jsonl(other)}
        overlap = semantic_ids & other_ids
        assert not overlap, f"shares regression_case_ids with {other.name}: {overlap}"


def test_check_script_passes_on_committed_seeds() -> None:
    errors = check(REGRESSIONS_SEMANTIC, SUMMARY)
    assert errors == [], f"check() reported problems: {errors}"


def test_check_script_rejects_drifted_pairs(tmp_path: Path) -> None:
    """If a seed cites a (case, profile) not in the audit summary, the check
    must fail — the linkage guard has teeth."""

    records = _records()
    records[0]["source_case_id"] = "case_fl_adv_v1_001"  # not a semantic-only flag
    bad = tmp_path / "bad.jsonl"
    bad.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    errors = check(bad, SUMMARY)
    assert errors, "check() should reject seeds that drift from the audit summary"


def test_seeder_is_deterministic(tmp_path: Path) -> None:
    out = tmp_path / "seeds.jsonl"
    records = seed(summary_path=SUMMARY, dataset_path=DATASET, out=out)
    pairs = {(r["source_case_id"], r["source_agent_system_version"]) for r in records}
    assert pairs == EXPECTED_PAIRS
    # Re-running produces a byte-identical file.
    first = out.read_text()
    seed(summary_path=SUMMARY, dataset_path=DATASET, out=out)
    assert out.read_text() == first


# --- Makefile targets must be credential-free / no model invocation ----------

def _target_block(target: str) -> str:
    lines = MAKEFILE.read_text().splitlines()
    header = f"{target}:"
    start = next((i for i, ln in enumerate(lines) if ln.startswith(header)), None)
    assert start is not None, f"Makefile target {target!r} not found"
    block = [lines[start]]
    for ln in lines[start + 1 :]:
        if not ln.strip() or not ln[0].isspace():
            break
        block.append(ln)
    return "\n".join(block)


def test_makefile_targets_exist_and_are_credential_free() -> None:
    for target in (
        "regression-seed-adversarial-v1-semantic",
        "regression-check-adversarial-v1-semantic",
    ):
        block = _target_block(target)
        # No credentials, no model call, no candidate rerun, no semantic-decision
        # generation, no eval replay.
        assert "check-llm-env" not in block, target
        assert "--agent-system-version" not in block, target
        assert "scripts/run_eval.py" not in block, target
        assert "generate_semantic_decisions" not in block, target
        assert "llm_candidate_v" not in block, target


def test_seed_target_uses_seeder_and_check_target_uses_checker() -> None:
    seed_block = _target_block("regression-seed-adversarial-v1-semantic")
    assert "scripts/seed_semantic_regressions_adversarial_v1.py" in seed_block
    assert "regressions_semantic_adversarial_v1.jsonl" in seed_block

    check_block = _target_block("regression-check-adversarial-v1-semantic")
    assert "scripts/check_semantic_regressions_adversarial_v1.py" in check_block
    assert "scripts/validate_dataset.py" in check_block


# --- Docs cite the seeds without overclaiming --------------------------------

def test_readme_plan_memo_cite_seeds_without_overclaim() -> None:
    readme = (ROOT / "README.md").read_text()
    plan = (ROOT / "PLAN.md").read_text()
    memo = (ROOT / "reports" / "llm_adversarial_v1_improvement_memo.md").read_text()

    for doc in (readme, plan, memo):
        assert "regressions_semantic_adversarial_v1.jsonl" in doc
        assert "NOT READY FOR PILOT" in doc

    # PLAN records the seeding as its own tracked row.
    assert "Semantic-only regression seeding" in plan

    # No affirmative readiness/safety overclaim in the new README seed paragraph.
    start = readme.index("semantic-only failures are now pinned")
    section = readme[start : start + 1400].lower()
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in section, f"README seed paragraph overclaims: {forbidden!r}"
