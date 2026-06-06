"""Deterministic synthetic side-effecting tool for the M9 action-suspension gate.

The Financial Links proof loop is ``draft_only`` — the agent never executes a
user-impacting action. M9 adds a *separate* synthetic harness that proves a
side-effecting action can be **suspended before execution** and gated on a human
approval decision. This module holds the one synthetic action that harness can
"execute".

It is deliberately inert: it never calls an external API, never touches a real
partner, customer, institution, or aggregator, and writes no real state. It only
returns a synthetic evidence dict. The *side effect* a test observes is recorded
by the gate (an execution record), not by this function reaching outside the
process. Nothing here implies a real action, production control, or readiness.
"""

from __future__ import annotations

from typing import Any

SYNTHETIC_ACTION_TYPE = "synthetic_relink"


def execute_synthetic_relink_action(
    action_id: str,
    synthetic_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return synthetic evidence that a relink action 'ran'. No external call.

    This is the only function the M9 gate may invoke on the approved path, and
    the gate guarantees it runs at most once per action. It is a pure function
    of its inputs (deterministic), so the same action_id always yields the same
    synthetic evidence.
    """

    return {
        "action_id": action_id,
        "action_type": SYNTHETIC_ACTION_TYPE,
        "status": "completed",
        "synthetic": True,
        "synthetic_result": (
            "Synthetic relink recorded for analyst review. No external system, "
            "partner, customer, or aggregator was contacted; this is a fabricated "
            "deployment-readiness example, not a real action."
        ),
        "args": dict(synthetic_args or {}),
        "external_call_made": False,
    }
