# Regulated AI Deployment Kit — PLAN v3

## Private thesis reference

When working locally, Claude Code and Codex should read `.project-memory/goal-thesis.md` before making architecture, README, or deployment-artifact changes. The file is intentionally gitignored; do not paste its contents into public docs, READMEs, webpages, reports, or generated artifacts.

## One-sentence positioning

**Regulated AI Deployment Kit** is a synthetic embedded-finance multi-agent deployment lab that shows how to move from prototype to pilot-readiness using workflow mapping, LangGraph orchestration, Braintrust-backed traces, deterministic-first evals, redacted evidence, regression tests, and launch-readiness memos.

---

## Target signal

The repo must demonstrate these capabilities clearly:

| Capability | Artifact that proves it |
|---|---|
| Understand regulated embedded-finance workflows | Workflow maps, synthetic datasets, approval matrix |
| Translate business goals into technical plans | Value case, KPI tree, delivery plan, acceptance criteria |
| Build controlled multi-agent systems | LangGraph orchestrator, specialist agents, evaluator node, human approval node |
| Instrument the system | Braintrust traces plus local trace JSON |
| Evaluate reliability | Deterministic graders, risk-weighted scoring, failure taxonomy |
| Improve with evidence | Baseline vs improved run, before/after memo, regression suite |
| Respect governance | Redaction policy, approval boundaries, synthetic-only data stance |
| Lead deployment | Milestone tracker, dependency map, risk register, pilot readiness review, exec update |
| Communicate cross-functionally | README, eval cards, launch memo, mini webpage |

---

## Core architecture

```text
Synthetic embedded-finance case
        ↓
IntakeNormalizer
        ↓
LangGraph OrchestratorAgent
        ↓
Specialist agents
  - FinancialLinksReliabilityAgent
  - CreditWellnessAgent
  - OfferActivationAgent
  - PrivacyIdentityAgent
        ↓
Synthetic tools + synthetic policies + synthetic data layer
        ↓
EvaluatorNode
  - schema checks
  - tool checks
  - consent checks
  - policy checks
  - approval checks
  - customer-communication checks
        ↓
HumanApprovalNode
        ↓
FinalResponseComposer
        ↓
Braintrust traces + local trace artifacts
        ↓
Offline graders + failure taxonomy
        ↓
Incident-to-regression workflow
        ↓
Trace redaction + evidence packager
        ↓
Eval card + deployment artifacts
        ↓
Mini webpage demonstration
```

### Design principle

Do not build an autonomous swarm. Build a **controlled supervisor/orchestrator pattern** that is easy to evaluate:

```text
1 orchestrator
3 primary specialist agents
1 evaluator node
1 human-approval node
1 final response composer
```

This is enough complexity to demonstrate real deployment judgment without turning the project into framework theater.

---

# Component 1 — Synthetic embedded-finance multi-agent system + datasets

## Purpose

Create realistic, public-safe embedded-finance workflows that show how a regulated multi-agent system should be evaluated before pilot.

The system under test is not a single chatbot. It is a multi-agent workflow where failures can happen at routing, handoff, tool selection, policy retrieval, evaluator enforcement, approval gating, or final communication.

## Required datasets

Build 2 datasets minimum; 3 strongly preferred.

### Dataset A — Financial Links / connectivity reliability

**Flagship dataset.** This should be the first and most polished workflow.

Workflow: a fintech or digital-banking partner reports user issues connecting, refreshing, or using linked financial-account data. The system must diagnose whether the issue is consent, aggregator health, partner configuration, institution metadata, stale data, or missing information.

Primary case types:

- account linking failed during onboarding
- stale balance or transaction data
- consent expired, revoked, or insufficient
- aggregator route degraded
- fallback route available but not permitted by partner config
- institution metadata missing
- user-facing error copy would be misleading
- partner asks agent to force completion despite missing consent
- engineering escalation required
- routine case that should not be over-escalated

Target size:

- V1: 75–100 cases
- Strong version: 125–150 cases
- Include 15–25 adversarial or misleading cases
- Include 15–25 regression cases generated from failures

### Dataset B — Credit wellness + offer activation

Workflow: a partner wants to surface credit-health insights or targeted financial offers inside a consumer experience. The system must inspect synthetic credit-profile bands, consent state, partner constraints, offer policy, and customer-safe communication rules.

Primary case types:

