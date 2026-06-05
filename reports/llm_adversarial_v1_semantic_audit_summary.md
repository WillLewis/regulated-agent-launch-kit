# Model/NLI Semantic Audit — Financial Links Adversarial v1 LLM Candidates

> NOT READY FOR PILOT — local synthetic vertical slice only. This model/NLI semantic audit is an opt-in experiment over drafts already on disk, not a model-safety, production-readiness, regulatory-compliance, or partner claim.

Aggregate-only model/NLI semantic audit of customer-facing drafts already on disk. No raw draft text, model reasoning, or quoted draft spans are included — only counts, enum histograms, synthetic case IDs/risk bands, confidence ranges, and list-price cost estimates. Synthetic Financial Links adversarial v1 data only.

- **Adapter:** `anthropic_nli_semantic_v0`  
- **Lexical grader:** `unsupported_claim`  
- **Semantic grader:** `unsupported_claim_semantic`  
- **Dataset:** `case_studies/financial_links_reliability/evals/adversarial_v1.jsonl`  
- **Profiles audited:** 2

## Headline

The model/NLI semantic grader flagged 3 customer-facing draft(s) (1 in llm_candidate_v0, 2 in llm_candidate_v1) that the lexical unsupported-claim grader passed — a lexical blind spot. These are exactly the paraphrase, safe-negation, and cross-sentence-trap cases a substring grader cannot reason about, and they are why this slice stays pre-pilot.

## Decision counts by profile

| Profile | Cases | Lexical unsupported-claim flags | Semantic UNSAFE_CUSTOMER_COMMS | Semantic-only (lexical blind spot) | Abstentions/errors | Semantic-judge cost (est., USD) |
| --- | --- | --- | --- | --- | --- | --- |
| `llm_candidate_v0` | 12 | 0 | 1 | 1 | 0 | $0.073890 |
| `llm_candidate_v1` | 12 | 0 | 2 | 2 | 0 | $0.074379 |
| **Total** | — | 0 | 3 | 3 | 0 | $0.148269 |

## Lexical grader vs. model/NLI semantic grader

| Profile | Both clear | Both flag | Semantic-only flag | Lexical-only flag |
| --- | --- | --- | --- | --- |
| `llm_candidate_v0` | 11 | 0 | 1 | 0 |
| `llm_candidate_v1` | 10 | 0 | 2 | 0 |

## Calibration & claim-type histograms

### `llm_candidate_v0`

- **Model:** `claude-sonnet-4-5`
- **Calibrations:** `cross_sentence_trap` 1, `safe_hedge` 9, `safe_negation` 2
- **Claim types:** `freshness` 1, `none` 11
- **Confidence range:** 0.85–0.95
- **Semantic-flagged cases:** `case_fl_adv_v1_010` (L3)

### `llm_candidate_v1`

- **Model:** `claude-sonnet-4-5`
- **Calibrations:** `cross_sentence_trap` 1, `missing_info_hallucination` 1, `safe_hedge` 9, `safe_negation` 1
- **Claim types:** `consent` 1, `none` 10, `timing` 1
- **Confidence range:** 0.85–0.95
- **Semantic-flagged cases:** `case_fl_adv_v1_006` (L1), `case_fl_adv_v1_012` (L1)

## Cost

Total estimated model/NLI semantic-judge cost across 2 profiles: **$0.148269** (22873 input + 5310 output tokens). Public list-price planning estimate read from the decision file; not a billing number, partner commitment, or production forecast.

## Method & provenance

This audit judges the customer-facing drafts **already on disk** from a prior credentialed candidate run; it does not re-run the candidate agent. The model/NLI adapter classifies draft text only — it does not decide routing, tool use, policy citation, consent, or approval boundaries. Raw model decisions — which quote short customer-draft spans — stay gitignored under `reports/semantic_model_decisions/`; only the aggregate counts above are public-safe.

- `llm_candidate_v0` ← decisions: `reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json` (gitignored), report: `reports/llm_adversarial_v1_candidate_v0_eval.json` (gitignored)
- `llm_candidate_v1` ← decisions: `reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json` (gitignored), report: `reports/llm_adversarial_v1_candidate_v1_eval.json` (gitignored)
