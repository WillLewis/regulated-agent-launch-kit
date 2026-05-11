# Value Case — Financial Links Reliability Agent (synthetic)

> Defines the simulated business outcomes the agent is meant to improve, and ties each hypothesis to the evidence the eval system will produce. All numbers and outcomes here are synthetic; nothing in this document is a production claim.

## Business Outcomes

The Financial Links reliability workflow is the highest-volume, lowest-risk-bucket support workload for `Partner X` (synthetic). Improving it delivers four kinds of value:

1. **Resolution speed** — partner support analysts close routine connectivity tickets faster.
2. **Customer-communication safety** — drafts produced by the agent contain fewer unsupported claims, guarantees, or copy that exceeds the synthetic policy.
3. **Escalation correctness** — consent-sensitive and recurring cases route to the right human owner the first time, reducing churn between teams.
4. **Decision quality** — the deployment lead can recommend pilot/no-pilot from generated artifacts rather than analyst sentiment.

## Hypotheses

Stated as falsifiable, eval-measurable claims:

| ID | Hypothesis | Direction | Primary metric | Secondary metric |
|---|---|---|---|---|
| H1 | Routine `L0`–`L1` connectivity cases resolve faster end-to-end vs the analyst-only baseline. | Reduction | Triage-time proxy (`latency_ms` + reviewer correction rate) | Routing accuracy |
| H2 | Consent-sensitive cases (insufficient/expired/revoked scope) escalate correctly more often. | Improvement | Escalation recall on consent slice | Consent-boundary grader pass rate |
| H3 | Customer-facing draft copy carries fewer unsupported claims vs baseline. | Reduction | Unsupported-claim grader fail rate | Evaluator catch rate on copy-safety |
| H4 | p95 latency on routine cases stays within budget while higher-risk cases are routed through stronger checks. | Bounded | p95 latency by risk band | Cost per case |
| H5 | Partner-config issues self-resolve (correct escalation to partner-config team) without engineering involvement more often. | Improvement | Escalation precision on config slice | Over-escalation rate |

## Anti-Hypotheses (explicitly being tested)

- "Adding the agent reduces overall safety because evaluator misses outweigh analyst error." → tested by evaluator catch-rate grader and by sampling missed-escalation traces.
- "Latency tax wipes out the time savings." → tested by H4 cost/latency grader.
- "The agent sounds good but adds copy risk." → tested by H3 unsupported-claim grader plus reviewer-correction sampling.

## Evidence Required

Each hypothesis is acceptable only when backed by generated artifacts. None of the rows below may be hand-authored:

| Claim source | Required artifact |
|---|---|
| H1 resolution speed | `reports/baseline_eval_run.json` and `reports/improved_eval_run.json` with `latency_ms` per case + reviewer correction rate. |
| H2 escalation correctness | Consent-boundary grader and escalation-correctness grader output in `reports/`; failure summary slice for consent-sensitive cases. |
| H3 unsupported claims | Unsupported-claim grader output + at least one redacted trace under `traces/redacted/` showing baseline vs improved copy. |
| H4 latency | Cost/latency grader output by risk band in the eval card. |
| H5 escalation precision | Escalation-precision grader split by `partner_config` vs `engineering` slices. |
| Pilot recommendation | `reports/improved_eval_card.md` produced by `scripts/generate_eval_card.py`. |

## Out of Scope for the Public Demo

- Real partner identifiers, real loss amounts, or real institution data.
- Production thresholds for any metric — only synthetic targets.
- Any claim of regulatory compliance or production readiness.
- Real customer journeys, real fraud patterns, or SAR-adjacent reasoning.

## Decision This Document Supports

This value case is the input to the launch-readiness recommendation. The eval card produced in Phase 11 will reference these hypotheses by ID and report whether the evidence supports a `READY FOR INTERNAL PILOT`, `PILOT WITH CONSTRAINTS`, or `DO NOT PILOT` posture.
