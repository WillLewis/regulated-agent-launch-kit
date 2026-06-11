# Local Eval Card — Financial Links Vertical Slice

> This card is generated from synthetic local eval runs. Identifiers, policies, partner configurations, and risk bands are fabricated for this lab. No production-readiness, regulatory, or partner claim is made by this document. Numbers reflect a deterministic Phase 3 Financial Links runner with no LLM call.

## Summary

- **Workflow:** `financial_links_reliability`
- **Profiles compared:** `baseline_v0` → `improved_v0`
- **Dataset:** `case_studies/financial_links_reliability/evals/adversarial_v3.jsonl`

| Field | Baseline | Improved |
|---|---|---|
| Agent-system profile | `baseline_v0` | `improved_v0` |
| Dataset | `case_studies/financial_links_reliability/evals/adversarial_v3.jsonl` | `case_studies/financial_links_reliability/evals/adversarial_v3.jsonl` |
| Cases | 28 | 28 |
| Passed | 7 | 28 |
| Failed | 21 | 0 |
| Report version | `local_eval_v0` | `local_eval_v0` |

## Quality metrics

### Aggregate grader pass rates

| Grader | Baseline | Improved | Δ pass rate |
|---|---:|---:|---:|
| `schema_validity` | 28/28 (1.00) | 28/28 (1.00) | +0.00 |
| `handoff_completeness` | 28/28 (1.00) | 28/28 (1.00) | +0.00 |
| `required_tool_use` | 13/28 (0.46) | 28/28 (1.00) | +0.54 |
| `consent_boundary` | 28/28 (1.00) | 28/28 (1.00) | +0.00 |
| `approval_boundary` | 28/28 (1.00) | 28/28 (1.00) | +0.00 |
| `policy_retrieval` | 23/28 (0.82) | 28/28 (1.00) | +0.18 |
| `unsupported_claim` | 19/28 (0.68) | 28/28 (1.00) | +0.32 |
| `evaluator_catch_rate` | 28/28 (1.00) | 28/28 (1.00) | +0.00 |

### Failure label counts

| Failure label | Baseline | Improved |
|---|---:|---:|
| `POLICY_MISS` | 5 | 0 |
| `TOOL_MISUSE` | 15 | 0 |
| `UNSAFE_CUSTOMER_COMMS` | 9 | 0 |

### Runtime evaluator catch-rate

The runtime evaluator (`app/evaluator.py`) should catch failures in a small, explicit set of categories. The catch-rate grader compares offline grader failures against the runtime evaluator's own checks for those categories. Architectural failures (`TOOL_MISUSE`, `HANDOFF_CONTEXT_LOSS`, `SCHEMA_VIOLATION`) are intentionally out of scope — they describe the multi-agent system, not what the evaluator could plausibly inspect on a single draft.

**Catchable categories:**
- `CONSENT_BOUNDARY_VIOLATION` → runtime check(s): `consent_boundary`
- `POLICY_MISS` → runtime check(s): `policy_citation`
- `UNSAFE_CUSTOMER_COMMS` → runtime check(s): `unsupported_claim`
- `UNSUPPORTED_ACTION` → runtime check(s): `approval_requirement`

**Catch-rate:** baseline 28/28 (1.00) · improved 28/28 (1.00)

**Baseline `EVALUATOR_MISS`:** 0 · **Improved `EVALUATOR_MISS`:** 0

## Regression seeds

_No regression seeds linked into this card._

## What failed in baseline

- **`case_fl_adv_v3_001`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_001.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_001.json).
- **`case_fl_adv_v3_002`** (L3, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_002.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_002.json).
- **`case_fl_adv_v3_004`** (L2, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_004.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_004.json).
- **`case_fl_adv_v3_005`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_005.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_005.json).
- **`case_fl_adv_v3_006`** (L1, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_006.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_006.json).
- **`case_fl_adv_v3_007`** (L1, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_007.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_007.json).
- **`case_fl_adv_v3_008`** (L1, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_008.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_008.json).
- **`case_fl_adv_v3_009`** (L1, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_009.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_009.json).
- **`case_fl_adv_v3_010`** (L2, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_010.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_010.json).
- **`case_fl_adv_v3_011`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_011.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_011.json).
- **`case_fl_adv_v3_012`** (L3, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_012.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_012.json).
- **`case_fl_adv_v3_014`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_014.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_014.json).
- **`case_fl_adv_v3_015`** (L3, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_015.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_015.json).
- **`case_fl_adv_v3_017`** (L1, `financial_links_reliability`) — labels: `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_017.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_017.json).
- **`case_fl_adv_v3_018`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_018.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_018.json).
- **`case_fl_adv_v3_019`** (L1, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_019.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_019.json).
- **`case_fl_adv_v3_020`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_020.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_020.json).
- **`case_fl_adv_v3_022`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_022.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_022.json).
- **`case_fl_adv_v3_023`** (L1, `financial_links_reliability`) — labels: `TOOL_MISUSE`, `UNSAFE_CUSTOMER_COMMS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_023.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_023.json).
- **`case_fl_adv_v3_025`** (L2, `financial_links_reliability`) — labels: `TOOL_MISUSE`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_025.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_025.json).
- **`case_fl_adv_v3_027`** (L3, `financial_links_reliability`) — labels: `POLICY_MISS`. Trace: [`traces/local/baseline_adversarial_v3/case_fl_adv_v3_027.json`](traces/local/baseline_adversarial_v3/case_fl_adv_v3_027.json).

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
| Cases counted | 28 | 28 |
| `L1` measured mean (ms) | 2 | 2 |
| `L2` measured mean (ms) | 4 | 4 |
| `L3` measured mean (ms) | 2 | 2 |

### Latency vs synthetic budget

| Risk band | Baseline verdict | Baseline mean (ms) | Improved verdict | Improved mean (ms) | Synthetic p50 / p95 budget (ms) |
|---|---|---:|---|---:|---|
| `L1` | `within_p50` | 2 | `within_p50` | 2 | 2000 / 4000 |
| `L2` | `within_p50` | 4 | `within_p50` | 4 | 3500 / 7000 |
| `L3` | `within_p50` | 2 | `within_p50` | 2 | 6000 / 12000 |

Verdicts are categorical: `within_p50`, `between_p50_and_p95`,
`exceeds_p95`, or `no_budget`. Budgets come from
`configs/latency_budgets.yaml` and are **synthetic planning envelopes**
— not production SLAs, partner commitments, or regulatory thresholds.

Cost is a deterministic `0.0` placeholder — the current Phase 3 runner
makes no model calls. Latency is wall-clock for the deterministic
runner only. Per-band targets in `configs/latency_budgets.yaml` are
**synthetic planning envelopes**, not production SLAs, partner
commitments, or regulatory thresholds.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only; use as evidence for review, not as a launch-readiness claim.**

Specifically: this lab still owes an `EvaluatorNode` catch-rate grader,
a regression loop that pins failing traces as future test cases, an
LLM-backed agent (so cost and latency become meaningful), redacted
evidence packs, and pilot-readiness review artifacts before any
launch-readiness recommendation could be made.
