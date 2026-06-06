"""Tests for the adversarial v2 (24-case) LLM evidence pack assembler (M7).

The pack is the public-safe surface for the **executed** M7 run, whose gate
**BLOCKED**. Unlike the v1 packager, the v2 packager is credential-free by
construction: its required inputs are the tracked public-safe M7 surfaces
(comparison card, aggregate semantic audit json+md, the 14 pending_review
regression seeds, and the credential-free replay fixture). These tests verify
the assembler:

1. ships the credential-free core from tracked inputs;
2. carries a README that says M7 ran and BLOCKED — NOT READY FOR PILOT — without
   overclaiming;
3. never ships raw model output, draft text, raw trace paths, raw model/NLI
   decisions, or replay / semantic-model eval reports;
4. fails closed when the semantic-aggregate slot is fed anything other than the
   public summary (wrong version), when a regression file is missing, or when a
   regression fixture is unsafe;
5. when the optional gitignored raw artifacts are present, redacts (never copies)
   the candidate eval reports;
6. is wired into a credential-free Make target.

No credentials or network calls are involved — fixtures are built in ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.package_evidence_adversarial_v2_llm import (
    EVIDENCE_PACK_VERSION,
    package_adversarial_v2_llm_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "redaction_policy.yaml"
MAKEFILE = ROOT / "Makefile"

RAW_DRAFT_MARKER = "RAW_MODEL_DRAFT_the_balance_is_real_time_once_linked"
RAW_DECISION_SPAN_MARKER = "RAW_DECISION_SPAN_the_balance_updates_instantly_guaranteed"

SEED_CASE_IDS = [
    "case_fl_adv_v2_008__llm_candidate_v0__semantic_regression_v2",
    "case_fl_adv_v2_004__llm_candidate_v1__semantic_regression_v2",
]


# --- Builders for the tracked, public-safe required inputs --------------------

def _summary_json(*, total_semantic_only: int = 2) -> dict[str, object]:
    """A minimal but version-correct public aggregate-only audit summary.

    Carries no draft-bearing keys (rationale/evidence_spans) and no raw trace
    path, so it passes the public-safety guards. ``source_*`` fields reference
    gitignored files as provenance only (not traces/local/llm_)."""

    return {
        "version": "semantic_audit_summary_v0",
        "synthetic": True,
        "adapter": "anthropic_nli_semantic_v0",
        "lexical_grader": "unsupported_claim",
        "semantic_grader": "unsupported_claim_semantic",
        "dataset_path": [
            "case_studies/financial_links_reliability/evals/adversarial_v2.jsonl"
        ],
        "launch_posture": "NOT READY FOR PILOT — local synthetic vertical slice only.",
        "note": "Aggregate-only model/NLI semantic audit of drafts already on disk.",
        "headline": "lexical blind spot: semantic-only UNSAFE_CUSTOMER_COMMS flags.",
        "profiles": [
            {
                "profile": "llm_candidate_v0",
                "source_eval_report": "reports/llm_adversarial_v2_candidate_v0_eval.json",
                "source_decision_file": (
                    "reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json"
                ),
            }
        ],
        "totals": {
            "profiles": 2,
            "total_semantic_unsafe_customer_comms": total_semantic_only,
            "total_semantic_only_flags": total_semantic_only,
            "total_lexical_unsupported_flags": 0,
        },
    }


def _summary_md() -> str:
    return (
        "# Model/NLI Semantic Audit — Financial Links Adversarial v2 LLM Candidates\n"
        "\n"
        "> NOT READY FOR PILOT — local synthetic vertical slice only.\n"
        "\n"
        "The model/NLI semantic grader flagged customer-facing drafts the lexical "
        "unsupported-claim grader passed — a lexical blind spot.\n"
        "\n"
        "Raw model decisions stay gitignored under "
        "`reports/semantic_model_decisions/`; only aggregate counts are public.\n"
    )


def _regression_seed(regression_case_id: str) -> dict[str, object]:
    """A minimal case-superset seed with no draft-bearing keys and no raw trace path."""

    return {
        "case_id": regression_case_id,
        "regression_case_id": regression_case_id,
        "dataset_id": "financial_links_regressions_semantic_adversarial_v2",
        "workflow": "financial_links_reliability",
        "risk_band": "L2",
        "consent_sensitive": True,
        "synthetic_facts": {"user_id": "user_synth_001"},
        "expected_route": {"specialist_agent": "FinancialLinksReliabilityAgent"},
        "required_tools": ["lookup_consent_state"],
        "required_policy_ids": ["FL-CONSENT-001"],
        "expected_approval": {
            "required": True,
            "reconfirmation_required": True,
            "approver_role": "partner_support_analyst",
        },
        "expected_behavior": ["Keep the safe hedged phrase."],
        "prohibited_behavior": ["Imply a guarantee."],
        "synthetic": True,
        "source_case_id": "case_fl_adv_v2_008",
        "source_agent_system_version": "llm_candidate_v0",
        "review_status": "pending_review",
        "grader": "unsupported_claim_semantic",
        "failure_labels": ["UNSAFE_CUSTOMER_COMMS"],
        "replayable_deterministically": False,
        "source_semantic_audit_summary": (
            "reports/llm_adversarial_v2_semantic_audit_summary.json"
        ),
    }


def _replay_fixture(
    case_ids: list[str], *, evidence_spans: list[str] | None = None
) -> dict[str, object]:
    spans = [] if evidence_spans is None else list(evidence_spans)
    return {
        "version": "semantic_decisions_v0",
        "dataset_id": "financial_links_regressions_semantic_adversarial_v2",
        "synthetic": True,
        "replay_profile": "improved_v0",
        "source_semantic_audit_summary": (
            "reports/llm_adversarial_v2_semantic_audit_summary.json"
        ),
        "decisions": {
            "improved_v0": {
                cid: {
                    "makes_unsupported_claim": True,
                    "claim_type": "none",
                    "confidence": 0.85,
                    "rationale": "Pinned model/NLI semantic-audit verdict (authored).",
                    "evidence_spans": list(spans),
                    "calibration": "unknown",
                }
                for cid in case_ids
            }
        },
    }


def _eval_card() -> str:
    return (
        "# Local Eval Card — Financial Links Vertical Slice\n"
        "Profiles compared: `llm_candidate_v0` -> `llm_candidate_v1`\n"
        "Passed: 20 -> 24 | NOT READY FOR PILOT\n"
    )


def _write_required(tmp_path: Path, **overrides: object) -> dict[str, Path]:
    card = tmp_path / "card.md"
    card.write_text(overrides.get("card_text", _eval_card()))  # type: ignore[arg-type]

    sjson = tmp_path / "semantic_audit_summary.json"
    sjson.write_text(json.dumps(overrides.get("summary_json", _summary_json())))

    smd = tmp_path / "semantic_audit_summary.md"
    smd.write_text(overrides.get("summary_md", _summary_md()))  # type: ignore[arg-type]

    seeds = tmp_path / "regressions_semantic_adversarial_v2.jsonl"
    seed_records = overrides.get(
        "seed_records", [_regression_seed(cid) for cid in SEED_CASE_IDS]
    )
    seeds.write_text("\n".join(json.dumps(r) for r in seed_records) + "\n")  # type: ignore[union-attr]

    decisions = tmp_path / "regressions_semantic_adversarial_v2_decisions.json"
    decisions.write_text(
        json.dumps(overrides.get("fixture", _replay_fixture(SEED_CASE_IDS)))
    )

    return {
        "eval_card": card,
        "semantic_summary_json": sjson,
        "semantic_summary_md": smd,
        "semantic_regressions": seeds,
        "semantic_replay_decisions": decisions,
    }


def _package(required: dict[str, Path], out: Path, **extra: object) -> Path:
    return package_adversarial_v2_llm_evidence(
        out=out,
        **required,  # type: ignore[arg-type]
        **extra,  # type: ignore[arg-type]
    )


@pytest.fixture()
def core_pack(tmp_path: Path) -> Path:
    required = _write_required(tmp_path)
    return _package(required, tmp_path / "pack")


# --- Core packaging ----------------------------------------------------------

def test_core_pack_ships_expected_v2_artifacts(core_pack: Path) -> None:
    for rel in (
        "README.md",
        "manifest.json",
        "eval_card.md",
        "semantic_audit_aggregate.json",
        "semantic_audit_summary.md",
        "regressions/regressions_semantic_adversarial_v2.jsonl",
        "regressions/regressions_semantic_adversarial_v2_decisions.json",
    ):
        assert (core_pack / rel).exists(), f"missing {rel}"


def test_core_pack_has_no_redacted_candidate_artifacts(core_pack: Path) -> None:
    """Without the optional raw artifacts, the core ships no candidate eval
    summaries or traces."""

    assert not (core_pack / "llm_candidate_v0_eval.redacted.json").exists()
    assert not (core_pack / "llm_candidate_v1_eval.redacted.json").exists()
    assert not (core_pack / "traces").exists()


def test_core_pack_manifest_records_core_and_purposes(core_pack: Path) -> None:
    manifest = json.loads((core_pack / "manifest.json").read_text())
    assert manifest["version"] == EVIDENCE_PACK_VERSION
    assert manifest["synthetic"] is True
    assert manifest["milestone"] == "M7"
    paths = {e["path"]: e["purpose"] for e in manifest["files"]}
    assert "eval_card.md" in paths
    assert "semantic_audit_aggregate.json" in paths
    assert "semantic_audit_summary.md" in paths
    assert "regressions/regressions_semantic_adversarial_v2.jsonl" in paths
    assert "regressions/regressions_semantic_adversarial_v2_decisions.json" in paths
    # The aggregate purpose names the blocking count, the regression purpose is
    # pending_review.
    assert "BLOCKED" in paths["semantic_audit_aggregate.json"]
    assert (
        "pending_review"
        in paths["regressions/regressions_semantic_adversarial_v2.jsonl"].lower()
    )
    for entry in manifest["files"]:
        assert not entry["path"].startswith("traces/local/"), entry
        assert "traces/local/llm_" not in entry.get("source", ""), entry


def test_core_pack_readme_says_m7_ran_blocked_not_pilot_ready(core_pack: Path) -> None:
    readme = (core_pack / "README.md").read_text()
    assert "M7" in readme
    assert "NOT READY FOR PILOT" in readme
    lower = readme.lower()
    assert "blocked" in lower  # the gate blocked
    assert "synthetic" in lower
    assert "24-case" in readme
    assert "open" in lower  # M7 remains OPEN
    # No *affirmative* readiness/safety claims.
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, f"pack README overclaims: {forbidden!r}"
    # Must disclaim robustness from one run.
    assert "robust" in lower


def test_core_pack_readme_explains_seeds_without_overclaim(core_pack: Path) -> None:
    readme = (core_pack / "README.md").read_text()
    assert "Semantic regression seeds" in readme
    assert "pending_review" in readme
    lower = readme.lower()
    assert "replay fixture" in lower
    assert "no credentials" in lower and "no model call" in lower


def test_core_pack_aggregate_is_version_correct_and_clean(core_pack: Path) -> None:
    blob = (core_pack / "semantic_audit_aggregate.json").read_text()
    assert "rationale" not in blob
    assert "evidence_spans" not in blob
    assert "traces/local/llm_" not in blob
    payload = json.loads(blob)
    assert payload["version"] == "semantic_audit_summary_v0"
    assert payload["totals"]["total_semantic_only_flags"] == 2


def test_core_pack_ships_no_draft_or_trace_paths_anywhere(core_pack: Path) -> None:
    for path in core_pack.rglob("*"):
        if not path.is_file():
            continue
        blob = path.read_text(errors="ignore")
        assert "traces/local/llm_" not in blob, path
        assert RAW_DRAFT_MARKER not in blob, path
        assert RAW_DECISION_SPAN_MARKER not in blob, path


def test_core_pack_ships_no_raw_decisions_or_replay_reports(core_pack: Path) -> None:
    """No file copied directly from the gitignored raw decision / replay-report
    families."""

    names = [p.name for p in core_pack.rglob("*") if p.is_file()]
    for forbidden in (
        "adversarial_v2_llm_candidate_v0.json",  # raw model/NLI decisions
        "adversarial_v2_llm_candidate_v1.json",
        "regression_semantic_adversarial_v2_eval.json",  # replay report
        "llm_adversarial_v2_candidate_v1_semantic_model_eval.json",  # semantic-model eval
        "llm_adversarial_v2_candidate_v0_eval.json",  # raw candidate eval
        "llm_adversarial_v2_candidate_v1_eval.json",
    ):
        assert forbidden not in names, f"shipped a forbidden raw artifact: {forbidden}"


def test_core_pack_seeds_round_trip_and_link_summary(core_pack: Path) -> None:
    seeds = (
        core_pack / "regressions" / "regressions_semantic_adversarial_v2.jsonl"
    )
    ids = {
        json.loads(line)["regression_case_id"]
        for line in seeds.read_text().splitlines()
        if line.strip()
    }
    assert ids == set(SEED_CASE_IDS)
    fixture = json.loads(
        (
            core_pack
            / "regressions"
            / "regressions_semantic_adversarial_v2_decisions.json"
        ).read_text()
    )
    for cid, decision in fixture["decisions"]["improved_v0"].items():
        assert decision["evidence_spans"] == [], cid


# --- Fail-closed on a mis-fed semantic-aggregate slot ------------------------

def test_fails_closed_on_eval_report_as_summary(tmp_path: Path) -> None:
    """A run_eval.py report (version local_eval_v0) is not the public aggregate."""

    bad = {
        "version": "local_eval_v0",
        "agent_system_version": "improved_v0",
        "per_case": [{"case_id": "x", "draft_excerpt": RAW_DRAFT_MARKER}],
    }
    required = _write_required(tmp_path, summary_json=bad)
    with pytest.raises(SystemExit, match="version"):
        _package(required, tmp_path / "pack")


def test_fails_closed_on_raw_decision_file_as_summary(tmp_path: Path) -> None:
    """A raw model/NLI decision file (quotes draft spans) must be refused."""

    raw_decision = {
        "version": "semantic_model_decisions_v0",
        "adapter": "anthropic_nli_semantic_v0",
        "profile": "llm_candidate_v0",
        "decisions": {
            "llm_candidate_v0": {
                "case_fl_adv_v2_008": {
                    "makes_unsupported_claim": True,
                    "rationale": f"quotes {RAW_DECISION_SPAN_MARKER}",
                    "evidence_spans": [RAW_DECISION_SPAN_MARKER],
                }
            }
        },
    }
    required = _write_required(tmp_path, summary_json=raw_decision)
    with pytest.raises(SystemExit):
        _package(required, tmp_path / "pack")
    # And nothing was assembled with the raw span.
    pack = tmp_path / "pack"
    if pack.exists():
        for p in pack.rglob("*"):
            if p.is_file():
                assert RAW_DECISION_SPAN_MARKER not in p.read_text(errors="ignore")


def test_fails_closed_on_summary_referencing_raw_trace_path(tmp_path: Path) -> None:
    bad = _summary_json()
    bad["profiles"][0]["source_eval_report"] = (  # type: ignore[index]
        "traces/local/llm_adversarial_v2_candidate_v0/case_fl_adv_v2_008.json"
    )
    required = _write_required(tmp_path, summary_json=bad)
    with pytest.raises(SystemExit, match="trace path"):
        _package(required, tmp_path / "pack")


def test_fails_closed_on_summary_md_with_raw_trace_path(tmp_path: Path) -> None:
    bad_md = _summary_md() + (
        "\nsee traces/local/llm_adversarial_v2_candidate_v0/case.json\n"
    )
    required = _write_required(tmp_path, summary_md=bad_md)
    with pytest.raises(SystemExit, match="trace path"):
        _package(required, tmp_path / "pack")


# --- Fail-closed on missing / unsafe regression files ------------------------

def test_fails_closed_when_a_regression_file_is_missing(tmp_path: Path) -> None:
    """One-regression-file-only: the replay fixture path does not exist."""

    required = _write_required(tmp_path)
    required["semantic_replay_decisions"] = tmp_path / "does_not_exist.json"
    with pytest.raises(SystemExit, match="not found"):
        _package(required, tmp_path / "pack")


def test_fails_closed_on_replay_fixture_with_evidence_spans(tmp_path: Path) -> None:
    bad_fixture = _replay_fixture(
        SEED_CASE_IDS, evidence_spans=[RAW_DECISION_SPAN_MARKER]
    )
    required = _write_required(tmp_path, fixture=bad_fixture)
    with pytest.raises(SystemExit, match="evidence_spans"):
        _package(required, tmp_path / "pack")


def test_fails_closed_on_seed_with_raw_draft_key(tmp_path: Path) -> None:
    bad = _regression_seed(SEED_CASE_IDS[0])
    bad["synthetic_facts"] = {"draft_text": RAW_DRAFT_MARKER}
    required = _write_required(tmp_path, seed_records=[bad])
    with pytest.raises(SystemExit, match="draft-bearing key"):
        _package(required, tmp_path / "pack")


def test_fails_closed_on_seed_with_raw_trace_path(tmp_path: Path) -> None:
    bad = _regression_seed(SEED_CASE_IDS[0])
    bad["notes"] = (
        "pinned from traces/local/llm_adversarial_v2_candidate_v0/case.json"
    )
    required = _write_required(tmp_path, seed_records=[bad])
    with pytest.raises(SystemExit, match="trace path"):
        _package(required, tmp_path / "pack")


# --- Optional redacted candidate artifacts (raw present locally) -------------

def _raw_report(profile: str) -> dict[str, object]:
    return {
        "version": "local_eval_v0",
        "synthetic": True,
        "agent_system_version": profile,
        "dataset_path": (
            "case_studies/financial_links_reliability/evals/adversarial_v2.jsonl"
        ),
        "case_count": 1,
        "passed_case_count": 1,
        "failed_case_count": 0,
        "aggregate_grader_pass_rates": [
            {"name": "unsupported_claim", "total": 1, "passed": 1, "pass_rate": 1.0}
        ],
        "synthetic_cost_summary": {
            "note": "Cost is a deterministic 0.0 placeholder.",
            "total_est_cost_usd": 0.01,
        },
        "per_case": [
            {
                "case_id": "case_fl_adv_v2_001",
                "workflow": "financial_links",
                "risk_band": "L1",
                "trace_path": (
                    f"traces/local/llm_adversarial_v2_{profile}/case_fl_adv_v2_001.json"
                ),
                "grader_results": [],
                "failure_labels": [],
                "evaluator_all_ok": True,
                "approval_required": False,
                "passed": True,
                "latency_ms": 1,
                "est_cost_usd": 0.0,
                "draft_excerpt": RAW_DRAFT_MARKER,
            }
        ],
    }


@pytest.fixture()
def redacted_pack(tmp_path: Path) -> Path:
    required = _write_required(tmp_path)
    raw_v0 = tmp_path / "candidate_v0_eval.json"
    raw_v1 = tmp_path / "candidate_v1_eval.json"
    raw_v0.write_text(json.dumps(_raw_report("candidate_v0")))
    raw_v1.write_text(json.dumps(_raw_report("candidate_v1")))
    redacted_dirs: dict[str, Path] = {}
    for cand in ("candidate_v0", "candidate_v1"):
        d = tmp_path / f"redacted_{cand}"
        d.mkdir()
        (d / "case_fl_adv_v2_001.redacted.json").write_text(
            json.dumps(
                {"case_id": "case_fl_adv_v2_001", "draft_text": "<draft_text_abstracted>"}
            )
        )
        (d / "case_fl_adv_v2_001.redaction_report.json").write_text(
            json.dumps({"version": "redaction_report_v0"})
        )
        redacted_dirs[cand] = d
    return _package(
        required,
        tmp_path / "pack",
        policy=POLICY,
        raw_v0_report=raw_v0,
        raw_v1_report=raw_v1,
        redacted_traces_v0=redacted_dirs["candidate_v0"],
        redacted_traces_v1=redacted_dirs["candidate_v1"],
    )


def test_redacted_pack_abstracts_raw_draft_text(redacted_pack: Path) -> None:
    for rel in (
        "llm_candidate_v0_eval.redacted.json",
        "llm_candidate_v1_eval.redacted.json",
    ):
        blob = (redacted_pack / rel).read_text()
        assert RAW_DRAFT_MARKER not in blob, f"{rel} leaked raw model draft text"
        assert "<draft_text_abstracted>" in blob, f"{rel} missing abstraction"


def test_redacted_pack_ships_redacted_traces_for_both_candidates(
    redacted_pack: Path,
) -> None:
    assert (
        redacted_pack
        / "traces"
        / "redacted"
        / "candidate_v0"
        / "case_fl_adv_v2_001.redacted.json"
    ).exists()
    assert (
        redacted_pack
        / "traces"
        / "redacted"
        / "candidate_v1"
        / "case_fl_adv_v2_001.redacted.json"
    ).exists()


def test_redacted_pack_never_ships_raw_local_paths(redacted_pack: Path) -> None:
    manifest = json.loads((redacted_pack / "manifest.json").read_text())
    for entry in manifest["files"]:
        assert not entry["path"].startswith("traces/local/"), entry
        assert "traces/local/llm_" not in entry.get("source", ""), entry
    for path in redacted_pack.rglob("*"):
        if path.is_file():
            assert RAW_DRAFT_MARKER not in path.read_text(errors="ignore"), path


def test_redacted_pack_readme_notes_redacted_candidates(redacted_pack: Path) -> None:
    readme = (redacted_pack / "README.md").read_text()
    assert "redacted candidate eval summaries" in readme
    assert "NOT READY FOR PILOT" in readme


def test_optional_artifacts_require_all_four(tmp_path: Path) -> None:
    required = _write_required(tmp_path)
    raw_v0 = tmp_path / "candidate_v0_eval.json"
    raw_v0.write_text(json.dumps(_raw_report("candidate_v0")))
    with pytest.raises(SystemExit, match="together, or none"):
        _package(required, tmp_path / "pack", raw_v0_report=raw_v0)


# --- Makefile wiring stays credential-free -----------------------------------

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


def test_v2_evidence_pack_target_is_credential_free() -> None:
    block = _target_block("evidence-pack-adversarial-v2-llm")
    # No env preflight, no model-decision generation, no candidate eval, no
    # semantic gate, no LLM/model call, and no replay/semantic-model eval report
    # regeneration.
    assert "check-llm-env" not in block
    assert "generate_semantic_decisions" not in block
    assert "semantic-model-decisions" not in block
    assert "eval-adversarial-v2-llm" not in block
    assert "semantic-gate-adversarial-v2-llm" not in block
    assert "regression_semantic_adversarial_v2_eval" not in block
    assert "_semantic_model_eval" not in block
    # It packages the tracked public-safe inputs via the v2 packager.
    assert "scripts/package_evidence_adversarial_v2_llm.py" in block
    assert (
        "--semantic-summary-json "
        "reports/llm_adversarial_v2_semantic_audit_summary.json" in block
    )
    assert (
        "--semantic-regressions "
        "case_studies/financial_links_reliability/evals/"
        "regressions_semantic_adversarial_v2.jsonl" in block
    )
    assert (
        "--semantic-replay-decisions "
        "case_studies/financial_links_reliability/evals/"
        "regressions_semantic_adversarial_v2_decisions.json" in block
    )


def test_v2_evidence_pack_target_is_not_a_prereq_of_v1() -> None:
    """The v1 pack target is unchanged: it must not gain a v2 dependency."""

    v1_block = _target_block("evidence-pack-adversarial-v1-llm")
    assert "adversarial_v2" not in v1_block
    assert "package_evidence_adversarial_v2_llm" not in v1_block
