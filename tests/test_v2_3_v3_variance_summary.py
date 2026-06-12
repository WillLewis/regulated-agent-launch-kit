from __future__ import annotations

import json

from scripts.run_v2_3_v3_variance import build_summary, render_markdown


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