- user eligible for credit education only
- user eligible for offer surfacing but not approval language
- insufficient consent for personalization
- partner configuration blocks certain offers
- score-change explanation request
- credit simulator explanation request
- user asks whether approval is guaranteed
- agent must avoid unsupported credit-outcome claims
- revenue-driving offer conflicts with safer educational path
- missing credit data but user asks for precise causal explanation
- communication requiring human/legal review

Target size:

- V1: 75–100 cases
- Strong version: 125–150 cases
- Include 20+ communication-safety cases
- Include 15+ conversion vs compliance tradeoff cases

### Dataset C — Privacy / identity alert triage

Workflow: a user receives a synthetic privacy or identity-protection alert. The system must classify the alert, retrieve synthetic policy, inspect synthetic exposure facts, recommend safe next steps, and escalate high-risk identity-support cases.

Primary case types:

- data-broker exposure alert
- exposed email, phone, or address class
- duplicate or false-positive alert
- customer asks whether identity theft occurred
- customer asks whether insurance coverage applies
- restoration support may be required
- customer asks for legal advice
- agent must provide safe next steps without overclaiming
- high-risk alert requiring human review

Target size:

- V1: 60–90 cases
- Strong version: 100–125 cases
- Include 20+ customer-communication safety cases
- Include 10–15 high-risk escalation cases

### Optional Dataset D — Subscription manager action approval

Workflow: a user wants help identifying, canceling, or negotiating recurring subscriptions. The agent may identify patterns and draft next steps, but cancellation or negotiation requires explicit user approval.

Use only if time allows. It is useful for the human-approval story but less central to regulated-finance reliability than datasets A–C.

---

## Dataset design rules

Public datasets must be synthetic and deliberately non-sensitive.

Never include:

- real fraud typologies
- production thresholds
- real customer journeys from work
- real customer identifiers
- real merchant names
- real credit attributes beyond abstract bands
- real bureau, provider, or partner schemas
- real partner configurations
- real loss amounts
- SAR-adjacent facts
- proprietary tool schemas
- sensitive vendor or source names
- adversarial bypass details

Use abstract fields:

```yaml
amount_band: low | medium | high | severe
risk_band: L0 | L1 | L2 | L3 | L4
profile_band: prime | near_prime | emerging | unknown
consent_state: granted | expired | revoked | insufficient | unknown
policy_rule: synthetic_policy_id
financial_impact: synthetic_loss_units
partner_id: synthetic_partner_id
institution_id: synthetic_institution_id
```

---

# Component 2 — Trace redaction and evidence packager

## Purpose

Convert rich traces into public-safe evidence packs. This is one of the strongest signals that the project is built by someone who understands regulated deployment.

## Trace requirements

Each raw trace should include:

- trace ID
- dataset ID
- case ID
- workflow
- risk band
- agent system version
- policy version
- orchestrator decision
- specialist-agent path
- handoff payload summary
- tool calls
- tool arguments
- tool outputs
- evaluator checks
- approval decision
- final response
- grader results
- failure labels
- latency
- cost/token estimate

## Redacted traces preserve

- workflow type
- agent version
- policy version
- node sequence
- handoff path
- tool sequence
- evaluator outcomes
- approval decision
- grader outcomes
- latency and cost metadata
- risk band
- failure taxonomy label

## Redacted traces remove or abstract

- customer identifiers
- partner identifiers if real
- institution names if real
- exact transaction amounts
- real merchant names
- real credit attributes
- real provider names
- internal rule names
- raw tool arguments that reveal controls
- sensitive policy text
- raw user messages if sensitive
- analyst names
- production URLs

## CLI targets

```bash
python scripts/redact_trace.py \
  --input traces/raw/run_001_case_042.json \
  --policy configs/redaction_policy.yaml \
  --output traces/redacted/run_001_case_042.redacted.json

python scripts/package_evidence.py \
  --run reports/eval_run_001.json \
  --traces traces/redacted/ \
  --output evidence_packs/eval_run_001/
```

## Acceptance criteria

- preserves enough trace structure to debug the system;
- removes sensitive operational details;
- outputs a machine-readable redaction report;
- flags uncovered fields;
- powers the README and mini webpage without exposing sensitive logic.

---

# Component 3 — Incident-to-regression workflow

## Purpose

Turn failures into durable regression tests. This demonstrates that evals are not static benchmarks; they are the learning system for deployment reliability.

## Flow

```text
1. Eval run identifies failure.
2. Failure is classified by taxonomy.
3. Incident summary is generated.
4. Human reviewer approves or edits the regression case.
5. Regression case is added to dataset.
6. Future eval runs must pass the regression case.
```

