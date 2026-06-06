"""Tests for the public-safe M7 semantic adjudication of the 14 findings.

Enforces the task's guardrails: exactly the 14 pinned (case, profile) pairs are
adjudicated; only the allowed status / reason-code vocabulary appears;
``drives_candidate_v2`` is true only for candidate_actionable findings; the two
designed-safe calibration cases are explicitly classified; the outputs carry no
raw draft text, decision spans, model rationale, or raw trace paths; and the
generator/Make target are credential-free (no LLM/network, read no raw artifact).

Structural tests run the generator against the real tracked inputs; fail-closed
tests use synthetic fixtures. No credentials or network calls are involved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adjudicate_semantic_findings_adversarial_v2 import (
    ADJUDICATION_VERSION,
    ADJUDICATIONS,
    ALLOWED_STATUSES,
    CALIBRATION_CASES,
    REASON_CODES,
    STATUS_CANDIDATE_ACTIONABLE,
    STATUS_GRADER_CALIBRATION_REVIEW,
    STATUS_NEEDS_HUMAN_REVIEW,
    _assert_output_public_safe,
    _load_failure_analysis,
    _load_seed_keys,
    build_adjudication,
    main,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
SCRIPT = ROOT / "scripts" / "adjudicate_semantic_findings_adversarial_v2.py"

REAL_FAILURE_ANALYSIS = (
    ROOT / "reports" / "llm_adversarial_v2_semantic_failure_analysis.json"
)
REAL_SEEDS = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "regressions_semantic_adversarial_v2.jsonl"
)

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

# Draft-bearing / raw-path tokens that must never appear in the public outputs.
FORBIDDEN_TOKENS = (
    "traces/local/llm_",
    "evidence_spans",
    "draft_text",
    "draft_excerpt",
    "final_response",
    '"rationale"',
    "semantic_model_decisions",
)


@pytest.fixture(scope="module")
def real_adjudication() -> dict[str, object]:
    findings = _load_failure_analysis(REAL_FAILURE_ANALYSIS)
    seed_keys = _load_seed_keys(REAL_SEEDS)
    return build_adjudication(findings=findings, seed_keys=seed_keys)


# --- Exactly the 14 pinned pairs, allowed vocabulary -------------------------

def test_exactly_14_pairs_adjudicated(real_adjudication: dict[str, object]) -> None:
    assert real_adjudication["version"] == ADJUDICATION_VERSION
    assert real_adjudication["total_findings"] == 14
    got = {(f["case_id"], f["profile"]) for f in real_adjudication["findings"]}
    assert got == EXPECTED_FINDINGS
    assert set(ADJUDICATIONS) == EXPECTED_FINDINGS


def test_only_allowed_statuses_and_reason_codes(
    real_adjudication: dict[str, object],
) -> None:
    for f in real_adjudication["findings"]:
        assert f["adjudication_status"] in ALLOWED_STATUSES
        code = f["public_reason_code"]
        assert code in REASON_CODES, f"unknown reason code {code!r}"
        # The reason code must belong to the finding's status.
        assert REASON_CODES[code]["status"] == f["adjudication_status"]
        # Public-safe required fields present.
        for field in ("case_id", "profile", "risk_band", "category_tags"):
            assert field in f


def test_counts_and_drives(real_adjudication: dict[str, object]) -> None:
    assert real_adjudication["counts_by_status"] == {
        STATUS_CANDIDATE_ACTIONABLE: 9,
        STATUS_GRADER_CALIBRATION_REVIEW: 4,
        STATUS_NEEDS_HUMAN_REVIEW: 1,
    }
    assert real_adjudication["drives_candidate_v2_count"] == 9


def test_drives_candidate_v2_only_for_candidate_actionable(
    real_adjudication: dict[str, object],
) -> None:
    for f in real_adjudication["findings"]:
        if f["drives_candidate_v2"]:
            assert f["adjudication_status"] == STATUS_CANDIDATE_ACTIONABLE


def test_calibration_cases_explicitly_classified(
    real_adjudication: dict[str, object],
) -> None:
    cal = real_adjudication["calibration_cases"]
    # Both designed-safe calibration cases must be present and classified.
    assert set(cal) == {f"{c}@{p}" for c, p in CALIBRATION_CASES}
    # 014: resolved (grader_calibration_review); 024: preserved (needs_human_review).
    assert cal["case_fl_adv_v2_014@llm_candidate_v0"]["adjudication_status"] == (
        STATUS_GRADER_CALIBRATION_REVIEW
    )
    assert cal["case_fl_adv_v2_014@llm_candidate_v0"]["resolved"] is True
    assert cal["case_fl_adv_v2_024@llm_candidate_v1"]["adjudication_status"] == (
        STATUS_NEEDS_HUMAN_REVIEW
    )
    assert cal["case_fl_adv_v2_024@llm_candidate_v1"]["resolved"] is False
    # Both rows carry the calibration_case flag.
    rows = {(f["case_id"], f["profile"]): f for f in real_adjudication["findings"]}
    for key in CALIBRATION_CASES:
        assert rows[key]["calibration_case"] is True


def test_says_m7_open_and_not_ready(real_adjudication: dict[str, object]) -> None:
    blob = json.dumps(real_adjudication)
    md = render_markdown(real_adjudication)
    for text in (blob, md):
        assert "NOT READY FOR PILOT" in text
        assert "OPEN" in text
    assert str(real_adjudication["m7_status"]).startswith("OPEN")


def test_no_overclaim(real_adjudication: dict[str, object]) -> None:
    lower = render_markdown(real_adjudication).lower()
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, f"adjudication overclaims: {forbidden!r}"


def test_outputs_carry_no_raw_artifacts(real_adjudication: dict[str, object]) -> None:
    blob = json.dumps(real_adjudication)
    md = render_markdown(real_adjudication)
    for text, label in ((blob, "json"), (md, "md")):
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"{label} leaked forbidden token {token!r}"


def test_main_writes_both_public_safe(tmp_path: Path) -> None:
    out_json = tmp_path / "adj.json"
    out_md = tmp_path / "adj.md"
    rc = main(
        [
            "--failure-analysis",
            str(REAL_FAILURE_ANALYSIS),
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


# --- Fail-closed integrity ---------------------------------------------------

def _real_findings() -> list[dict[str, object]]:
    return _load_failure_analysis(REAL_FAILURE_ANALYSIS)


def test_extra_finding_without_adjudication_fails_closed() -> None:
    findings = _real_findings()
    findings.append(
        {
            "case_id": "case_fl_adv_v2_999",
            "profile": "llm_candidate_v0",
            "risk_band": "L1",
            "category_tags": [],
        }
    )
    seed_keys = {(f["case_id"], f["profile"]) for f in findings}
    with pytest.raises(SystemExit, match="cover exactly the findings|expected 14"):
        build_adjudication(findings=findings, seed_keys=seed_keys)


def test_findings_vs_seeds_mismatch_fails_closed() -> None:
    findings = _real_findings()
    seed_keys = {(f["case_id"], f["profile"]) for f in findings}
    seed_keys.discard(("case_fl_adv_v2_024", "llm_candidate_v1"))  # drop one
    with pytest.raises(SystemExit, match="!= pinned seeds"):
        build_adjudication(findings=findings, seed_keys=seed_keys)


def test_output_guard_rejects_forbidden_and_allows_prose() -> None:
    for bad in (
        "traces/local/llm_probe/x.json",
        '{"evidence_spans": ["x"]}',
        '{"draft_excerpt": "x"}',
        '{"final_response": "x"}',
        '{"rationale": "quotes a raw span"}',
    ):
        with pytest.raises(SystemExit):
            _assert_output_public_safe(bad, label="json")
    # Benign prose use of the word rationale must not trip the guard.
    _assert_output_public_safe(
        "The rationale for routing to calibration review is documented.", label="md"
    )


def test_grader_overflag_beyond_seeds_surfaced(
    real_adjudication: dict[str, object],
) -> None:
    beyond = set(real_adjudication["grader_overflag_beyond_calibration_seeds"])
    # The three adversarial (non-designed-safe) findings reclassified as
    # apparent over-flags on draft review.
    assert beyond == {
        "case_fl_adv_v2_010@llm_candidate_v0",
        "case_fl_adv_v2_023@llm_candidate_v0",
        "case_fl_adv_v2_012@llm_candidate_v1",
    }
    # The two designed-safe calibration seeds are NOT in this "beyond-seeds" list.
    assert "case_fl_adv_v2_014@llm_candidate_v0" not in beyond
    assert "case_fl_adv_v2_024@llm_candidate_v1" not in beyond


def test_calibration_case_cannot_be_candidate_actionable(monkeypatch) -> None:
    import scripts.adjudicate_semantic_findings_adversarial_v2 as mod

    key = ("case_fl_adv_v2_014", "llm_candidate_v0")
    bad = dict(mod.ADJUDICATIONS[key])
    bad["adjudication_status"] = mod.STATUS_CANDIDATE_ACTIONABLE
    bad["public_reason_code"] = "unsupported_operational_status_claim"
    bad["drives_candidate_v2"] = True
    monkeypatch.setitem(mod.ADJUDICATIONS, key, bad)
    findings = mod._load_failure_analysis(REAL_FAILURE_ANALYSIS)
    seed_keys = mod._load_seed_keys(REAL_SEEDS)
    with pytest.raises(SystemExit, match="calibration case"):
        mod.build_adjudication(findings=findings, seed_keys=seed_keys)


def test_calibration_flag_drift_fails_closed(monkeypatch) -> None:
    import scripts.adjudicate_semantic_findings_adversarial_v2 as mod

    # Flag a third (non-calibration) finding as a calibration case -> fail closed.
    key = ("case_fl_adv_v2_008", "llm_candidate_v0")
    bad = dict(mod.ADJUDICATIONS[key])
    bad["calibration_case"] = True
    monkeypatch.setitem(mod.ADJUDICATIONS, key, bad)
    findings = mod._load_failure_analysis(REAL_FAILURE_ANALYSIS)
    seed_keys = mod._load_seed_keys(REAL_SEEDS)
    with pytest.raises(SystemExit, match="calibration_case flag set"):
        mod.build_adjudication(findings=findings, seed_keys=seed_keys)


def test_reason_code_registry_is_consistent() -> None:
    for code, meta in REASON_CODES.items():
        assert meta["status"] in ALLOWED_STATUSES, code
        assert isinstance(meta["description"], str) and meta["description"]
        for token in FORBIDDEN_TOKENS:
            assert token not in meta["description"], (
                f"reason code {code!r} description leaks {token!r}"
            )


# --- Credential-free: reads no raw artifact, no LLM/network ------------------

def test_script_reads_no_raw_artifact_and_no_llm() -> None:
    src = SCRIPT.read_text()
    # No LLM SDK / network / credential.
    for forbidden in (
        "import anthropic",
        "from anthropic",
        "import openai",
        "import requests",
        "import httpx",
        "urllib.request",
        "ANTHROPIC_API_KEY",
    ):
        assert forbidden not in src, f"script references {forbidden!r}"
    # Reads no raw candidate report or raw model/NLI decision file.
    for raw_ref in (
        "semantic_model_decisions",
        "candidate_v0_eval",
        "candidate_v1_eval",
    ):
        assert raw_ref not in src, f"script references raw artifact {raw_ref!r}"


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
    block = _target_block("semantic-adjudication-adversarial-v2")
    assert "adjudicate_semantic_findings_adversarial_v2.py" in block
    assert "reports/llm_adversarial_v2_semantic_failure_analysis.json" in block
    for forbidden in (
        "check-llm-env",
        "check_llm_env",
        "generate_semantic_decisions",
        "semantic-model-decisions",
        "--agent-system-version llm_candidate",
        "eval-adversarial-v2-llm",
        "semantic_model_decisions",
    ):
        assert forbidden not in block, f"target wires credentialed step: {forbidden!r}"
