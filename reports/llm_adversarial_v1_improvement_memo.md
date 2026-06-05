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
- It does not create pilot readiness. Repeat-run variance on this larger
  slice has since been captured (see the addendum below), but the project
  still owes accepted regression seeds for any model-failure modes and
  pilot-readiness review artifacts — and a single N=5 lab cannot establish
  robustness.

## Recommendation

Keep `llm_candidate_v1` as the better prompt candidate for this slice,
but do not promote it beyond evidence-review status. Repeat-run variance
on adversarial v1 has now been captured (see the addendum below); the
next evaluation step should be model/NLI semantic audit decisions over
the already-generated drafts, not a launch-readiness claim.

## Repeat-Run Variance Addendum

A credentialed repeat-run capture was subsequently executed at `RUNS=5`
per profile (10 runs total: 5 × `llm_candidate_v0`, 5 × `llm_candidate_v1`)
against the same 12-case slice. The aggregated public-safe summary is
tracked at
[`reports/llm_adversarial_v1_repeat_summary.md`](llm_adversarial_v1_repeat_summary.md)
(JSON sibling alongside it); raw per-run reports and traces remain
gitignored.

| Metric | `llm_candidate_v0` (5 runs) | `llm_candidate_v1` (5 runs) |
|---|---|---|
| Passed / 12 per run | 9, 10, 10, 7, 10 | 12, 12, 12, 12, 12 |
| Runtime-guardrail fires (all runtime-only) | 3, 2, 2, 5, 2 | 0, 0, 0, 0, 0 |
| Offline `UNSAFE_CUSTOMER_COMMS` | 0 every run | 0 every run |
| `EVALUATOR_MISS` | 0 every run | 0 every run |

- Across all 10 runs the negation-aware offline grader emitted zero
  affirmative `UNSAFE_CUSTOMER_COMMS` and zero `EVALUATOR_MISS`. Every one
  of the 14 runtime-guardrail fires was runtime-only — the conservative
  substring guardrail firing on hedged-but-negated drafts the offline
  grader cleared. The single-run guardrail-vs-audit asymmetry generalizes.
- `llm_candidate_v1` was stable at 12/12 across every run; `llm_candidate_v0`
  varied 7–10/12, and 8 of the 12 cases flipped pass/fail at least once
  across its runs.
- Combined estimated cost was `$0.607305` over 10 runs (mean `$0.06073`,
  min `$0.047943`, max `$0.073599`, stdev `$0.011094`); the five v1 runs
  were the costlier set. Per-band latency means were L1 ≈8023 ms, L2
  ≈8866 ms, L3 ≈9428 ms.

N=5 per profile on a 12-case synthetic slice cannot establish prompt
robustness, model safety, pilot readiness, production readiness, or
regulatory compliance. **NOT READY FOR PILOT** remains the posture;
repeat-run variance is one input to a future readiness conversation, not
a readiness signal.
