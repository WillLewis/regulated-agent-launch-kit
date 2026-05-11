# KPI Tree

> Connects each Phase 1 business outcome to operational KPIs, agent metrics, and safety metrics. Every leaf metric maps to at least one grader so movement in the tree is observable from generated reports, not narrative.

## Hypothesis ↔ Metric Map

This tree refers to hypothesis IDs (`H1`–`H5`) defined in `deployment/value_case.md`. Every leaf metric must be emitted by a grader or evaluator check so the eval card can render it without hand-authored numbers.

---

## Outcome 1 — Faster Partner-Support Resolution (H1, H5)

```
Faster resolution
├── Operational KPI
│   ├── Triage-time proxy (per case, by risk band)
│   ├── Reviewer correction rate (drafts edited before send)
│   └── Escalation precision (config vs engineering vs none)
├── Agent metric
│   ├── Orchestrator routing accuracy
│   ├── Required-tool use (was the right synthetic tool called?)
│   └── Handoff completeness (did the specialist get sufficient state?)
└── Safety metric
    ├── Consent-boundary adherence
    ├── Unsupported-claim rate in routine drafts
    └── Over-escalation rate (routine cases sent to engineering)
```

Mapped graders: routing grader, required-tool grader, handoff-completeness grader, consent grader, escalation-precision grader, cost/latency grader.

## Outcome 2 — Safer Customer Communication (H3)

```
Safer customer comms
├── Operational KPI
│   ├── Reviewer correction rate on copy
│   └── Human approval queue depth and turnaround
├── Agent metric
│   ├── EvaluatorNode catch rate on copy-safety checks
│   └── Prohibited-action avoidance rate
└── Safety metric
    ├── Unsupported-claim grader fail rate
    ├── Hallucinated-fact grader fail rate
    └── `UNSAFE_CUSTOMER_COMMS` failure label frequency
```

Mapped graders: unsupported-claim grader, hallucinated-fact grader, evaluator catch-rate grader, prohibited-action grader.

## Outcome 3 — Right Escalation, First Time (H2, H5)

```
Right escalation
├── Operational KPI
│   ├── Escalation recall (high-risk cases that should escalate, did)
│   ├── Escalation precision (escalated cases that needed to be)
│   └── Mean turnaround per escalation slice
├── Agent metric
│   ├── Risk-band routing accuracy
│   └── Approval-boundary adherence (per `configs/approval_matrix.yaml`)
└── Safety metric
    ├── Consent-boundary grader pass rate on consent-sensitive slice
    └── `MISSED_ESCALATION` failure label frequency
```

Mapped graders: escalation-correctness grader, approval-boundary grader, consent grader, risk-weighted scoring.

## Outcome 4 — Pilot Decision Quality (H1–H5 aggregate)

```
Pilot decision quality
├── Operational KPI
│   ├── Launch recommendation traceability (each claim → artifact)
│   └── Blocker clarity (named owners + acceptance conditions)
├── Agent metric
│   ├── Regression pass rate
│   └── Risk-weighted score (cases × risk band weight per `configs/risk_weights.yaml`)
└── Safety metric
    ├── Redaction coverage (% of trace fields covered by `configs/redaction_policy.yaml`)
    └── Public-safe evidence completeness (every README/webpage claim → artifact path)
```

Mapped graders: regression grader, deployment-readiness grader, redaction-coverage check.

## Operating Constraints

- p95 latency budget: defined per risk band in `configs/`. Synthetic numbers only — no production thresholds.
- Cost budget: per case and per eval run, reported in `reports/eval_run.json`.
- Quality floor below which pilot is blocked: `DO NOT PILOT` if any L3 case fails consent grader or evaluator misses an unsupported claim (see `deployment/acceptance_criteria.md`).

## Reading This Tree

A leaf metric without a mapped grader is a gap. Phase 6 (graders implementation) treats this tree as the authoritative grader checklist; any leaf that is not covered must be added to the grader plan or removed from the tree.
