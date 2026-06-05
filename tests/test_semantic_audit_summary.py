"""Tests for the public-safe model/NLI semantic audit summary.

These cover the pure aggregation in ``evals.semantic_audit`` and the
``scripts/summarize_semantic_audit_adversarial_v1_llm.py`` CLI. The central
guarantee under test is **public safety**: the audit summary is built from raw
decision files that quote draft spans, but the summary must carry only
aggregate counts — never the raw draft text, model reasoning, or quoted spans.
No credentials or network calls are involved; fixtures are built in-memory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.semantic_audit import (
    SEMANTIC_ADAPTER_NAME,
    assert_public_safe,
    build_profile_audit,
    build_semantic_audit_summary,
    lexical_unsupported_flags,
    render_markdown,
)
from scripts.summarize_semantic_audit_adversarial_v1_llm import summarize


# A marker standing in for raw model draft text quoted inside a decision's
# rationale / evidence spans. It must never reach the public summary.
RAW_DRAFT_MARKER = "RAW_DRAFT_the_balance_is_always_current_once_linked"


def _report(profile: str, *, lexical_flags: dict[str, bool]) -> dict[str, object]:
    """A minimal eval report whose per-case grader_results align positionally
    with a single ``unsupported_claim`` (lexical) grader."""

    per_case = []
    for case_id, flagged in lexical_flags.items():
        per_case.append(
            {
                "case_id": case_id,
                "workflow": "financial_links",
                "risk_band": "L3" if case_id.endswith("010") else "L1",
                "trace_path": f"traces/local/llm_adversarial_v1_{profile}/{case_id}.json",
                "grader_results": [{"passed": not flagged}],
                "failure_labels": [],
                "evaluator_all_ok": True,
                "approval_required": False,
                "passed": not flagged,
            }
        )
    return {
        "version": "local_eval_v0",
        "synthetic": True,
        "agent_system_version": profile,
        "dataset_path": "case_studies/financial_links_reliability/evals/adversarial_v1.jsonl",
        "case_count": len(per_case),
        "passed_case_count": sum(1 for c in per_case if c["passed"]),
        "failed_case_count": sum(1 for c in per_case if not c["passed"]),
        "aggregate_grader_pass_rates": [
            {"name": "unsupported_claim", "total": len(per_case), "passed": 0, "pass_rate": 0.0}
        ],
        "per_case": per_case,
    }


def _decision_file(
    profile: str,
    *,
    semantic_flags: dict[str, bool],
    cost: float = 0.04,
) -> dict[str, object]:
    """A decision file in the shape generate_semantic_decisions.py emits, with
    a RAW_DRAFT_MARKER planted in the draft-bearing fields of every decision."""

    decisions: dict[str, dict[str, object]] = {}
    metadata: dict[str, dict[str, object]] = {}
    for case_id, flagged in semantic_flags.items():
        decisions[case_id] = {
            "makes_unsupported_claim": flagged,
            "claim_type": "freshness" if flagged else "none",
            "confidence": 0.9,
            "rationale": f"The draft said {RAW_DRAFT_MARKER}" if flagged else "no claim",
            "evidence_spans": [RAW_DRAFT_MARKER] if flagged else [],
            "calibration": "affirmative_overpromise" if flagged else "safe_hedge",
        }
        metadata[case_id] = {
            "adapter": SEMANTIC_ADAPTER_NAME,
            "model": "claude-sonnet-4-5",
            "input_tokens": 100,
            "output_tokens": 20,
            "est_cost_usd": cost / max(len(semantic_flags), 1),
            "cost_estimation_note": "rate_used",
            "latency_ms": 5,
        }
    return {
        "version": "semantic_model_decisions_v0",
        "synthetic": True,
        "adapter": SEMANTIC_ADAPTER_NAME,
        "dataset_path": "case_studies/financial_links_reliability/evals/adversarial_v1.jsonl",
        "source_eval_report": f"reports/llm_adversarial_v1_{profile}_eval.json",
        "profile": profile,
        "note": "fixture",
        "decisions": {profile: decisions},
        "adapter_metadata": {profile: metadata},
        "summary": {
            "case_count": len(decisions),
            "unsupported_claim_true_count": sum(1 for f in semantic_flags.values() if f),
            "total_input_tokens": 100 * len(decisions),
            "total_output_tokens": 20 * len(decisions),
            "total_est_cost_usd": cost,
        },
    }


def _pair() -> list[tuple[dict[str, object], dict[str, object], str]]:
    # Lexical clears everything; semantic flags one case in v0 and two in v1 ->
    # all semantic flags are a lexical blind spot.
    v0_cases = {f"case_fl_adv_v1_{i:03d}": False for i in range(1, 13)}
    v1_cases = dict(v0_cases)
    sem_v0 = dict(v0_cases)
    sem_v0["case_fl_adv_v1_010"] = True
    sem_v1 = dict(v0_cases)
    sem_v1["case_fl_adv_v1_006"] = True
    sem_v1["case_fl_adv_v1_012"] = True
    return [
        (
            _report("llm_candidate_v0", lexical_flags=v0_cases),
            _decision_file("llm_candidate_v0", semantic_flags=sem_v0, cost=0.05),
            "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json",
        ),
        (
            _report("llm_candidate_v1", lexical_flags=v1_cases),
            _decision_file("llm_candidate_v1", semantic_flags=sem_v1, cost=0.06),
            "reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json",
        ),
    ]


def test_lexical_unsupported_flags_alignment() -> None:
    report = _report(
        "llm_candidate_v0",
        lexical_flags={"case_fl_adv_v1_001": True, "case_fl_adv_v1_002": False},
    )
    flags = lexical_unsupported_flags(report)
    assert flags == {"case_fl_adv_v1_001": True, "case_fl_adv_v1_002": False}


def test_summary_excludes_raw_draft_text_and_draft_keys() -> None:
    summary = build_semantic_audit_summary(_pair())
    blob = json.dumps(summary)
    assert RAW_DRAFT_MARKER not in blob, "summary leaked raw draft text"
    assert "rationale" not in blob
    assert "evidence_spans" not in blob
    # provenance paths must not be raw trace dirs
    assert "traces/local/llm_" not in blob


def test_summary_counts_and_lexical_blind_spot() -> None:
    summary = build_semantic_audit_summary(_pair())
    totals = summary["totals"]
    assert totals["total_semantic_unsafe_customer_comms"] == 3
    # lexical cleared every draft, so every semantic flag is a blind spot
    assert totals["total_lexical_unsupported_flags"] == 0
    assert totals["total_semantic_only_flags"] == 3
    assert totals["abstention_or_error_count"] == 0
    assert totals["total_semantic_judge_cost_usd"] == pytest.approx(0.11, abs=1e-6)

    v0 = summary["profiles"][0]
    assert v0["semantic"]["unsafe_customer_comms_count"] == 1
    assert v0["semantic"]["flagged_case_ids"] == ["case_fl_adv_v1_010"]
    assert v0["semantic"]["flagged_case_risk_bands"]["case_fl_adv_v1_010"] == "L3"
    assert v0["lexical_vs_semantic"]["semantic_only_flag"] == 1
    assert v0["lexical_vs_semantic"]["both_flag"] == 0


def test_build_profile_audit_rejects_profile_mismatch() -> None:
    report = _report("llm_candidate_v0", lexical_flags={"case_fl_adv_v1_001": False})
    decisions = _decision_file("llm_candidate_v1", semantic_flags={"case_fl_adv_v1_001": False})
    with pytest.raises(ValueError, match="does not match"):
        build_profile_audit(report, decisions)


def test_build_profile_audit_rejects_case_id_mismatch() -> None:
    report = _report("llm_candidate_v0", lexical_flags={"case_fl_adv_v1_001": False})
    decisions = _decision_file("llm_candidate_v0", semantic_flags={"case_fl_adv_v1_999": False})
    with pytest.raises(ValueError, match="case IDs do not match"):
        build_profile_audit(report, decisions)


def test_assert_public_safe_rejects_draft_bearing_key() -> None:
    with pytest.raises(ValueError, match="draft-bearing key"):
        assert_public_safe({"profiles": [{"evidence_spans": ["leak"]}]})


def test_assert_public_safe_rejects_raw_trace_path() -> None:
    with pytest.raises(ValueError, match="traces/local/llm_"):
        assert_public_safe({"note": "see traces/local/llm_candidate_v0/x.json"})


def test_render_markdown_is_public_safe_and_pre_pilot() -> None:
    summary = build_semantic_audit_summary(_pair())
    md = render_markdown(summary)
    assert "NOT READY FOR PILOT" in md
    assert RAW_DRAFT_MARKER not in md
    assert "rationale" not in md
    assert "evidence_spans" not in md
    assert "traces/local/llm_" not in md
    assert "lexical blind spot" in md.lower()
    # affirmative readiness overclaims must be absent
    for forbidden in ("production ready", "production-ready", "pilot ready", "pilot-ready"):
        assert forbidden not in md.lower()


def test_summarize_cli_writes_public_safe_artifacts(tmp_path: Path) -> None:
    report_v0, dec_v0, _ = _pair()[0]
    report_v1, dec_v1, _ = _pair()[1]
    rv0 = tmp_path / "v0_report.json"
    rv1 = tmp_path / "v1_report.json"
    dv0 = tmp_path / "v0_decisions.json"
    dv1 = tmp_path / "v1_decisions.json"
    rv0.write_text(json.dumps(report_v0))
    rv1.write_text(json.dumps(report_v1))
    dv0.write_text(json.dumps(dec_v0))
    dv1.write_text(json.dumps(dec_v1))
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    summarize(
        report_v0=rv0,
        report_v1=rv1,
        decisions_v0=dv0,
        decisions_v1=dv1,
        out_json=out_json,
        out_md=out_md,
    )

    assert out_json.exists() and out_md.exists()
    for path in (out_json, out_md):
        text = path.read_text()
        assert RAW_DRAFT_MARKER not in text
        assert "evidence_spans" not in text
    payload = json.loads(out_json.read_text())
    assert payload["totals"]["total_semantic_unsafe_customer_comms"] == 3
