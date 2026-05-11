# Project Plan

The canonical phased build plan is [`PLAN_v3_openai_tdl_fde.md`](PLAN_v3_openai_tdl_fde.md). This file tracks status and locked decisions on top of that plan.

Local agent context should also read `.project-memory/goal-thesis.md` when present. That file is intentionally ignored so the private thesis can guide Claude Code and Codex without being published.

## Phase Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Repo skeleton, public-safety stance, Claude/Codex operating model | Complete | Scaffolding, hooks, subagents, `AGENTS.md` Codex review checklists, evaluator/grader skeletons, Makefile, `.env.example`. |
| Phase 1 — Deployment narrative and workflow map | Complete | Six artifacts under `deployment/` (workflow map, value case, KPI tree, acceptance criteria, risk register, dependency map). Verified by `tests/test_deployment_artifacts.py`. |
| Phase 2 — Synthetic Domain Model and Schemas (Financial Links flagship) | Complete | Pydantic schemas, synthetic Financial Links policy fixtures, synthetic connectivity tools, approval matrix (L2 consent-sensitive gating with band-independent grading flag per R8), `configs/latency_budgets.yaml`, runtime evaluator + offline graders (kept separate), the README `Synthetic Domain Model` exit gate, and the v0 dataset slice (10 hand-authored cases + 4-case smoke slice + `scripts/validate_dataset.py` + `make dataset-test`) are all in place. Coverage for the other workflows (`credit_wellness_offer_activation`, `privacy_identity_alert_triage`, `subscription_action`) is deferred to the Expand Workflows phase. |
| Phase 3 — Financial Links Vertical Slice | Active | Deterministic single-case runner at `app/runner.py`; specialist module `app/agents/financial_links_reliability_agent.py`; CLI `scripts/run_case.py`; end-to-end tests in `tests/test_runner.py` covering smoke, L2 expired-consent escalation, adversarial force-completion refusal, and trace shape. Still pending: full v0 baseline run with grader output, before/after iteration, a LangGraph-backed orchestration once the deterministic slice is stable. |
| Expand Workflows — Credit Wellness + Privacy datasets | Deferred | `credit_wellness_offer_activation` and `privacy_identity_alert_triage` dataset slices are not in Phase 3 scope. They live after the Financial Links baseline eval and improvement loop are honest. |
| Phases 4–12 | Not started | See `PLAN_v3_openai_tdl_fde.md`. |

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
