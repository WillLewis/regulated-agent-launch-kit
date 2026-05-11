# Local Eval Card — Financial Links Vertical Slice

> This card is generated from synthetic local eval runs. Identifiers, policies, partner configurations, and risk bands are fabricated for this lab. No production-readiness, regulatory, or partner claim is made by this document. Numbers reflect a deterministic Phase 3 Financial Links runner with no LLM call.

## Summary

- **Workflow:** `financial_links_reliability`
- **Profiles compared:** `baseline_v0` → `improved_v0`
- **Dataset:** `case_studies/financial_links_reliability/evals/smoke.jsonl`

| Field | Baseline | Improved |
|---|---|---|
| Agent-system profile | `baseline_v0` | `improved_v0` |
| Dataset | `case_studies/financial_links_reliability/evals/smoke.jsonl` | `case_studies/financial_links_reliability/evals/smoke.jsonl` |
| Cases | 4 | 4 |
| Passed | 3 | 4 |
| Failed | 1 | 0 |
| Report version | `local_eval_v0` | `local_eval_v0` |

## Quality metrics

### Aggregate grader pass rates

| Grader | Baseline | Improved | Δ pass rate |
|---|---:|---:|---:|
| `schema_validity` | 4/4 (1.00) | 4/4 (1.00) | +0.00 |
| `handoff_completeness` | 4/4 (1.00) | 4/4 (1.00) | +0.00 |
| `required_tool_use` | 4/4 (1.00) | 4/4 (1.00) | +0.00 |
| `consent_boundary` | 4/4 (1.00) | 4/4 (1.00) | +0.00 |
| `approval_boundary` | 4/4 (1.00) | 4/4 (1.00) | +0.00 |
| `policy_retrieval` | 3/4 (0.75) | 4/4 (1.00) | +0.25 |
| `unsupported_claim` | 4/4 (1.00) | 4/4 (1.00) | +0.00 |

### Failure label counts

| Failure label | Baseline | Improved |
|---|---:|---:|
| `POLICY_MISS` | 1 | 0 |

## What failed in baseline

- **`case_fl_v0_005`** (L2, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_smoke/case_fl_v0_005.json`](traces/local/baseline_smoke/case_fl_v0_005.json).

## What failed in improved

_No failing cases in this run._

## What changed in improved profile

- Restores the synthetic partner-fallback policy citation (`FL-PARTNER-FALLBACK-002`) on cases the baseline omitted.

This is a synthetic deterministic change set; it demonstrates the eval
loop closing on planted failures. Do not infer pilot, production, or
regulatory acceptance from this delta — the baseline failures were
authored as targets for this lab.

## Operational metrics

| Metric | Baseline | Improved |
|---|---:|---:|
| Total est. cost (USD) | 0.0 | 0.0 |
| Cases counted | 4 | 4 |
| `L1` measured mean (ms) | 2 | 2 |
| `L2` measured mean (ms) | 0 | 0 |
| `L3` measured mean (ms) | 0 | 0 |

Cost is a deterministic `0.0` placeholder — the current Phase 3 runner
makes no model calls. Latency is wall-clock for the deterministic
runner only. Per-band targets in `configs/latency_budgets.yaml` are
**synthetic planning envelopes**, not production SLAs, partner
commitments, or regulatory thresholds.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only; proceed to evaluator catch-rate and regression-loop work.**

Specifically: this lab still owes an `EvaluatorNode` catch-rate grader,
a regression loop that pins failing traces as future test cases, an
LLM-backed agent (so cost and latency become meaningful), redacted
evidence packs, and pilot-readiness review artifacts before any
launch-readiness recommendation could be made.
