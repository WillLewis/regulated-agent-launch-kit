# Pilot Readiness Review — Financial Links Reliability (synthetic)

> Synthetic deployment-readiness review for the Financial Links flagship
> workflow. Every readiness claim below points to a generated artifact or a
> deployment doc; nothing here is hand-authored. Risk bands, policies, partner
> roles, and budgets are fabricated for this lab. This review makes **no**
> production-readiness, regulatory-compliance, model-safety, or partner claim.

**Verdict: NOT READY FOR PILOT — local synthetic vertical slice only.**

The deterministic Financial Links slice closes its planted-failure eval loop
(`reports/adversarial_v1_eval_card.md`: improved `12/12`), but an opt-in
model/NLI semantic audit surfaced unsupported-claim drafts that the deterministic
pipeline cleared (`reports/llm_adversarial_v1_semantic_audit_summary.md`: 3
semantic-only `UNSAFE_CUSTOMER_COMMS`, including one `L3`). That gap and the
narrow synthetic scope keep the slice pre-pilot. (The action-suspension
*mechanism* is now proven credential-free by the separate M9 harness — see
Blocked — but is not wired into the live `draft_only` loop.) This maps to the
`DO NOT PILOT` posture in `deployment/acceptance_criteria.md` rather than
`PILOT WITH CONSTRAINTS`.

## Ready

Internally demonstrable today on the synthetic Financial Links slice:

- **Mapped workflow + controlled architecture.** `deployment/customer_workflow_map.md`
  documents decision/approval points; the runner uses a controlled
  `Orchestrator → Specialist → Evaluator → HumanApproval` pattern (no autonomous
  swarm), per `deployment/acceptance_criteria.md` "System Behavior Acceptance".
- **Deterministic improvement closes the planted-failure loop.**
  `reports/adversarial_v1_eval_card.md`: `baseline_v0` `4/12` → `improved_v0`
  `12/12`; `required_tool_use` `0.42 → 1.00`, `unsupported_claim` `0.58 → 1.00`,
  `policy_retrieval` `0.92 → 1.00`; baseline labels `TOOL_MISUSE` 7 /
  `UNSAFE_CUSTOMER_COMMS` 5 / `POLICY_MISS` 1 → all `0`.
- **Runtime evaluator vs. offline graders are separate and measured.**
  `evaluator_catch_rate` `12/12` with `EVALUATOR_MISS` `0` in the deterministic
  run (same card).
- **Redacted, public-safe evidence exists.**
  `evidence_packs/financial_links_llm_adversarial_v1/` ships redacted summaries,
  redacted traces for both candidates, the aggregate-only semantic audit, and
  (under `regressions/`) the semantic regression seeds + credential-free replay
  fixture.
- **Incident-to-regression loop is wired.**
  `case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl`
  pins the 3 semantic-only failures as `pending_review` seeds; the offline
  semantic grader fires on all 3 with no credentials
  (`make regression-replay-adversarial-v1-semantic`).

## Blocked

Unresolved items that block any pilot conversation:

- **Narrow synthetic scope.** One workflow (Financial Links), 12 adversarial
  cases (`case_studies/financial_links_reliability/evals/adversarial_v1.jsonl`).
  `deployment/risk_register.md` R7 (synthetic-data false confidence) is
  unmitigated at this dataset size.
- **Semantic-only unsafe-comms findings are `pending_review` — and the M7
  credentialed run blocked the gate on the broader slice.** On the 12-case v1
  slice, 3 drafts the lexical `unsupported_claim` grader and runtime evaluator
  both cleared were flagged `UNSAFE_CUSTOMER_COMMS` by the model/NLI grader
  (`reports/llm_adversarial_v1_semantic_audit_summary.md`). The **M7 credentialed
  run on the 24-case v2 slice reproduced and widened this**: lexical `0/24`, but
  the model/NLI grader flagged **14 semantic-only `UNSAFE_CUSTOMER_COMMS`** (8 in
  `llm_candidate_v0`, 6 in `llm_candidate_v1`;
  `reports/llm_adversarial_v2_semantic_audit_summary.md`), so the semantic gate
  **blocked** and **M7 stays open**. All 14 are pinned as `pending_review`
  regression seeds (`regressions_semantic_adversarial_v2.jsonl`). This is a live,
  repeated instance of `risk_register.md` R2 (evaluator misses an unsupported
  claim); offline pass rates (`12/12`, `24/24`) are not a copy-safety guarantee.
- **Human-approval suspension proven in a harness, not wired into the live loop.**
  M9 (`app/action_suspension.py`) proves the mechanism credential-free: a real
  LangGraph interrupts before `HumanApprovalNode`, so a synthetic side-effecting
  action is **suspended before execution**, never executes on reject/missing
  approval (fail-closed), and executes **exactly once** when approved
  (`tests/test_action_suspension.py`; traces under
  `traces/local/action_suspension/`). But this is a *separate* synthetic harness:
  `configs/approval_matrix.yaml` is still `action_boundary: draft_only` for every
  FL rule, and the live Financial Links loop neither executes nor suspends a real
  action. Wiring the gate into a production action path (beyond `draft_only`)
  remains a product decision, not done here.
