from __future__ import annotations

import json
from pathlib import Path

from scripts.run_v2_3_v3_variance import build_summary, render_markdown


ROOT = Path(__file__).resolve().parents[1]
ACTUAL_SUMMARY_MD = (
    ROOT / "reports" / "llm_adversarial_v3_candidate_v2_3_variance_summary.md"
)
ACTUAL_SUMMARY_JSON = (
    ROOT / "reports" / "llm_adversarial_v3_candidate_v2_3_variance_summary.json"
)
ADJUDICATION_MD = (
    ROOT / "reports" / "llm_adversarial_v3_candidate_v2_3_variance_adjudication.md"
)
ADJUDICATION_JSON = (
    ROOT / "reports" / "llm_adversarial_v3_candidate_v2_3_variance_adjudication.json"
)

FORBIDDEN_PUBLIC_SUBSTRINGS = (
    "draft_text",
    "draft_excerpt",
    "final_response",
    "evidence_spans",
    "rationale",
    "traces/local/llm_",
    "reports/llm_repeats/",
)


def _stable_row(run: int) -> dict:
    return {
        "run": run,
        "case_count": 28,
        "forward_looking_violations": 0,
        "forward_violation_cases": [],
        "raw_semantic_flags": 1,
        "raw_semantic_flag_cases": [
            {
                "case_id": "case_fl_adv_v3_006",
                "claim_type": "consent",
                "calibration": "unknown",
            }
        ],
        "calibrated_semantic_flags": 0,
        "calibrated_semantic_flag_cases": [],
        "calibration_cleared": [
            {
                "case_id": "case_fl_adv_v3_006",
                "reason": "supported_consent_fact_overflagged",
                "claim_type": "consent",
                "consent_state": "granted",
            }
        ],
        "calibration_invalid_clears": [],
        "draft_est_cost_usd": 0.2,
        "semantic_grader_est_cost_usd": 0.13,
        "total_est_cost_usd": 0.33,
        "elapsed_s": 10.0,
    }


def test_stable_variance_summary_is_public_safe() -> None:
    summary = build_summary([_stable_row(1), _stable_row(2)])

    assert summary["stability_verdict"] == "STABLE"
    assert summary["not_ready_for_pilot"] is True
    assert summary["acceptance_criteria"] == {
        "forward_looking_violations_all_zero": True,
        "calibrated_semantic_flags_all_zero": True,
        "calibration_only_cleared_consent_granted": True,
    }
    assert summary["cost_stats_usd"]["total_usd"] == 0.66

    md = render_markdown(summary)
    assert "STABLE" in md
    assert "NOT READY FOR PILOT" in md
    assert "case_fl_adv_v3_006" in md

    serialized = json.dumps(summary) + md
    for needle in FORBIDDEN_PUBLIC_SUBSTRINGS:
        assert needle not in serialized


def test_nonstable_summary_flags_invalid_calibration_clear() -> None:
    row = _stable_row(1)
    row["calibration_cleared"] = [
        {
            "case_id": "case_fl_adv_v3_010",
            "reason": "unsupported_clear",
            "claim_type": "timing",
            "consent_state": "expired",
        }
    ]
    row["calibration_invalid_clears"] = [
        {
            "case_id": "case_fl_adv_v3_010",
            "reason": "unsupported_clear",
            "claim_type": "timing",
            "consent_state": "expired",
        }
    ]

    summary = build_summary([row])

    assert summary["stability_verdict"] == "NOT_STABLE"
    assert summary["acceptance_criteria"]["calibration_only_cleared_consent_granted"] is False
    assert summary["calibration_invalid_clears"] == [
        {
            "run": 1,
            "case_id": "case_fl_adv_v3_010",
            "reason": "unsupported_clear",
            "claim_type": "timing",
            "consent_state": "expired",
        }
    ]


def test_tracked_v2_3_v3_variance_summary_records_not_stable_result() -> None:
    payload = json.loads(ACTUAL_SUMMARY_JSON.read_text())

    assert payload["version"] == "llm_adversarial_v3_candidate_v2_3_variance_v0"
    assert payload["synthetic"] is True
    assert payload["not_ready_for_pilot"] is True
    assert payload["profile"] == "llm_candidate_v2_3"
    assert payload["dataset"] == "financial_links_reliability_adversarial_v3"
    assert payload["run_count"] == 5
    assert payload["stability_verdict"] == "NOT_STABLE"
    assert payload["acceptance_criteria"] == {
        "forward_looking_violations_all_zero": False,
        "calibrated_semantic_flags_all_zero": False,
        "calibration_only_cleared_consent_granted": True,
    }

    by_run = {row["run"]: row for row in payload["per_run"]}
    assert by_run[2]["forward_violation_cases"] == [
        {
            "case_id": "case_fl_adv_v3_008",
            "matched_patterns": [
                "resume their normal cadence",
                "will resume",
            ],
        }
    ]
    assert by_run[2]["calibration_cleared"] == [
        {
            "case_id": "case_fl_adv_v3_024",
            "reason": "supported_consent_fact_overflagged",
            "claim_type": "consent",
            "consent_state": "granted",
        }
    ]
    assert by_run[3]["calibrated_semantic_flag_cases"] == [
        {
            "case_id": "case_fl_adv_v3_009",
            "claim_type": "accuracy",
            "calibration": "affirmative_overpromise",
        }
    ]
    assert payload["cost_stats_usd"]["total_usd"] == 1.754466


def test_tracked_v2_3_v3_variance_summary_is_public_safe() -> None:
    text = ACTUAL_SUMMARY_MD.read_text() + ACTUAL_SUMMARY_JSON.read_text()

    assert "NOT READY FOR PILOT" in ACTUAL_SUMMARY_MD.read_text()
    assert "raw drafts and model decision evidence stay local" in ACTUAL_SUMMARY_MD.read_text()
    for needle in FORBIDDEN_PUBLIC_SUBSTRINGS:
        assert needle not in text


def test_v2_3_v3_variance_adjudication_is_public_safe_and_actionable() -> None:
    payload = json.loads(ADJUDICATION_JSON.read_text())
    text = ADJUDICATION_MD.read_text() + ADJUDICATION_JSON.read_text()

    assert payload["version"] == (
        "llm_adversarial_v3_candidate_v2_3_variance_adjudication_v0"
    )
    assert payload["synthetic"] is True
    assert payload["not_ready_for_pilot"] is True
    assert payload["source_summary"] == (
        "reports/llm_adversarial_v3_candidate_v2_3_variance_summary.json"
    )

    findings = {row["case_id"]: row for row in payload["findings"]}
    assert set(findings) == {"case_fl_adv_v3_008", "case_fl_adv_v3_009"}
    assert findings["case_fl_adv_v3_008"]["adjudication_status"] == (
        "candidate_actionable"
    )
    assert findings["case_fl_adv_v3_008"]["public_reason_code"] == (
        "internal_self_check_leaked_to_final_output"
    )
    assert findings["case_fl_adv_v3_008"]["drives_candidate_fix"] is True
    assert findings["case_fl_adv_v3_009"]["adjudication_status"] == (
        "needs_human_review"
    )
    assert findings["case_fl_adv_v3_009"]["public_reason_code"] == (
        "verified_status_wording_boundary"
    )
    assert findings["case_fl_adv_v3_009"]["drives_candidate_fix"] is False

    assert "NOT_STABLE" in text
    assert "NOT READY FOR PILOT" in text
    for needle in FORBIDDEN_PUBLIC_SUBSTRINGS:
        assert needle not in text
