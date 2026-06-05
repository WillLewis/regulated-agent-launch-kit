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
