# Semantic Grader Reliability — Financial Links Gold Set

> NOT READY FOR PILOT — synthetic vertical slice. This measures the model/NLI semantic **grader** against a human-authored gold set whose labels are independent of the grader. It is a reliability check on the measurement instrument, not a safety or readiness claim about the agent.

- **Verdicts source:** anthropic_nli_semantic_v0 gold-pass (replayed, public-safe)
- **Scored items:** 28 (14 known-bad, 14 known-safe)
- **Positive class:** positive = grader flags an unsupported claim (makes_unsupported_claim=true)

## Headline

- **Recall (caught overpromises): 100.0%** (95% CI 78–100%) — the safety-critical metric.
- Precision (flags that were right): 100.0% (95% CI 78–100%)
- Specificity (safe drafts left alone): 100.0%
- Accuracy: 100.0%  |  F1: 100.0%

## Confusion matrix

| | grader flags | grader clean |
| --- | --- | --- |
| **gold: unsupported claim** | 14 (caught) | 0 (**missed**) |
| **gold: safe** | 0 (over-flag) | 14 (correct pass) |

## What a clean gate does and does not prove

- On this set the grader caught **all 14** known overpromises (recall 100.0% (95% CI 78–100%)).
- A clean gate is therefore **consistent with** safety on this synthetic slice — but the wide small-N interval means it is **not proof**. The lower CI bound is the honest floor on detection.
- It says nothing about claim types or phrasings absent from the gold set; expand the set before treating a clean gate as strong evidence.

## Missed overpromises (false negatives)

None — the grader caught every known overpromise on this set.

## Over-flags (false positives)

None — the grader left every known-safe draft alone.

## By difficulty

| slice | n | recall | precision | specificity |
| --- | --- | --- | --- | --- |
| easy | 12 | 100.0% | 100.0% | 100.0% |
| hard | 16 | 100.0% | 100.0% | 100.0% |

_Hard = paraphrased / cross-sentence drafts that defeat lexical matching. Recall on the hard slice is where false negatives hide._

## Caveats

- Synthetic gold set; labels human-authored independently of the grader.
- Grader received the synthetic operational context but NOT the gold label or any expected/prohibited-behavior answer key, so this measures the grader's independent discrimination.
- Small N (14 known-bad, 14 known-safe): point estimates carry wide Wilson 95% CIs — read this as a directional reliability check, not a tight estimate.

