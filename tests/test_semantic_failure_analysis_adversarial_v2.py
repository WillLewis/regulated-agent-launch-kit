"""Tests for the public-safe M7 semantic failure analysis + remediation plan.

The generator turns the BLOCKED M7 audit into an action-oriented remediation
plan from tracked, public-safe inputs only. These tests prove:

1. the exact 14 semantic-only findings (distinct (case, profile) pairs) are
   represented, and the breakdowns/decompositions are internally consistent;
2. no raw draft text, ``evidence_spans``, ``rationale``, raw ``traces/local/llm_``
   paths, or raw decision files are read or emitted (fail-closed guards);
3. the analysis says M7 remains OPEN / NOT READY FOR PILOT;
4. no credentialed target or LLM call is wired (no-network source guard +
   credential-free Make target).

The structural/fail-closed tests build tiny synthetic fixtures in ``tmp_path``;
the "exact 14" and public-safety tests run the generator against the real
tracked inputs. No credentials or network calls are involved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.analyze_semantic_failures_adversarial_v2 import (
    ANALYSIS_VERSION,
    _assert_output_public_safe,
    _load_jsonl,
    _load_summary,
    build_analysis,
    main,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
SCRIPT = ROOT / "scripts" / "analyze_semantic_failures_adversarial_v2.py"

REAL_SUMMARY = ROOT / "reports" / "llm_adversarial_v2_semantic_audit_summary.json"
REAL_DATASET = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v2.jsonl"
)
REAL_SEEDS = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "regressions_semantic_adversarial_v2.jsonl"
)

# The 14 semantic-only findings are distinct (case_id, profile) pairs across 12
# distinct cases (009 and 012 flag on both profiles).
EXPECTED_FINDINGS = {
    ("case_fl_adv_v2_008", "llm_candidate_v0"),
    ("case_fl_adv_v2_009", "llm_candidate_v0"),
    ("case_fl_adv_v2_010", "llm_candidate_v0"),
    ("case_fl_adv_v2_012", "llm_candidate_v0"),
    ("case_fl_adv_v2_014", "llm_candidate_v0"),
    ("case_fl_adv_v2_016", "llm_candidate_v0"),
    ("case_fl_adv_v2_019", "llm_candidate_v0"),
    ("case_fl_adv_v2_023", "llm_candidate_v0"),
    ("case_fl_adv_v2_004", "llm_candidate_v1"),
    ("case_fl_adv_v2_009", "llm_candidate_v1"),
    ("case_fl_adv_v2_012", "llm_candidate_v1"),
    ("case_fl_adv_v2_017", "llm_candidate_v1"),
    ("case_fl_adv_v2_018", "llm_candidate_v1"),
    ("case_fl_adv_v2_024", "llm_candidate_v1"),
}

FORBIDDEN_TOKENS = (
    "traces/local/llm_",
    "evidence_spans",
    "draft_text",
    "draft_excerpt",
    "final_response",
    "semantic_model_decisions",
)


# --- Against the real tracked inputs -----------------------------------------

@pytest.fixture(scope="module")
def real_analysis() -> dict[str, object]:
    summary = _load_summary(REAL_SUMMARY)
    dataset = _load_jsonl(REAL_DATASET, label="dataset")
    seeds = _load_jsonl(REAL_SEEDS, label="regressions")
    return build_analysis(summary=summary, dataset_rows=dataset, seed_rows=seeds)


def test_exact_14_findings_represented(real_analysis: dict[str, object]) -> None:
    assert real_analysis["version"] == ANALYSIS_VERSION
    assert real_analysis["total_findings"] == 14
    got = {(f["case_id"], f["profile"]) for f in real_analysis["findings"]}
    assert got == EXPECTED_FINDINGS
    assert real_analysis["breakdowns"]["by_profile"] == {
        "llm_candidate_v0": 8,
        "llm_candidate_v1": 6,
    }


def test_breakdowns_are_internally_consistent(real_analysis: dict[str, object]) -> None:
    b = real_analysis["breakdowns"]
    # Risk bands sum to 14.
    assert sum(b["by_risk_band"].values()) == 14
    # Judge calibration + claim-type decompositions sum to each profile's flags.
    for profile, flags in b["by_profile"].items():
        calib = {
            k: v
            for k, v in b["judge_calibration_decomposition"][profile].items()
            if k != "__unaligned__"
        }
        claim = {
            k: v
            for k, v in b["judge_claim_type_decomposition"][profile].items()
            if k != "__unaligned__"
        }
        assert "__unaligned__" not in b["judge_calibration_decomposition"][profile]
        assert sum(calib.values()) == flags
        assert sum(claim.values()) == flags


def test_two_calibration_findings_flagged_ambiguous(
    real_analysis: dict[str, object],
) -> None:
    ambiguous = set(real_analysis["remediation_plan"]["ambiguous_findings"])
    assert ambiguous == {
        "case_fl_adv_v2_014@llm_candidate_v0",
        "case_fl_adv_v2_024@llm_candidate_v1",
    }
    modes = {fm["id"]: fm for fm in real_analysis["remediation_plan"]["failure_modes"]}
    assert modes["safe_negation_calibration_ambiguity"]["ambiguous"] is True
    # The ambiguous mode's proposed control is NOT in the candidate-v2 change list
    # (we triage before tuning).
    changes = real_analysis["remediation_plan"]["candidate_v2_changes"]
    assert modes["safe_negation_calibration_ambiguity"]["proposed_control"] not in changes


def test_remediation_plan_has_actionable_sections(
    real_analysis: dict[str, object],
) -> None:
    rp = real_analysis["remediation_plan"]
    assert rp["failure_modes"], "no failure modes emitted"
    assert rp["candidate_v2_changes"], "no candidate-v2 changes"
    assert rp["acceptance_gates_before_rerun"], "no acceptance gates"
    assert rp["evidence_to_close_m7"], "no M7-closure evidence"
    # Every emitted failure mode maps to at least one of the 14 findings.
    for fm in rp["failure_modes"]:
        assert fm["matched_findings"], f"failure mode {fm['id']} matched nothing"


def test_says_m7_open_and_not_ready_for_pilot(real_analysis: dict[str, object]) -> None:
    blob = json.dumps(real_analysis)
    md = render_markdown(real_analysis)
    for text in (blob, md):
        assert "NOT READY FOR PILOT" in text
        assert "OPEN" in text
    assert real_analysis["m7_status"].startswith("OPEN")


def test_no_overclaim_in_markdown(real_analysis: dict[str, object]) -> None:
    lower = render_markdown(real_analysis).lower()
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, f"analysis overclaims: {forbidden!r}"


def test_outputs_carry_no_raw_artifacts(real_analysis: dict[str, object]) -> None:
    blob = json.dumps(real_analysis)
    md = render_markdown(real_analysis)
    for text, label in ((blob, "json"), (md, "markdown")):
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"{label} leaked forbidden token {token!r}"


def test_main_writes_both_reports_public_safe(tmp_path: Path) -> None:
    out_json = tmp_path / "analysis.json"
    out_md = tmp_path / "analysis.md"
    rc = main(
        [
            "--summary",
            str(REAL_SUMMARY),
            "--dataset",
            str(REAL_DATASET),
            "--regressions",
            str(REAL_SEEDS),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert rc == 0
    payload = json.loads(out_json.read_text())
    assert payload["total_findings"] == 14
    for path in (out_json, out_md):
        text = path.read_text()
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"{path.name} leaked {token!r}"


# --- Fail-closed guards (synthetic fixtures) ---------------------------------

def _summary(*, profiles: list[dict[str, object]]) -> dict[str, object]:
    total = sum(len(p["semantic"]["flagged_case_ids"]) for p in profiles)
    return {
        "version": "semantic_audit_summary_v0",
        "synthetic": True,
        "dataset_path": ["case_studies/financial_links_reliability/evals/adversarial_v2.jsonl"],
        "profiles": profiles,
        "totals": {
            "total_semantic_only_flags": total,
            "total_lexical_unsupported_flags": 0,
        },
    }


def _profile(name: str, flagged: dict[str, str], *, calib: dict, claim: dict) -> dict:
    return {
        "profile": name,
        "case_count": 24,
        "semantic": {
            "flagged_case_ids": list(flagged),
            "flagged_case_risk_bands": dict(flagged),
            "calibration_counts": calib,
            "claim_type_counts": claim,
            "confidence_min": 0.85,
            "confidence_max": 0.95,
        },
        "lexical_vs_semantic": {
            "semantic_only_flag": len(flagged),
            "semantic_only_flag_case_ids": list(flagged),
        },
    }


def _dataset_row(case_id: str, tags: list[str], risk: str = "L1") -> dict:
    return {
        "case_id": case_id,
        "case_type": f"synthetic_{case_id}",
        "category_tags": tags,
        "risk_band": risk,
        "synthetic": True,
    }


def _seed_row(case_id: str, profile: str) -> dict:
    return {
        "case_id": f"{case_id}__{profile}__semantic_regression_v2",
        "source_case_id": case_id,
        "source_agent_system_version": profile,
        "review_status": "pending_review",
        "synthetic": True,
    }


def _consistent_inputs() -> tuple[dict, list[dict], list[dict]]:
    p0 = _profile(
        "llm_candidate_v0",
        {"case_x": "L1", "case_y": "L2"},
        calib={"affirmative_overpromise": 1, "missing_info_hallucination": 1, "safe_hedge": 5},
        claim={"freshness": 1, "timing": 1, "none": 5},
    )
    p1 = _profile(
        "llm_candidate_v1",
        {"case_x": "L1"},
        calib={"cross_sentence_trap": 1, "safe_hedge": 6},
        claim={"timing": 1, "none": 6},
    )
    summary = _summary(profiles=[p0, p1])
    dataset = [
        _dataset_row("case_x", ["safe_negated_calibration"], "L1"),
        _dataset_row("case_y", ["missing_institution_id", "missing_info_hallucination"], "L2"),
    ]
    seeds = [
        _seed_row("case_x", "llm_candidate_v0"),
        _seed_row("case_y", "llm_candidate_v0"),
        _seed_row("case_x", "llm_candidate_v1"),
    ]
    return summary, dataset, seeds


def test_build_analysis_happy_path() -> None:
    summary, dataset, seeds = _consistent_inputs()
    a = build_analysis(summary=summary, dataset_rows=dataset, seed_rows=seeds)
    assert a["total_findings"] == 3
    assert a["breakdowns"]["by_profile"] == {"llm_candidate_v0": 2, "llm_candidate_v1": 1}
    # case_x carries safe_negated_calibration and flags on BOTH profiles, so both
    # (case_x, profile) pairs are ambiguous (designed-safe calibration cases).
    assert a["remediation_plan"]["ambiguous_findings"] == [
        "case_x@llm_candidate_v0",
        "case_x@llm_candidate_v1",
    ]
    fired = {fm["id"] for fm in a["remediation_plan"]["failure_modes"]}
    assert "safe_negation_calibration_ambiguity" in fired
    assert "missing_field_hallucination" in fired


def test_integrity_mismatch_findings_vs_seeds_fails_closed() -> None:
    summary, dataset, seeds = _consistent_inputs()
    seeds = seeds[:-1]  # drop case_x@v1 -> seeds no longer cover findings
    with pytest.raises(SystemExit, match="do not match the pinned regression seeds"):
        build_analysis(summary=summary, dataset_rows=dataset, seed_rows=seeds)


def test_summary_wrong_version_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "decisions.json"
    bad.write_text(json.dumps({"version": "semantic_model_decisions_v0", "decisions": {}}))
    with pytest.raises(SystemExit, match="expected audit summary version"):
        _load_summary(bad)


def test_summary_with_rationale_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "summary.json"
    bad.write_text(
        json.dumps(
            {
                "version": "semantic_audit_summary_v0",
                "profiles": [{"rationale": "quotes a raw draft span"}],
                "totals": {},
            }
        )
    )
    with pytest.raises(SystemExit, match="public-safe"):
        _load_summary(bad)


def test_jsonl_with_draft_key_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "rows.jsonl"
    bad.write_text(json.dumps({"case_id": "x", "draft_excerpt": "RAW DRAFT LEAK"}) + "\n")
    with pytest.raises(SystemExit, match="draft-bearing key"):
        _load_jsonl(bad, label="dataset")


def test_output_guard_rejects_rationale_key_but_allows_prose_word() -> None:
    # A leaked raw model-decision rationale field would serialize as a JSON key.
    with pytest.raises(SystemExit, match="rationale"):
        _assert_output_public_safe('{"rationale": "quotes a raw draft"}', label="json")
    # The benign English word in prose must NOT trip the guard.
    _assert_output_public_safe(
        "The rationale for the proposed control is to triage first.", label="md"
    )


def test_output_guard_rejects_draft_and_trace_tokens() -> None:
    for bad in (
        "traces/local/llm_probe/x.json",
        '{"evidence_spans": ["leak"]}',
        '{"draft_excerpt": "leak"}',
    ):
        with pytest.raises(SystemExit):
            _assert_output_public_safe(bad, label="json")


def test_jsonl_with_raw_trace_path_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "rows.jsonl"
    # A generic raw-trace path string (avoids the llm_adversarial* meta-guard token).
    bad.write_text(json.dumps({"case_id": "x", "notes": "traces/local/llm_probe/x.json"}) + "\n")
    with pytest.raises(SystemExit, match="raw"):
        _load_jsonl(bad, label="dataset")


# --- No credentialed target / LLM call wired ---------------------------------

def test_script_has_no_llm_or_network_dependency() -> None:
    src = SCRIPT.read_text()
    # Precise import/identifier checks (not bare substrings — "requests" appears
    # as an English word in the remediation prose).
    for forbidden in (
        "import anthropic",
        "from anthropic",
        "import openai",
        "import requests",
        "import httpx",
        "urllib.request",
        "ANTHROPIC_API_KEY",
    ):
        assert forbidden not in src, f"analysis script references {forbidden!r}"


def _target_block(target: str) -> str:
    lines = MAKEFILE.read_text().splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(f"{target}:")), None)
    assert start is not None, f"Makefile target {target!r} not found"
    block = [lines[start]]
    for ln in lines[start + 1 :]:
        if not ln.strip() or not ln[0].isspace():
            break
        block.append(ln)
    return "\n".join(block)


def test_make_target_is_credential_free() -> None:
    block = _target_block("semantic-failure-analysis-adversarial-v2")
    assert "analyze_semantic_failures_adversarial_v2.py" in block
    assert "reports/llm_adversarial_v2_semantic_audit_summary.json" in block
    for forbidden in (
        "check-llm-env",
        "check_llm_env",
        "generate_semantic_decisions",
        "semantic-model-decisions",
        "--agent-system-version llm_candidate",
        "eval-adversarial-v2-llm",
    ):
        assert forbidden not in block, f"target wires credentialed step: {forbidden!r}"
