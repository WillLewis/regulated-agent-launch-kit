# Agent Instructions — Regulated AI Deployment Kit

## Mission

This repository is a portfolio-grade deployment-readiness case study for regulated embedded-finance AI systems. The goal is to demonstrate top 1% Forward Deployed PM / Technical Deployment Lead capability, not to build a flashy demo.

When present, read `.project-memory/goal-thesis.md` for private local project context. That file is intentionally ignored; use it to guide decisions, but do not copy its contents into public artifacts.

Every implementation choice should make the repo better at proving that the owner can map a regulated workflow, build a controlled multi-agent system, instrument traces, evaluate reliability, improve with evidence, govern sensitive artifacts, and make a launch/no-launch recommendation.

If a change does not improve that signal, avoid it.

---

## Non-negotiable standards

1. **Synthetic only.** Do not add real customer data, real fraud patterns, real thresholds, real partner configs, real credit attributes, real vendor schemas, or SAR-adjacent examples.
2. **Deployment-readiness over demo polish.** Prioritize workflow maps, evals, traces, failure analysis, approval boundaries, redaction, regression tests, and launch memos over UI flash.
3. **Deterministic-first evals.** Use deterministic graders for schema, tool use, policy retrieval, consent, approvals, routing, and prohibited actions. Use LLM/rubric grading only where subjectivity is unavoidable.
4. **Local artifacts required.** Braintrust/W&B outputs are useful, but every run must also create local JSON/Markdown artifacts reviewable without platform credentials.
5. **Evaluator and grader separation.** The runtime EvaluatorNode checks outputs before final response. Offline graders independently evaluate whether the EvaluatorNode caught issues.
6. **Human approval boundaries are product decisions.** Do not automate high-risk actions just because it is technically possible.
7. **Claims require artifacts.** README/webpage claims must be backed by generated traces, eval reports, redacted evidence packs, or deployment docs.
8. **No false production claims.** The repo uses synthetic workflows and should never imply regulatory compliance or production readiness.

---

## Preferred stack

- Python for the agent system, scripts, evals, and reports.
- LangGraph for orchestration.
- LangChain components only where useful for model/tool abstraction.
- Pydantic for schemas.
- Braintrust as primary tracing/eval platform.
- W&B Weave optional only after the Braintrust/local path works.
- JSONL/YAML for datasets, policies, configs, rubrics, and failure taxonomy.
- Vite + React or static Next.js export for the final mini webpage.
- pytest for tests.
- Prefer `uv` for Python environment management unless the repo has already standardized something else.

---

## Target repo shape

```text
app/                  # LangGraph app, state, schemas, orchestrator, evaluator, agents, tools
case_studies/         # synthetic workflow datasets, policies, traces, reports
evals/                # graders, failure classifier, risk scoring, platform adapters
scripts/              # CLI scripts for datasets, evals, redaction, reports, regressions
configs/              # taxonomy, redaction policy, risk weights, approval matrix
deployment/           # workflow map, value case, delivery plan, risk register, exec memo
reports/              # generated eval cards and before/after comparisons
evidence_packs/       # redacted traces and shareable evidence
web/                  # final mini webpage
tests/                # unit/integration tests
```

---

## Required architecture

Use a controlled multi-agent pattern:

```text
Synthetic case
  → IntakeNormalizer
  → OrchestratorAgent
  → Specialist agent
  → Synthetic tools / policy retrieval
  → EvaluatorNode
  → HumanApprovalNode when required
  → FinalResponseComposer
  → Trace + eval artifacts
```

Primary specialist agents:

- `FinancialLinksReliabilityAgent`
- `CreditWellnessAgent`
- `OfferActivationAgent`
- `PrivacyIdentityAgent`

Optional only if time allows:

- `SubscriptionActionAgent`

Do not create extra agents unless they make evaluation clearer.

---

## Required synthetic datasets

Build at least two; three is the target.

1. **Financial Links / connectivity reliability** — flagship dataset.
2. **Credit wellness + offer activation** — consent, safe credit language, conversion vs compliance.
3. **Privacy / identity alert triage** — high-risk escalation and unsupported-claim prevention.

Each dataset needs:

- dataset card;
- synthetic policies;
- routine cases;
- missing-info cases;
- high-risk cases;
- adversarial/misleading cases;
- regression-style cases;
- expected behavior fields;
- prohibited behavior fields.

---

## Required eval dimensions

Implement graders for:

- orchestrator routing accuracy;
- handoff completeness;
- required-tool use;
- prohibited-tool/action avoidance;
- policy retrieval;
- consent-boundary adherence;
- approval-boundary adherence;
- escalation correctness;
- schema validity;
- unsupported claims;
- hallucinated facts;
- EvaluatorNode catch rate;
- cost/latency;
- regression pass/fail;
- deployment readiness.

Every grader result should include:

```json
{
  "passed": true,
  "score": 1.0,
  "severity": "L2",
  "failure_label": null,
  "explanation": "...",
  "evidence": {...}
}
```

---

## Trace requirements

Every eval run should emit local traces with:

- trace ID;
- dataset ID;
- case ID;
- workflow;
- risk band;
- agent system version;
- policy version;
- orchestrator decision;
- specialist-agent path;
- handoff summary;
- tool calls, arguments, and outputs;
- evaluator checks;
- approval decision;
- final response;
- grader results;
- failure labels;
- latency;
- token/cost estimate.

