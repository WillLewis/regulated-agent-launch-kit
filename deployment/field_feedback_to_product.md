# Field Feedback To Product — Financial Links Reliability (synthetic)

> Synthetic field-feedback log. It converts what the eval loop surfaced on the
> Financial Links slice into reusable product/platform requirements. Every
> learning cites a generated artifact; all data is fabricated for this lab and
> implies no production, regulatory, or partner claim.

## Deployment Learnings

Eval-loop findings generalized into platform/product asks. Each row names the
evidence and the reusable requirement (not a Financial-Links-only patch):

| # | Learning (from this slice) | Evidence | Category | Reusable product/platform ask |
|---|---|---|---|---|
| F1 | Substring/lexical unsupported-claim grading has a blind spot for paraphrase, safe-negation, and cross-sentence traps. | `reports/llm_adversarial_v1_semantic_audit_summary.md` (lexical `0/12`; model/NLI `3` semantic-only) | Eval platform improvement | First-class semantic/NLI grading primitive that runs alongside deterministic graders, not as a bolt-on. |
| F2 | A deterministic `12/12` pass is not a copy-safety guarantee — the "improved" profile carried *more* semantic flags. | `reports/adversarial_v1_eval_card.md` (improved `12/12`) vs `semantic_audit_summary.md` (`v1` > `v0` flags) | Model behavior issue | Separate "offline-pass" from "semantically safe" in eval reporting so a green card cannot imply copy safety. |
| F3 | Single-run eval cards overstate stability; run-to-run variance is real. | `reports/llm_adversarial_v1_repeat_summary.md` (passed `7–12/12` over 10 runs) | Eval platform improvement | Built-in repeat-run/variance aggregation as a default, with a "single run ≠ robustness" guardrail in the UI. |
| F4 | Redaction must preserve eval evidence while dropping draft text; raw model decisions quote draft spans. | `evidence_packs/financial_links_llm_adversarial_v1/regressions/regressions_semantic_adversarial_v1_decisions.json` (empty `evidence_spans`) | Trace visualization need / Policy or versioning gap | A draft-span-free "decision artifact" pattern (aggregate counts + authored provenance) as a reusable redaction primitive. |
| F5 | Approval boundaries are `draft_only`; no real side-effecting action is ever suspended. | `configs/approval_matrix.yaml` (`action_boundary: draft_only` on every rule) | SDK or tool integration gap | A real human-approval *suspension* primitive that gates an actual tool call, so approval can be tested end-to-end. |
| F6 | LLM latency (8–9.4 s/case) dwarfs the synthetic latency envelopes used for the deterministic runner. | `reports/llm_adversarial_v1_repeat_summary.md` vs `configs/latency_budgets.yaml` | Customer adoption blocker | Per-risk-band latency/cost budgeting that distinguishes deterministic from model-backed paths. |

## Product Feedback Categories

- SDK or tool integration gap.
- Eval platform improvement request.
- Model behavior issue.
- Trace visualization need.
- Policy or versioning gap.
- Customer adoption blocker.

## Feedback Loop

How a failure becomes a product requirement, with the worked example already in
the repo:

1. **Failure surfaces in an eval artifact** — e.g., the model/NLI audit flags a
   draft the lexical grader cleared (`semantic_audit_summary.md`).
2. **Reviewer note → incident** — the `compliance_reviewer`
   (`deployment/adoption_plan.md`) records it; it is not silently closed.
3. **Incident → `pending_review` regression seed** — pinned (with no raw draft
   text) into
   `case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl`
   and made replayable credential-free
   (`make regression-replay-adversarial-v1-semantic`).
4. **Seed → categorized product ask** — the seed's failure mode is tagged with a
   category above (F1/F2 for the semantic blind spot) and lands here as a reusable
   requirement, so the same gap informs the platform, not just this workflow.
5. **Ask → risk register** — if it changes deployment risk, it updates
   `deployment/risk_register.md` (the semantic blind spot is the live instance of
   R2).

This loop is what keeps `deployment/exec_update.md` honest: each "what changed"
line traces back to an artifact and forward to a product or risk action.
