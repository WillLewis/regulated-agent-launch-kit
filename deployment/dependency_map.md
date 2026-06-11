# Dependency Map

> Dependencies between Phase 1 deployment artifacts and the Phase 2+ implementation work, organized so that a reviewer can see what blocks what before any agent code is written.

## Reading Order

This map is read alongside `PLAN.md` (phase status) and `deployment/delivery_plan.md`. A dependency arrow means "the right side cannot be done well without the left side."

## Technical Dependencies

| Implementation work | Depends on | Why |
|---|---|---|
| `app/schemas.py` Pydantic models (already scaffolded) | Phase 1 workflow map and approval matrix | Risk band, consent state, approval boundary, and handoff payload shapes need to match the workflow's decision points. |
| `app/orchestrator.py` and `app/evaluator.py` runtime | `deployment/customer_workflow_map.md` decision and approval points | Orchestrator routing rules and evaluator checks encode the workflow's decision points; if the workflow changes, these change. |
| Synthetic tools under `app/tools/` | Synthetic policies in `case_studies/financial_links_reliability/policies/` | Tool I/O matches the synthetic policy shape; tool selection correctness depends on the policy being authoritative. |
| `evals/graders.py` (already scaffolded) | `deployment/kpi_tree.md` leaf metrics | Each leaf metric in the KPI tree maps to at least one grader; without the tree, grader coverage is ad-hoc. |
| `scripts/run_eval.py` baseline runner | Synthetic dataset + Pydantic schemas + graders | Cannot run end-to-end until upstream artifacts exist; smoke path must work without external credentials. |
| Braintrust adapter | `configs/platform.yaml`, optional `BRAINTRUST_API_KEY` (per `.env.example`) | Adapter is a wrapper around local artifacts; local JSON path remains the source of truth. |
| Trace redaction (`scripts/redact_trace.py`) | `configs/redaction_policy.yaml` + raw trace structure | Cannot redact reliably until the trace structure is fixed; coverage report depends on the policy. |
| Mini webpage | All generated artifacts under `reports/`, `traces/redacted/`, `evidence_packs/`, `deployment/`, `case_studies/*/dataset_card.md` | Webpage must read generated artifacts only — never invent metrics. |

## Product / Content Dependencies

| Product work | Depends on | Why |
|---|---|---|
| Failure taxonomy curation (`configs/failure_taxonomy.yaml`) | `deployment/risk_register.md` | Each register risk has at least one corresponding failure label so risks are observable in eval output. |
| Approval matrix (`configs/approval_matrix.yaml`) | `deployment/customer_workflow_map.md` approval points | Approval rules per workflow + risk band must match the documented approval points. |
| Dataset cards (`case_studies/*/dataset_card.md`) | `deployment/value_case.md` hypotheses | Dataset slices must include the cases needed to test each hypothesis (consent, escalation, copy safety, latency). |
| Eval card (`scripts/generate_eval_card.py`, planned) | `deployment/acceptance_criteria.md` launch-gate conditions | Card's launch recommendation logic reads the launch gates verbatim; gates must be unambiguous. |
| Pilot readiness review (`deployment/pilot_readiness_review.md`, Phase 11) | All Phase 1 artifacts + first improved eval run | Cannot honestly say "ready" without the workflow, value case, KPIs, criteria, risks, and dependency clarity. |

## Human / Review Dependencies

| Review activity | Depends on | Why |
|---|---|---|
| Workflow realism review by human owner | `deployment/customer_workflow_map.md` | Synthetic-only stance is preserved only if the human owner confirms no real partner/customer detail bled in. |
| Failure taxonomy quality review | `configs/failure_taxonomy.yaml` + first baseline failure summary | Taxonomy labels are only useful if a reviewer can apply them without ambiguity to actual traces. |
| Codex architecture-critic pass | `AGENTS.md` "Codex review responsibilities" + the change being reviewed | Codex applies the deployment-architecture-critic checklist; the checklist needs to live in `AGENTS.md` (not only `.claude/agents/`) so Codex can read it. |
| Codex eval-loop review pass | `AGENTS.md` "Eval-loop reviewer" + grader/evaluator separation in `app/` and `evals/` | Reviewer enforces evaluator/grader split; without the separation in code, the review becomes narrative. |
| Codex redaction review pass | `AGENTS.md` "Redaction / evidence reviewer" + `configs/redaction_policy.yaml` + redacted traces | Redaction reviewer flags uncovered fields; cannot do so without redacted trace samples. |

## External-Credential Boundaries

The basic local smoke path (scaffold tests, schema/grader unit tests, dataset inspection, Phase 1 doc tests) **must not require external credentials**. Specifically:

- `make test` and `python -m pytest` succeed without `.env`.
- Braintrust is optional; tracing falls back to local JSON when `BRAINTRUST_API_KEY` is absent (per `.env.example`).
- Model-provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) are required only for live agent runs, never for the deterministic eval, grader, redaction, or scaffold paths.

## Cross-Cutting Dependencies

- **Public-safety hook** (`.claude/hooks/check_public_safety.py`) runs on every Write/Edit and is a soft check across all artifacts; not a substitute for human review.
- **Private thesis** (`.project-memory/goal-thesis.md`) is gitignored and not propagated into git worktrees. Agents working in a worktree must read it via the main repo absolute path or operate from session memory.
- **Synthetic-only stance** is a dependency of every artifact — violating it invalidates the rest of the chain.

## What This Map Is Not

- Not a Gantt chart. Owners and dates live in `deployment/delivery_plan.md`.
- Not a complete CI dependency graph — that lives in `Makefile` and (eventually) CI config.