## Failure taxonomy

```yaml
failure_taxonomy:
  ORCHESTRATOR_MISROUTE:
    description: Orchestrator routed the case to the wrong specialist or path.
  HANDOFF_CONTEXT_LOSS:
    description: Required state was lost between orchestrator and specialist agent.
  TOOL_MISUSE:
    description: Agent failed to call required tool, called wrong tool, or used unsafe arguments.
  POLICY_MISS:
    description: Agent failed to retrieve or apply relevant synthetic policy.
  CONSENT_BOUNDARY_VIOLATION:
    description: Agent acted or recommended action without sufficient synthetic consent.
  MISSED_ESCALATION:
    description: Agent failed to escalate a case requiring human review.
  OVER_ESCALATION:
    description: Agent escalated a routine case unnecessarily.
  UNSUPPORTED_ACTION:
    description: Agent attempted an action that required approval.
  HALLUCINATED_FACT:
    description: Agent invented account, credit, offer, identity, policy, or product facts.
  UNSAFE_CUSTOMER_COMMS:
    description: Agent drafted customer-facing language with unsupported claims, guarantees, or overpromises.
  SCHEMA_VIOLATION:
    description: Agent output failed required JSON/schema contract.
  EVALUATOR_MISS:
    description: Evaluator failed to catch a downstream policy, schema, or approval issue.
  COST_LATENCY_REGRESSION:
    description: Quality improved but cost or latency violated guardrails.
  TRACE_REDACTION_GAP:
    description: Trace contained a field not covered by redaction policy.
  DELIVERY_RISK_UNADDRESSED:
    description: Technical result looks acceptable but pilot/adoption/governance risks remain unresolved.
```

## Acceptance criteria

- every high-risk failure can become a regression test;
- generated tests include expected and prohibited behavior;
- tests require review before being added;
- regression pass/fail is reported separately from general quality;
- README and webpage show at least one failure becoming a regression.

---

# Component 4 — Eval-card and launch-readiness generator

## Purpose

Generate PM-grade decision artifacts from eval results. The eval card should answer:

> Is this multi-agent workflow ready to pilot, blocked, or safe only with constraints?

## CLI target

```bash
python scripts/generate_eval_card.py \
  --run reports/eval_run_002.json \
  --failures reports/failure_summary_002.json \
  --delivery deployment/pilot_readiness.yaml \
  --output reports/eval_card_002.md
```

## Eval card structure

```markdown
# Eval Card — Regulated Embedded-Finance Multi-Agent System

## Summary
- Agent system version:
- Dataset versions:
- Workflows evaluated:
- Primary users:
- Automation boundary:
- Launch recommendation:

## Quality metrics
- System task success:
- Orchestrator routing accuracy:
- Specialist-agent success:
- Evaluator catch rate:
- Tool selection accuracy:
- Policy adherence:
- Consent-boundary adherence:
- Escalation recall:
- Escalation precision:
- Unsupported action rate:
- Unsupported claim rate:
- Regression pass rate:

## Operational metrics
- Average latency:
- p95 latency:
- Average estimated cost:
- Total eval cost:
- Cost by workflow:

## Risk-weighted results
- L0/L1 performance:
- L2 performance:
- L3/L4 performance:
- Highest-risk unresolved failure:

## Deployment readiness
- Customer value hypothesis:
- Baseline metric:
- Pilot KPI:
- Human approvals required:
- Open dependencies:
- Adoption risks:
- Executive decision needed:

## Product decision
- What changed since baseline:
- What improved:
- What got worse:
- Recommended launch posture:
- Remaining blockers:

## Governance notes
- Data boundaries:
- Redaction status:
- Known grader limitations:
- Known dataset limitations:
```

## Example launch recommendations

```text
DO NOT PILOT
Reason: Evaluator missed customer-facing unsupported claims in L3 identity-support cases.

PILOT WITH CONSTRAINTS
Reason: High-risk cases route correctly, but over-escalation creates partner-support load. Enable human review for all L2+ identity cases and sample 20% of L1 connectivity cases.

READY FOR LIMITED INTERNAL PILOT
Reason: Regression suite passed, unsupported-action rate is zero, and orchestrator routing exceeds threshold across mandatory workflows.
```

---

# Component 5 — Deployment leadership layer

## Purpose

