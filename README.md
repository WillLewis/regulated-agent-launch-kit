# Regulated AI Deployment Kit

Synthetic embedded-finance deployment-readiness case study for regulated AI systems.

This repository is not a generic agent demo. It is structured to show the full loop from workflow mapping to measurable multi-agent behavior, traces, deterministic-first evals, redacted evidence, regression creation, and a launch/no-launch recommendation.

## Public-Safety Stance

- Synthetic cases, policies, identifiers, risk bands, and partner configurations only.
- No real customer data, production thresholds, proprietary workflows, SAR-adjacent examples, or real fraud controls.
- Public claims must be backed by generated traces, eval reports, redacted evidence packs, or deployment docs.
- Local raw traces and private project context are excluded from version control by default.

## Architecture Target

```text
Synthetic case
  -> IntakeNormalizer
  -> OrchestratorAgent
  -> Specialist agent
  -> Synthetic tools and policies
  -> EvaluatorNode
  -> HumanApprovalNode when required
  -> FinalResponseComposer
  -> Trace and eval artifacts
  -> Redacted evidence
  -> Eval card and pilot recommendation
```

## Current Status

Phase 1 (deployment narrative) is complete. The repo currently contains the deployment-readiness artifacts that scope and constrain the agent system; the agent system itself is not yet implemented and no eval runs have been performed.

Phase 1 artifacts:

- [Customer workflow map](deployment/customer_workflow_map.md) — synthetic Financial Links / connectivity reliability workflow, current and future state.
- [Value case](deployment/value_case.md) — synthetic business outcomes (`H1`–`H5`) with required evidence per claim.
- [KPI tree](deployment/kpi_tree.md) — outcomes mapped to operational, agent, and safety metrics with grader assignments.
- [Acceptance criteria](deployment/acceptance_criteria.md) — Phase 1, system, workflow, eval, artifact, and launch-gate conditions.
- [Risk register](deployment/risk_register.md) — synthetic deployment risks with severity, likelihood, mitigation, detection signal, and owner.
- [Dependency map](deployment/dependency_map.md) — what blocks what across technical, product, and review dependencies.

