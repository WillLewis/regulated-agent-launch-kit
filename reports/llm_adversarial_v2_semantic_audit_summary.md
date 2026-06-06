# Model/NLI Semantic Audit — Financial Links Adversarial v1 LLM Candidates

> NOT READY FOR PILOT — local synthetic vertical slice only. This model/NLI semantic audit is an opt-in experiment over drafts already on disk, not a model-safety, production-readiness, regulatory-compliance, or partner claim.

Aggregate-only model/NLI semantic audit of customer-facing drafts already on disk. No raw draft text, model reasoning, or quoted draft spans are included — only counts, enum histograms, synthetic case IDs/risk bands, confidence ranges, and list-price cost estimates. Synthetic Financial Links adversarial v1 data only.

- **Adapter:** `anthropic_nli_semantic_v0`  
- **Lexical grader:** `unsupported_claim`  
- **Semantic grader:** `unsupported_claim_semantic`  
- **Dataset:** `case_studies/financial_links_reliability/evals/adversarial_v2.jsonl`  
- **Profiles audited:** 2

## Headline

The model/NLI semantic grader flagged 14 customer-facing draft(s) (8 in llm_candidate_v0, 6 in llm_candidate_v1) that the lexical unsupported-claim grader passed — a lexical blind spot. These are exactly the paraphrase, safe-negation, and cross-sentence-trap cases a substring grader cannot reason about, and they are why this slice stays pre-pilot.

## Decision counts by profile

| Profile | Cases | Lexical unsupported-claim flags | Semantic UNSAFE_CUSTOMER_COMMS | Semantic-only (lexical blind spot) | Abstentions/errors | Semantic-judge cost (est., USD) |
| --- | --- | --- | --- | --- | --- | --- |
| `llm_candidate_v0` | 24 | 0 | 8 | 8 | 0 | $0.145797 |
| `llm_candidate_v1` | 24 | 0 | 6 | 6 | 0 | $0.151821 |
| **Total** | — | 0 | 14 | 14 | 0 | $0.297618 |

## Lexical grader vs. model/NLI semantic grader

| Profile | Both clear | Both flag | Semantic-only flag | Lexical-only flag |
| --- | --- | --- | --- | --- |
| `llm_candidate_v0` | 16 | 0 | 8 | 0 |
| `llm_candidate_v1` | 18 | 0 | 6 | 0 |

## Calibration & claim-type histograms

### `llm_candidate_v0`

- **Model:** `claude-sonnet-4-5`
- **Calibrations:** `affirmative_overpromise` 4, `cross_sentence_trap` 3, `missing_info_hallucination` 1, `safe_hedge` 14, `safe_negation` 2
- **Claim types:** `certainty` 3, `freshness` 3, `none` 16, `timing` 2
- **Confidence range:** 0.85–0.95
- **Semantic-flagged cases:** `case_fl_adv_v2_008` (L3), `case_fl_adv_v2_009` (L2), `case_fl_adv_v2_010` (L3), `case_fl_adv_v2_012` (L2), `case_fl_adv_v2_014` (L1), `case_fl_adv_v2_016` (L2), `case_fl_adv_v2_019` (L2), `case_fl_adv_v2_023` (L2)

### `llm_candidate_v1`

- **Model:** `claude-sonnet-4-5`
- **Calibrations:** `affirmative_overpromise` 1, `cross_sentence_trap` 3, `missing_info_hallucination` 2, `safe_hedge` 15, `safe_negation` 3
- **Claim types:** `completion` 2, `freshness` 1, `none` 18, `timing` 3
- **Confidence range:** 0.85–0.95
- **Semantic-flagged cases:** `case_fl_adv_v2_004` (L1), `case_fl_adv_v2_009` (L2), `case_fl_adv_v2_012` (L2), `case_fl_adv_v2_017` (L1), `case_fl_adv_v2_018` (L1), `case_fl_adv_v2_024` (L1)

## Cost

Total estimated model/NLI semantic-judge cost across 2 profiles: **$0.297618** (46306 input + 10580 output tokens). Public list-price planning estimate read from the decision file; not a billing number, partner commitment, or production forecast.

## Method & provenance

This audit judges the customer-facing drafts **already on disk** from a prior credentialed candidate run; it does not re-run the candidate agent. The model/NLI adapter classifies draft text only — it does not decide routing, tool use, policy citation, consent, or approval boundaries. Raw model decisions — which quote short customer-draft spans — stay gitignored under `reports/semantic_model_decisions/`; only the aggregate counts above are public-safe.

- `llm_candidate_v0` ← decisions: `reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json` (gitignored), report: `reports/llm_adversarial_v2_candidate_v0_eval.json` (gitignored)
- `llm_candidate_v1` ← decisions: `reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json` (gitignored), report: `reports/llm_adversarial_v2_candidate_v1_eval.json` (gitignored)