Prove that this is not merely an engineering repo. It is a simulated customer deployment with measurable outcomes, milestones, dependencies, risk management, and executive communication.

## Required deployment artifacts

```text
deployment/
  customer_workflow_map.md
  value_case.md
  kpi_tree.md
  delivery_plan.md
  dependency_map.md
  acceptance_criteria.md
  risk_register.md
  pilot_readiness_review.md
  adoption_plan.md
  exec_update.md
  field_feedback_to_product.md
```

### customer_workflow_map.md

Must show the current-state and future-state workflow.

Required sections:

- current manual workflow
- pain points
- users/stakeholders
- systems touched
- decision points
- approval points
- future-state agent-assisted workflow
- what remains human-owned

### value_case.md

Must define business outcomes and measurable hypotheses.

Example hypotheses:

```text
H1: Reduce partner-support triage time for Financial Links issues by 40% in an internal pilot.
H2: Improve correct escalation of consent-sensitive cases to 95%+.
H3: Reduce unsafe or misleading customer-facing draft language by 60% versus baseline.
H4: Maintain p95 latency below target for routine L0–L2 cases while routing L3+ cases through stronger checks.
```

### kpi_tree.md

Connect business outcomes to technical metrics.

```text
Business outcome: Faster partner-support resolution
  ↓
Operational KPI: triage time proxy, escalation precision
  ↓
Agent metrics: routing accuracy, required-tool use, schema validity
  ↓
Safety metrics: consent-boundary adherence, unsupported-claim rate
```

### delivery_plan.md

Must include phases, milestones, owners, dependencies, acceptance criteria, and risks.

### risk_register.md

Include at least:

- consent-sensitive case misrouted
- evaluator misses unsupported customer claim
- partner schema changes break tool calls
- latency hurts workflow adoption
- redacted evidence loses too much diagnostic value
- dataset realism is insufficient
- over-escalation increases support burden
- false confidence from synthetic-only scores

### pilot_readiness_review.md

Must answer:

- what is ready;
- what is blocked;
- what can pilot only with constraints;
- which humans must approve which actions;
- which metrics must be monitored during pilot;
- what kill-switch or rollback condition exists.

### exec_update.md

One-page status memo after the improved eval run:

```text
Status: Pilot with constraints / Not ready / Ready for internal pilot
What changed:
Top metric movement:
Top unresolved risk:
Decision needed:
Recommendation:
Next milestone:
```

### field_feedback_to_product.md

Show how deployment learnings become reusable platform/product feedback:

- missing SDK/tooling need
- eval platform improvement request
- model behavior issue
- trace visualization need
- policy/versioning gap
- customer adoption blocker

---

# Recommended tracing/eval platform

## Decision

Use **Braintrust as the primary tracing/eval platform**. Keep local JSON traces and reports as the portable source of truth. Add W&B Weave as optional only if there is time.

## Why Braintrust primary

Braintrust maps cleanly to the core loop:

```text
datasets → experiments → scorers → traces → failures → regressions → eval cards → launch decision
```

## Local artifact requirement

Every eval run must also write:

```text
reports/eval_run.json
reports/failure_summary.json
reports/eval_card.md
traces/raw/*.json
traces/redacted/*.json
evidence_packs/*
deployment/exec_update.md
```

A reviewer must understand the project without logging into Braintrust.

---

# Recommended implementation stack

```text
Python
  - LangGraph orchestration
  - LangChain model/tool adapters where useful
  - Pydantic schemas
  - deterministic graders
  - trace capture
  - report generation

Braintrust
  - primary experiment/eval/tracing platform
  - scorers and experiment comparison

Optional W&B Weave
  - secondary tracing/eval adapter
  - visualization/platform comparison

JSONL / YAML
  - datasets
  - rubrics
  - synthetic policies
  - failure taxonomy
  - approval matrix
  - redaction policy

Static web app
  - Vite + React or Next.js static export
  - reads precomputed report JSON
  - no backend for v1

CI
  - pytest
  - regression gate
  - schema checks
  - redaction-policy check
```

---

# Suggested repo structure

