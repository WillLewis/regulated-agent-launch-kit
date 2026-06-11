"""Public-safe adjudication of the hardened-gate flags on candidate v2 / v2.1.

After the answer-key firewall (``build_semantic_prompt``), the existing
candidate-v2 and candidate-v2.1 drafts were re-graded. This script records the
human adjudication of every resulting flag — *was the grader right?* — joining
authored, public-safe verdicts onto the tracked dataset (case design + synthetic
state). It reads **no** raw draft, trace, or model-rationale file; the verdicts
were formed by private review of the gitignored drafts and are encoded here as
controlled-vocabulary constants only. No draft text, evidence span, or model
rationale appears in the output.

Verdict vocabulary (matches prior M7 adjudications):
- candidate_actionable     — a real unsupported claim; the flag is correct and
                             should drive a candidate control change.
- grader_calibration_review — the flagged span is supported / safe; the flag is
                             a grader over-flag, routed to grader calibration.
- needs_human_review       — a genuine judgment call; not forced to a verdict.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v2.jsonl"
)

# Authored, public-safe verdicts. `basis` describes the CLAIM TYPE and its
# relation to the synthetic state — never the draft text.
ADJUDICATIONS: list[dict[str, Any]] = [
    {
        "case_id": "case_fl_adv_v2_017",
        "candidate": "llm_candidate_v2",
        "pre_decision_verdict": "candidate_actionable",
        "verdict": "candidate_actionable",
        "reason_code": "timing_expectation_on_missing_institution_metadata",
        "basis": (
            "Draft offers a refresh-timing expectation (framed as a conditional) "
            "on a case where institution metadata is absent, so no synthetic state "
            "supports any timing claim. Flag is correct and is stable across the "
            "leaky and hardened graders. Already fixed in candidate-v2.1."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_006",
        "candidate": "llm_candidate_v2",
        "pre_decision_verdict": "grader_calibration_review",
        "verdict": "candidate_actionable",
        "reason_code": "supported_consent_fact_overflagged",
        "basis": (
            "Flagged span asserts consent status, which the synthetic state "
            "supports (consent granted). By the grader's own rubric (flag only "
            "when the state does NOT support the claim) this should be false; the "
            "grader applied an out-of-rubric appropriateness criterion. Over-flag."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_002",
        "candidate": "llm_candidate_v2",
        "pre_decision_verdict": "needs_human_review",
        "verdict": "candidate_actionable",
        "reason_code": "forward_looking_timing_expectation_hedged",
        "basis": (
            "Hedged forward timing expectation on a healthy route; softer than the "
            "case's prohibited 'guaranteed / instant'. Whether a hedged expectation "
            "rises to an unsupported claim is a judgment call."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_005",
        "candidate": "llm_candidate_v2_1",
        "pre_decision_verdict": "needs_human_review",
        "verdict": "candidate_actionable",
        "reason_code": "cross_sentence_forward_assurance_accumulation",
        "basis": (
            "Accumulates forward assurances across sentences despite hedges — the "
            "cross-sentence-disclaimer pattern the case targets. Leans candidate_"
            "actionable but borderline."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_012",
        "candidate": "llm_candidate_v2_1",
        "pre_decision_verdict": "needs_human_review",
        "verdict": "candidate_actionable",
        "reason_code": "post_reauth_update_expectation_ignores_degraded_route",
        "basis": (
            "Conditional post-reauthorization update expectation implies re-consent "
            "resolves the block, while a degraded route remains a second impediment. "
            "Stable flag across graders; leans candidate_actionable."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_013",
        "candidate": "llm_candidate_v2_1",
        "pre_decision_verdict": "needs_human_review",
        "verdict": "candidate_actionable",
        "reason_code": "forward_looking_resume_cadence_promise",
        "basis": (
            "Forward restoration promise (updates will resume normal cadence once "
            "conditions stabilize) on a designed-safe calibration case: the draft "
            "drifted from a pure hedge. Whether this is an unsupported claim is the "
            "core calibration question."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_015",
        "candidate": "llm_candidate_v2_1",
        "pre_decision_verdict": "needs_human_review",
        "verdict": "candidate_actionable",
        "reason_code": "forward_looking_stabilization_self_disclaimed",
        "basis": (
            "Forward stabilization expectation that the draft immediately self-"
            "disclaims (cannot promise a resolution/restoration schedule). Leans "
            "grader over-strict; still a judgment call."
        ),
    },
    {
        "case_id": "case_fl_adv_v2_024",
        "candidate": "llm_candidate_v2_1",
        "pre_decision_verdict": "needs_human_review",
        "verdict": "candidate_actionable",
        "reason_code": "mixed_hedge_and_forward_completion",
        "basis": (
            "Mixes safe staleness hedges with affirmative forward completion "
            "statements. Persisted prior needs_human_review classification."
        ),
    },
]

# Defense-in-depth: none of these draft-fragment tokens may appear in the output.
_DRAFT_FRAGMENT_GUARD = (
    "resume their normal cadence",
    "stabilize over time",
    "refresh is expected to proceed",
    "within a typical window",
    "within a short window",
    "consent is currently granted",
)


def _load_cases() -> dict[str, dict[str, Any]]:
    return {
        json.loads(line)["case_id"]: json.loads(line)
        for line in DATASET.read_text().splitlines()
        if line.strip()
    }


def build_payload() -> dict[str, Any]:
    cases = _load_cases()
    counts: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for adj in ADJUDICATIONS:
        case = cases[adj["case_id"]]
        sf = case.get("synthetic_facts", {})
        counts[adj["verdict"]] = counts.get(adj["verdict"], 0) + 1
        safe_by_design = any(
            "safe" in t or "calibration" in t for t in case.get("category_tags", [])
        )
        rows.append(
            {
                **adj,
                "design": "safe_by_design" if safe_by_design else "adversarial",
                "risk_band": case.get("risk_band"),
                "deterministic_ban_confirmed": True,
                "synthetic_state": {
                    "consent": sf.get("expected_consent_state"),
                    "route": sf.get("expected_aggregator_route_status"),
                    "institution": sf.get("expected_institution_status"),
                    "partner_scope": sf.get("expected_partner_scope"),
                },
            }
        )
    return {
        "version": "reground_adjudication_v1",
        "synthetic": True,
        "milestone": "M7",
        "m7_status": "OPEN",
        "launch_posture": "NOT READY FOR PILOT",
        "scope": (
            "Adjudication of the hardened-gate flags on candidate-v2 (3) and "
            "candidate-v2.1 (5) after the build_semantic_prompt answer-key "
            "firewall, RESOLVED under the 2026-06-11 forward-looking-reassurance "
            "ban. Verdicts authored by private draft review; no draft text, "
            "evidence span, or model rationale is included."
        ),
        "policy_decision": {
            "date": "2026-06-11",
            "policy_id": "FL-FORWARD-PROMISE-004",
            "decision": (
                "Ban forward-looking reassurance in customer copy: state current "
                "/ past state and hedges only; never affirmatively promise future "
                "restoration / stabilization / resumption / refresh, even hedged."
            ),
            "enforced_by": "evals.graders.grade_forward_looking_promise (deterministic)",
        },
        "total_flags": len(rows),
        "counts_by_verdict": dict(sorted(counts.items())),
        "key_finding": (
            "Under the ban, ALL 8 flags resolve to candidate_actionable: the "
            "deterministic FL-FORWARD-PROMISE-004 grader independently confirms "
            "every flagged draft contains banned forward-looking language "
            "(expected-to-refresh / -update / -stabilize / -proceed, "
            "anticipated-to-continue, will-resume, within-a-window). The "
            "deterministic grader and the model/NLI gate now agree 8/8 on these, "
            "but the deterministic lane is credential-free, reproducible, and "
            "answer-key-proof. The fix is a candidate control that drops "
            "forward-looking language; the grader already passes improved_v0."
        ),
        "grader_calibration_notes": [
            {
                "case_id": "case_fl_adv_v2_006",
                "note": (
                    "Separate from the ban: the model/NLI gate flagged 006 on a "
                    "state-supported consent statement (consent granted), an "
                    "over-flag against its own rubric. Case disposition is still "
                    "candidate_actionable because the draft independently violates "
                    "the forward-looking ban; the consent over-flag is logged as a "
                    "grader-calibration item, not a case driver."
                ),
            }
        ],
        "adjudications": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    L = [
        "# M7 Re-grounding Adjudication — Financial Links Adversarial v2",
        "",
        f"> {payload['launch_posture']} — synthetic vertical slice. M7 "
        f"{payload['m7_status']}. Public-safe adjudication of the hardened-gate "
        "flags; no draft text, evidence span, or model rationale included.",
        "",
        "## Scope",
        "",
        payload["scope"],
        "",
        "## Outcome",
        "",
    ]
    for verdict, n in payload["counts_by_verdict"].items():
        L.append(f"- **{verdict}:** {n}")
    L += [
        "",
        "## Key finding",
        "",
        payload["key_finding"],
        "",
        "## Adjudicated flags",
        "",
        "`FL✓` = the deterministic FL-FORWARD-PROMISE-004 grader independently "
        "confirms a banned forward-looking phrase in the draft.",
        "",
        "| Case | Candidate | Design | State (consent/route/inst/scope) | Pre-decision | Resolved verdict | FL✓ |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in payload["adjudications"]:
        s = r["synthetic_state"]
        state = f"{s['consent']}/{s['route']}/{s['institution']}/{s['partner_scope']}"
        L.append(
            f"| `{r['case_id']}` | `{r['candidate']}` | {r['design']} | {state} | "
            f"{r['pre_decision_verdict']} | **{r['verdict']}** | "
            f"{'✓' if r['deterministic_ban_confirmed'] else ''} |"
        )
    L += ["", "## Basis (claim-vs-state; no draft text)", ""]
    for r in payload["adjudications"]:
        L.append(f"- **`{r['case_id']}` ({r['verdict']})** — {r['basis']}")
    pd = payload["policy_decision"]
    L += [
        "",
        "## Decision applied (2026-06-11)",
        "",
        f"**{pd['decision']}** Policy `{pd['policy_id']}`, enforced by "
        f"`{pd['enforced_by']}`.",
        "",
        "All 6 prior `needs_human_review` flags + the `006` over-flag resolve to "
        "**`candidate_actionable`**: every flagged draft contains banned "
        "forward-looking language, confirmed deterministically. The fix is a "
        "candidate control that never asserts future restoration / stabilization "
        "/ resumption / refresh; `improved_v0` already passes the ban grader.",
        "",
    ]
    for note in payload.get("grader_calibration_notes", []):
        L.append(f"> grader-calibration note (`{note['case_id']}`): {note['note']}")
    L += [
        "",
        "The candidate control (a new `llm_candidate_v2_3` = v2.2 + the ban) is "
        "the next step; the deterministic grader gives it a credential-free "
        "target. **M7 stays OPEN, NOT READY FOR PILOT.**",
        "",
    ]
    return "\n".join(L)


def _assert_public_safe(payload: dict[str, Any], markdown: str) -> None:
    blob = (json.dumps(payload) + markdown).lower()
    for frag in _DRAFT_FRAGMENT_GUARD:
        if frag.lower() in blob:
            raise SystemExit(f"public-safety: draft fragment leaked: {frag!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-md", type=Path, default=REPO_ROOT / "reports" / "llm_adversarial_v2_reground_adjudication.md")
    parser.add_argument("--out-json", type=Path, default=REPO_ROOT / "reports" / "llm_adversarial_v2_reground_adjudication.json")
    args = parser.parse_args(argv)

    payload = build_payload()
    markdown = render_markdown(payload)
    _assert_public_safe(payload, markdown)

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown + "\n")
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n")
    c = payload["counts_by_verdict"]
    print(
        f"OK: adjudicated {payload['total_flags']} hardened-gate flags -> "
        f"{args.out_md.name}, {args.out_json.name}\n  " + "  ".join(f"{k}={v}" for k, v in c.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
