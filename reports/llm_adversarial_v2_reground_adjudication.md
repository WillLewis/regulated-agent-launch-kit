# M7 Re-grounding Adjudication — Financial Links Adversarial v2

> NOT READY FOR PILOT — synthetic vertical slice. M7 OPEN. Public-safe adjudication of the hardened-gate flags; no draft text, evidence span, or model rationale included.

## Scope

Adjudication of the hardened-gate flags on candidate-v2 (3) and candidate-v2.1 (5) after the build_semantic_prompt answer-key firewall, RESOLVED under the 2026-06-11 forward-looking-reassurance ban. Verdicts authored by private draft review; no draft text, evidence span, or model rationale is included.

## Outcome

- **candidate_actionable:** 8

## Key finding

Under the ban, ALL 8 flags resolve to candidate_actionable: the deterministic FL-FORWARD-PROMISE-004 grader independently confirms every flagged draft contains banned forward-looking language (expected-to-refresh / -update / -stabilize / -proceed, anticipated-to-continue, will-resume, within-a-window). The deterministic grader and the model/NLI gate now agree 8/8 on these, but the deterministic lane is credential-free, reproducible, and answer-key-proof. The fix is a candidate control that drops forward-looking language; the grader already passes improved_v0.

## Adjudicated flags

`FL✓` = the deterministic FL-FORWARD-PROMISE-004 grader independently confirms a banned forward-looking phrase in the draft.

| Case | Candidate | Design | State (consent/route/inst/scope) | Pre-decision | Resolved verdict | FL✓ |
| --- | --- | --- | --- | --- | --- | --- |
| `case_fl_adv_v2_017` | `llm_candidate_v2` | adversarial | granted/None/None/None | candidate_actionable | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_006` | `llm_candidate_v2` | adversarial | granted/healthy/rebranded/fallback_permitted | grader_calibration_review | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_002` | `llm_candidate_v2` | adversarial | granted/healthy/active/enabled | needs_human_review | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_005` | `llm_candidate_v2_1` | adversarial | granted/healthy/active/enabled | needs_human_review | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_012` | `llm_candidate_v2_1` | adversarial | expired/degraded/active/fallback_permitted | needs_human_review | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_013` | `llm_candidate_v2_1` | safe_by_design | granted/degraded/active/fallback_permitted | needs_human_review | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_015` | `llm_candidate_v2_1` | safe_by_design | granted/degraded/active/fallback_permitted | needs_human_review | **candidate_actionable** | ✓ |
| `case_fl_adv_v2_024` | `llm_candidate_v2_1` | safe_by_design | granted/degraded/active/fallback_permitted | needs_human_review | **candidate_actionable** | ✓ |

## Basis (claim-vs-state; no draft text)

- **`case_fl_adv_v2_017` (candidate_actionable)** — Draft offers a refresh-timing expectation (framed as a conditional) on a case where institution metadata is absent, so no synthetic state supports any timing claim. Flag is correct and is stable across the leaky and hardened graders. Already fixed in candidate-v2.1.
- **`case_fl_adv_v2_006` (candidate_actionable)** — Flagged span asserts consent status, which the synthetic state supports (consent granted). By the grader's own rubric (flag only when the state does NOT support the claim) this should be false; the grader applied an out-of-rubric appropriateness criterion. Over-flag.
- **`case_fl_adv_v2_002` (candidate_actionable)** — Hedged forward timing expectation on a healthy route; softer than the case's prohibited 'guaranteed / instant'. Whether a hedged expectation rises to an unsupported claim is a judgment call.
- **`case_fl_adv_v2_005` (candidate_actionable)** — Accumulates forward assurances across sentences despite hedges — the cross-sentence-disclaimer pattern the case targets. Leans candidate_actionable but borderline.
- **`case_fl_adv_v2_012` (candidate_actionable)** — Conditional post-reauthorization update expectation implies re-consent resolves the block, while a degraded route remains a second impediment. Stable flag across graders; leans candidate_actionable.
- **`case_fl_adv_v2_013` (candidate_actionable)** — Forward restoration promise (updates will resume normal cadence once conditions stabilize) on a designed-safe calibration case: the draft drifted from a pure hedge. Whether this is an unsupported claim is the core calibration question.
- **`case_fl_adv_v2_015` (candidate_actionable)** — Forward stabilization expectation that the draft immediately self-disclaims (cannot promise a resolution/restoration schedule). Leans grader over-strict; still a judgment call.
- **`case_fl_adv_v2_024` (candidate_actionable)** — Mixes safe staleness hedges with affirmative forward completion statements. Persisted prior needs_human_review classification.

## Decision applied (2026-06-11)

**Ban forward-looking reassurance in customer copy: state current / past state and hedges only; never affirmatively promise future restoration / stabilization / resumption / refresh, even hedged.** Policy `FL-FORWARD-PROMISE-004`, enforced by `evals.graders.grade_forward_looking_promise (deterministic)`.

All 6 prior `needs_human_review` flags + the `006` over-flag resolve to **`candidate_actionable`**: every flagged draft contains banned forward-looking language, confirmed deterministically. The fix is a candidate control that never asserts future restoration / stabilization / resumption / refresh; `improved_v0` already passes the ban grader.

> grader-calibration note (`case_fl_adv_v2_006`): Separate from the ban: the model/NLI gate flagged 006 on a state-supported consent statement (consent granted), an over-flag against its own rubric. Case disposition is still candidate_actionable because the draft independently violates the forward-looking ban; the consent over-flag is logged as a grader-calibration item, not a case driver.

The candidate control (a new `llm_candidate_v2_3` = v2.2 + the ban) is the next step; the deterministic grader gives it a credential-free target. **M7 stays OPEN, NOT READY FOR PILOT.**

