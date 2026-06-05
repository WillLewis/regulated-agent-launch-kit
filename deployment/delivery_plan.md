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
| M7 | Semantic grader hardened to a blocking gate | **Next** | (planned) `unsupported_claim_semantic` as a tracked CI gate | Compliance reviewer | M6, expanded dataset | Sustained `0` semantic-only `UNSAFE_CUSTOMER_COMMS` across multiple runs |
| M8 | Dataset expansion beyond 12 cases | Done | `case_studies/financial_links_reliability/evals/adversarial_v2.jsonl` (24-case deterministic slice; `reports/adversarial_v2_eval_card.md`) | Human owner | M5, `risk_register.md` R7 | Broader slice validated; `improved_v0` 24/24, `baseline_v0` 15/24 across 3 labels; credential-free |
| M9 | Real action-suspension gate exercised | **Next** | (planned) side-effecting synthetic tool gated by `HumanApprovalNode` | Partner support lead | M2, `configs/approval_matrix.yaml` | Approval suspends an actual action end-to-end (today `draft_only` only) |
| M10 | Mini webpage over generated artifacts | Deferred | (planned) `web/` reading `reports/`, `evidence_packs/`, `deployment/` | Deployment lead | M3–M6 | Reads generated artifacts only; invents no metric |

The pilot decision (`deployment/pilot_readiness_review.md`) stays
**NOT READY FOR PILOT** until at least M7 and M9 close (M8, the broader
adversarial v2 slice, is done; M7's semantic blocking gate is the next chunk).
M10 is presentation, not a readiness gate.

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
