# Evidence Pack — Financial Links LLM Adversarial v0

> This evidence pack is generated from a fully synthetic local eval run. Identifiers, policies, partner configurations, and risk bands are fabricated for this deployment-readiness lab. The candidate profile (`llm_candidate_v0`) calls a real LLM via the credential-gated path, but every case in the dataset is synthetic and no real customer data is involved. Raw LLM traces and the raw JSON eval report are intentionally excluded from this pack and from git tracking; only redacted artifacts ship here. Nothing in this pack implies model safety, production readiness, regulatory compliance, or partner endorsement.

## What this pack contains

This is a public-safe view of the local synthetic Financial Links
**adversarial** v0 eval comparing the deterministic `improved_v0`
profile (reference) against the credential-gated `llm_candidate_v0`
profile (candidate). Every artifact below is generated from on-disk
inputs:

- `eval_card.md` — Corrected before/after eval card (markdown).
- `reference_eval.json` — Deterministic reference profile JSON eval report (already public-safe).
- `llm_candidate_eval.redacted.json` — Candidate profile JSON eval report with raw draft text abstracted and IDs removed.
- `llm_candidate_eval.redaction_report.json` — Redaction report for the candidate JSON eval (removed / abstracted / preserved / uncovered fields).
- `regressions_llm_v0.jsonl` — Pinned pending_review regression seeds derived from the candidate's failing cases.
- `traces/redacted/case_fl_adv_v0_001.redacted.json` — Redacted synthetic LLM trace.
- `traces/redacted/case_fl_adv_v0_002.redacted.json` — Redacted synthetic LLM trace.
- `traces/redacted/case_fl_adv_v0_003.redacted.json` — Redacted synthetic LLM trace.
- `traces/redacted/case_fl_adv_v0_004.redacted.json` — Redacted synthetic LLM trace.
- `traces/redacted/case_fl_adv_v0_005.redacted.json` — Redacted synthetic LLM trace.
- `traces/redacted/case_fl_adv_v0_006.redacted.json` — Redacted synthetic LLM trace.
- `traces/redacted/case_fl_adv_v0_001.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_002.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_003.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_004.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_005.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_adv_v0_006.redaction_report.json` — Per-trace redaction report (removed/abstracted/preserved/uncovered fields).

The redacted traces in `traces/redacted/` are paired with redaction
reports (`*.redaction_report.json`) that list removed, abstracted,
preserved, and uncovered top-level fields. The same applies to the
candidate's redacted JSON eval summary (`llm_candidate_eval.redacted.json`
+ `llm_candidate_eval.redaction_report.json`). The redaction policy used
is `configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw LLM traces under `traces/local/llm_adversarial/...` —
  intentionally excluded and gitignored;
- the raw JSON eval report `reports/llm_adversarial_eval.json` —
  intentionally excluded and gitignored (it embeds raw draft text);
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable before/after summary
   (`improved_v0` reference vs `llm_candidate_v0` candidate). It uses
   the corrected disclaimer that names the real LLM call.
2. `reference_eval.json` is the deterministic reference's JSON eval
   report. It is unchanged from `reports/improved_adversarial_eval.json`
   and carries no raw model output.
3. `llm_candidate_eval.redacted.json` is the candidate's JSON eval
   report after applying `configs/redaction_policy.yaml`. Raw
   `draft_text` / `draft_excerpt` / `final_response` values have been
   replaced with the policy's abstraction placeholder.
4. `regressions_llm_v0.jsonl` lists the pinned `pending_review`
   regression seeds derived from the candidate's failing cases.
5. `traces/redacted/*.redacted.json` show the synthetic trace shape an
   analyst can reason about without raw model output.
6. `manifest.json` is the machine-readable index.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only.** This
pack proves the redaction-and-evidence loop closes on real LLM traces;
it does **not** prove model safety, pilot readiness, regulatory
compliance, partner endorsement, or production behavior.
