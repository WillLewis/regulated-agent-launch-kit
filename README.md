# Regulated AI Deployment Kit

This is a synthetic deployment-readiness case study for a regulated embedded-finance AI workflow.

It is built for third-party review: the useful question is not "can I fork this?"
but "does the repo show how a high-risk AI deployment is mapped, measured,
redacted, and held at a launch gate with evidence?"

## Review Verdict

**NOT READY FOR PILOT.** The current computed launch decision is
`DO_NOT_PILOT`, generated from committed synthetic artifacts by
[`reports/launch_decision.md`](reports/launch_decision.md).

The main blocker is semantic unsupported-claim risk. The deterministic Financial
Links workflow closes its planted-failure loop, but credentialed model/NLI audit
and held-out variance checks still show unresolved instability:

- [`deployment/pilot_readiness_review.md`](deployment/pilot_readiness_review.md)
  records the current launch-governance posture and blockers.
- [`reports/launch_decision.md`](reports/launch_decision.md) computes the
  current `DO_NOT_PILOT` decision from launch gates.
- [`reports/llm_adversarial_v3_candidate_v2_3_variance_summary.md`](reports/llm_adversarial_v3_candidate_v2_3_variance_summary.md)
  records the latest held-out v3 repeat result as `NOT_STABLE`.
- [`reports/grader_gold_reliability.md`](reports/grader_gold_reliability.md)
  records one small-N grader reliability measurement for the semantic judge.

This repo makes no claim of model safety, regulatory compliance, partner
approval, customer launch readiness, or production behavior.

## What This Is

- A public-safe, synthetic case study for launch governance in regulated AI.
- A controlled multi-agent workflow with runtime evaluator checks, offline
  graders, local traces, redaction, evidence packs, and launch-gate aggregation.
- A Financial Links reliability slice with deterministic baseline/improved
  profiles and opt-in credentialed LLM candidate profiles.
- A repository of generated evidence: eval cards, regression seeds, redacted
  traces, semantic audit summaries, and deployment-review documents.

## What This Is Not

- Not a generic agent demo.
- Not a reusable production framework.
- Not a compliance package.
- Not based on real customer data, real fraud patterns, real thresholds, real
  partner configuration, real credit attributes, or real vendor schemas.
- Not optimized for external contributors or forks; the README is a map for
  reviewers first.

## Fast Reader Path

Start here if you are reviewing the project cold:

1. [`deployment/customer_workflow_map.md`](deployment/customer_workflow_map.md)
   explains the synthetic Financial Links workflow and approval boundaries.
2. [`deployment/pilot_readiness_review.md`](deployment/pilot_readiness_review.md)
   gives the current ready/blocked assessment.
3. [`reports/launch_decision.md`](reports/launch_decision.md) shows the computed
   launch gate decision.
4. [`reports/adversarial_v2_eval_card.md`](reports/adversarial_v2_eval_card.md)
   shows the deterministic planted-failure loop on the broader synthetic slice.
5. [`reports/llm_adversarial_v2_semantic_failure_analysis.md`](reports/llm_adversarial_v2_semantic_failure_analysis.md)
   explains the semantic failure mode that kept M7 open.
6. [`reports/llm_adversarial_v3_candidate_v2_3_variance_summary.md`](reports/llm_adversarial_v3_candidate_v2_3_variance_summary.md)
   shows why the latest candidate is still not stable.
7. [`evidence_packs/financial_links_llm_adversarial_v2/README.md`](evidence_packs/financial_links_llm_adversarial_v2/README.md)
   is the public-safe evidence pack for the blocked M7 run.

## Current Evidence Snapshot

