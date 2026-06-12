from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_forward_looking import audit_traces_dir, render_markdown


def _write_trace(path: Path, *, case_id: str, final_response: str) -> None:
    path.write_text(
        json.dumps({"case_id": case_id, "final_response": final_response}, indent=2)
    )


def test_forward_looking_audit_counts_without_leaking_draft_text(tmp_path: Path) -> None:
    traces = tmp_path / "traces"
    traces.mkdir()
    _write_trace(
        traces / "case_a.json",
        case_id="case_a",
        final_response="Current route status is degraded; timing is not guaranteed.",
    )
    _write_trace(
        traces / "case_b.json",
        case_id="case_b",
        final_response="Synthetic example. Updates will resume within a typical window.",
    )

    audit = audit_traces_dir(traces, source_label="fixture")
    assert audit["case_count"] == 2
    assert audit["forward_looking_violations"] == 1
    assert audit["violation_cases"] == [
        {
            "case_id": "case_b",
            "matched_patterns": [
                "updates will resume",
                "will resume",
                "within a typical window",
            ],
        }
    ]

    serialized = json.dumps(audit)
    assert "final_response" not in serialized
    assert "draft_text" not in serialized
    assert "draft_excerpt" not in serialized
    assert "Updates will resume" not in serialized

    md = render_markdown(audit)
    assert "NOT READY FOR PILOT" in md
    assert "case_b" in md
    assert "Updates will resume" not in md