```text
regulated-ai-deployment-kit/
  README.md
  PLAN.md
  AGENTS.md
  AGENT.md
  CLAUDE.md

  app/
    graph.py
    state.py
    schemas.py
    orchestrator.py
    evaluator.py
    agents/
      financial_links_reliability_agent.py
      credit_wellness_agent.py
      offer_activation_agent.py
      privacy_identity_agent.py
    tools/
      synthetic_connectivity_tools.py
      synthetic_credit_tools.py
      synthetic_offer_tools.py
      synthetic_privacy_tools.py
      policy_tools.py

  case_studies/
    financial_links_reliability/
      README.md
      dataset_card.md
      policies/
      data/
      evals/
      traces/
      reports/

    credit_wellness_offer_activation/
      README.md
      dataset_card.md
      policies/
      data/
      evals/
      traces/
      reports/

    privacy_identity_alert_triage/
      README.md
      dataset_card.md
      policies/
      data/
      evals/
      traces/
      reports/

  evals/
    graders.py
    risk_weighted_scoring.py
    failure_classifier.py
    braintrust_adapter.py
    weave_adapter.py

  scripts/
    generate_synthetic_dataset.py
    run_eval.py
    compare_runs.py
    redact_trace.py
    package_evidence.py
    incident_to_regression.py
    generate_eval_card.py
    generate_deployment_docs.py

  configs/
    failure_taxonomy.yaml
    redaction_policy.yaml
    risk_weights.yaml
    approval_matrix.yaml
    platform.yaml

  deployment/
    customer_workflow_map.md
    value_case.md
    kpi_tree.md
    delivery_plan.md
    dependency_map.md
    acceptance_criteria.md
    risk_register.md
    pilot_readiness_review.md
    adoption_plan.md
    exec_update.md
    field_feedback_to_product.md

  reports/
    baseline_eval_card.md
    improved_eval_card.md
    before_after_comparison.md
    summary.json

  evidence_packs/
    example_eval_run/

  web/
    README.md
    package.json
    src/
    public/
      reports/
      traces/
      datasets/
      deployment/

  tests/
    test_graph_routing.py
    test_evaluator_node.py
    test_graders.py
    test_redaction.py
    test_regression_cases.py
    test_eval_card_generation.py
    test_deployment_artifacts.py
```

---

# Phased build plan

## Phase 0 — Lock target signal and public-safety posture

Goal: Make the repo impossible to confuse with a toy demo.

Deliverables:

- README skeleton
- product thesis
- top 1% acceptance criteria
- public-safety policy
- synthetic-only data rules
- decision log explaining LangGraph + Braintrust
- Claude/Codex operating model

Acceptance criteria:

- first 60 seconds of README communicate deployment-readiness, not demo-building;
- real data and real fraud controls are explicitly out of scope;
- automation boundaries are visible.

---

## Phase 1 — Build deployment narrative and workflow map

Goal: Define the simulated customer problem before building agents.

Deliverables:

- `deployment/customer_workflow_map.md`
- `deployment/value_case.md`
- `deployment/kpi_tree.md`
- `deployment/acceptance_criteria.md`
- `deployment/risk_register.md`

Acceptance criteria:

- business outcomes map to eval metrics;
- current and future workflows are clear;
- pilot constraints and human-approval boundaries are explicit.

---

## Phase 2 — Build synthetic domain model

Goal: Create fake but credible embedded-finance operating environments.

Deliverables:

- synthetic policies
- synthetic tools
- case schemas
- risk bands
- approval matrix
- failure taxonomy
- Pydantic state/output schemas

Acceptance criteria:

- agent cannot bypass consent;
- agent cannot guarantee approval or credit outcomes;
- agent cannot diagnose identity theft or promise coverage;
- agent cannot take external action without approval;
- agent must retrieve relevant synthetic policy before recommendation;
- agent must escalate high-risk cases.

---

## Phase 3 — Implement LangGraph multi-agent runner

Goal: Build the orchestrator, specialist agents, evaluator node, and human approval node.

Deliverables:

- `app/graph.py`
- orchestrator
- 3 specialist agents
- evaluator node
- human approval node
- local trace collector
- baseline prompts/configs

Acceptance criteria:

- one synthetic case runs end-to-end;
- each graph node emits trace metadata;
- evaluator node checks every final output;
- output schema is enforced;
- human approval boundary exists even if simulated.

---

## Phase 4 — Add Braintrust tracing/evals and local artifact logging

Goal: Make traces realistic and tool-backed while preserving local reproducibility.

Deliverables:

- Braintrust setup notes
- Braintrust adapter
- experiment metadata logging
- local trace JSON
- local eval-run JSON
- optional W&B Weave adapter stub

Acceptance criteria:

- Braintrust shows at least one full multi-agent trace;
- local artifacts mirror key trace/eval information;
- a reviewer can understand the trace without credentials.

---

