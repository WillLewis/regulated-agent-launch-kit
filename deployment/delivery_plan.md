# Delivery Plan — Financial Links Reliability (synthetic)

> Synthetic delivery plan for the Financial Links flagship slice. Owners are
> fabricated synthetic roles (`deployment/risk_register.md`,
> `configs/approval_matrix.yaml`). "Done" rows cite a generated artifact; nothing
> here is a production, schedule, or compliance commitment.

## Phases

1. Repo skeleton and public-safety stance.
2. Deployment narrative and workflow map.
3. Synthetic domain model.
4. LangGraph multi-agent runner.
5. Local traces and Braintrust adapter.
6. Baseline eval and failure analysis.
7. Improvement pass and before/after comparison.
8. Redaction, evidence pack, and regression workflow.
9. Eval card, pilot readiness review, and mini webpage.

## Milestones

Status is grounded in artifacts, not narrative. Acceptance gates reference
`deployment/acceptance_criteria.md`.

| # | Milestone | Status | Target artifact (evidence) | Synthetic owner | Depends on | Acceptance gate |
|---|---|---|---|---|---|---|
| M1 | Workflow mapped + value/KPI/risk artifacts | Done | `deployment/customer_workflow_map.md`, `value_case.md`, `kpi_tree.md`, `risk_register.md` | Deployment lead | Phase 1 | All Phase 1 docs substantive + free of placeholder stubs (`tests/test_deployment_artifacts.py`) |
| M2 | Controlled multi-agent runner | Done | `app/` orchestrator/evaluator/specialist + `tests/test_runner.py` | Deployment engineer | M1, `app/schemas.py` | `Orchestrator → Specialist → Evaluator → HumanApproval` pattern, no swarm |
| M3 | Deterministic baseline→improved loop | Done | `reports/adversarial_v1_eval_card.md` (`4/12` → `12/12`) | Deployment engineer | M2, `evals/graders.py` | All planted failure labels → `0`; `evaluator_catch_rate` `12/12` |
| M4 | Redaction + public-safe evidence pack | Done | `evidence_packs/financial_links_llm_adversarial_v1/` | Risk reviewer | M3, `configs/redaction_policy.yaml` | Redacted traces preserve eval evidence; redaction report lists fields |
| M5 | Incident→regression loop | Done | `case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl` + replay fixture | Compliance reviewer | M3 | Offline semantic grader fires `3/3` (`make regression-replay-adversarial-v1-semantic`) |
| M6 | Model/NLI semantic audit (once) | Done | `reports/llm_adversarial_v1_semantic_audit_summary.md` (3 semantic-only flags) | Compliance reviewer | M3 (drafts on disk) | Aggregate-only, no raw spans; bundled in evidence pack |
| M7a | Semantic gate **infrastructure** wired (credential-free) | Done | `scripts/check_semantic_gate.py` + `tests/test_semantic_gate.py`; negative-control + pass-path Make targets | Compliance reviewer | M6 | Reusable blocking gate exists, fails closed when the lane is absent, and blocks the 3 known-bad seeds (negative control) |
| M7b | Adversarial v2 LLM + semantic-gate **pipeline** wired | Done (rails); the credentialed run was subsequently executed — see M7 | Opt-in credentialed targets (`eval-adversarial-v2-llm-v0/v1`, `eval-card-adversarial-v2-llm`, `semantic-model-decisions-adversarial-v2-llm-v0/v1`), on-disk summary target, and a credential-free `semantic-gate-adversarial-v2-llm` (re-keys candidate verdicts under `improved_v0` via `scripts/build_semantic_replay_adversarial_v2_llm.py`); `tests/test_adversarial_v2_llm_targets.py` | Compliance reviewer | M7a, M8 | Targets exist + gate fires credential-free on synthetic verdicts (pass on clean, block on flagged); raw artifacts gitignored. The credentialed audit has since been run (M7) |
| M7 | Semantic gate run on a credentialed audit | **Executed once; gate BLOCKED — M7 stays OPEN** | Card `reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md` (deterministic `v0` 20/24 → `v1` 24/24); `reports/llm_adversarial_v2_semantic_audit_summary.{md,json}` (lexical `0/24`, model/NLI **14 semantic-only `UNSAFE_CUSTOMER_COMMS`** — 8 in `v0`, 6 in `v1`); the 14 are pinned as `pending_review` regression seeds `regressions_semantic_adversarial_v2.jsonl` + credential-free replay fixture | Compliance reviewer | M7b + the credentialed run (done) | **NOT met.** The bar is sustained `0` semantic-only flags across multiple credentialed runs; the one run executed produced **14** and the gate **blocked**. M7 remains open; raw reports/traces/decisions stay gitignored |
| M8 | Dataset expansion beyond 12 cases | Done | `case_studies/financial_links_reliability/evals/adversarial_v2.jsonl` (24-case deterministic slice; `reports/adversarial_v2_eval_card.md`) | Human owner | M5, `risk_register.md` R7 | Broader slice validated; `improved_v0` 24/24, `baseline_v0` 15/24 across 3 labels; credential-free |
| M9 | Synthetic action-suspension gate **infrastructure** | Done (synthetic harness; separate from the draft_only FL loop) | `app/action_suspension.py` (real LangGraph that interrupts before `HumanApprovalNode`), `app/tools/synthetic_action_tools.py`, `evals/action_suspension_grader.py`, `scripts/run_action_suspension_demo.py`, traces under `traces/local/action_suspension/`, `tests/test_action_suspension.py` | Partner support lead | M2 | Proven credential-free: a synthetic side-effecting action is **suspended before execution**, never executes on reject/missing-approval (fail-closed), and executes **exactly once** when approved. This is infrastructure on a separate harness — the live FL loop stays `draft_only`; it is not a production action gate |
| M10 | Mini webpage over generated artifacts | Deferred | (planned) `web/` reading `reports/`, `evidence_packs/`, `deployment/` | Deployment lead | M3–M6 | Reads generated artifacts only; invents no metric |

