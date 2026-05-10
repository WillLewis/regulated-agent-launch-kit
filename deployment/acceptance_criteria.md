# Acceptance Criteria

## System Behavior

- Synthetic cases route through a controlled orchestrator/specialist/evaluator pattern.
- The evaluator checks schema, policy, consent, approval, and customer-communication constraints before final output.
- Human approval is required for configured high-risk actions.

## Eval Behavior

- Deterministic graders cover routing, tools, policy retrieval, consent, approval, escalation, schema validity, unsupported claims, hallucinated facts, evaluator catch rate, cost/latency, regressions, and deployment readiness.
- Eval reports include pass/fail, score, severity, failure label, explanation, and evidence.

## Artifact Behavior

- Claims in README and webpage are backed by generated reports, traces, redacted evidence, or deployment docs.
- Raw traces and private thesis context are not committed.
- Redacted traces preserve diagnostic structure while removing sensitive operational detail.