Active phase: Phase 2 — synthetic domain model and Pydantic schemas. The Phase 2 contracts (schemas, approval matrix, synthetic tools, runtime evaluator and offline graders) are in place; see the [Synthetic Domain Model](#synthetic-domain-model) section below. Synthetic datasets, baseline eval runs, and pilot-readiness artifacts are still pending. See [`PLAN.md`](PLAN.md) for status and locked decisions, and [`PLAN_v3_openai_tdl_fde.md`](PLAN_v3_openai_tdl_fde.md) for the full phased plan.

## Synthetic Domain Model

Phase 2 locks in the contracts the runtime agent system and the offline eval system both rely on. Everything below is **synthetic and public-safe**: every identifier, partner name, institution ID, and policy ID is fabricated for this lab. Nothing in this section implies production readiness, regulatory compliance, completed eval runs, or any pilot outcome.

Full definitions live in [`app/schemas.py`](app/schemas.py), [`configs/approval_matrix.yaml`](configs/approval_matrix.yaml), and [`app/tools/synthetic_connectivity_tools.py`](app/tools/synthetic_connectivity_tools.py). The examples below are short illustrations, not exhaustive schemas.

### 1. Synthetic case

A `Case` is the orchestrator's input. It carries the workflow, the ground-truth risk band, and a `consent_sensitive` flag that the offline graders rely on so an orchestrator misroute cannot lower the band the grader uses.

```python
Case(
    case_id="case_l2_consent_001",
    workflow=Workflow.FINANCIAL_LINKS_RELIABILITY,
    risk_band=RiskBand.L2,
    consent_sensitive=True,
    payload={"user_id": "user_synth_002", "institution_id": "inst_synth_002"},
)
```

### 2. Runtime case state / handoff payload

State flows between nodes through `HandoffPayload`. Pydantic enforces consent, risk, and route context at construction (PLAN.md R9) — a specialist agent can never receive a handoff that lacks them.

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

### 3. Agent output

`AgentOutput` is what a specialist agent emits before final composition. Consent fields are first-class (PLAN.md R1); approval posture is a typed `ApprovalDecision` rather than free text; tool calls and policy references are captured for graders.

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

### 4. Approval matrix

The synthetic approval matrix lives at [`configs/approval_matrix.yaml`](configs/approval_matrix.yaml). The default action boundary is `draft_only`. L2 consent-sensitive Financial Links cases require explicit consent re-confirmation **or** human approval before user-impacting guidance is drafted.

```yaml
- workflow: financial_links_reliability
  risk_band: L2
  consent_sensitive: true
  approval_required: true
  requires_consent_reconfirmation: true
  action_boundary: draft_only
  human_owner: partner_support_analyst
```

Synthetic per-band latency budgets sit alongside it in [`configs/latency_budgets.yaml`](configs/latency_budgets.yaml). They are eval-planning envelopes only, and are not production SLAs, partner commitments, or regulatory thresholds.

### 5. Synthetic tools

The Financial Links workflow uses deterministic, dependency-free tools in [`app/tools/synthetic_connectivity_tools.py`](app/tools/synthetic_connectivity_tools.py):

- `lookup_consent_state(user_id)` — synthetic consent state per synthetic user.
- `lookup_institution_status(institution_id)` — synthetic institution + aggregator route status.
- `lookup_partner_config(partner_id, institution_id)` — synthetic per-partner scope and fallback permissions.
- `lookup_policy(policy_id)` — synthetic policy retrieval; missing IDs return a `retrieved=false` stub rather than raising.

Every tool output includes `"synthetic": True` so synthetic facts cannot be mistaken for real-system facts in traces or reports.

### Evaluator vs. grader separation

The runtime `EvaluatorNode` ([`app/evaluator.py`](app/evaluator.py)) and the offline graders ([`evals/graders.py`](evals/graders.py)) are intentionally distinct modules with distinct return types (`EvaluatorReport` vs. `GraderResult`):

- The **runtime evaluator** inspects an `AgentOutput` before the final response is composed, surfacing inline blocks for missing schema fields, missing consent re-confirmation at L2+ consent-sensitive cases, and missing approval when the matrix demands it.
- **Offline graders** run after a trace completes and produce a `GraderResult` per concept (handoff completeness, required tool use, consent boundary, approval boundary, schema validity).

Keeping the two surfaces separate is what lets the offline catch-rate grader honestly measure whether the runtime evaluator caught the issues it was supposed to.

### Approval grading asymmetry (PLAN.md R8)

The runtime evaluator inspects `AgentOutput.declared_risk_band` — it can only see what the agent declared. The offline approval-boundary grader does **not**: it derives the required approval from the case's ground-truth `risk_band` and `consent_sensitive` flag against the matrix. An orchestrator misroute that lowers the declared band therefore cannot bypass approval-grading; the eval score reflects the true required gate.

This asymmetry is recorded in `configs/approval_matrix.yaml` under `evaluation_rules.approval_band_independent_of_declared: true`.

---

The kit is mid-Phase 2: contracts are in place, but no synthetic datasets, baseline eval, or improvement run have been produced yet. Any pilot or launch claim remains explicitly out of scope until those artifacts exist.

## Starter Layout

- `PLAN_v3_openai_tdl_fde.md` contains the detailed build plan.
- `deployment/` contains the customer-deployment leadership artifacts.
- `case_studies/` contains public-safe synthetic datasets and dataset cards.
- `app/` will contain the LangGraph system under test.
- `evals/` will contain deterministic graders and eval adapters.
- `scripts/` will contain local CLIs for datasets, evals, redaction, regressions, and reports.
- `.claude/` contains Claude Code subagent and hook scaffolding.

## First Build Milestones

1. Complete deployment docs for workflow map, value case, KPI tree, acceptance criteria, and risk register.
2. Define Pydantic schemas for cases, graph state, traces, and grader results.
3. Build the Financial Links reliability workflow first.
4. Run a baseline eval with local JSON artifacts.
5. Convert at least one failure into a regression case and update the eval card.
