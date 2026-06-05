# LLM Prompt-Improvement Memo — Financial Links Adversarial v1

> Synthetic deployment-readiness lab. Identifiers, policies, partner
> configurations, and risk bands are fabricated. Both compared profiles
> call a real LLM via the credential-gated path; every case is synthetic.
> **Nothing in this memo implies model safety, pilot readiness,
> production readiness, regulatory compliance, or partner endorsement.**
> One credentialed run on a 12-case slice cannot establish prompt
> robustness.

## Scope

- **Dataset:** `financial_links_reliability_adversarial_v1` — 12
  hand-authored synthetic adversarial cases.
- **Profiles compared:**
  - Before: `llm_candidate_v0`
  - After: `llm_candidate_v1`
- **Comparison card:** [`reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md`](llm_adversarial_v1_candidate_v1_vs_v0_card.md)
- **Public-safe evidence pack:** [`evidence_packs/financial_links_llm_adversarial_v1/`](../evidence_packs/financial_links_llm_adversarial_v1/)
- **Run count:** one credentialed Before run + one credentialed After run.

## Headline Metrics

| Metric | Before (`llm_candidate_v0`) | After (`llm_candidate_v1`) | Delta |
|---|---:|---:|---:|
| Cases | 12 | 12 | - |
| Passed overall | 6 | 12 | +6 |
| Failed overall | 6 | 0 | -6 |
| Offline failure labels | 0 | 0 | 0 |
| `EVALUATOR_MISS` | 0 | 0 | 0 |
| Total est. cost (USD) | 0.051408 | 0.071079 | +0.019671 (+38%) |

The six Before failures were runtime-guardrail fires with no offline
failure labels. This is the expected guardrail-vs-audit asymmetry: the
runtime evaluator is deliberately conservative, while the offline
unsupported-claim grader is negation-aware and cleared the relevant
drafts as non-affirmative.

## What Improved

`llm_candidate_v1` cleared the conservative runtime guardrail on all 12
cases while preserving the deterministic decision graph: tool use,
policy citations, approval boundaries, and prohibited-action avoidance
remained controlled by code, not by the LLM draft.

The result is useful because adversarial v1 expands beyond the original
6-case slice into paraphrased overpromise pressure, safe-negation
calibration, cross-sentence traps, consent pressure, policy-citation
traps, and missing-info hallucination resistance.

## Cost And Latency

| Risk band | Before mean (ms) | Before verdict | After mean (ms) | After verdict |
|---|---:|---|---:|---|
| L1 | 8440 | `exceeds_p95` | 8597 | `exceeds_p95` |
| L2 | 9468 | `exceeds_p95` | 7712 | `exceeds_p95` |
| L3 | 11305 | `between_p50_and_p95` | 12839 | `exceeds_p95` |

The After prompt cost more (+38%) and did not solve latency against the
synthetic planning envelopes. L1 and L2 remain above synthetic p95 on
both profiles; L3 regressed from `between_p50_and_p95` to `exceeds_p95`
on this single run. These envelopes are synthetic planning targets, not
production SLAs.

## What This Does Not Prove

- It does not prove `llm_candidate_v1` is robust; this is one run on 12
  synthetic cases.
- It does not prove the semantic/model audit lane; this run used the
  default offline graders, and model/NLI semantic decisions remain
  separate opt-in artifacts.
- It does not create pilot readiness. The project still owes repeat-run
  variance on this larger slice, accepted regression seeds for any
  model-failure modes, and pilot-readiness review artifacts.

## Recommendation

Keep `llm_candidate_v1` as the better prompt candidate for this slice,
but do not promote it beyond evidence-review status. The next
evaluation step should be repeat-run variance on adversarial v1 or
model/NLI semantic audit decisions over the already-generated drafts,
not a launch-readiness claim.
