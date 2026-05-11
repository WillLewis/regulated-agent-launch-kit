"""Pydantic schemas for the regulated-agent-launch-kit.

Locks in the contract between two intentionally distinct surfaces:

- Runtime: `app.evaluator` emits ``EvaluatorCheck`` / ``EvaluatorReport``
  before the final response is composed.
- Offline: ``evals.graders`` emit ``GraderResult`` after a trace completes.

Keeping these as separate types prevents the runtime evaluator from being
silently swapped for offline grading (or vice versa). See the
"Evaluator and grader separation" non-negotiable in ``AGENTS.md``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskBand(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class Severity(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class Case(BaseModel):
    case_id: str
    workflow: str
    risk_band: RiskBand
    payload: dict[str, Any] = Field(default_factory=dict)


class EvaluatorCheck(BaseModel):
    """Single inline check produced by the runtime EvaluatorNode."""

    name: str
    ok: bool
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluatorReport(BaseModel):
    """Bundle of EvaluatorChecks from one runtime EvaluatorNode invocation."""

    checks: list[EvaluatorCheck] = Field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(check.ok for check in self.checks)


class GraderResult(BaseModel):
    """Offline grader output. Shape is fixed by ``AGENTS.md``."""

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    failure_label: str | None = None
    explanation: str
    evidence: dict[str, Any] = Field(default_factory=dict)
