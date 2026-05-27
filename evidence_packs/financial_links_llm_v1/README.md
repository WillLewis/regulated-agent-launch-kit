# Evidence Pack — Financial Links LLM Prompt-Improvement v1

> This evidence pack is generated from a fully synthetic local eval run on a 6-case adversarial slice. Identifiers, policies, partner configurations, and risk bands are fabricated for this deployment-readiness lab. Both compared profiles call a real LLM via the credential-gated path, but every case in the dataset is synthetic and no real customer data is involved. Raw LLM traces and the raw JSON eval reports are intentionally excluded from this pack and from git tracking; only redacted artifacts ship here. Nothing in this pack implies model safety, production readiness, regulatory compliance, or partner endorsement. One credentialed run on a 6-case synthetic slice is not enough evidence to claim a prompt is robust.

## What this pack contains

This is a public-safe view of the local synthetic Financial Links
**adversarial v0 → v1 prompt-improvement loop**. The compared profiles
are `llm_candidate_v0` (Before) and `llm_candidate_v1` (After). Every
artifact below is generated from on-disk inputs:

- `eval_card.md` — Before/After v0-vs-v1 comparison eval card (markdown).
- `improvement_memo.md` — Concise evidence-backed prompt-improvement memo.
- `llm_candidate_v0_eval.redacted.json` — v0 (Before) JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_v0_eval.redaction_report.json` — Redaction report for the v0 JSON eval.
- `llm_candidate_v1_eval.redacted.json` — v1 (After) JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_v1_eval.redaction_report.json` — Redaction report for the v1 JSON eval.
- `regressions_llm_v0.jsonl` — Pinned pending_review regression seeds derived from v0 failures; still useful context for the improvement loop.
- `repeat_run_summary.md` — Public-safe repeat-run variance summary aggregated from credentialed repeat-run capture (no raw draft text, no raw trace paths).
- `repeat_run_summary.json` — Machine-readable repeat-run variance summary (per-run pass/fail, runtime-vs-offline asymmetry, per-case instability, latency by band, cost distribution).
- `traces/redacted/case_fl_adv_v0_001.redacted.json` — Redacted synthetic v1 LLM trace.
- `traces/redacted/case_fl_adv_v0_002.redacted.json` — Redacted synthetic v1 LLM trace.
- `traces/redacted/case_fl_adv_v0_003.redacted.json` — Redacted synthetic v1 LLM trace.
- `traces/redacted/case_fl_adv_v0_004.redacted.json` — Redacted synthetic v1 LLM trace.
- `traces/redacted/case_fl_adv_v0_005.redacted.json` — Redacted synthetic v1 LLM trace.
- `traces/redacted/case_fl_adv_v0_006.redacted.json` — Redacted synthetic v1 LLM trace.
- `traces/redacted/case_fl_adv_v0_001.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_002.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_003.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_004.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_005.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_006.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).

The redacted traces in `traces/redacted/` are paired with redaction
reports (`*.redaction_report.json`) that list removed, abstracted,
preserved, and uncovered top-level fields. The same applies to each
candidate's redacted JSON eval summary. The redaction policy used is
`configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw LLM traces (gitignored under the `llm_adversarial_v1/` traces
  directory) — intentionally excluded;
- the raw JSON eval reports (the v1 report is gitignored; the v0 report
  is tracked as an audit artifact in the parent repo but the pack only
  ships its redacted summary) — intentionally excluded as raw payloads;
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable Before/After comparison
   (`llm_candidate_v0` vs `llm_candidate_v1`). It links only to
   redacted-trace paths.
2. `improvement_memo.md` (when present) is the concise evidence-backed
   write-up of what changed in the prompt and what the delta was.
3. `llm_candidate_v0_eval.redacted.json` is the v0 (Before) JSON eval
   report after applying `configs/redaction_policy.yaml`. Raw
   `draft_text` / `draft_excerpt` / `final_response` values have been
   replaced with the policy's abstraction placeholder.
4. `llm_candidate_v1_eval.redacted.json` is the v1 (After) eval report
   under the same redaction policy.
5. `regressions_llm_v0.jsonl` lists the pending-review regression seeds
   that captured v0 failure modes; they remain useful context for the
   improvement loop.
6. `repeat_run_summary.md` / `repeat_run_summary.json` (when present)
   are the public-safe aggregated outputs of a credentialed repeat-run
   capture (N runs × the same adversarial slice for each profile).
   They describe run-to-run variance — pass/fail per run, runtime-vs-
   offline asymmetry, per-case instability, per-band latency, and cost
   distribution — without any raw draft text or raw trace path.
7. `traces/redacted/*.redacted.json` show the synthetic v1 trace shape
   an analyst can reason about without raw model output.
8. `manifest.json` is the machine-readable index.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only.** This
pack proves the prompt-improvement loop closes locally on real LLM
traces; it does **not** prove v1 is robust, pilot grade, regulatory
compliant, partner endorsed, or production grade. A single credentialed
run on a 6-case synthetic slice cannot establish prompt robustness —
real evaluation needs many more runs and many more cases.