| Area | Current evidence | Reader takeaway |
|---|---|---|
| Workflow mapping | [`deployment/customer_workflow_map.md`](deployment/customer_workflow_map.md), [`deployment/value_case.md`](deployment/value_case.md), [`deployment/kpi_tree.md`](deployment/kpi_tree.md) | The workflow, value hypothesis, and measurable KPIs are defined before automation. |
| Deterministic proof loop | [`reports/v0_eval_card.md`](reports/v0_eval_card.md), [`reports/adversarial_v1_eval_card.md`](reports/adversarial_v1_eval_card.md), [`reports/adversarial_v2_eval_card.md`](reports/adversarial_v2_eval_card.md) | Planted deterministic failures are detected, converted into regressions, and cleared by the improved profile. |
| Semantic safety gap | [`reports/llm_adversarial_v2_semantic_audit_summary.md`](reports/llm_adversarial_v2_semantic_audit_summary.md), [`reports/llm_adversarial_v2_semantic_failure_analysis.md`](reports/llm_adversarial_v2_semantic_failure_analysis.md) | Lexical and deterministic checks were not enough; semantic unsupported-claim risk remained. |
| Regression loop | [`case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl`](case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl), [`case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2_decisions.json`](case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2_decisions.json) | Semantic failures are pinned into credential-free replay fixtures. |
| Redacted evidence | [`evidence_packs/README.md`](evidence_packs/README.md), [`evidence_packs/financial_links_v0/README.md`](evidence_packs/financial_links_v0/README.md), [`evidence_packs/financial_links_llm_adversarial_v2/README.md`](evidence_packs/financial_links_llm_adversarial_v2/README.md) | Public evidence preserves sequence and grader results while removing raw sensitive text. |
| Launch decision | [`configs/launch_gates.yaml`](configs/launch_gates.yaml), [`evals/launch_decision.py`](evals/launch_decision.py), [`reports/launch_decision.md`](reports/launch_decision.md) | The launch posture is computed from evidence, not hand-stamped prose. |

## Architecture

The controlled workflow target is:

```text
Synthetic case
  -> IntakeNormalizer
  -> OrchestratorAgent
  -> Specialist agent
  -> Synthetic tools and policy retrieval
  -> EvaluatorNode
  -> HumanApprovalNode when required
  -> FinalResponseComposer
  -> Trace and eval artifacts
```

[`app/graph.py`](app/graph.py) is the canonical Financial Links execution path.
It is a real `langgraph.graph.StateGraph` wiring the named nodes above.
[`app/runner.py`](app/runner.py) invokes the compiled graph, and local eval
scripts run through that path.

The primary implemented specialist is the
`FinancialLinksReliabilityAgent`. The Credit Wellness and Privacy/Identity
workflow folders exist as future expansion surfaces; they are not the evidence
authority for the current launch posture.

## Synthetic Domain Model

The runtime and eval layers share explicit contracts in
[`app/schemas.py`](app/schemas.py). Everything below is synthetic and public-safe.

### Synthetic Case

A `Case` is the orchestrator input. It carries the workflow, ground-truth risk
band, consent sensitivity, and synthetic payload fields. Offline graders use
the case's ground-truth risk and consent fields so an agent-declared lower risk
band cannot weaken scoring.

```python
Case(
    case_id="case_l2_consent_001",
    workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
    risk_band=RiskBand.L2,
    consent_sensitive=True,
    payload={"user_id": "user_synth_002", "institution_id": "inst_synth_002"},
)
```

### Handoff Payload

`HandoffPayload` is the runtime case state passed from orchestration to the
specialist. Pydantic enforces required consent, risk, and route context at the
handoff boundary.

```python
HandoffPayload(
    case_id="case_l2_consent_001",
    workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
    from_node="OrchestratorAgent",
    to_agent="FinancialLinksReliabilityAgent",
    declared_risk_band=RiskBand.L2,
    consent_state=ConsentState.EXPIRED,
    consent_reconfirmed=False,
    route_context={"institution_id": "inst_synth_002"},
)
```

### Agent Output

`AgentOutput` is the specialist output before final composition. Tool calls,
policy references, approval posture, consent state, and the customer-facing
draft are structured so graders can inspect them.

```python
AgentOutput(
    case_id="case_l2_consent_001",
    workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
    declared_risk_band=RiskBand.L2,
    consent_state=ConsentState.EXPIRED,
    consent_reconfirmed=True,
    draft_text="Synthetic, hedged draft for analyst review.",
    policy_references=[PolicyReference(policy_id="FL-CONSENT-001")],
    approval=ApprovalDecision(required=True, approver_role="partner_support_analyst"),
)
```

### Approval Matrix

The synthetic approval matrix is
[`configs/approval_matrix.yaml`](configs/approval_matrix.yaml). The default
action boundary is `draft_only`. L2 consent-sensitive Financial Links cases
require consent re-confirmation or human approval before user-impacting guidance
is drafted.

