# Adoption Plan — Financial Links Reliability (synthetic)

> Synthetic adoption plan for the Financial Links flagship workflow. Roles are
> fabricated synthetic personas drawn from `configs/approval_matrix.yaml` and
> `deployment/risk_register.md`; no real team, partner, or customer is described.
> Adoption is **pre-pilot and hypothetical** until the blockers in
> `deployment/pilot_readiness_review.md` close. No production or compliance claim
> is made.

## Pilot Users

Synthetic stakeholder roles and their review responsibilities:

| Role | Source | Responsibility |
|---|---|---|
| `partner_support_analyst` | `configs/approval_matrix.yaml` (`L2` consent-sensitive owner) | Reviews and sends `L2`/consent-sensitive drafts; reconfirms consent before send; files copy corrections as incidents. |
| `partner_support_lead` | `configs/approval_matrix.yaml` (`L3` owner) | Approves/sends `L3` drafts; owns escalation-precision and over-escalation review (`risk_register.md` R5). |
| `compliance_reviewer` | `risk_register.md` R1/R2 owner | Samples `L2`+ copy for unsupported claims and consent-boundary adherence; owns the semantic-grader blind-spot follow-up. |
| Deployment lead | `risk_register.md` R8/R10 owner | Owns the launch/no-launch posture and claim-to-artifact traceability. |
| Risk reviewer | `risk_register.md` R6 owner | Confirms redacted evidence packs preserve diagnostic value without leaking draft text. |

## Onboarding

How a synthetic reviewer comes up to speed and operates:

1. **Read the posture first.** `deployment/pilot_readiness_review.md` (verdict +
   blockers) and `deployment/exec_update.md` (current state).
2. **Inspect redacted traces, never raw.** Work only from
   `evidence_packs/financial_links_llm_adversarial_v1/` (redacted traces +
   per-trace redaction reports); the raw local LLM trace directories are
   gitignored and out of bounds.
3. **Read the eval cards as the metric source.**
   `reports/adversarial_v1_eval_card.md` (deterministic Before/After) and
   `reports/llm_adversarial_v1_repeat_summary.md` (variance). Reviewers do not
   hand-author numbers.
4. **Review drafts at the approval gate.** Every `L2`/`L3` draft is `draft_only`,
   so the owner in `configs/approval_matrix.yaml` reads the draft + cited policy
   and approves the send; prohibited actions are never offered.
5. **Report failure modes into the regression loop.** A bad draft becomes a
   `pending_review` seed via the incident-to-regression path — the worked example
   is `case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl`.

## Operating Cadence

| Cadence | Activity | Inputs / outputs |
|---|---|---|
| Weekly | Eval review | Read latest `reports/adversarial_v1_eval_card.md` + `reports/llm_adversarial_v1_repeat_summary.md`; note metric movement and variance. |
| Weekly | Regression intake | Triage `pending_review` semantic seeds; confirm the offline grader still fires (`make regression-replay-adversarial-v1-semantic`). |
| Bi-weekly | Risk-register update | Update `deployment/risk_register.md` likelihood/status as evals surface new failure modes (e.g., R2 now has a concrete instance). |
| Per change / milestone | Executive status | Refresh `deployment/exec_update.md` (status, metric movement, top risk, decision, recommendation, next milestone). |

## Adoption Risks

| Risk | Why it matters here | Mitigation / signal |
|---|---|---|
| Reviewer **trust** erodes if blind spots surface late | The semantic audit found 3 `UNSAFE_CUSTOMER_COMMS` the deterministic pipeline cleared | Surface the semantic gap in every readiness doc; keep seeds `pending_review`, not silently closed. |
| **Latency** tax hurts the analyst experience | LLM means 8–9.4 s/case (`repeat_summary.md`) exceed synthetic `L1`/`L2` envelopes | `risk_register.md` R4 cost/latency grader; set non-synthetic targets before pilot. |
| **Reviewer load** from 100% draft review | `draft_only` means every `L2`/`L3` draft needs a human send | `risk_register.md` R5 over-escalation metric; tune escalation precision. |
| **Unclear ownership** of the blind-spot fix | The semantic gap spans eval + model behavior | Named owner (`compliance_reviewer`) in the table above. |
| **Evidence readability** vs. redaction | Redaction must not strip diagnostic value | `risk_register.md` R6; redaction reports list removed/abstracted/preserved fields. |