## Phase 5 — Build 2–3 synthetic datasets

Goal: Build Array-aligned / embedded-finance datasets that illustrate the eval system.

Required:

1. Financial Links / connectivity reliability
2. Credit wellness + offer activation
3. Privacy / identity alert triage

Acceptance criteria:

- at least two datasets complete;
- three datasets strongly preferred;
- each has a dataset card;
- each includes routine, missing-info, high-risk, adversarial, and regression-style cases;
- no real operational controls or customer data.

---

## Phase 6 — Implement graders and evaluator checks

Goal: Create deterministic-first grading across the multi-agent system.

Required graders:

1. orchestrator routing grader
2. handoff completeness grader
3. required-tool grader
4. prohibited-tool/action grader
5. policy retrieval grader
6. consent-boundary grader
7. approval-boundary grader
8. escalation correctness grader
9. schema validity grader
10. unsupported-claim grader
11. hallucinated-fact grader
12. evaluator catch-rate grader
13. cost/latency grader
14. regression grader
15. deployment-readiness grader

Acceptance criteria:

- at least 70% of grading logic is deterministic;
- every grader emits pass/fail, severity, explanation, and failure label;
- evaluator node and offline graders are separate, so the system can test whether the evaluator caught issues.

---

## Phase 7 — Run baseline eval and diagnose failures

Goal: Show baseline system failures and diagnose them from traces.

Deliverables:

- Braintrust baseline experiment
- local baseline eval report
- failure summary
- representative raw and redacted traces
- cost/latency report
- baseline exec update

Acceptance criteria:

- baseline has visible failures;
- failures are classified by taxonomy;
- at least one evaluator miss is visible;
- at least one high-risk failure is selected for regression;
- the launch recommendation is not inflated.

---

## Phase 8 — Make product/system change and compare before/after

Goal: Demonstrate an evidence-backed reliability improvement.

Potential changes:

- prompt change: orchestrator must inspect consent before connectivity remediation;
- routing change: identity-alert cases with coverage/restoration questions must route to human review;
- tool change: split `lookup_offer_policy` from `lookup_credit_profile_band`;
- evaluator change: block final output when unsupported claims appear;
- schema change: require explicit `evidence_sufficiency` and `approval_required` fields;
- model routing change: cheaper config for routine cases, stronger config for high-risk cases.

Deliverables:

- improved agent version
- after eval run
- before/after comparison
- cost/latency/quality tradeoff memo
- updated risk register

Acceptance criteria:

- at least one important metric improves;
- cost/latency tradeoff is explicit;
- regression suite is run after change;
- launch recommendation changes or remains blocked for a clear reason.

---

## Phase 9 — Build trace redaction and evidence packaging

Goal: Create public-safe trace artifacts.

Deliverables:

- redaction policy
- redaction script
- redacted trace examples
- redaction reports
- evidence pack

Acceptance criteria:

- redaction removes sensitive fields;
- redaction preserves node sequence, handoffs, tool use, evaluator outcomes, and grader outcomes;
- redaction report flags uncovered fields;
- evidence pack can power README and webpage.

---

## Phase 10 — Build incident-to-regression workflow

Goal: Convert failures into durable tests.

Deliverables:

- incident summary generator
- regression case generator
- review status field
- regression report

Acceptance criteria:

- at least 5 failures become regression tests;
- at least 2 high-risk failures become regression tests;
- improved system passes new regression tests or clearly explains remaining blockers.

---

## Phase 11 — Generate eval cards and deployment leadership artifacts

Goal: Translate eval results into PM/TDL-grade deployment recommendations.

Deliverables:

- eval-card generator
- baseline eval card
- improved eval card
- portfolio launch memo
- model-risk-style review memo
- pilot readiness review
- exec update
- field-feedback-to-product memo

Acceptance criteria:

- eval cards are generated from actual eval outputs;
- launch recommendation is evidence-backed;
- remaining blockers and approval requirements are explicit;
- artifacts are readable to PM, engineering, risk, and executive stakeholders.

---

## Final Phase 12 — Build mini webpage demonstration

Goal: Create a polished, public-facing demonstration that lets a reviewer understand the reliability system in under five minutes.

The page should visualize generated artifacts, not hand-built mockups.

Recommended sections:

```text
/overview
  - thesis
  - embedded-finance context
  - public-safety posture
  - deployment-readiness framing

/workflows
  - Financial Links reliability
  - Credit wellness + offer activation
  - Privacy / identity alert triage
  - human approval boundaries

/architecture
  - LangGraph nodes
  - orchestrator and specialist agents
  - evaluator node
  - Braintrust trace mapping

/delivery
  - value case
  - KPI tree
  - delivery plan
  - risk register
  - pilot readiness status

/datasets
  - dataset cards
  - risk-band distribution
  - case-type distribution
  - synthetic example cases

/eval-runs
  - baseline vs improved metrics
  - routing accuracy
  - evaluator catch rate
  - unsupported action rate
  - unsupported claim rate
  - cost
  - latency

/traces
  - redacted trace viewer
  - graph node timeline
  - tool sequence
  - handoff payload summary
  - evaluator checks
  - grader outcomes

/failures
  - failure taxonomy
  - failure counts
  - representative high-risk failures

/regressions
  - incidents converted to regression tests
  - regression pass/fail
  - remaining blockers

/eval-card
  - generated launch-readiness memo
  - pilot recommendation
  - approval gates
  - unresolved risks
```

Minimum visualizations:

- architecture diagram
- metric cards
- before/after comparison table
- failure taxonomy chart
- risk-band distribution chart
- redacted trace timeline
- evaluator catch/miss examples
- regression test table
- launch recommendation panel
- delivery milestone/status panel

Acceptance criteria:

A recruiter or hiring manager can:

- understand the product problem quickly;
- see embedded-finance relevance;
- understand the multi-agent architecture;
- inspect a redacted trace;
- see why baseline was unsafe;
- see the before/after improvement;
- understand what still blocks launch;
- see how deployment would be managed;
- recognize that this is a deployment-readiness system, not a toy dashboard.

---

# Required scripts

```bash
python scripts/generate_synthetic_dataset.py \
  --workflow financial_links_reliability \
  --count 100 \
  --out case_studies/financial_links_reliability/evals/dataset_v1.jsonl

python scripts/run_eval.py \
  --workflow financial_links_reliability \
  --dataset case_studies/financial_links_reliability/evals/dataset_v1.jsonl \
  --agent-system-version baseline_v0 \
  --platform braintrust \
  --traces-out case_studies/financial_links_reliability/traces/raw \
  --report-out reports/baseline_eval_run.json

python scripts/compare_runs.py \
  --before reports/baseline_eval_run.json \
  --after reports/improved_eval_run.json \
  --out reports/before_after_comparison.md

python scripts/redact_trace.py \
  --input traces/raw/trace_001.json \
  --policy configs/redaction_policy.yaml \
  --output traces/redacted/trace_001.redacted.json

python scripts/incident_to_regression.py \
  --failure reports/failures/failure_0042.json \
  --trace traces/redacted/trace_0042.redacted.json \
  --out case_studies/financial_links_reliability/evals/dataset_v2_regression.jsonl

python scripts/generate_eval_card.py \
  --run reports/improved_eval_run.json \
  --failures reports/failure_summary.json \
  --delivery deployment/pilot_readiness_review.md \
  --out reports/improved_eval_card.md
```

---

# README product case study structure

## 1. Problem

Embedded-finance companies can build agent demos quickly, but deploying agents into B2B2C financial workflows requires a higher bar: consent boundaries, customer-safe language, partner-specific configuration, traceability, approval gates, measurable reliability, and evidence that routing/tool/prompt changes improved outcomes.

## 2. Users

Primary users:

- forward-deployed PM
- technical deployment lead
- deployment engineer
- partner success manager
- platform engineer
- risk/compliance reviewer
- embedded-finance product owner
- developer experience lead

## 3. Architecture

Show the full loop:

```text
Synthetic case → LangGraph orchestrator → specialist agents → tools → evaluator node → Braintrust traces → graders → failures → regressions → redacted evidence → eval card → launch decision → deployment memo
```

## 4. Product decisions

Explain why:

- multi-agent orchestration is used instead of one monolithic agent;
- the orchestrator routes but does not make final high-risk decisions;
- evaluator checks run before final output;
- deterministic graders are preferred for schema, tool, policy, consent, and approval checks;
- rubric/LLM grading is limited to subjective communication quality;
- traces are redacted before publication;
- real fraud-dollar scoring is replaced by synthetic loss units and risk bands;
- deployment artifacts are included because reliability is not enough without adoption and governance.

## 5. Safety / governance

Document:

- approval gates
- consent boundaries
- logging fields
- redaction rules
- data boundaries
- prohibited examples
- failure modes
- public-safety stance