```yaml
- workflow: financial_links_reliability
  risk_band: L2
  consent_sensitive: true
  approval_required: true
  requires_consent_reconfirmation: true
  action_boundary: draft_only
  human_owner: partner_support_analyst
```

Synthetic latency budgets live in
[`configs/latency_budgets.yaml`](configs/latency_budgets.yaml). They are
planning envelopes for evals only, not production SLAs, partner commitments, or
regulatory thresholds.

### Synthetic Tools

Financial Links tools are deterministic and dependency-free in
[`app/tools/synthetic_connectivity_tools.py`](app/tools/synthetic_connectivity_tools.py):

- `lookup_consent_state(user_id)`
- `lookup_institution_status(institution_id)`
- `lookup_partner_config(partner_id, institution_id)`
- `lookup_policy(policy_id)`

Tool outputs carry `"synthetic": true` so trace consumers do not mistake lab
facts for real operational data.

### Evaluator and Grader Separation

The runtime evaluator and offline graders are deliberately separate:

- Runtime checks live in [`app/evaluator.py`](app/evaluator.py) and return an
  `EvaluatorReport`.
- Offline graders live in [`evals/graders.py`](evals/graders.py) and return
  `GraderResult` records.

That separation lets the offline eval system measure whether the runtime
evaluator caught issues before final response composition. It also prevents a
single checker from both creating and validating the launch evidence.

### R8 Approval Grading Asymmetry

R8 is encoded in
[`configs/approval_matrix.yaml`](configs/approval_matrix.yaml) as
`approval_band_independent_of_declared: true`.

The runtime evaluator can inspect only the agent's declared risk band. The
offline approval-boundary grader instead derives the required approval from the
case's ground-truth `risk_band` and `consent_sensitive` fields. If the
orchestrator misroutes or under-declares risk, the offline score still evaluates
the true required gate.

## Financial Links Evidence

Financial Links reliability is the flagship slice.

### V0 Evidence

The v0 dataset is the first end-to-end synthetic loop: baseline failure,
offline grading, runtime evaluator catch-rate, pinned regressions, redaction,
and evidence packaging.

| Metric | `baseline_v0` | `improved_v0` |
|---|---:|---:|
| Cases | 10 | 10 |
| Passed | 7 | 10 |
| Failed | 3 | 0 |
| Baseline failure labels | `POLICY_MISS`, `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS` | none |
| Runtime evaluator catch-rate | 10/10 | 10/10 |

Key artifacts:

- [`case_studies/financial_links_reliability/dataset_card.md`](case_studies/financial_links_reliability/dataset_card.md)
- [`case_studies/financial_links_reliability/data/cases_v0.jsonl`](case_studies/financial_links_reliability/data/cases_v0.jsonl)
- [`case_studies/financial_links_reliability/evals/smoke.jsonl`](case_studies/financial_links_reliability/evals/smoke.jsonl)
- [`reports/v0_eval_card.md`](reports/v0_eval_card.md)
- [`case_studies/financial_links_reliability/evals/regressions_v0.jsonl`](case_studies/financial_links_reliability/evals/regressions_v0.jsonl)
- [`evidence_packs/financial_links_v0/README.md`](evidence_packs/financial_links_v0/README.md)

### Expanded Adversarial Slices

| Slice | Cases | Credential-free result | Purpose |
|---|---:|---|---|
| [`adversarial_v1`](case_studies/financial_links_reliability/evals/adversarial_v1.jsonl) | 12 | `baseline_v0` 4/12 -> `improved_v0` 12/12 | Paraphrased overpromise, negation calibration, consent pressure, policy citation, missing-info traps. |
| [`adversarial_v2`](case_studies/financial_links_reliability/evals/adversarial_v2.jsonl) | 24 | `baseline_v0` 9/24 -> `improved_v0` 24/24 | Broader multi-policy and missing-metadata surface; source of the blocked M7 semantic analysis. |
| [`adversarial_v3`](case_studies/financial_links_reliability/evals/adversarial_v3.jsonl) | 28 | Held-out surface for candidate-side variance testing | Tests whether candidate controls generalize without tuning to earlier slices. |

Relevant reports:

- [`reports/adversarial_v1_eval_card.md`](reports/adversarial_v1_eval_card.md)
- [`reports/adversarial_v2_eval_card.md`](reports/adversarial_v2_eval_card.md)
- [`reports/adversarial_v3_eval_card.md`](reports/adversarial_v3_eval_card.md)

