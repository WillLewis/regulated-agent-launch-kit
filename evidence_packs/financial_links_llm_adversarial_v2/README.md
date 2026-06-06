# Evidence Pack — Financial Links LLM Adversarial v2 (M7, gate BLOCKED)

> This evidence pack is generated from a fully synthetic local eval run on the 24-case Financial Links adversarial v2 slice (milestone M7). Identifiers, policies, partner configurations, and risk bands are fabricated for this deployment-readiness lab. Both compared profiles call a real LLM via the credential-gated path, but every case in the dataset is synthetic and no real customer data is involved. M7 was executed once with a real key and the credential-free semantic gate BLOCKED: the model/NLI audit found 14 semantic-only UNSAFE_CUSTOMER_COMMS drafts the lexical grader cleared, so M7 remains OPEN. Raw LLM traces, the raw JSON eval reports, and the raw model/NLI decision files are intentionally excluded from this pack and from git tracking; only redacted and aggregate-only artifacts ship here. Nothing in this pack implies model safety, production readiness, regulatory compliance, partner endorsement, or pilot readiness. One credentialed run on a 24-case synthetic slice is not enough evidence to claim a prompt is robust — and this run blocked.

## What this pack contains

This is a public-safe view of the **executed** Financial Links adversarial v2
(24-case) LLM milestone (**M7**). The compared profiles are `llm_candidate_v0`
(Before) and `llm_candidate_v1` (After). M7 **ran once** with a real key; the
deterministic comparison improved (`v0` 20/24 → `v1` 24/24), but the
credential-free model/NLI **semantic gate BLOCKED** on 14 semantic-only
`UNSAFE_CUSTOMER_COMMS` drafts (8 in `v0`, 6 in `v1`) that the lexical
unsupported-claim grader cleared — a lexical blind spot. **M7 remains OPEN.**

Every artifact below is generated from on-disk inputs:

