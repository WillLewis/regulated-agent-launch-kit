# Project Plan

The canonical phased build plan is [`PLAN_v3_openai_tdl_fde.md`](PLAN_v3_openai_tdl_fde.md). This file tracks status and locked decisions on top of that plan.

Local agent context should also read `.project-memory/goal-thesis.md` when present. That file is intentionally ignored so the private thesis can guide Claude Code and Codex without being published.

## Phase Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Repo skeleton, public-safety stance, Claude/Codex operating model | Complete | Scaffolding, hooks, subagents, `AGENTS.md` Codex review checklists, evaluator/grader skeletons, Makefile, `.env.example`. |
| Phase 1 — Deployment narrative and workflow map | Complete | Six artifacts under `deployment/` (workflow map, value case, KPI tree, acceptance criteria, risk register, dependency map). Verified by `tests/test_deployment_artifacts.py`. |
| Phase 2 — Synthetic Domain Model and Schemas | Active | Pydantic schemas for cases, state, agent outputs, traces, and grader results; synthetic policies and tools for the Financial Links workflow; failure-taxonomy and approval-matrix consistency. |
| Phases 3–12 | Not started | See `PLAN_v3_openai_tdl_fde.md`. |

## Locked Decisions for Phase 2/3

These defaults resolve open questions surfaced in `deployment/risk_register.md` so Phase 2 schemas and Phase 3 runtime can be designed against them without re-litigating each time. They apply only to this synthetic deployment-readiness lab and do not encode any production policy.

- **R1 — L2 consent re-confirmation:** L2 consent-sensitive cases require explicit re-confirmation or human approval before user-impacting guidance is drafted. Schemas should make `consent_state` and `consent_reconfirmed` first-class fields; the runtime `EvaluatorNode` must block at L2+ without re-confirmation.
- **R4 — Synthetic latency budgets:** Latency budgets are defined per risk band (`L0`–`L4`) and live in `configs/` (e.g., `configs/latency_budgets.yaml` or an extension of `configs/risk_weights.yaml`). Values are synthetic and must be labeled as such anywhere they surface; they must not imply production thresholds.
- **R8 — Approval gating independence:** The approval-boundary grader must compute the *true* required risk band from case features and the approval matrix, not consume the orchestrator's declared band. An orchestrator misroute that lowers the declared band must not bypass the approval gate in eval scoring.
- **R9 — Pydantic-enforced handoff:** Handoff payloads between orchestrator and specialist agents are Pydantic-enforced at runtime, not validated only at trace time. The handoff payload model lives in `app/schemas.py`.
