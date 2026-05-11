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
