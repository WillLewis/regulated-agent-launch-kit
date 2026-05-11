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

Active phase: Phase 2 — synthetic domain model and Pydantic schemas. See [`PLAN.md`](PLAN.md) for status and locked decisions, and [`PLAN_v3_openai_tdl_fde.md`](PLAN_v3_openai_tdl_fde.md) for the full phased plan.

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