The pilot decision (`deployment/pilot_readiness_review.md`) stays
**NOT READY FOR PILOT** — the gating blocker is now **M7**. M8 (broader
adversarial v2 slice), M7a (semantic gate *infrastructure*), M7b (v2 LLM gate
pipeline wired), and M9 (action-suspension *infrastructure*) are done; **M7 has
now been run once on a real credentialed audit and the semantic gate BLOCKED** —
the model/NLI grader flagged 14 semantic-only `UNSAFE_CUSTOMER_COMMS` drafts
(`reports/llm_adversarial_v2_semantic_audit_summary.md`) that the lexical grader
cleared. That is the opposite of the acceptance bar (sustained zero semantic-only
findings across multiple runs), so M7 stays open and the 14 are pinned as
`pending_review` regression seeds. The 14 findings are translated into a
credential-free, public-safe **failure analysis + remediation plan**
(`reports/llm_adversarial_v2_semantic_failure_analysis.md`; `make
semantic-failure-analysis-adversarial-v2`) that breaks them down by profile /
risk band / category, flags the 2 designed-safe calibration cases as ambiguous
(triage before tuning), and defines the acceptance gates and sustained-zero
evidence required to close M7 — no prompt tuning or rerun was performed. M9
proved the suspension *mechanism* on a
separate synthetic harness; wiring it into a live action path (beyond
`draft_only`) is a later product decision, not a pilot prerequisite. M10 is
presentation, not a readiness gate.

## Review Gates

Codex review checkpoints, mirroring the checklists in `AGENTS.md` "Codex review
responsibilities". Each gate blocks merge of the change class it covers.

| Gate | When it runs | What it blocks | Checklist source |
|---|---|---|---|
| Architecture critic | Changes to architecture, workflow, deployment artifacts, delivery plan | Unmapped workflow, implicit approval boundaries, components with no grader, claims without artifacts | `AGENTS.md` "Deployment architecture critic" |
| Eval-loop reviewer | Changes to graders, evaluator checks, datasets, taxonomy, regression cases, eval reports | Non-deterministic grading where deterministic is possible; evaluator/grader coupling; baseline-vs-improved claims unbacked by reports | `AGENTS.md` "Eval-loop reviewer" |
| Redaction / evidence reviewer | Changes to redaction policy, redaction scripts, redacted traces, evidence packs | Lost node/tool/evaluator/grader sequence; leaked identifiers/draft text/raw trace paths; evidence not traceable to redacted artifacts | `AGENTS.md` "Redaction / evidence reviewer" |
| Launch-readiness review | Before any posture change in `deployment/pilot_readiness_review.md` or `exec_update.md` | Posture change not backed by the acceptance gates in `deployment/acceptance_criteria.md` | `deployment/acceptance_criteria.md` launch gates |

Independent confirmation of these gates having teeth is on record: the redaction /
evidence reviewer pass on the evidence-pack regression bundle verified the
public-safety guards refuse raw model decision payloads, raw draft text, and raw
trace paths.
