# Customer Workflow Map — Financial Links / Connectivity Reliability

> Synthetic embedded-finance workflow used to scope agent automation, evaluator coverage, and human-approval boundaries. No real partner, institution, or end-user data is referenced anywhere in this document.

## Customer Profile (synthetic)

The simulated customer is `Partner X`, a fictional embedded-finance partner that has integrated linked-account data into a consumer-facing product (e.g., digital banking, expense tracking, credit health, or budgeting categories). End users link bank or brokerage accounts via a synthetic aggregator service. The partner's support team triages reliability tickets when end users report problems with linking, refresh, or feature availability.

## Current Manual Workflow

1. End user files a support ticket via the partner's app or web channel.
2. Partner support analyst receives the ticket and inspects synthetic logs:
   - linking attempt status,
   - last successful refresh,
   - aggregator route status,
   - reported user-facing symptom.
3. Analyst manually consults synthetic policy docs to classify the root cause:
   - `consent_state` insufficient, expired, or revoked,
   - aggregator route degraded or unavailable,
   - partner config (institution not enabled, scope mismatch),
   - institution metadata stale (rebrand, deprecated route),
   - stale data only (refresh delay, no error).
4. Analyst drafts customer-facing copy, decides on escalation, or closes as known limitation.
5. Partner support lead reviews ambiguous, consent-sensitive, or recurring cases.
6. Engineering and partner-config teams handle escalations.

## Pain Points

- **Triage time variance**: similar synthetic cases take 10–60 minutes depending on analyst familiarity.
- **Inconsistent policy retrieval**: analysts work from notes or analyst memory rather than the current synthetic policy version.
- **Consent state missed**: insufficient-scope cases are often misdiagnosed as aggregator failure, leading to wasted engineering escalations.
- **Over-escalation**: routine partner-config issues are escalated to engineering, increasing on-call load.
- **Inconsistent customer-facing copy**: language occasionally implies guarantees that the synthetic policy does not support (e.g., "your account will refresh within X minutes").
- **Audit gaps**: no structured trace of which policy version informed the recommendation.

## Users and Stakeholders (synthetic roles)

| Role | Concern |
|---|---|
| Partner support analyst | Triage speed, copy quality |
| Partner support lead | Escalation correctness, consent-sensitive case sign-off |
| Deployment engineer | Aggregator + partner-config root-cause |
| Embedded-finance product owner | Workflow definition, prioritization, dataset realism |
| Compliance reviewer | Customer-communication safety, consent boundaries |
| Risk reviewer | Failure taxonomy quality, redaction sign-off |
| Executive sponsor | Pilot/no-pilot decision and ROI accountability |
| Synthetic end user | Outcome only — never directly served by the agent without human approval at L2+ |

## Systems Touched (synthetic)

- `aggregator_health_monitor` — synthetic tool returning route status per institution.
- `partner_config_store` — synthetic policy: enabled institutions, scopes, fallback rules per partner.
- `consent_ledger` — synthetic policy: per-user consent scope and expiry.
- `institution_metadata_index` — synthetic tool: institution name (synthetic), status, alternate routes.
- `ticket_workflow` — synthetic surface where the agent posts drafts for human approval.
- `trace_store` — local JSON traces plus optional Braintrust persistence.

## Decision Points

1. **Routing** — `OrchestratorAgent` selects `FinancialLinksReliabilityAgent` based on intake symptoms.
2. **Consent sufficiency** — does the user's `consent_state` cover the requested diagnosis or remediation? Insufficient scope must block automated remediation and surface a re-prompt recommendation only.
3. **Root-cause classification** — aggregator route vs partner config vs institution metadata vs stale data only.
4. **Recommendation type** — copy template, engineering escalation, partner-config escalation, consent re-prompt, or close-as-known-limit.
5. **Risk-band assignment** — derived from impact, consent sensitivity, and customer-facing exposure (`L0`–`L4` per `configs/risk_weights.yaml`).

## Approval Points

Per `configs/approval_matrix.yaml`:

| Risk band | Action boundary | Approver |
|---|---|---|
| L0 / L1 (routine, low partner impact) | Draft only; auto-send permitted only if explicitly enabled per partner | None or sampled review |
| L2 (consent-adjacent, customer-comm sensitive) | Draft only; reviewed before send | Partner support analyst |
| L3 (consent re-prompt, recurring failure, copy that approaches policy edge) | Draft only; held for approval | `partner_support_lead` |
| L4 (do-not-automate path for this public synthetic system) | Agent must escalate without drafting | Human owner |

Default action boundary across the system: `draft_only`.

## Prohibited Actions

Per `configs/approval_matrix.yaml`, `FinancialLinksReliabilityAgent` must never:

- `force_completion_without_consent` — drive remediation when `consent_state` is `expired`, `revoked`, or `insufficient`.
- Execute any external customer action (e.g., trigger a re-link attempt on the user's behalf) without explicit human approval.
- Imply guaranteed timing, success, or coverage in customer-facing copy.

## Future-State Agent-Assisted Workflow

```
Synthetic ticket
  → IntakeNormalizer (parse symptoms, identifiers, stated user goal)
  → OrchestratorAgent (route → FinancialLinksReliabilityAgent)
  → FinancialLinksReliabilityAgent (call synthetic tools + retrieve synthetic policy)
  → EvaluatorNode (schema, consent, policy, prohibited-action, copy-safety checks)
  → HumanApprovalNode (when risk band ≥ L3 or evaluator flags)
  → FinalResponseComposer (synthesize draft for ticket workflow)
  → trace + offline graders + redacted evidence
```

The agent always drafts; it never sends. Human approval is preserved at every action boundary defined in the approval matrix.

## Human-Owned Work (does not automate)

- Final sign-off on consent re-prompt copy (L3+).
- Decisions about partner-config policy changes.
- Engineering root-cause investigation when `aggregator_health_monitor` reports degraded.
- Failure taxonomy curation and regression-case approval.
- Pilot/no-pilot decision based on the eval card.
- All customer communications classified as L4.

## Public-Safety Boundaries

- All identifiers, partner names, institution names, consent records, route names, and policy IDs in this workflow are **synthetic**.
- No real fraud typologies, real bureau schemas, real partner configurations, real loss amounts, or SAR-adjacent facts are introduced.
- The workflow does **not** imply regulatory compliance or production readiness; it is a deployment-readiness lab.
