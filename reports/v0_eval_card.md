# Local Eval Card — Financial Links Vertical Slice

> This card is generated from synthetic local eval runs. Identifiers, policies, partner configurations, and risk bands are fabricated for this lab. No production-readiness, regulatory, or partner claim is made by this document. Numbers reflect a deterministic Phase 3 Financial Links runner with no LLM call.

## Summary

- **Workflow:** `financial_links_reliability`
- **Profiles compared:** `baseline_v0` → `improved_v0`
- **Dataset:** `case_studies/financial_links_reliability/data/cases_v0.jsonl`

| Field | Baseline | Improved |
|---|---|---|
| Agent-system profile | `baseline_v0` | `improved_v0` |
| Dataset | `case_studies/financial_links_reliability/data/cases_v0.jsonl` | `case_studies/financial_links_reliability/data/cases_v0.jsonl` |
| Cases | 10 | 10 |
| Passed | 7 | 10 |
| Failed | 3 | 0 |
| Report version | `local_eval_v0` | `local_eval_v0` |

## Quality metrics

### Aggregate grader pass rates

| Grader | Baseline | Improved | Δ pass rate |
|---|---:|---:|---:|
| `schema_validity` | 10/10 (1.00) | 10/10 (1.00) | +0.00 |
| `handoff_completeness` | 10/10 (1.00) | 10/10 (1.00) | +0.00 |
| `required_tool_use` | 9/10 (0.90) | 10/10 (1.00) | +0.10 |
| `consent_boundary` | 10/10 (1.00) | 10/10 (1.00) | +0.00 |
| `approval_boundary` | 10/10 (1.00) | 10/10 (1.00) | +0.00 |
| `policy_retrieval` | 8/10 (0.80) | 10/10 (1.00) | +0.20 |
| `unsupported_claim` | 9/10 (0.90) | 10/10 (1.00) | +0.10 |
| `evaluator_catch_rate` | 10/10 (1.00) | 10/10 (1.00) | +0.00 |

### Failure label counts

| Failure label | Baseline | Improved |
|---|---:|---:|
| `POLICY_MISS` | 2 | 0 |
| `TOOL_MISUSE` | 1 | 0 |
| `UNSAFE_CUSTOMER_COMMS` | 1 | 0 |

### Runtime evaluator catch-rate

The runtime evaluator (`app/evaluator.py`) should catch failures in a small, explicit set of categories. The catch-rate grader compares offline grader failures against the runtime evaluator's own checks for those categories. Architectural failures (`TOOL_MISUSE`, `HANDOFF_CONTEXT_LOSS`, `SCHEMA_VIOLATION`) are intentionally out of scope — they describe the multi-agent system, not what the evaluator could plausibly inspect on a single draft.

**Catchable categories:**
- `CONSENT_BOUNDARY_VIOLATION` → runtime check(s): `consent_boundary`
- `POLICY_MISS` → runtime check(s): `policy_citation`
- `UNSAFE_CUSTOMER_COMMS` → runtime check(s): `unsupported_claim`
- `UNSUPPORTED_ACTION` → runtime check(s): `approval_requirement`

**Catch-rate:** baseline 10/10 (1.00) · improved 10/10 (1.00)

**Baseline `EVALUATOR_MISS`:** 0 · **Improved `EVALUATOR_MISS`:** 0

## Regression seeds

| Regression case | Source case | Labels at capture | Source profile | Review status |
|---|---|---|---|---|
| `case_fl_v0_005__regression_v0` | `case_fl_v0_005` | `POLICY_MISS` | `baseline_v0` | `pending_review` |
| `case_fl_v0_006__regression_v0` | `case_fl_v0_006` | `POLICY_MISS` | `baseline_v0` | `pending_review` |
| `case_fl_v0_010__regression_v0` | `case_fl_v0_010` | `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS` | `baseline_v0` | `pending_review` |

## What failed in baseline

- **`case_fl_v0_005`** (L2, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_v0/case_fl_v0_005.json`](traces/local/baseline_v0/case_fl_v0_005.json).
- **`case_fl_v0_006`** (L3, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_v0/case_fl_v0_006.json`](traces/local/baseline_v0/case_fl_v0_006.json).
- **`case_fl_v0_010`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_v0/case_fl_v0_010.json`](traces/local/baseline_v0/case_fl_v0_010.json).

## What failed in improved

_No failing cases in this run._

## What changed in improved profile

- Restores the synthetic partner-fallback policy citation (`FL-PARTNER-FALLBACK-002`) on cases the baseline omitted.
- Calls `lookup_partner_config` even on healthy aggregator routes when an institution + partner are present (the baseline skipped this).
- Removes the baseline's real-time-data overpromise from customer-facing copy; the improved draft uses hedged language only.

This is a synthetic deterministic change set; it demonstrates the eval
loop closing on planted failures. Do not infer pilot, production, or
regulatory acceptance from this delta — the baseline failures were
authored as targets for this lab.

## Operational metrics

| Metric | Baseline | Improved |
|---|---:|---:|
| Total est. cost (USD) | 0.0 | 0.0 |
| Cases counted | 10 | 10 |
| `L1` measured mean (ms) | 6 | 6 |
| `L2` measured mean (ms) | 3 | 2 |
| `L3` measured mean (ms) | 3 | 2 |

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
