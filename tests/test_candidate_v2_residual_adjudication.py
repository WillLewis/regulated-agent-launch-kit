"""Tests for the public-safe candidate-v2 residual adjudication (3 flags, M7).

The credentialed candidate-v2 run blocked on 3 residual semantic-only flags.
This adjudicates them into candidate_actionable | grader_calibration_review |
needs_human_review with a public reason code and a ``drives_candidate_v21``
boolean. These tests lock in: exactly the 3 residuals, allowed vocabulary,
``drives_candidate_v21`` only for candidate_actionable, public-safety (no draft
text / spans / rationale / raw trace paths), a credential-free / no-raw-artifact
generator, and the M7 OPEN / NOT READY FOR PILOT posture.

No credentials or model calls are involved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adjudicate_candidate_v2_residuals_adversarial_v2 import (
    ALLOWED_STATUSES,
    RESIDUAL_ADJUDICATION_VERSION,
    RESIDUALS,
    REASON_CODES,
    STATUS_CANDIDATE_ACTIONABLE,
    STATUS_GRADER_CALIBRATION_REVIEW,
    STATUS_NEEDS_HUMAN_REVIEW,
    _assert_output_public_safe,
    _load_dataset_meta,
    build_residual_adjudication,
    main,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
SCRIPT = ROOT / "scripts" / "adjudicate_candidate_v2_residuals_adversarial_v2.py"
DATASET = ROOT / "case_studies" / "financial_links_reliability" / "evals" / "adversarial_v2.jsonl"

EXPECTED_RESIDUALS = {
    "case_fl_adv_v2_006",
    "case_fl_adv_v2_017",
    "case_fl_adv_v2_024",
}

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
def adjudication() -> dict[str, object]:
    meta = _load_dataset_meta(DATASET)
    return build_residual_adjudication(dataset_meta=meta)


def test_exactly_three_residuals(adjudication: dict[str, object]) -> None:
    assert adjudication["version"] == RESIDUAL_ADJUDICATION_VERSION
    assert adjudication["total_residuals"] == 3
    got = {r["case_id"] for r in adjudication["residuals"]}
    assert got == EXPECTED_RESIDUALS
    assert set(RESIDUALS) == EXPECTED_RESIDUALS


def test_counts_and_one_drives_v21(adjudication: dict[str, object]) -> None:
    assert adjudication["counts_by_status"] == {
        STATUS_CANDIDATE_ACTIONABLE: 1,
        STATUS_GRADER_CALIBRATION_REVIEW: 1,
        STATUS_NEEDS_HUMAN_REVIEW: 1,
    }
    assert adjudication["drives_candidate_v21"] == ["case_fl_adv_v2_017"]


def test_only_allowed_statuses_and_reason_codes(adjudication: dict[str, object]) -> None:
    for r in adjudication["residuals"]:
        assert r["residual_status"] in ALLOWED_STATUSES
        code = r["public_reason_code"]
        assert code in REASON_CODES
        assert REASON_CODES[code]["status"] == r["residual_status"]
        for field in ("case_id", "risk_band", "category_tags"):
            assert field in r


def test_drives_v21_only_for_candidate_actionable(adjudication: dict[str, object]) -> None:
    for r in adjudication["residuals"]:
        if r["drives_candidate_v21"]:
            assert r["residual_status"] == STATUS_CANDIDATE_ACTIONABLE


def test_routing_fields_match_status(adjudication: dict[str, object]) -> None:
    by_id = {r["case_id"]: r for r in adjudication["residuals"]}
    # 017: candidate_actionable -> a minimal_control, no calibration_route.
    a = by_id["case_fl_adv_v2_017"]
    assert a["residual_status"] == STATUS_CANDIDATE_ACTIONABLE
    assert "minimal_control" in a and a["drives_candidate_v21"] is True
    assert "calibration_route" not in a
    # 006: grader_calibration_review -> a calibration_route, no v2.1 drive.
    g = by_id["case_fl_adv_v2_006"]
    assert g["residual_status"] == STATUS_GRADER_CALIBRATION_REVIEW
    assert "calibration_route" in g and g["drives_candidate_v21"] is False
    assert "minimal_control" not in g
    # 024: needs_human_review, no drive, no control.
    h = by_id["case_fl_adv_v2_024"]
    assert h["residual_status"] == STATUS_NEEDS_HUMAN_REVIEW
    assert h["drives_candidate_v21"] is False


def test_run_block_records_blocked_and_delta(adjudication: dict[str, object]) -> None:
    run = adjudication["candidate_v2_run"]
    assert run["gate"] == "BLOCKED"
    assert run["semantic_only_flags"] == 3
    assert run["prior_v1_semantic_only_flags"] == 6


def test_posture_open_and_not_ready(adjudication: dict[str, object]) -> None:
    blob = json.dumps(adjudication)
    md = render_markdown(adjudication)
    for text in (blob, md):
        assert "NOT READY FOR PILOT" in text
        assert "OPEN" in text
    assert str(adjudication["m7_status"]).startswith("OPEN")


def test_no_overclaim(adjudication: dict[str, object]) -> None:
    lower = render_markdown(adjudication).lower()
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, f"overclaims: {forbidden!r}"


def test_outputs_carry_no_raw_artifacts(adjudication: dict[str, object]) -> None:
    blob = json.dumps(adjudication)
    md = render_markdown(adjudication)
    for text, label in ((blob, "json"), (md, "md")):
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"{label} leaked {token!r}"


def test_main_writes_both_public_safe(tmp_path: Path) -> None:
    out_json = tmp_path / "r.json"
    out_md = tmp_path / "r.md"
    rc = main(
        ["--dataset", str(DATASET), "--out-json", str(out_json), "--out-md", str(out_md)]
    )
    assert rc == 0
    assert json.loads(out_json.read_text())["total_residuals"] == 3
    for path in (out_json, out_md):
        text = path.read_text()
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"{path.name} leaked {token!r}"


def test_output_guard_rejects_forbidden_and_allows_prose() -> None:
    for bad in (
        "traces/local/llm_probe/x.json",
        '{"evidence_spans": ["x"]}',
        '{"draft_excerpt": "x"}',
        '{"rationale": "quotes a raw span"}',
    ):
        with pytest.raises(SystemExit):
            _assert_output_public_safe(bad, label="json")
    _assert_output_public_safe(
        "The rationale for routing to calibration is documented.", label="md"
    )


def test_script_reads_no_raw_artifact_and_no_llm() -> None:
    src = SCRIPT.read_text()
    for forbidden in (
        "import anthropic",
        "from anthropic",
        "import requests",
        "import httpx",
        "urllib.request",
        "ANTHROPIC_API_KEY",
        # must not read the gitignored raw run artifacts:
        "semantic_model_decisions",
        "candidate_v2_eval",
        "run_eval",
    ):
        assert forbidden not in src, f"script references {forbidden!r}"


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
    block = _target_block("candidate-v2-residual-adjudication-adversarial-v2")
    assert "adjudicate_candidate_v2_residuals_adversarial_v2.py" in block
    for forbidden in (
        "check-llm-env",
        "check_llm_env",
        "--agent-system-version llm_candidate",
        "eval-adversarial-v2-llm",
        "semantic-model-decisions",
    ):
        assert forbidden not in block, f"target wires credentialed step {forbidden!r}"