### Opt-in LLM Candidate Evidence

LLM profiles are credential-gated and optional. They delegate only the
customer-facing draft text to a model; deterministic decisions such as tool
calls, policy citations, approval boundaries, routing, and prohibited-action
avoidance stay in code.

No default target or standard test requires an LLM key. Credentialed targets
gate on `make check-llm-env` and fail closed if `ANTHROPIC_API_KEY` or the
`anthropic` SDK is missing.

The useful reader-facing artifacts are the redacted reports and summaries:

- [`reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md`](reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md)
- [`reports/llm_adversarial_v1_repeat_summary.md`](reports/llm_adversarial_v1_repeat_summary.md)
- [`reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md`](reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md)
- [`reports/llm_adversarial_v2_semantic_audit_summary.md`](reports/llm_adversarial_v2_semantic_audit_summary.md)
- [`reports/llm_adversarial_v2_semantic_failure_analysis.md`](reports/llm_adversarial_v2_semantic_failure_analysis.md)
- [`reports/llm_adversarial_v3_candidate_v2_3_variance_summary.md`](reports/llm_adversarial_v3_candidate_v2_3_variance_summary.md)
- [`evidence_packs/financial_links_llm_adversarial_v1/README.md`](evidence_packs/financial_links_llm_adversarial_v1/README.md)
- [`evidence_packs/financial_links_llm_adversarial_v2/README.md`](evidence_packs/financial_links_llm_adversarial_v2/README.md)

Raw LLM reports, raw traces, and raw model decisions are treated as local
evidence and are excluded from public review unless redacted and packaged.

## Human Approval and Action Suspension

The live Financial Links workflow remains `draft_only`.

A separate credential-free harness in
[`app/action_suspension.py`](app/action_suspension.py) proves the approval
mechanism can suspend a synthetic side-effecting action before execution. It
uses a real LangGraph checkpointer and interrupt before `HumanApprovalNode`.
The offline action-suspension grader is separate in
[`evals/action_suspension_grader.py`](evals/action_suspension_grader.py).

This is infrastructure evidence, not a wired external-action path.

## Local Verification

These commands are for reviewers who want to reproduce the credential-free
evidence locally. They do not require external services.

```bash
uv sync --extra agent --extra dev
uv run pytest tests/test_readme.py
uv run pytest tests/test_deployment_artifacts.py
uv run pytest tests/test_launch_decision.py
uv run pytest tests/test_graders.py
uv run pytest tests/test_redaction.py
make launch-decision
make eval-card-v0
make eval-card-adversarial-v2
make regression-replay-adversarial-v2-semantic
make action-suspension-demo
```

Opt-in LLM checks require credentials and can spend tokens:

```bash
make check-llm-env
RUNS=5 make repeat-v2-3-v3
```

Use those only when refreshing credentialed evidence, not for normal review.

## Repository Map

- [`app/`](app/) - LangGraph runtime, schemas, evaluator, agents, and synthetic tools.
- [`case_studies/`](case_studies/) - synthetic datasets, policies, eval slices, and dataset cards.
- [`configs/`](configs/) - approval matrix, redaction policy, launch gates, risk weights, latency budgets, and cost rates.
- [`deployment/`](deployment/) - workflow map, value case, risk register, acceptance criteria, pilot review, adoption plan, and executive update.
- [`evals/`](evals/) - deterministic graders, semantic audit helpers, action-suspension grader, and launch-decision aggregation.
- [`reports/`](reports/) - generated eval cards, semantic summaries, adjudications, variance reports, and launch decisions.
- [`evidence_packs/`](evidence_packs/) - public-safe redacted evidence bundles.
- [`scripts/`](scripts/) - local CLIs for eval runs, redaction, reports, regression seeding, evidence packaging, and launch decisions.
- [`tests/`](tests/) - contract tests for schemas, graders, routing, redaction, reports, regression replay, and launch gates.
- [`PLAN.md`](PLAN.md) - phase history and locked decisions.

## Public-Safety Rules

- Synthetic cases, policies, identifiers, risk bands, and partner configurations only.
- No real customer data, production thresholds, proprietary workflows,
  SAR-adjacent examples, or real fraud controls.
- Public claims must point to generated traces, eval reports, redacted evidence
  packs, or deployment docs.
- Local raw traces and private project context are excluded from version control
  by default.
