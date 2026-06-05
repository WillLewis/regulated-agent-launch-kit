"""Tests for the adversarial v1 (12-case) LLM evidence pack assembler.

The pack is the only public-safe surface for the credentialed
``llm_candidate_v0`` (Before) → ``llm_candidate_v1`` (After) comparison on
the adversarial v1 slice. These tests verify the assembler:

1. abstracts raw model draft text out of BOTH candidate eval reports;
2. ships redacted traces for BOTH candidates;
3. carries the synthetic-only / NOT READY FOR PILOT disclaimer;
4. never ships a raw ``traces/local/llm_*`` path or a file sourced from one.

No credentials or network calls are involved — the fixtures are built in
``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.package_evidence_adversarial_v1_llm import (
    EVIDENCE_PACK_VERSION,
    package_adversarial_v1_llm_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "configs" / "redaction_policy.yaml"

RAW_DRAFT_MARKER = "RAW_MODEL_DRAFT_the_data_is_real_time_once_linked"


def _raw_report(profile: str) -> dict[str, object]:
    """A minimal but realistic raw eval report that embeds raw draft text
    in the exact fields the redaction policy is supposed to abstract."""

    return {
        "version": "local_eval_v0",
        "synthetic": True,
        "agent_system_version": profile,
        "dataset_path": (
            "case_studies/financial_links_reliability/evals/adversarial_v1.jsonl"
        ),
        "case_count": 1,
        "passed_case_count": 1,
        "failed_case_count": 0,
        "aggregate_grader_pass_rates": [
            {"name": "unsupported_claim", "total": 1, "passed": 1, "pass_rate": 1.0}
        ],
        "synthetic_latency_envelope": {
            "measured_ms": {
                "note": "Wall-clock latency for the deterministic runner only."
            }
        },
        "synthetic_cost_summary": {
            "note": "Cost is a deterministic 0.0 placeholder.",
            "total_est_cost_usd": 0.001,
            "per_case_count": 1,
        },
        "per_case": [
            {
                "case_id": "case_fl_adv_v1_001",
                "workflow": "financial_links",
                "risk_band": "L1",
                "trace_path": (
                    f"traces/local/llm_adversarial_v1_{profile}/"
                    "case_fl_adv_v1_001.json"
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
def pack(tmp_path: Path) -> Path:
    raw_v0 = tmp_path / "candidate_v0_eval.json"
    raw_v1 = tmp_path / "candidate_v1_eval.json"
    raw_v0.write_text(json.dumps(_raw_report("candidate_v0")))
    raw_v1.write_text(json.dumps(_raw_report("candidate_v1")))

    card = tmp_path / "card.md"
    card.write_text(
        "# Before/After\nllm_candidate_v0 vs llm_candidate_v1\n"
        "NOT READY FOR PILOT\n"
    )

    redacted_dirs: dict[str, Path] = {}
    for cand in ("candidate_v0", "candidate_v1"):
        d = tmp_path / f"redacted_{cand}"
        d.mkdir()
        (d / "case_fl_adv_v1_001.redacted.json").write_text(
            json.dumps(
                {"case_id": "case_fl_adv_v1_001", "draft_text": "<draft_text_abstracted>"}
            )
        )
        (d / "case_fl_adv_v1_001.redaction_report.json").write_text(
            json.dumps({"version": "redaction_report_v0"})
        )
        redacted_dirs[cand] = d

    out = tmp_path / "pack"
    return package_adversarial_v1_llm_evidence(
        raw_v0_report=raw_v0,
        raw_v1_report=raw_v1,
        eval_card=card,
        redacted_traces_v0=redacted_dirs["candidate_v0"],
        redacted_traces_v1=redacted_dirs["candidate_v1"],
        policy=POLICY,
        out=out,
    )


def test_pack_readme_is_synthetic_and_not_ready_for_pilot(pack: Path) -> None:
    readme = (pack / "README.md").read_text()
    assert "NOT READY FOR PILOT" in readme
    lower = readme.lower()
    assert "synthetic" in lower
    assert "12-case" in readme
    # No *affirmative* readiness/safety claims. (The launch-posture line
    # legitimately negates "regulatory compliant" / "production grade", so
    # we only ban phrases that would appear if the pack actually overclaimed.)
    for forbidden in (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "model is safe",
        "safe to deploy",
    ):
        assert forbidden not in lower, f"pack README overclaims: {forbidden!r}"
    # The launch posture must explicitly disclaim robustness from one run.
    assert "robust" in lower


def test_pack_abstracts_raw_draft_text_from_both_reports(pack: Path) -> None:
    for rel in (
        "llm_candidate_v0_eval.redacted.json",
        "llm_candidate_v1_eval.redacted.json",
    ):
        blob = (pack / rel).read_text()
        assert RAW_DRAFT_MARKER not in blob, (
            f"{rel} leaked raw model draft text"
        )
        assert "<draft_text_abstracted>" in blob, (
            f"{rel} missing the abstraction placeholder"
        )


def test_pack_ships_redacted_traces_for_both_candidates(pack: Path) -> None:
    assert (
        pack / "traces" / "redacted" / "candidate_v0" / "case_fl_adv_v1_001.redacted.json"
    ).exists()
    assert (
        pack / "traces" / "redacted" / "candidate_v1" / "case_fl_adv_v1_001.redacted.json"
    ).exists()


def test_pack_rewrites_eval_summary_trace_paths_to_redacted_pack_paths(
    pack: Path,
) -> None:
    for rel, candidate in (
        ("llm_candidate_v0_eval.redacted.json", "candidate_v0"),
        ("llm_candidate_v1_eval.redacted.json", "candidate_v1"),
    ):
        payload = json.loads((pack / rel).read_text())
        trace_path = payload["per_case"][0]["trace_path"]
        assert trace_path == (
            f"traces/redacted/{candidate}/case_fl_adv_v1_001.redacted.json"
        )
        assert "traces/local/llm_" not in trace_path


def test_pack_rewrites_stale_deterministic_cost_and_latency_notes(pack: Path) -> None:
    payload = json.loads((pack / "llm_candidate_v0_eval.redacted.json").read_text())
    cost_note = payload["synthetic_cost_summary"]["note"]
    latency_note = payload["synthetic_latency_envelope"]["measured_ms"]["note"]
    assert "credential-gated LLM trace metadata" in cost_note
    assert "deterministic 0.0 placeholder" not in cost_note
    assert "including credential-gated LLM" in latency_note
    assert "deterministic runner only" not in latency_note


def test_pack_manifest_has_no_raw_local_paths(pack: Path) -> None:
    manifest = json.loads((pack / "manifest.json").read_text())
    assert manifest["version"] == EVIDENCE_PACK_VERSION
    assert manifest["synthetic"] is True
    for entry in manifest["files"]:
        assert not entry["path"].startswith("traces/local/"), entry
        assert "traces/local/llm_" not in entry.get("source", ""), entry


def test_pack_refuses_raw_trace_source(tmp_path: Path) -> None:
    """Defense-in-depth: a redacted-trace dir whose *.redacted.json was
    (mis)placed under a raw traces/local/llm_ path must be refused. We
    simulate this by pointing the assembler at inputs that resolve to a
    raw-LLM source location for the eval reports."""

    raw = tmp_path / "traces" / "local" / "llm_adversarial_v1_candidate_v0"
    raw.mkdir(parents=True)
    report = raw / "candidate_v0_eval.json"
    report.write_text(json.dumps(_raw_report("candidate_v0")))
    raw_v1 = tmp_path / "candidate_v1_eval.json"
    raw_v1.write_text(json.dumps(_raw_report("candidate_v1")))
    card = tmp_path / "card.md"
    card.write_text("NOT READY FOR PILOT\n")
    for cand in ("candidate_v0", "candidate_v1"):
        d = tmp_path / f"redacted_{cand}"
        d.mkdir()
        (d / "case.redacted.json").write_text("{}")

    with pytest.raises(SystemExit) as exc:
        package_adversarial_v1_llm_evidence(
            raw_v0_report=report,  # sourced from traces/local/llm_*
            raw_v1_report=raw_v1,
            eval_card=card,
            redacted_traces_v0=tmp_path / "redacted_candidate_v0",
            redacted_traces_v1=tmp_path / "redacted_candidate_v1",
            policy=POLICY,
            out=tmp_path / "pack",
        )
    assert "raw-LLM trace dir" in str(exc.value)


# --- Optional aggregate-only model/NLI semantic audit artifacts --------------

SEMANTIC_DRAFT_MARKER = "RAW_DECISION_SPAN_the_balance_updates_instantly_guaranteed"


def _raw_report_with_lexical_grader(profile: str) -> dict[str, object]:
    """Like ``_raw_report`` but with a per-case grader result aligned to the
    single ``unsupported_claim`` grader, so the semantic aggregation can read
    lexical pass/fail. Lexical passes (clears the draft)."""

    report = _raw_report(profile)
    report["per_case"][0]["grader_results"] = [
        {
            "passed": True,
            "score": 1.0,
            "severity": "L2",
            "failure_label": None,
            "explanation": "lexical grader cleared the draft",
            "evidence": {},
        }
    ]
    return report


def _semantic_decision_file(profile: str, *, makes_claim: bool) -> dict[str, object]:
    """A decision file in generate_semantic_decisions.py shape, with a
    SEMANTIC_DRAFT_MARKER planted in the draft-bearing fields."""

    case_id = "case_fl_adv_v1_001"
    return {
        "version": "semantic_model_decisions_v0",
        "synthetic": True,
        "adapter": "anthropic_nli_semantic_v0",
        "dataset_path": (
            "case_studies/financial_links_reliability/evals/adversarial_v1.jsonl"
        ),
        "source_eval_report": f"reports/llm_adversarial_v1_{profile}_eval.json",
        "profile": profile,
        "note": "fixture",
        "decisions": {
            profile: {
                case_id: {
                    "makes_unsupported_claim": makes_claim,
                    "claim_type": "freshness" if makes_claim else "none",
                    "confidence": 0.9,
                    "rationale": f"quotes {SEMANTIC_DRAFT_MARKER}",
                    "evidence_spans": [SEMANTIC_DRAFT_MARKER] if makes_claim else [],
                    "calibration": (
                        "affirmative_overpromise" if makes_claim else "safe_hedge"
                    ),
                }
            }
        },
        "adapter_metadata": {
            profile: {
                case_id: {
                    "adapter": "anthropic_nli_semantic_v0",
                    "model": "claude-sonnet-4-5",
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "est_cost_usd": 0.01,
                    "cost_estimation_note": "rate_used",
                    "latency_ms": 5,
                }
            }
        },
        "summary": {
            "case_count": 1,
            "unsupported_claim_true_count": 1 if makes_claim else 0,
            "total_input_tokens": 100,
            "total_output_tokens": 20,
            "total_est_cost_usd": 0.01,
        },
    }


@pytest.fixture()
def semantic_pack(tmp_path: Path) -> Path:
    raw_v0 = tmp_path / "candidate_v0_eval.json"
    raw_v1 = tmp_path / "candidate_v1_eval.json"
    raw_v0.write_text(json.dumps(_raw_report_with_lexical_grader("candidate_v0")))
    raw_v1.write_text(json.dumps(_raw_report_with_lexical_grader("candidate_v1")))

    card = tmp_path / "card.md"
    card.write_text("# Before/After\nNOT READY FOR PILOT\n")

    redacted_dirs: dict[str, Path] = {}
    for cand in ("candidate_v0", "candidate_v1"):
        d = tmp_path / f"redacted_{cand}"
        d.mkdir()
        (d / "case_fl_adv_v1_001.redacted.json").write_text(
            json.dumps(
                {"case_id": "case_fl_adv_v1_001", "draft_text": "<draft_text_abstracted>"}
            )
        )
        (d / "case_fl_adv_v1_001.redaction_report.json").write_text(
            json.dumps({"version": "redaction_report_v0"})
        )
        redacted_dirs[cand] = d

    dv0 = tmp_path / "decisions_v0.json"
    dv1 = tmp_path / "decisions_v1.json"
    # Lexical cleared both; semantic flags candidate_v0 only -> lexical blind spot.
    dv0.write_text(json.dumps(_semantic_decision_file("candidate_v0", makes_claim=True)))
    dv1.write_text(json.dumps(_semantic_decision_file("candidate_v1", makes_claim=False)))

    summary_md = tmp_path / "semantic_audit_summary.md"
    summary_md.write_text(
        "# Model/NLI Semantic Audit\nNOT READY FOR PILOT\nlexical blind spot\n"
    )

    out = tmp_path / "pack"
    return package_adversarial_v1_llm_evidence(
        raw_v0_report=raw_v0,
        raw_v1_report=raw_v1,
        eval_card=card,
        redacted_traces_v0=redacted_dirs["candidate_v0"],
        redacted_traces_v1=redacted_dirs["candidate_v1"],
        policy=POLICY,
        out=out,
        semantic_decisions_v0=dv0,
        semantic_decisions_v1=dv1,
        semantic_summary=summary_md,
    )


def test_semantic_pack_ships_aggregate_only(semantic_pack: Path) -> None:
    agg_path = semantic_pack / "semantic_audit_aggregate.json"
    assert agg_path.exists()
    blob = agg_path.read_text()
    assert SEMANTIC_DRAFT_MARKER not in blob, "aggregate leaked a quoted draft span"
    assert "rationale" not in blob
    assert "evidence_spans" not in blob
    payload = json.loads(blob)
    assert payload["totals"]["total_semantic_unsafe_customer_comms"] == 1
    # lexical cleared every draft, so the one semantic flag is a blind spot
    assert payload["totals"]["total_semantic_only_flags"] == 1


def test_semantic_pack_copies_summary_markdown(semantic_pack: Path) -> None:
    md = semantic_pack / "semantic_audit_summary.md"
    assert md.exists()
    assert "NOT READY FOR PILOT" in md.read_text()


def test_semantic_pack_never_ships_raw_decision_payload(semantic_pack: Path) -> None:
    names = [p.name for p in semantic_pack.rglob("*") if p.is_file()]
    assert "decisions_v0.json" not in names
    assert "decisions_v1.json" not in names
    for path in semantic_pack.rglob("*"):
        if path.is_file():
            assert SEMANTIC_DRAFT_MARKER not in path.read_text(errors="ignore"), path


def test_semantic_pack_manifest_records_aggregate_and_summary(
    semantic_pack: Path,
) -> None:
    manifest = json.loads((semantic_pack / "manifest.json").read_text())
    paths = {e["path"] for e in manifest["files"]}
    assert "semantic_audit_aggregate.json" in paths
    assert "semantic_audit_summary.md" in paths
    for entry in manifest["files"]:
        assert "traces/local/llm_" not in entry.get("source", ""), entry


def test_pack_requires_both_semantic_decision_files(tmp_path: Path) -> None:
    raw_v0 = tmp_path / "candidate_v0_eval.json"
    raw_v1 = tmp_path / "candidate_v1_eval.json"
    raw_v0.write_text(json.dumps(_raw_report_with_lexical_grader("candidate_v0")))
    raw_v1.write_text(json.dumps(_raw_report_with_lexical_grader("candidate_v1")))
    card = tmp_path / "card.md"
    card.write_text("NOT READY FOR PILOT\n")
    redacted_dirs: dict[str, Path] = {}
    for cand in ("candidate_v0", "candidate_v1"):
        d = tmp_path / f"redacted_{cand}"
        d.mkdir()
        (d / "case_fl_adv_v1_001.redacted.json").write_text(json.dumps({"case_id": "x"}))
        redacted_dirs[cand] = d
    dv0 = tmp_path / "decisions_v0.json"
    dv0.write_text(json.dumps(_semantic_decision_file("candidate_v0", makes_claim=True)))

    with pytest.raises(SystemExit) as exc:
        package_adversarial_v1_llm_evidence(
            raw_v0_report=raw_v0,
            raw_v1_report=raw_v1,
            eval_card=card,
            redacted_traces_v0=redacted_dirs["candidate_v0"],
            redacted_traces_v1=redacted_dirs["candidate_v1"],
            policy=POLICY,
            out=tmp_path / "pack",
            semantic_decisions_v0=dv0,  # only one -> error
        )
    assert "both --semantic-decisions-v0 and --semantic-decisions-v1" in str(exc.value)


def test_base_pack_has_no_semantic_artifacts(pack: Path) -> None:
    """Backward compatibility: omitting the semantic flags ships no semantic
    artifacts."""

    assert not (pack / "semantic_audit_aggregate.json").exists()
    assert not (pack / "semantic_audit_summary.md").exists()
