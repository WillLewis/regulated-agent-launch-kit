# Project Plan

This is the short execution index for Claude Code and Codex. The detailed source of truth remains [`PLAN_v3_openai_tdl_fde.md`](PLAN_v3_openai_tdl_fde.md).

When present, local agents should also read `.project-memory/goal-thesis.md` before architecture, README, or deployment-artifact work. That file is intentionally ignored so private thesis context can guide decisions without being published.

## Active Phase

**Next active implementation phase: Phase 1 - Deployment Narrative Before Code.**

Entry gate: Phase 0 scaffold must be present in the active worktree and tests must pass. If the latest scaffold work is still in a Claude worktree, merge or apply it before starting Phase 1 implementation.

## Current Phase Sequence

| Phase | Purpose | Core Outputs | Exit Gate |
|---|---|---|---|
| 0. Foundation And Operating Model | Establish the repo, agent operating model, and safety posture. | Repo scaffold, agent docs, private thesis reference, uv/bootstrap path, evaluator/grader split. | Scaffold tests pass; Codex/Claude roles are visible; private thesis remains ignored. |
| 1. Deployment Narrative Before Code | Define the simulated customer deployment before building agent behavior. | Workflow map, value case, KPI tree, acceptance criteria, risk register, dependency map. | Business outcomes map to eval metrics; approval boundaries and pilot constraints are explicit. |
| 2. Synthetic Domain Model And Schemas | Create the public-safe embedded-finance operating model. | Pydantic case/state/output/trace schemas, risk bands, approval matrix, synthetic policies, synthetic tools. | Synthetic-only constraints are encoded; consent, approval, and escalation rules are testable. |
| 3. Financial Links Vertical Slice | Prove one end-to-end controlled workflow. | Intake, orchestrator, Financial Links specialist, tools, evaluator, approval node, final response, trace. | One synthetic case runs end-to-end and emits local trace metadata. |
| 4. Deterministic Eval Loop | Separate runtime evaluator behavior from offline grading. | Offline graders, local eval CLI, failure taxonomy, local reports, optional Braintrust adapter. | Graders emit required structured results; local eval runs without external credentials. |
| 5. Baseline Dataset And Eval Card | Show baseline failures without inflating readiness. | Initial Financial Links dataset, baseline eval, failure summary, baseline eval card. | Visible failures are classified; launch posture is evidence-backed and not overstated. |
| 6. Redaction And Evidence Packaging | Make trace evidence public-safe while preserving diagnostic value. | Redaction script, redaction policy, redacted traces, evidence packs, redaction report. | Redacted traces preserve sequence and eval evidence; sensitive operational detail is removed. |
| 7. Incident-To-Regression Loop | Turn failures into durable tests. | Incident summaries, reviewed regression cases, regression pass/fail reports. | High-risk failures can become reviewed regression cases and appear in future evals. |
| 8. Improvement Pass And Comparison | Demonstrate an evidence-backed reliability improvement. | Product/system change, after eval, before/after comparison, cost/latency tradeoff. | At least one important metric improves or remains blocked for a clear reason. |
| 9. Expand Workflows | Extend coverage beyond the flagship workflow. | Credit Wellness/Offer Activation and Privacy/Identity datasets, policies, eval slices, cards. | At least two workflows are complete; three are preferred; dataset cards remain public-safe. |
| 10. Launch Readiness Artifacts | Translate eval results into deployment judgment. | Pilot readiness review, exec update, adoption plan, field feedback, launch/no-launch recommendation. | Recommendation is backed by generated reports, redacted evidence, and deployment docs. |
| 11. Public Demo Webpage | Present the reliability and deployment loop publicly. | Static webpage reading generated artifacts only. | Webpage contains no invented metrics and links claims back to artifacts. |

## Phase Done Rules

- Run the smallest relevant verification command before closing a phase; run the broader suite when feasible.
- Do not claim improvement, readiness, or safety unless generated traces, eval reports, redacted evidence, or deployment docs support it.
- Keep raw traces, credentials, and private thesis context out of version control.
- Use Codex review at architecture, eval-loop, redaction/evidence, and launch-readiness gates.
- Update this file only when the execution sequence or active phase changes; keep detailed implementation notes in `PLAN_v3_openai_tdl_fde.md` or the relevant artifact.
