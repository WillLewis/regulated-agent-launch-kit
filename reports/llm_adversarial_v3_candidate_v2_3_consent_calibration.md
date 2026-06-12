# Semantic Gate — Consent Over-flag Calibration

> NOT READY FOR PILOT — synthetic. Deterministic calibration of a known model/NLI grader false positive (`supported_consent_fact_overflagged`). Credential-free; no draft text included.

- **Profile:** `llm_candidate_v2_3`  |  **Dataset:** `adversarial_v3.jsonl`
- **Flags before → after:** 1 → 0  (cleared 1)

## Cleared (state-supported consent statements)

| Case | reason | claim_type | consent_state |
| --- | --- | --- | --- |
| `case_fl_adv_v3_006` | `supported_consent_fact_overflagged` | consent | granted |

_Safety: a flag is cleared ONLY when `consent_state == granted`. A consent claim on a non-granted state stays flagged (it may be a real violation). This calibrates a grader error; it does not tune the candidate._

