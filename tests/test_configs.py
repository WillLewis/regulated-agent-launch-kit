"""Phase 2 config alignment tests.

Locks in the approval-matrix and latency-budget shape so the runtime
evaluator, offline graders, and dataset generators can rely on it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def approval_matrix() -> dict:
    return yaml.safe_load((ROOT / "configs" / "approval_matrix.yaml").read_text())


@pytest.fixture(scope="module")
def latency_budgets() -> dict:
    return yaml.safe_load((ROOT / "configs" / "latency_budgets.yaml").read_text())


@pytest.fixture(scope="module")
def launch_gates() -> dict:
    return yaml.safe_load((ROOT / "configs" / "launch_gates.yaml").read_text())


def test_approval_matrix_default_boundary_is_draft_only(approval_matrix: dict) -> None:
    assert approval_matrix["default_action_boundary"] == "draft_only"


def test_approval_matrix_has_l2_consent_sensitive_financial_links_rule(approval_matrix: dict) -> None:
    """PLAN.md R1: L2 consent-sensitive cases require explicit reconfirmation or approval."""

    matches = [
        rule
        for rule in approval_matrix["rules"]
        if rule.get("workflow") == "financial_links_reliability"
        and rule.get("risk_band") == "L2"
    ]
    assert matches, "expected an L2 financial_links_reliability rule"
    rule = matches[0]
    assert rule.get("consent_sensitive") is True
    assert rule.get("approval_required") is True
    assert rule.get("requires_consent_reconfirmation") is True


def test_approval_matrix_records_band_independent_grading(approval_matrix: dict) -> None:
    """PLAN.md R8: graders compute true required band independent of declared band."""

    rules = approval_matrix.get("evaluation_rules", {})
    assert rules.get("approval_band_independent_of_declared") is True


def test_approval_matrix_keeps_prohibited_actions(approval_matrix: dict) -> None:
    prohibited = set(approval_matrix.get("prohibited_actions", []))
    assert "force_completion_without_consent" in prohibited
    assert "execute_external_customer_action_without_approval" in prohibited


def test_latency_budgets_cover_all_risk_bands(latency_budgets: dict) -> None:
    bands = latency_budgets["risk_bands"]
    assert set(bands.keys()) == {"L0", "L1", "L2", "L3", "L4"}
    for name, budget in bands.items():
        assert "p50_ms" in budget, name
        assert "p95_ms" in budget, name
        assert budget["p50_ms"] > 0, name
        assert budget["p95_ms"] >= budget["p50_ms"], name


def test_latency_budgets_labeled_synthetic(latency_budgets: dict) -> None:
    """PLAN.md R4: synthetic label must be visible anywhere budgets surface."""

    assert latency_budgets.get("synthetic") is True
    note = (latency_budgets.get("note") or "").lower()
    assert "synthetic" in note or "not production" in note


def test_financial_links_policies_are_synthetic_and_present() -> None:
    path = ROOT / "case_studies" / "financial_links_reliability" / "policies" / "connectivity_policies.yaml"
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert data.get("synthetic") is True
    ids = {policy["id"] for policy in data.get("policies", [])}
    # consent re-confirmation, partner fallback permissions, stale-data copy safety
    assert "FL-CONSENT-001" in ids
    assert "FL-PARTNER-FALLBACK-002" in ids
    assert "FL-COPY-STALE-003" in ids


def test_launch_gates_config_header(launch_gates: dict) -> None:
    assert launch_gates["version"] == "launch_gates_v0"
    assert launch_gates["synthetic"] is True
    assert launch_gates["high_risk_bands"] == ["L3"]


def test_launch_gates_have_unique_ids_and_required_keys(launch_gates: dict) -> None:
    required = {
        "id",
        "description",
        "tier",
        "signal",
        "comparator",
        "threshold",
        "severity",
        "gating",
        "backing_artifact",
    }
    gates = launch_gates["gates"]
    ids = [gate["id"] for gate in gates]
    assert len(ids) == len(set(ids))
    for gate in gates:
        assert set(gate) == required, gate["id"]


def test_launch_gates_use_known_tiers(launch_gates: dict) -> None:
    known = {"ready", "constraints", "do_not_pilot"}
    assert {gate["tier"] for gate in launch_gates["gates"]} <= known


def test_launch_gates_do_not_pilot_tier_has_expected_ids(launch_gates: dict) -> None:
    expected = {
        "dnp_evaluator_miss_l3",
        "dnp_semantic_unsupported_claim_l3",
        "dnp_consent_grader_failure_l3",
        "dnp_redaction_coverage_below_80",
        "dnp_regression_failure_high_risk",
    }
    actual = {
        gate["id"]
        for gate in launch_gates["gates"]
        if gate["tier"] == "do_not_pilot"
    }
    assert actual == expected


def _backing_artifacts(gate: dict) -> list[str]:
    ba = gate["backing_artifact"]
    return [ba] if isinstance(ba, str) else list(ba)


def test_launch_gates_backing_artifact_discipline(launch_gates: dict) -> None:
    by_id = {gate["id"]: gate for gate in launch_gates["gates"]}

    # The L3 semantic blocker must read the TRACKED public audit summary,
    # never the gitignored semantic regression replay report.
    sem = _backing_artifacts(by_id["dnp_semantic_unsupported_claim_l3"])
    assert any("semantic_audit_summary" in p for p in sem), sem
    assert all("regression_semantic" not in p for p in sem), sem

    # Redaction coverage gates must cite PER-TRACE redaction reports, not
    # eval-report-level redaction reports (those legitimately show high
    # preserve_missing and would falsely tank coverage).
    for gate_id in ("dnp_redaction_coverage_below_80", "ready_redaction_coverage_95"):
        paths = _backing_artifacts(by_id[gate_id])
        assert all("traces/redacted" in p for p in paths), (gate_id, paths)
        assert all(not p.endswith("_eval.redaction_report.json") for p in paths), (gate_id, paths)


def test_launch_gates_risk_weighted_score_is_advisory(launch_gates: dict) -> None:
    gate = next(
        gate
        for gate in launch_gates["gates"]
        if gate["id"] == "ready_risk_weighted_score"
    )
    assert gate["gating"] is False
    assert gate["comparator"] == "advisory"
    assert gate["threshold"] is None