## 6. Evals

Show:

- dataset design
- metrics
- grader logic
- baseline results
- improved results
- regression results
- cost/latency/quality tradeoffs
- evaluator catch/miss analysis

## 7. Deployment readiness

Show:

- value case
- KPI tree
- delivery plan
- dependency map
- risk register
- pilot-readiness review
- executive update
- field feedback to product

## 8. Demo

Include:

- terminal walkthrough
- Braintrust screenshots or public-safe screenshots
- mini webpage link
- representative redacted traces
- generated eval cards
- deployment memo

## 9. Roadmap

Include:

- production trace sampling interface
- human annotation workflow
- policy versioning
- CI regression gate
- Braintrust + W&B adapter support
- OpenAI Evals adapter
- cost-aware routing
- partner-facing launch dashboard
- adoption analytics

---

# Claude Code + Codex operating model

## Recommendation

Use **Claude Code as the implementation driver** and **Codex as planner, QA reviewer, architecture critic, and eval-loop reviewer**.

This division is better than trying to make one agent do everything.

## Claude Code owns

- scaffolding repo
- implementing LangGraph app
- implementing Pydantic schemas
- writing synthetic tools
- generating datasets
- implementing deterministic graders
- integrating Braintrust
- writing scripts
- writing tests
- building static webpage
- refactoring code

## Codex owns

- reviewing PLAN/README for target-role signal
- critiquing architecture before large implementation changes
- QA of grader correctness
- test coverage review
- redaction-policy review
- eval result interpretation review
- PR review style feedback
- checking whether artifacts support the claims

## Human owner owns

- product thesis
- workflow realism
- approval boundaries
- failure taxonomy quality
- launch-readiness judgment
- executive narrative
- final README and demo script

Do not outsource the product judgment. That is the portfolio signal.

---

# Suggested first 10 build tasks

1. Create repo skeleton from PLAN v3.
2. Add `AGENT.md`, `AGENTS.md`, and `CLAUDE.md`.
3. Draft README skeleton with top-level product thesis.
4. Create `deployment/value_case.md`, `customer_workflow_map.md`, and `risk_register.md`.
5. Define Pydantic schemas for cases, state, agent outputs, traces, and grader results.
6. Build synthetic policies and tools for Financial Links.
7. Implement LangGraph runner for one Financial Links case.
8. Add local trace collector and deterministic skeleton graders.
9. Generate 30 hand-reviewed Financial Links cases.
10. Run the first baseline eval and create the first eval card.

---

# Demo storyline

```text
1. Here is the embedded-finance workflow and why a demo is not enough.
2. Here is the customer value case, KPI tree, and deployment plan.
3. Here is the LangGraph multi-agent architecture.
4. Here are the synthetic datasets and approval boundaries.
5. Here is the baseline run in Braintrust.
6. Here is where the orchestrator/evaluator failed, including a redacted trace.
7. Here is the prompt/tool/routing/evaluator change.
8. Here is the improved eval run.
9. Here is the tradeoff: quality improved, latency/cost changed.
10. Here is a failure converted into a regression test.
11. Here is the eval card and pilot recommendation.
12. Here is the webpage showing the full reliability and deployment loop.
```

Avoid:

- claiming production readiness;
- implying regulatory compliance;
- showing real fraud logic;
- exposing real product controls;
- over-indexing on UI polish;
- presenting synthetic scores as real-world performance.

---

# Final definition of done

The project is done when the repo can answer these questions with generated artifacts:

1. What embedded-finance workflows does this agent system support?
2. Who uses it?
3. What business outcome does it target?
4. What does the customer workflow look like before and after the agent?
5. Why is a multi-agent architecture appropriate?
6. What is the orchestrator allowed to decide?
7. What must remain human-approved?
8. What does good behavior mean by workflow?
9. What datasets test that behavior?
10. What traces prove what happened?
11. What graders measure routing, tools, policy, consent, schema, evaluator behavior, and communication quality?
12. Where did baseline fail?
13. What changed?
14. Did the change improve quality?
15. What did it cost in latency and spend?
16. What regressions are now protected?
17. What trace evidence is safe to share?
18. What launch recommendation follows from the eval?
19. What delivery risks remain?
20. What would be measured in pilot?
21. What feedback should go back to the platform/product team?

If the repo answers those questions clearly, it supports the target signal: **top 1% forward-deployed PM / Technical Deployment Lead capability in regulated embedded-finance AI deployment**.