- `eval_card.md` — Before/After candidate_v0-vs-candidate_v1 comparison eval card (markdown) on the 24-case adversarial v2 slice (v0 20/24 → v1 24/24).
- `semantic_audit_aggregate.json` — Aggregate-only model/NLI semantic audit: counts, enum histograms, synthetic case IDs/risk bands, confidence ranges, and cost. The 14 semantic-only UNSAFE_CUSTOMER_COMMS flags that BLOCKED the M7 gate. No draft text, model reasoning, or quoted spans.
- `semantic_audit_summary.md` — Human-readable public-safe model/NLI semantic audit summary (aggregate-only).
- `llm_candidate_v0_eval.redacted.json` — candidate_v0 (Before) JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_v0_eval.redaction_report.json` — Redaction report for the candidate_v0 JSON eval.
- `llm_candidate_v1_eval.redacted.json` — candidate_v1 (After) JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_v1_eval.redaction_report.json` — Redaction report for the candidate_v1 JSON eval.
- `traces/redacted/candidate_v0/case_fl_adv_v2_001.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_002.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_003.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_004.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_005.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_006.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_007.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_008.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_009.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_010.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_011.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_012.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_013.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_014.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_015.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_016.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_017.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_018.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_019.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_020.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_021.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_022.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_023.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_024.redacted.json` — Redacted synthetic candidate_v0 LLM trace.
- `traces/redacted/candidate_v0/case_fl_adv_v2_001.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_002.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_003.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_004.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_005.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_006.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_007.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_008.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_009.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_010.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_011.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_012.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_013.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_014.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_015.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_016.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_017.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_018.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_019.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_020.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_021.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_022.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_023.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v0/case_fl_adv_v2_024.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_001.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_002.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_003.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_004.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_005.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_006.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_007.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_008.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_009.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_010.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_011.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_012.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_013.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_014.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_015.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_016.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_017.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_018.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_019.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_020.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_021.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_022.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_023.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_024.redacted.json` — Redacted synthetic candidate_v1 LLM trace.
- `traces/redacted/candidate_v1/case_fl_adv_v2_001.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_002.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_003.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_004.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_005.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_006.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_007.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_008.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_009.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_010.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_011.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_012.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_013.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_014.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_015.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_016.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_017.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_018.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_019.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_020.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_021.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_022.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_023.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/candidate_v1/case_fl_adv_v2_024.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `regressions/regressions_semantic_adversarial_v2.jsonl` — Pending_review synthetic semantic-only regression seeds — the 14 model/NLI UNSAFE_CUSTOMER_COMMS drafts the lexical grader cleared (a lexical blind spot). Case-superset records linked to the public semantic audit summary; no raw trace path or raw draft text.
- `regressions/regressions_semantic_adversarial_v2_decisions.json` — Credential-free SemanticDecision replay fixture: feeding it to run_eval.py --semantic-decisions with the deterministic improved_v0 profile fires the offline unsupported_claim_semantic grader on every seed with no model call. evidence_spans empty; rationale is authored provenance, not raw draft text.

This pack was assembled on a machine that still held the gitignored raw M7 artifacts, so it **also** ships redacted candidate eval summaries (`llm_candidate_v{0,1}_eval.redacted.json`) and redacted per-candidate traces under `traces/redacted/candidate_v{0,1}/`. Raw `draft_text` / `draft_excerpt` / `final_response` values were abstracted via `configs/redaction_policy.yaml`; the raw reports and raw traces themselves are never copied. When the raw artifacts are absent (any fresh clone), the credential-free core above is still assembled byte-for-byte from tracked inputs — the redacted candidate artifacts are simply omitted.

## What this pack does **not** contain

- raw LLM traces (the gitignored per-candidate raw-trace directories) —
  intentionally excluded; when present locally only their *redacted* form ships;
- the raw JSON candidate eval reports (gitignored) — never copied; when present
  locally only their *redacted* summaries ship;
- raw model/NLI semantic-decision payloads (gitignored under the
  `semantic_model_decisions` reports directory) — those quote short draft spans.
  Only the aggregate-only `semantic_audit_aggregate.json` (counts, enum
  histograms, synthetic case IDs/risk bands, confidence ranges, cost) and the
  public `semantic_audit_summary.md` ship;
- the regenerable replay / semantic-model eval reports (gitignored check
  outputs, not evidence);
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable Before/After comparison
   (`llm_candidate_v0` 20/24 → `llm_candidate_v1` 24/24) on the 24-case slice.
   The deterministic graders all pass; the semantic gate is what blocks.
2. `semantic_audit_aggregate.json` is the aggregate-only model/NLI audit:
   counts, calibration/claim-type histograms, synthetic case IDs/risk bands,
   confidence ranges, and list-price cost. No draft text, model reasoning, or
   quoted spans.
3. `semantic_audit_summary.md` is the human-readable version of the same
   aggregate, including the 14 semantic-only flags that blocked the gate.
4. `regressions/regressions_semantic_adversarial_v2.jsonl` and
   `regressions/regressions_semantic_adversarial_v2_decisions.json` are covered
   below.
5. `manifest.json` is the machine-readable index.

## Semantic regression seeds + credential-free replay fixture

- `regressions/regressions_semantic_adversarial_v2.jsonl` pins all **14**
  model/NLI **semantic-only** `UNSAFE_CUSTOMER_COMMS` findings as
  `pending_review` synthetic regression seeds — customer-facing drafts the
  lexical `unsupported_claim` grader cleared. Each seed is a case-superset
  record sourced only from the public summary's `semantic_only_flag_case_ids`
  plus the synthetic dataset, and linked to
  `reports/llm_adversarial_v2_semantic_audit_summary.json`; none carries a raw
  trace path or raw draft text.
- `regressions/regressions_semantic_adversarial_v2_decisions.json` is the
  tracked `SemanticDecision` **replay fixture**. Feeding it to the offline
  precomputed-decision lane (`run_eval.py --semantic-decisions`) with the
  deterministic `improved_v0` profile fires the offline
  `unsupported_claim_semantic` grader (`UNSAFE_CUSTOMER_COMMS`) on all 14 seeds
  **with no credentials and no model call** — it proves the offline grader
  fires; it does not re-derive the claim from a live draft. The fixture pins the
  audit verdict (`makes_unsupported_claim: true`); `evidence_spans` is empty and
  `rationale` is an authored provenance string, so no raw draft text, model
  reasoning, or quoted spans ship. It feeds only the offline grader, never the
  runtime EvaluatorNode (evaluator/grader separation preserved).
- These seeds are `pending_review`, not a fix; they are a reason the slice stays
  **NOT READY FOR PILOT**.

## Launch posture

**M7 ran once and the semantic gate BLOCKED — M7 remains OPEN; NOT READY FOR
PILOT.** The acceptance bar is *sustained zero* semantic-only flags across
multiple runs; one credentialed run produced 14, so the gate blocked. This pack
shows the deterministic v2 comparison closes locally on real LLM traces while
the semantic audit surfaces a real blind spot; it does **not** prove
`llm_candidate_v1` is robust, pilot grade, regulatory compliant, partner
endorsed, or production grade. A single credentialed run on a 24-case synthetic
slice cannot establish prompt robustness — and this one blocked.
