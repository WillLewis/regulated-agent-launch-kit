"""Runtime EvaluatorNode for the LangGraph multi-agent system.

This module is intentionally separate from ``evals.graders``:

- ``EvaluatorNode`` runs **inline** before the final response is composed
  and decides whether to block, escalate, or allow the output. It returns
  ``EvaluatorReport`` / ``EvaluatorCheck``.
- Offline graders run **after** a trace is complete and produce
  ``GraderResult`` objects for eval reports.

Mixing the two creates an evaluator that cannot be honestly graded.
See the "Evaluator and grader separation" non-negotiable in ``AGENTS.md``.
"""

from __future__ import annotations

from typing import Any

from app.schemas import EvaluatorCheck, EvaluatorReport


def schema_check(output: dict[str, Any], required_fields: list[str]) -> EvaluatorCheck:
    """Verify required fields are present in an agent output draft."""

    missing = [field for field in required_fields if field not in output]
    return EvaluatorCheck(
        name="schema_required_fields",
        ok=not missing,
        reason=None if not missing else f"missing required fields: {missing}",
        metadata={"required_fields": list(required_fields), "missing": missing},
    )


def evaluate(
    output: dict[str, Any],
    required_fields: list[str] | None = None,
) -> EvaluatorReport:
    """Run all runtime checks against an agent's draft output.

    Returns an ``EvaluatorReport``. Does **not** return ``GraderResult`` —
    that shape is reserved for offline graders in ``evals.graders``.
    """

    checks: list[EvaluatorCheck] = []
    if required_fields is not None:
        checks.append(schema_check(output, required_fields))
    return EvaluatorReport(checks=checks)
