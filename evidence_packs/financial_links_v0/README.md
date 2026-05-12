# Evidence Pack — Financial Links v0

> This evidence pack is generated from a fully synthetic local eval run. Identifiers, policies, partner configurations, and risk bands are fabricated for this deployment-readiness lab. Nothing in this pack implies production readiness, regulatory compliance, partner endorsement, or real-world performance. Raw traces are intentionally excluded; only redacted artifacts ship in this directory.

## What this pack contains

This is a public-safe view of the local synthetic Financial Links v0
eval. Every file in it is generated from artifacts already on disk:

- `eval_card.md` — Before/after eval card (markdown).
- `baseline_eval.json` — Baseline profile JSON eval report.
- `improved_eval.json` — Improved profile JSON eval report.
- `regressions.jsonl` — Pinned regression seeds derived from baseline failures.
- `traces/redacted/case_fl_v0_005.redacted.json` — Redacted synthetic trace.
- `traces/redacted/case_fl_v0_006.redacted.json` — Redacted synthetic trace.
- `traces/redacted/case_fl_v0_010.redacted.json` — Redacted synthetic trace.
- `traces/redacted/case_fl_v0_005.redaction_report.json` — Redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_v0_006.redaction_report.json` — Redaction report (removed/abstracted/preserved/uncovered fields).
- `traces/redacted/case_fl_v0_010.redaction_report.json` — Redaction report (removed/abstracted/preserved/uncovered fields).

The redacted traces in `traces/redacted/` are paired with redaction
reports (`*.redaction_report.json`) that list removed, abstracted,
preserved, and uncovered top-level fields. The redaction policy used to
produce them is `configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw traces (under `traces/local/...`) — intentionally excluded;
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, or regulatory claim.

## How to read the pack

1. `eval_card.md` is the human-readable summary; it links to the
   underlying baseline/improved reports.
2. `baseline_eval.json` / `improved_eval.json` carry per-case grader
   results and the synthetic latency / cost summary.
3. `regressions.jsonl` lists the pinned regression seeds derived from
   baseline failures (see `scripts/incident_to_regression.py`).
4. `traces/redacted/*.redacted.json` show the synthetic trace shape an
   analyst can reason about without raw IDs or raw draft text.
5. `manifest.json` is the machine-readable index of the above.
