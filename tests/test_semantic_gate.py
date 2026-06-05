"""Tests for the reusable credential-free semantic blocking gate (M7a).

``scripts/check_semantic_gate.py`` promotes the offline
``unsupported_claim_semantic`` grader from an optional reporting lane into a
blocking gate over an eval report. These tests verify:

1. a clean semantic report passes (exit 0);
2. a report with semantic failures fails (exit 1) and names the failing
   ``case_id`` / ``failure_label`` values;
3. a report missing the semantic grader fails **closed** (exit 1) unless
   ``--allow-missing`` is given;
4. the gate uses no credentials / no model / no network;
5. the default deterministic eval report has no semantic grader, so the gate
   correctly refuses to "pass" it (the default proof loop is unchanged);
6. the gate works on the tracked fixture-backed semantic reports.

Everything here is deterministic and credential-free.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_semantic_gate import (
    SEMANTIC_GRADER,
    evaluate_semantic_gate,
)

ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = ROOT / "scripts" / "check_semantic_gate.py"
SEMANTIC_FAILURE_LABEL = "UNSAFE_CUSTOMER_COMMS"

# Grader order used by the synthetic fixtures — semantic is intentionally NOT
# first, so the positional index logic is actually exercised.
_GRADER_ORDER = [
    "schema_validity",
    "unsupported_claim",
    SEMANTIC_GRADER,
    "evaluator_catch_rate",
]


def _grader_result(passed: bool, label: str | None = None) -> dict:
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "severity": "L1" if passed else "L2",
        "failure_label": label,
        "explanation": "clean" if passed else "semantic decision flagged the draft",
        "evidence": {},
    }


def _report(case_semantic_pass: dict[str, bool], *, include_semantic: bool = True) -> dict:
    """Build a minimal eval report. ``case_semantic_pass`` maps case_id -> whether
    that case PASSED the semantic grader."""

    names = [
        n
        for n in _GRADER_ORDER
        if include_semantic or n != SEMANTIC_GRADER
    ]
    per_case: list[dict] = []
    sem_passed = 0
    for cid, sem_ok in case_semantic_pass.items():
        results = []
        for n in names:
            if n == SEMANTIC_GRADER:
                results.append(
                    _grader_result(sem_ok, None if sem_ok else SEMANTIC_FAILURE_LABEL)
                )
            else:
                results.append(_grader_result(True))
        per_case.append({"case_id": cid, "grader_results": results})
        if sem_ok:
            sem_passed += 1

    n_cases = len(case_semantic_pass)
    rates = []
    for n in names:
        passed = sem_passed if n == SEMANTIC_GRADER else n_cases
        rates.append(
            {
                "name": n,
                "total": n_cases,
                "passed": passed,
                "pass_rate": (passed / n_cases) if n_cases else 0.0,
            }
        )
    return {
        "version": "local_eval_v0",
        "synthetic": True,
        "aggregate_grader_pass_rates": rates,
        "per_case": per_case,
    }


# --- Pure-function behavior --------------------------------------------------


def test_clean_semantic_report_passes() -> None:
    report = _report({"c1": True, "c2": True, "c3": True})
    result = evaluate_semantic_gate(report)
    assert result.present is True
    assert result.passed is True
    assert result.failing == []
    assert result.total == 3
    assert result.passed_count == 3


def test_semantic_failures_fail_and_identify_cases() -> None:
    report = _report({"c1": True, "c2": False, "c3": False})
    result = evaluate_semantic_gate(report)
    assert result.passed is False
    failing_ids = {f["case_id"] for f in result.failing}
    assert failing_ids == {"c2", "c3"}
    assert all(f["failure_label"] == SEMANTIC_FAILURE_LABEL for f in result.failing)
    assert result.passed_count == result.total - len(result.failing)
    # The human-readable messages must surface the failing case IDs.
    blob = "\n".join(result.messages)
    assert "c2" in blob and "c3" in blob
    assert SEMANTIC_FAILURE_LABEL in blob


def test_gate_output_carries_no_draft_bearing_fields() -> None:
    """Public-safety: the gate must not lift the semantic decision's
    ``rationale`` / ``evidence_spans`` (draft-bearing on a real credentialed
    report) into its failing entries or printed messages — only case_id and
    failure_label."""

    marker = "RAW_DRAFT_the_balance_updates_instantly_guaranteed"
    report = _report({"c1": False})
    sem_idx = [
        r["name"] for r in report["aggregate_grader_pass_rates"]
    ].index(SEMANTIC_GRADER)
    sem_result = report["per_case"][0]["grader_results"][sem_idx]
    # Plant draft-bearing content as a real credentialed semantic report would.
    sem_result["explanation"] = f"semantic decision quoted: {marker}"
    sem_result["evidence"] = {"rationale": marker, "evidence_spans": [marker]}

    result = evaluate_semantic_gate(report)
    assert result.passed is False
    blob = json.dumps(result.failing) + "\n".join(result.messages)
    assert marker not in blob, "gate leaked draft-bearing content into its output"
    assert "rationale" not in blob
    assert "evidence_spans" not in blob
    # It still surfaces the actionable fields.
    assert "c1" in blob and SEMANTIC_FAILURE_LABEL in blob


def test_missing_semantic_grader_fails_closed() -> None:
    report = _report({"c1": True, "c2": True}, include_semantic=False)
    result = evaluate_semantic_gate(report)
    assert result.present is False
    assert result.passed is False, "absent semantic grader must fail closed by default"
    assert any("fail-closed" in m.lower() for m in result.messages)


def test_allow_missing_downgrades_absence_to_warning() -> None:
    report = _report({"c1": True}, include_semantic=False)
    result = evaluate_semantic_gate(report, allow_missing=True)
    assert result.present is False
    assert result.passed is True
    assert any("allow-missing" in m.lower() for m in result.messages)


def test_allow_missing_does_not_pass_a_present_but_failing_report() -> None:
    """--allow-missing only excuses ABSENCE; a present-but-failing semantic lane
    must still block."""

    report = _report({"c1": False})
    result = evaluate_semantic_gate(report, allow_missing=True)
    assert result.present is True
    assert result.passed is False


def test_fails_closed_when_aggregate_reports_failures_without_per_case_detail() -> None:
    """Defensive: a malformed report whose aggregate row says cases failed but
    whose per_case detail is missing must not slip through as a pass."""

    report = _report({"c1": True, "c2": True})
    # Corrupt: aggregate says 1 of 2 semantic cases failed, but per_case shows
    # both passing (detail gap).
    for row in report["aggregate_grader_pass_rates"]:
        if row["name"] == SEMANTIC_GRADER:
            row["passed"] = 1
    result = evaluate_semantic_gate(report)
    assert result.passed is False
    assert any("more failing" in m.lower() for m in result.messages)


# --- CLI exit codes ----------------------------------------------------------


def _run_gate(report: dict, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report))
    return subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--report", str(report_path), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exit_zero_on_clean_report(tmp_path: Path) -> None:
    proc = _run_gate(_report({"c1": True, "c2": True}), tmp_path)
    assert proc.returncode == 0, proc.stderr


def test_cli_exit_one_and_lists_cases_on_failure(tmp_path: Path) -> None:
    proc = _run_gate(_report({"c1": False, "c2": True}), tmp_path)
    assert proc.returncode == 1
    assert "c1" in proc.stderr
    assert SEMANTIC_FAILURE_LABEL in proc.stderr


def test_cli_exit_one_when_missing_then_zero_with_allow_missing(tmp_path: Path) -> None:
    missing = _report({"c1": True}, include_semantic=False)
    assert _run_gate(missing, tmp_path).returncode == 1
    assert _run_gate(missing, tmp_path, "--allow-missing").returncode == 0


def test_cli_fails_on_missing_report_file() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--report", "does/not/exist.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "not found" in proc.stderr.lower()


# --- No credentials / no model / no network ----------------------------------


def test_gate_script_uses_no_credentials_or_network() -> None:
    """Static guard: the gate must not import a model SDK, an HTTP client, or
    read a provider credential. It only reads a JSON report."""

    source = GATE_SCRIPT.read_text()
    lowered = source.lower()
    for forbidden in ("anthropic", "openai", "requests", "urllib", "httpx", "socket"):
        assert forbidden not in lowered, f"gate must not reference {forbidden!r}"
    for cred in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "getenv", "environ"):
        assert cred not in source, f"gate must not read credentials ({cred!r})"
    # Importing the gate must not pull a model SDK into the process — this also
    # covers the imported ``evals.semantic_audit`` staying credential-free.
    import importlib
    import sys as _sys

    importlib.import_module("scripts.check_semantic_gate")
    assert "anthropic" not in _sys.modules
    assert "openai" not in _sys.modules


# --- Default deterministic eval has no semantic grader (proof loop unchanged) -


def test_default_grader_names_exclude_semantic() -> None:
    """Task 5: unsupported_claim_semantic must NOT be in the default grader set
    or the GRADERS registry — both are the "default reports unchanged" guarantee."""

    from evals.graders import GRADERS
    from evals.run import _GRADER_NAMES

    assert SEMANTIC_GRADER not in _GRADER_NAMES
    assert SEMANTIC_GRADER not in GRADERS


def test_gate_fails_closed_on_a_fresh_default_eval_report(tmp_path: Path) -> None:
    """A default (no --semantic-decisions) deterministic eval report has no
    semantic grader, so the gate fails closed on it — and passes only with the
    explicit --allow-missing escape hatch. Credential-free."""

    from evals.run import run_eval

    dataset = (
        ROOT
        / "case_studies"
        / "financial_links_reliability"
        / "evals"
        / "adversarial_v2.jsonl"
    )
    report = run_eval(
        dataset_path=dataset,
        traces_out=tmp_path / "traces",
        report_out=tmp_path / "report.json",
        agent_system_version="improved_v0",
    )
    payload = report.model_dump(mode="json")
    assert evaluate_semantic_gate(payload).passed is False
    assert evaluate_semantic_gate(payload, allow_missing=True).passed is True


# --- Tracked fixture-backed semantic reports ---------------------------------


def test_gate_passes_on_tracked_clean_improved_semantic_report() -> None:
    """The hand-authored synthetic fixture authors improved_v0 as all-clean, so
    its tracked semantic report clears the gate. This proves the gate's pass
    path on a real on-disk artifact — not model safety or pilot readiness."""

    path = ROOT / "reports" / "improved_adversarial_v1_semantic_eval.json"
    if not path.exists():
        pytest.skip("tracked improved semantic report not present")
    result = evaluate_semantic_gate(json.loads(path.read_text()))
    assert result.present is True
    assert result.passed is True


def test_gate_blocks_tracked_baseline_semantic_report() -> None:
    """The baseline semantic fixture plants affirmative overpromises, so its
    tracked report must be blocked by the gate (a real-artifact negative case)."""

    path = ROOT / "reports" / "baseline_adversarial_v1_semantic_eval.json"
    if not path.exists():
        pytest.skip("tracked baseline semantic report not present")
    result = evaluate_semantic_gate(json.loads(path.read_text()))
    assert result.present is True
    assert result.passed is False
    assert result.failing, "baseline semantic report should surface flagged cases"
    assert all(
        f["failure_label"] == SEMANTIC_FAILURE_LABEL for f in result.failing
    )