- **Latency/cost are local synthetic evidence only.** Credentialed LLM means are
  `L1` 8023 ms / `L2` 8866 ms / `L3` 9428 ms
  (`reports/llm_adversarial_v1_repeat_summary.md`), above the synthetic `L1`/`L2`
  planning envelopes in `configs/latency_budgets.yaml`; cost is a list-price
  estimate ($0.607305 across 10 runs), not a billing or partner-negotiated
  number. No production SLA exists.
- **Thin credentialed evidence + run-to-run variance.** The redacted candidate
  comparison in the evidence pack rests on one credentialed run per profile; the
  separate 10-run repeat summary shows passed counts ranging `7–12/12`
  (`reports/llm_adversarial_v1_repeat_summary.md`). One comparison run on 12
  synthetic cases cannot establish robustness.
- **No production or compliance claim is or may be made** from this slice.

## Pilot Only With Constraints

This section is **not yet reachable** — the Blocked items above must close first.
It records the constraints a future constrained internal pilot would carry, so
the bar is explicit in advance:

- 100% human review of every `L2`/`L3` and every consent-sensitive draft (the
  `draft_only` boundary already forces a human send).
- The model/NLI `unsupported_claim_semantic` grader promoted to a **blocking**
  offline gate in CI, with a sustained `0` semantic-only `UNSAFE_CUSTOMER_COMMS`
  across a materially larger dataset and multiple credentialed runs.
- A real action-suspension path exercised end-to-end (a side-effecting synthetic
  tool actually gated by `HumanApprovalNode`).
- Named latency/cost targets that are not the current synthetic envelopes.

Reaching this state would move the posture toward `PILOT WITH CONSTRAINTS` in
`deployment/acceptance_criteria.md`; it has not been reached.

## Approval Boundaries

Source of truth: `configs/approval_matrix.yaml` (`version: approval_matrix_v1`,
`default_action_boundary: draft_only`). Financial Links rules:

| Risk band | Approval required | Consent reconfirmation | Action boundary | Synthetic human owner |
|---|---|---|---|---|
| `L2` (consent-sensitive) | yes | yes | `draft_only` | `partner_support_analyst` |
| `L3` | yes | yes | `draft_only` | `partner_support_lead` |

- Approval-band evaluation is **independent of the orchestrator-declared band**
  (`evaluation_rules.approval_band_independent_of_declared: true`), addressing
  `risk_register.md` R8 (misroute compounding the gate).
- Prohibited actions are enforced as never-invoke:
  `force_completion_without_consent`, `guarantee_credit_approval`,
  `diagnose_identity_theft`, `confirm_insurance_coverage`,
  `execute_external_customer_action_without_approval`.
- **Caveat:** because every boundary is `draft_only`, these owners review and
  send drafts; no owner has yet suspended a live external action in this lab.

## Monitored Metrics

Each metric maps to a grader (`deployment/kpi_tree.md`) and a current source
artifact. Targets are synthetic.

| Metric | Grader / signal | Current (artifact) |
|---|---|---|
| Routing accuracy | orchestrator routing grader | improved selects `FinancialLinksReliabilityAgent` on the slice (`adversarial_v1_eval_card.md`) |
| Evaluator catch rate | `evaluator_catch_rate` | `12/12`, `EVALUATOR_MISS` `0` (deterministic card) |
| Unsupported-claim rate (lexical) | `unsupported_claim` | improved `12/12 (1.00)` (deterministic card) |
| Unsupported-claim rate (semantic) | `unsupported_claim_semantic` | 3 semantic-only flags (`semantic_audit_summary.md`); target `0` per the `acceptance_criteria.md` `DO NOT PILOT` gate |
| Approval-boundary adherence | `approval_boundary` | `12/12` (deterministic card) |
| Regression pass/fire | semantic regression replay | grader fires `3/3` on seeds (`make regression-replay-adversarial-v1-semantic`) |
| Latency by risk band | cost/latency grader | LLM means `L1/L2/L3` 8023/8866/9428 ms (`repeat_summary.md`) |
| Estimated cost | cost summary | $0.607305 / 10 runs, list-price (`repeat_summary.md`); excludes the one-time semantic-audit $0.148269 (`semantic_audit_summary.md`) |

## Rollback Conditions

Kill-switch conditions for any future constrained pilot. Any one trips a hold:

- `EVALUATOR_MISS` > 0 on an `L2`/`L3` case, **or** a new semantic-only
  `UNSAFE_CUSTOMER_COMMS` on a high-risk case (the current blocker, generalized).
- `approval_boundary` or consent-grader failure on any `L3` case
  (`acceptance_criteria.md` `DO NOT PILOT` gate).
- Orchestrator misroute on an `L3` case (`risk_register.md` R8).
- Redaction-coverage gap that prevents reproducing a diagnosis from a redacted
  trace (`risk_register.md` R6).
- Latency/cost regression beyond the agreed (non-synthetic) target, or a
  reviewer support-load regression (`risk_register.md` R4, R5).
- Any public artifact making a claim without a backing file
  (`risk_register.md` R10).