Redacted traces must preserve sequence and eval evidence while removing sensitive operational detail.

---

## Deployment artifacts are mandatory

Create and maintain:

```text
deployment/customer_workflow_map.md
deployment/value_case.md
deployment/kpi_tree.md
deployment/delivery_plan.md
deployment/dependency_map.md
deployment/acceptance_criteria.md
deployment/risk_register.md
deployment/pilot_readiness_review.md
deployment/adoption_plan.md
deployment/exec_update.md
deployment/field_feedback_to_product.md
```

These artifacts are not filler. They are how the repo demonstrates deployment leadership.

---

## Coding rules

- Keep modules small and readable.
- Favor explicit schemas over loose dictionaries.
- Prefer pure functions for graders and redaction logic.
- Keep runtime evaluator checks separate from offline grading.
- Add tests for every grader, redaction policy, and regression workflow.
- Do not hide important behavior inside prompts alone; encode critical checks in code where possible.
- Log enough metadata to debug failures.
- Do not add heavy dependencies without a clear reason.
- Update README/PLAN when architecture or CLI behavior changes.

---

## Testing expectations

When changing Python code, run the smallest relevant test first, then the broader suite when feasible.

Preferred commands once the repo exists:

```bash
uv run pytest tests/test_graders.py
uv run pytest tests/test_redaction.py
uv run pytest tests/test_graph_routing.py
uv run pytest
```

For eval changes, run a small smoke dataset before a full dataset:

```bash
uv run python scripts/run_eval.py --dataset case_studies/financial_links_reliability/evals/smoke.jsonl --agent-system-version baseline_v0
```

If a test command does not exist yet, create the minimal test harness needed rather than skipping verification.

---

## Build order preference

1. Repo skeleton and README thesis.
2. Deployment docs: workflow map, value case, KPI tree, risk register.
3. Schemas and synthetic policies.
4. Financial Links synthetic tools and 30 hand-reviewed cases.
5. LangGraph single-workflow runner.
6. Trace collector.
7. Deterministic graders.
8. Braintrust adapter.
9. Baseline eval.
10. Failure analysis and first eval card.
11. Improvement and before/after run.
12. Redaction and evidence pack.
13. Incident-to-regression.
14. Additional datasets.
15. Mini webpage.

---

## Definition of done for any feature

A feature is done only when:

- it supports the deployment-readiness narrative;
- it has tests or a documented verification path;
- it emits or consumes the expected local artifacts;
- it respects synthetic-only and redaction constraints;
- it is reflected in README/PLAN/docs if user-facing;
- it does not weaken the top 1% FDE/TDL signal.

---

## Review checklist

Before presenting work as complete, check:

- Does the change make the system more measurable?
- Does it clarify the workflow, risk, or launch decision?
- Does it preserve public safety?
- Are artifacts generated rather than hand-waved?
- Are baseline and improved results honestly represented?
- Are cost/latency/quality tradeoffs visible?
- Would a deployment lead or FDE respect the judgment shown here?

---

## Codex review responsibilities

Codex (and any LLM-based reviewer that cannot read `.claude/agents/`) acts as planner, architecture critic, eval-loop reviewer, and redaction reviewer for this repo. The checklists below mirror the Claude subagents in `.claude/agents/` so Codex applies the same standards.

Across all review modes:

- Review for **deployment-readiness signal** (workflow mapping, human-approval boundaries, measurable evals, redaction discipline, launch-decision artifacts), not demo polish.
- Treat README, webpage, and report claims as acceptable **only when supported by generated artifacts** — traces, eval reports, redacted evidence packs, or deployment docs. Flag any claim that is not.
- Read `.project-memory/goal-thesis.md` if present, but never quote, summarize, or copy it into public files.
- Order findings by deployment risk. Cite file paths and give concrete remediation.

### Deployment architecture critic

Use when reviewing changes to architecture, workflows, deployment artifacts, or delivery plans.

- The customer workflow is mapped before automation is built.
- Human-approval boundaries are explicit per workflow and risk band.
- Architecture choices are measurable in evals — each component maps to at least one grader.
- Dependencies, risks, and launch constraints are visible in `deployment/`.
- README and webpage claims trace back to generated artifacts.

### Eval-loop reviewer

Use when reviewing graders, evaluator checks, datasets, failure taxonomy, regression cases, or eval reports.

- Grading is **deterministic-first** for schema, routing, tools, policy, consent, approval, escalation, and prohibited-action checks.
- The runtime `EvaluatorNode` and offline graders remain **separate** (different modules, different return types) so the system can measure whether the evaluator caught issues.
- Failure labels are specific enough to drive regression cases.
- Baseline-vs-improved claims are supported by generated reports, not narrative.
- Regression cases preserve both expected and prohibited behavior.

### Redaction / evidence reviewer

Use when reviewing redaction policy, redaction scripts, redacted traces, or evidence packs.

- Redaction preserves node sequence, tool sequence, evaluator outcomes, grader outcomes, risk band, and latency/cost metadata.
- Redaction removes identifiers, raw sensitive text, exact amounts, internal rule names, provider/source details, and production controls.
- A redaction report lists removed fields and uncovered fields.
- README and webpage evidence is traceable back to redacted artifacts and never to raw traces.

Flag any field that could expose sensitive operational detail or that would let a public artifact make a production claim.
