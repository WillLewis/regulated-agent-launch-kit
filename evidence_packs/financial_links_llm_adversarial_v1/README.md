# Evidence Pack — Financial Links LLM Adversarial v1

> This evidence pack is generated from a fully synthetic local eval run on the 12-case Financial Links adversarial v1 slice. Identifiers, policies, partner configurations, and risk bands are fabricated for this deployment-readiness lab. Both compared profiles call a real LLM via the credential-gated path, but every case in the dataset is synthetic and no real customer data is involved. Raw LLM traces and the raw JSON eval reports are intentionally excluded from this pack and from git tracking; only redacted artifacts ship here. Nothing in this pack implies model safety, production readiness, regulatory compliance, or partner endorsement. One credentialed run on a 12-case synthetic slice is not enough evidence to claim a prompt is robust.

## What this pack contains

This is a public-safe view of the local synthetic Financial Links
**adversarial v1 (12-case) LLM candidate comparison**. The compared
profiles are `llm_candidate_v0` (Before) and `llm_candidate_v1` (After),
both run against the expanded 12-case adversarial v1 slice. Every artifact
below is generated from on-disk inputs:

- `eval_card.md` — Before/After candidate_v0-vs-candidate_v1 comparison eval card (markdown) on the 12-case adversarial v1 slice.
- `improvement_memo.md` — Concise evidence-backed prompt-improvement memo.
- `llm_candidate_v0_eval.redacted.json` — candidate_v0 (Before) JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_v0_eval.redaction_report.json` — Redaction report for the candidate_v0 JSON eval.
- `llm_candidate_v1_eval.redacted.json` — candidate_v1 (After) JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_v1_eval.redaction_report.json` — Redaction report for the candidate_v1 JSON eval.
- `traces/redacted/candidate_v0/case_fl_adv_v1_001.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_002.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_003.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_004.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_005.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_006.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_007.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_008.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_009.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_010.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_011.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_012.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v1_001.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_002.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_003.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_004.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_005.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_006.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_007.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_008.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_009.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_010.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_011.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v1_012.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_001.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_002.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_003.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_004.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_005.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_006.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_007.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_008.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_009.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_010.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_011.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_012.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v1_001.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_002.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_003.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_004.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_005.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_006.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_007.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_008.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_009.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_010.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_011.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v1_012.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `semantic_audit_aggregate.json` — Aggregate-only model/NLI semantic audit: counts, enum histograms, synthetic case IDs/risk bands, confidence ranges, and cost. Derived from the gitignored raw decision files; no draft text, model reasoning, or quoted spans are included.
- `semantic_audit_summary.md` — Human-readable public-safe model/NLI semantic audit summary (aggregate-only).
- `regressions/regressions_semantic_adversarial_v1.jsonl` — Pending_review synthetic semantic-only regression seeds — the model/NLI UNSAFE_CUSTOMER_COMMS drafts the lexical grader cleared (a lexical blind spot). Case-superset records linked to the public semantic audit summary; no raw trace path or raw draft text.
- `regressions/regressions_semantic_adversarial_v1_decisions.json` — Credential-free SemanticDecision replay fixture: feeding it to run_eval.py --semantic-decisions with the deterministic improved_v0 profile fires the offline unsupported_claim_semantic grader on every seed with no model call. evidence_spans empty; rationale is authored provenance, not raw draft text.

The redacted traces under `traces/redacted/candidate_v0/` and
`traces/redacted/candidate_v1/` are paired with redaction reports
(`*.redaction_report.json`) that list removed, abstracted, preserved, and
uncovered top-level fields. The same applies to each candidate's redacted
JSON eval summary. The redaction policy used is
`configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw LLM traces (the gitignored per-candidate raw-trace directories) —
  intentionally excluded;
- the raw JSON eval reports (both candidate reports are gitignored; the
  pack ships only their redacted summaries) — intentionally excluded as
  raw payloads;
- raw model/NLI semantic-decision payloads — those quote short draft
  spans and remain gitignored under `reports/semantic_model_decisions/`.
  When a semantic audit has been run, this pack ships only the
  aggregate-only `semantic_audit_aggregate.json` (counts, enum histograms,
  synthetic case IDs/risk bands, cost) and the public
  `semantic_audit_summary.md` — never the raw decisions. The
  `regressions/..._decisions.json` that ships (when present) is the
  **credential-free replay fixture** with empty `evidence_spans`, not a raw
  model decision file;
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable Before/After comparison
   (`llm_candidate_v0` vs `llm_candidate_v1`) on the 12-case slice. It
   links only to redacted-trace paths.
2. `improvement_memo.md` (when present) is the concise evidence-backed
   write-up of what changed in the prompt and what the delta was.
3. `llm_candidate_v0_eval.redacted.json` is the v0 (Before) JSON eval
   report after applying `configs/redaction_policy.yaml`. Raw
   `draft_text` / `draft_excerpt` / `final_response` values have been
   replaced with the policy's abstraction placeholder.
4. `llm_candidate_v1_eval.redacted.json` is the v1 (After) eval report
   under the same redaction policy.
5. `traces/redacted/candidate_v0/*.redacted.json` and
   `traces/redacted/candidate_v1/*.redacted.json` show the synthetic
   trace shape an analyst can reason about without raw model output.
6. `manifest.json` is the machine-readable index.

## Semantic regression seeds + credential-free replay fixture

- `regressions/regressions_semantic_adversarial_v1.jsonl` pins the three model/NLI **semantic-only** `UNSAFE_CUSTOMER_COMMS` findings as `pending_review` synthetic regression seeds — customer-facing drafts the lexical `unsupported_claim` grader cleared (a lexical blind spot). Each seed is a case-superset record linked to the public `reports/llm_adversarial_v1_semantic_audit_summary.json`; none carries a raw trace path or raw draft text.
- `regressions/regressions_semantic_adversarial_v1_decisions.json` is the tracked `SemanticDecision` **replay fixture**. Feeding it to the offline precomputed-decision lane (`run_eval.py --semantic-decisions`) with the deterministic `improved_v0` profile fires the offline `unsupported_claim_semantic` grader (`UNSAFE_CUSTOMER_COMMS`) on all three seeds **with no credentials and no model call** — it proves the offline semantic grader fires; it does not re-derive the claim from a live draft. The fixture pins the audit verdict (`makes_unsupported_claim: true`); `evidence_spans` is empty and `rationale` is an authored provenance string, so no raw draft text, model reasoning, or quoted spans ship. It feeds only the offline grader, never the runtime EvaluatorNode (evaluator/grader separation preserved).
- These seeds are `pending_review`, not a fix; they are a reason the slice stays **NOT READY FOR PILOT**.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only.** This pack
shows the adversarial v1 candidate comparison closes locally on real LLM
traces; it does **not** prove `llm_candidate_v1` is robust, pilot grade,
regulatory compliant, partner endorsed, or production grade. A single
credentialed run on a 12-case synthetic slice cannot establish prompt
robustness — real evaluation needs many more runs and many more cases.
