@AGENTS.md

# Claude Code Instructions

Claude Code is the primary implementation driver for this project. Follow the shared agent instructions above, then apply these Claude-specific working rules.

---

## Working mode

0. If `.project-memory/goal-thesis.md` exists, read it as private local context. Do not paste its contents into public artifacts.
1. Start every substantial task by reading `PLAN.md` or `PLAN_v3_openai_tdl_fde.md`, `README.md` if present, and the relevant files for the requested area.
2. Make a short implementation plan before editing more than one file.
3. Prefer small, reviewable changes over large rewrites.
4. After code changes, run the smallest relevant verification command. If no test exists, create one or document why verification is not possible yet.
5. Summarize what changed, what was verified, and what remains risky.

---

## Product bar

The purpose of this repo is to demonstrate top 1% Forward Deployed PM / Technical Deployment Lead capability. Do not optimize for a shallow demo. Optimize for artifacts that prove deployment judgment:

- workflow mapping;
- business-value hypothesis;
- controlled multi-agent architecture;
- traceability;
- deterministic-first evals;
- failure taxonomy;
- redacted evidence;
- incident-to-regression loop;
- launch-readiness recommendation;
- delivery leadership artifacts.

If a proposed change does not improve this signal, push back or deprioritize it.

---

## Implementation priorities

When starting from an empty or partial repo, implement in this order:

1. Repo skeleton.
2. README thesis and public-safety stance.
3. Deployment docs under `deployment/`.
4. Pydantic schemas for cases, graph state, traces, and grader results.
5. Financial Links synthetic policies/tools/cases.
6. LangGraph runner for one end-to-end case.
7. Trace collector.
8. Deterministic graders.
9. Braintrust adapter and local eval artifacts.
10. Baseline eval report and eval card.
11. Improvement pass and before/after comparison.
12. Redaction and evidence packaging.
13. Incident-to-regression.
14. Additional datasets.
15. Mini webpage.

---

## Coding conventions

- Use Python type hints throughout.
- Use Pydantic models for external-facing schemas and trace/eval artifacts.
- Keep prompts, policies, and dataset definitions versioned and inspectable.
- Keep graders pure where possible.
- Keep the EvaluatorNode runtime checks separate from offline graders.
- Keep Braintrust integration behind an adapter so local evals still work without credentials.
- Never require external credentials for the basic smoke test path.
- Prefer deterministic fixtures for tests.

---

## Safety and data rules

Do not introduce:

- real user data;
- real employer/customer workflows;
- real fraud scenarios;
- production risk thresholds;
- real credit bureau schemas;
- proprietary vendor names;
- SAR-adjacent examples;
- adversarial bypass recipes.

When in doubt, abstract into bands, synthetic IDs, or synthetic policy labels.

---

## Eval discipline

For every eval-related change:

- define the metric being improved;
- identify the dataset slice affected;
- run or create a smoke eval;
- preserve before/after artifacts;
- update failure taxonomy if a new failure mode appears;
- avoid claiming improvement unless the generated report supports it.

---

## Redaction discipline

For trace or evidence-pack work:

- preserve node sequence, tool sequence, evaluator results, grader results, risk band, and latency/cost metadata;
- remove or abstract identifiers, raw sensitive text, exact amounts, internal rule names, provider/source details, and operational controls;
- produce a redaction report listing removed fields and uncovered fields.

---

## Webpage rules

The webpage is the final phase, not the first phase. It should read generated artifacts from `reports/`, `traces/redacted/`, `evidence_packs/`, `case_studies/*/dataset_card.md`, and `deployment/`.

Do not build a mock dashboard that invents metrics. The mini webpage must visualize the actual eval artifacts.

---

## Coordination with Codex

Codex should be used as planner, QA reviewer, architecture critic, and eval-loop reviewer. Before large changes, prepare a clear summary that Codex can review:

```text
Goal:
Files changed:
Architecture decision:
Artifacts produced:
Tests run:
Open risks:
Questions for review:
```

After Codex review, incorporate only feedback that improves reliability, deployment readiness, or clarity. Do not churn the repo for cosmetic suggestions.
