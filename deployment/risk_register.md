# Risk Register — Phase 1

> Synthetic deployment risks for the Financial Links flagship workflow. Severity uses the L0–L4 risk-band scale defined in `configs/risk_weights.yaml`. Each risk names a detection signal (a grader, evaluator check, or process artifact) so that the risk is observable, not aspirational.

## How to Read

- **Severity**: maximum L-band the risk could create if unmitigated.
- **Likelihood**: low / medium / high based on synthetic dataset coverage and known failure modes.
- **Detection signal**: the grader, evaluator check, dataset slice, or review process that should surface the risk in normal operation.
- **Owner**: synthetic role accountable for resolving the risk.
- **Open question**: outstanding decision the team needs to make.

## Risks

| # | Risk | Severity | Likelihood | Mitigation | Detection signal | Owner | Open question |
|---|---|---|---|---|---|---|---|
| R1 | Consent-sensitive case is misrouted or recommendation is drafted despite insufficient consent. | L3 | Medium | Consent-boundary grader; runtime EvaluatorNode consent check; approval gate on L3; consent-slice regression cases. | Consent grader fail; `CONSENT_BOUNDARY_VIOLATION` failure label. | Compliance reviewer | Should L2 cases also require explicit consent re-confirmation in copy? |
| R2 | EvaluatorNode misses an unsupported customer-facing claim before send. | L3 | Medium | Offline unsupported-claim grader; sampled human review of L2+ drafts; `EVALUATOR_MISS` failure label. | Evaluator catch-rate grader < target; `UNSAFE_CUSTOMER_COMMS` label. | Compliance reviewer | What sampling rate balances reviewer load vs detection? |
| R3 | Partner aggregator/config schema drifts and breaks tool calls or returns silent partial data. | L2 | Medium | Schema-validity grader; required-tool grader; pinned synthetic schema versions; trace metadata records `policy_version`. | `SCHEMA_VIOLATION` label; required-tool grader fail. | Deployment engineer | How often should synthetic schemas be intentionally drifted in regression cases? |
| R4 | Latency tax on routine cases erodes the speed gain claimed by H1 and hurts adoption. | L1 | Medium | Cost/latency grader by risk band; routing policy that uses cheaper config for L0–L1; latency budget per risk band in eval card. | `COST_LATENCY_REGRESSION` label; p95 latency by risk band > budget. | Product owner | What latency budget represents an acceptable analyst experience? |
| R5 | Over-escalation increases human review burden and partner support load. | L2 | High | Escalation-precision grader; over-escalation rate metric; tuning of risk-band thresholds. | `OVER_ESCALATION` label; escalation-precision drop in `improved_eval_run.json`. | Partner support lead | Which slice tolerates more over-escalation: copy-safety or root-cause? |
| R6 | Redaction loses too much diagnostic value, weakening public evidence packs. | L2 | Medium | Redaction-coverage report flags removed fields; redaction-evidence-reviewer subagent + Codex review checklist; preserve node/tool/evaluator/grader sequence per `configs/redaction_policy.yaml`. | `TRACE_REDACTION_GAP` label; reviewer cannot reproduce diagnosis from redacted trace. | Risk reviewer | Are there fields currently redacted that should be abstracted (kept in band form) instead? |
| R7 | Synthetic dataset realism is insufficient; eval scores create false confidence in pilot readiness. | L2 | High | Dataset card per workflow; human-owner review of dataset realism; explicit "synthetic-only" disclaimer in every public artifact and exec memo. | `DELIVERY_RISK_UNADDRESSED` label on otherwise-passing runs; reviewer flag during dataset card review. | Human owner | Is the dataset adversarial mix (15–25 cases) sufficient to stress-test L3 routing? |
| R8 | Misrouted high-risk case escapes evaluator and approval gates because of orchestrator misroute. | L3 | Low | Orchestrator routing grader; risk-band routing accuracy metric; approval gate keyed off declared risk band, so misroute compounds. | `ORCHESTRATOR_MISROUTE` co-occurring with `MISSED_ESCALATION`. | Deployment lead | Should approval gating be evaluated independently of orchestrator-declared risk band? |
| R9 | Handoff between orchestrator and specialist loses required state (e.g., consent context). | L2 | Medium | Handoff-completeness grader; structured handoff payload schema in `app/schemas.py`. | `HANDOFF_CONTEXT_LOSS` label; handoff grader fail. | Deployment engineer | Should handoff payload be a Pydantic model enforced at runtime, not just at trace time? |
| R10 | Public claim ("baseline → improved") is made without supporting artifact. | L2 | Medium | README/webpage claim audit by Codex review checklist (`AGENTS.md` Codex review responsibilities); `tests/test_deployment_artifacts.py` for placeholder discipline. | Reviewer flag during PR; deployment-readiness grader fail. | Deployment lead | Should there be an automated link-checker that maps each claim to an artifact path? |

## Phase-Specific Followups

- Add Pydantic enforcement for handoff payload (R9) before Phase 3 runner is written.
- Decide L2 consent re-confirmation policy (R1) before Phase 5 dataset finalization.
- Define latency budget by risk band (R4) before Phase 4 trace collector lands.
- Add link-check or claim-to-artifact map (R10) before Phase 12 webpage build.

## What This Register Is Not

- It is not a model risk management (MRM) document. The repo is synthetic. Severity bands here do not imply equivalent real-world impact.
- It is not exhaustive — it is a Phase 1 first pass intended to be expanded as evals surface new failure modes.
