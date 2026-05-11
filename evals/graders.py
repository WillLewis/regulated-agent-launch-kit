"""Offline graders for eval runs.

Each grader is a pure function over (case, trace_or_output) and returns a
``GraderResult`` with the shape required by ``AGENTS.md``:
``passed``, ``score``, ``severity``, ``failure_label``, ``explanation``,
``evidence``.

Graders are intentionally separate from ``app.evaluator`` so they can be
used to measure whether the runtime ``EvaluatorNode`` actually caught the
issues it was supposed to catch (the "evaluator catch-rate" grader).
"""

from __future__ import annotations

from typing import Any, Callable

from app.schemas import GraderResult, Severity


def grade_schema_validity(
    output: dict[str, Any],
    required_fields: list[str],
) -> GraderResult:
    """Offline schema-validity grader for trace post-processing."""

    missing = [field for field in required_fields if field not in output]
    passed = not missing
    return GraderResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        severity=Severity.L1 if passed else Severity.L2,
        failure_label=None if passed else "SCHEMA_VIOLATION",
        explanation=(
            "All required fields present."
            if passed
            else f"Missing required fields: {missing}"
        ),
        evidence={"required_fields": list(required_fields), "missing": missing},
    )


GRADERS: dict[str, Callable[..., GraderResult]] = {
    "schema_validity": grade_schema_validity,
}
