# Project Plan

The canonical phased build plan is [`PLAN_v3_openai_tdl_fde.md`](PLAN_v3_openai_tdl_fde.md). This file tracks status and locked decisions on top of that plan.

Local agent context should also read `.project-memory/goal-thesis.md` when present. That file is intentionally ignored so the private thesis can guide Claude Code and Codex without being published.

## Phase Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Repo skeleton, public-safety stance, Claude/Codex operating model | Complete | Scaffolding, hooks, subagents, `AGENTS.md` Codex review checklists, evaluator/grader skeletons, Makefile, `.env.example`. |
| Phase 1 — Deployment narrative and workflow map | Complete | Six artifacts under `deployment/` (workflow map, value case, KPI tree, acceptance criteria, risk register, dependency map). Verified by `tests/test_deployment_artifacts.py`. |
| Phase 2 — Synthetic Domain Model and Schemas | Active (contracts and v0 dataset in place; baseline smoke run pending) | Pydantic schemas for cases, state, agent outputs, traces, and grader results landed in `app/schemas.py`; synthetic Financial Links policy fixtures under `case_studies/financial_links_reliability/policies/`; synthetic connectivity tools in `app/tools/synthetic_connectivity_tools.py`; approval matrix updated for L2 consent-sensitive gating with band-independent grading flag; `configs/latency_budgets.yaml` added (synthetic, L0–L4). Runtime evaluator and offline graders extended with handoff, consent, and approval checks (kept separate). README `Synthetic Domain Model` exit gate cleared (see below). First Financial Links synthetic dataset slice (10 hand-authored cases) now lives at `case_studies/financial_links_reliability/data/cases_v0.jsonl` with a 4-case `evals/smoke.jsonl`, a structural validator at `scripts/validate_dataset.py`, a `make dataset-test` target, and tests in `tests/test_dataset_validation.py`; the dataset card has been rewritten to match. Phase 2 remains active because no baseline agent run / eval report has been produced yet. |
| Phases 3–12 | Not started | See `PLAN_v3_openai_tdl_fde.md`. |

## Locked Decisions for Phase 2/3

These defaults resolve open questions surfaced in `deployment/risk_register.md` so Phase 2 schemas and Phase 3 runtime can be designed against them without re-litigating each time. They apply only to this synthetic deployment-readiness lab and do not encode any production policy.

- **R1 — L2 consent re-confirmation:** L2 consent-sensitive cases require explicit re-confirmation or human approval before user-impacting guidance is drafted. Schemas should make `consent_state` and `consent_reconfirmed` first-class fields; the runtime `EvaluatorNode` must block at L2+ without re-confirmation.
- **R4 — Synthetic latency budgets:** Latency budgets are defined per risk band (`L0`–`L4`) and live in `configs/` (e.g., `configs/latency_budgets.yaml` or an extension of `configs/risk_weights.yaml`). Values are synthetic and must be labeled as such anywhere they surface; they must not imply production thresholds.
- **R8 — Approval gating independence:** The approval-boundary grader must compute the *true* required risk band from case features and the approval matrix, not consume the orchestrator's declared band. An orchestrator misroute that lowers the declared band must not bypass the approval gate in eval scoring.
- **R9 — Pydantic-enforced handoff:** Handoff payloads between orchestrator and specialist agents are Pydantic-enforced at runtime, not validated only at trace time. The handoff payload model lives in `app/schemas.py`.

## Phase 2 Exit Gate — README Domain Model Documentation

Phase 2 is not complete until `README.md` is updated to reflect the locked synthetic domain model. After the Phase 2 schemas, approval matrix, and synthetic tools are implemented and tested, add a concise **Synthetic Domain Model** section to `README.md` covering:

1. **Synthetic case** — the input case schema.
2. **Runtime case state** — the LangGraph state object passed between nodes.
3. **Agent output** — the specialist-agent output contract.
4. **Approval matrix** — risk-band to required-approver mapping (from `configs/`).
5. **Synthetic tools** — the Financial Links synthetic tool surface.

Requirements for that future README section:

- Examples must be generated from, or aligned to, the actual implemented schemas and configs — no drift from code.
- Every example is explicitly labeled synthetic and public-safe.
- No production-readiness or regulatory-compliance claims.
- No real customer data, real thresholds, real vendor schemas, SAR-adjacent examples, or production controls.
- Section stays explanatory, not exhaustive — prefer linking to source modules and configs over reproducing them.

Do not draft this README section until the Phase 2 contracts exist and the relevant tests pass. The purpose of recording the requirement here is to make documentation an explicit Phase 2 exit gate rather than a follow-up afterthought.

**Status:** Cleared. `README.md` now carries a `## Synthetic Domain Model` section covering the five concepts above, plus an evaluator/grader separation note, the R8 approval-grading asymmetry, and a pointer to `configs/latency_budgets.yaml`. Verified by `tests/test_readme.py`.
