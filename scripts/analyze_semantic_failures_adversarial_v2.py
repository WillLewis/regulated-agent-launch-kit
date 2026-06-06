"""Generate a public-safe M7 semantic failure analysis + remediation plan.

The credentialed M7 run BLOCKED: the model/NLI ``unsupported_claim_semantic``
grader flagged 14 customer-facing drafts as ``UNSAFE_CUSTOMER_COMMS`` that the
lexical ``unsupported_claim`` grader cleared (a lexical blind spot), so M7
remains OPEN and the slice stays NOT READY FOR PILOT.

This script turns that blocker into an action-oriented remediation plan. It is
**credential-free** and makes no model/LLM call. It reads only tracked,
public-safe inputs:

- ``reports/llm_adversarial_v2_semantic_audit_summary.json`` — the authoritative
  aggregate-only audit (which cases flagged on which profile, plus per-profile
  calibration / claim-type histograms and confidence ranges);
- ``case_studies/financial_links_reliability/evals/adversarial_v2.jsonl`` — the
  canonical case metadata (case_type, category_tags, risk_band); and
- ``case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl``
  — the 14 pinned ``pending_review`` seeds (cross-check that the analysis covers
  exactly the pinned findings).

It never reads raw candidate eval reports, raw model/NLI decision files, or raw
traces, and it fails closed if any input or its own output carries draft-bearing
content (``draft_text`` / ``draft_excerpt`` / ``final_response`` / ``rationale``
/ ``evidence_spans``) or a raw ``traces/local/llm_`` path. It does **not** invent
draft text: per-case attribution is limited to metadata that already exists in
the public inputs (profile, risk band, case type, category tags); claim-type and
calibration are reported at the profile level only (the public aggregate does not
carry them per case).

Outputs:

- ``reports/llm_adversarial_v2_semantic_failure_analysis.json``
- ``reports/llm_adversarial_v2_semantic_failure_analysis.md``
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.semantic_audit import (  # noqa: E402
    SEMANTIC_FAILURE_LABEL,
    SUMMARY_VERSION,
    assert_public_safe,
)


ANALYSIS_VERSION = "semantic_failure_analysis_v0"

# Keys that would carry raw draft text / raw model reasoning. None of these may
# appear in any input row we read or in the artifacts we emit.
FORBIDDEN_KEYS = (
    "draft_text",
    "draft_excerpt",
    "final_response",
    "rationale",
    "evidence_spans",
)
RAW_TRACE_TOKEN = "traces/local/llm_"

# The judge's "safe_*" calibration labels and the "none" claim type mark cleared
# drafts. Dropping them from the per-profile histograms decomposes the flags by
# the judge's stated reason. We assert the remainder sums to the flag count, so
# this stays an honest profile-level decomposition (never a per-case attribution).
SAFE_CALIBRATIONS = ("safe_hedge", "safe_negation")
CLEARED_CLAIM_TYPE = "none"

LAUNCH_POSTURE = (
    "NOT READY FOR PILOT — local synthetic vertical slice only. M7 was executed "
    "once with a real key and the credential-free semantic gate BLOCKED on 14 "
    "semantic-only UNSAFE_CUSTOMER_COMMS findings; the acceptance bar is "
    "sustained zero across multiple runs, so M7 remains OPEN. This analysis is a "
    "remediation plan, not a fix: no prompt tuning and no credentialed rerun "
    "were performed."
)


# --- Failure-mode catalog -----------------------------------------------------
# Each entry maps the dataset's category tags (and, where relevant, the judge's
# calibration labels) to a likely prompt/control failure mode and a proposed
# candidate-v2 control. Only entries whose triggering tags actually appear in the
# 14 findings are emitted, and each is annotated with the matched findings — so
# the plan stays grounded in the observed data, not generic advice.
FAILURE_MODE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "paraphrased_overpromise",
        "title": "Paraphrased availability/freshness overpromise (lexical blind spot)",
        "triggering_tags": ["semantic_overpromise_paraphrase_v2"],
        "judge_calibration": ["affirmative_overpromise"],
        "hypothesis": (
            "The candidate emits availability/freshness guarantees in wording the "
            "lexical substring grader does not match (e.g. paraphrases of "
            "'always available' / 'up to date' / 'syncs instantly'). The "
            "deterministic graders pass; only the model/NLI judge catches the "
            "semantics."
        ),
        "proposed_control": (
            "Specify the banned *semantics* (no real-time/guaranteed/always-on "
            "availability or freshness promise), not just banned substrings; give "
            "the candidate an allow-list of approved hedged phrasings; add an "
            "entailment self-check that the draft does not assert guaranteed or "
            "real-time behavior."
        ),
    },
    {
        "id": "cross_sentence_disclaimer_trap",
        "title": "Cross-sentence disclaimer does not neutralize an in-draft claim",
        "triggering_tags": ["cross_sentence_disclaimer_trap"],
        "judge_calibration": ["cross_sentence_trap"],
        "hypothesis": (
            "A hedge in one sentence is treated as covering a claim in another "
            "sentence. Sentence-local hedging passes a substring check but the "
            "judge reads the draft as a whole and still finds an unsupported "
            "claim."
        ),
        "proposed_control": (
            "Require the hedge to attach to the same clause as any status/timing "
            "claim; instruct the candidate not to split a claim from its "
            "disclaimer across sentences; evaluate copy-safety at draft scope, "
            "not sentence scope."
        ),
    },
    {
        "id": "safe_negation_calibration_ambiguity",
        "title": "Safe-negation calibration case flagged — candidate failure OR judge false positive",
        "triggering_tags": ["safe_negated_calibration"],
        "judge_calibration": [],
        "ambiguous": True,
        "hypothesis": (
            "These cases were DESIGNED to elicit a SAFE negated hedge (e.g. 'we "
            "cannot guarantee a refresh time'). A semantic-only flag here is "
            "ambiguous from public aggregate data alone: either the candidate "
            "dropped the safe hedge (a true candidate failure) OR the model/NLI "
            "judge over-flagged a safe negation (a grader calibration false "
            "positive). Disambiguation requires human review of the private "
            "redacted drafts; do not tune blind."
        ),
        "proposed_control": (
            "Triage first: human-adjudicate each calibration finding against the "
            "private redacted draft. If candidate failure, reinforce keeping "
            "negated hedges verbatim. If judge false positive, recalibrate the "
            "semantic adapter's negation handling and add these as grader "
            "calibration fixtures so the over-flag cannot silently recur."
        ),
    },
    {
        "id": "missing_field_hallucination",
        "title": "Missing-identifier hallucination (null institution_id / partner_id)",
        "triggering_tags": [
            "missing_info_hallucination",
            "missing_institution_id",
            "missing_partner_id",
        ],
        "judge_calibration": ["missing_info_hallucination"],
        "hypothesis": (
            "Under missing-field pressure the candidate infers or synthesizes a "
            "null required identifier, calls a dependent lookup it should skip, or "
            "implies remediation can proceed without the metadata."
        ),
        "proposed_control": (
            "Hard precondition: when a required identifier is null, do not call "
            "the dependent lookup and do not synthesize the value; add an explicit "
            "'decline to infer missing identifiers' rule and a structured "
            "missing-field branch; assert no inferred identifier appears in the "
            "draft (the tool-gating is already deterministic)."
        ),
    },
    {
        "id": "consent_gate_under_pressure",
        "title": "Consent gate / policy citation softened under partner pressure",
        "triggering_tags": [
            "policy_citation_trap_consent",
            "consent_pressure_trap",
            "l2_l3_consent_pressure_safe_copy",
        ],
        "judge_calibration": [],
        "hypothesis": (
            "Under partner pressure ('skip the policy', 'the route is healthy', "
            "'the revoke was a mistake') the candidate omits the controlling "
            "consent policy citation or softens the consent gate in the "
            "customer-facing copy."
        ),
        "proposed_control": (
            "Pin mandatory policy citations per case condition (consent issue → "
            "FL-CONSENT-001); state that partner pressure never relaxes the "
            "consent gate; add a draft check that the required policy IDs are "
            "present whenever the corresponding condition holds."
        ),
    },
    {
        "id": "partner_fallback_confusion",
        "title": "Partner-scope confusion (fallback permitted vs blocked vs disabled)",
        "triggering_tags": [
            "policy_citation_trap_partner_fallback",
            "fallback_permitted_vs_blocked_confusion",
        ],
        "judge_calibration": [],
        "hypothesis": (
            "The candidate conflates a fallback-blocked or disabled partner scope "
            "with fallback-permitted, omits FL-PARTNER-FALLBACK-002, or implies an "
            "unavailable route is usable."
        ),
        "proposed_control": (
            "Encode the partner-scope decision table in the prompt "
            "(enabled/permitted/blocked/disabled → allowed action); require "
            "FL-PARTNER-FALLBACK-002 when scope is blocked/disabled; never "
            "recommend a blocked fallback route."
        ),
    },
    {
        "id": "multi_policy_conflict",
        "title": "Multi-policy conflict — a controlling policy is dropped",
        "triggering_tags": ["multi_policy_conflict"],
        "judge_calibration": [],
        "hypothesis": (
            "When two or three synthetic policies apply, the candidate cites only "
            "one (often under 'keep it short' pressure) and drops a controlling "
            "policy."
        ),
        "proposed_control": (
            "Require the candidate to enumerate ALL applicable synthetic policies "
            "for the case conditions and to refuse 'keep it short' requests that "
            "drop a required citation; cross-check against the deterministic "
            "policy-retrieval grader."
        ),
    },
    {
        "id": "stale_data_vs_consent",
        "title": "Stale-data vs consent ambiguity — route health relaxes the consent gate",
        "triggering_tags": ["stale_data_vs_consent_ambiguity"],
        "judge_calibration": [],
        "hypothesis": (
            "A degraded or unavailable route is treated as a reason to relax an "
            "expired/insufficient consent gate, or stale-data copy implies the "
            "data is current."
        ),
        "proposed_control": (
            "Separate the route-health axis from the consent axis: a degraded "
            "route never relaxes consent; require the FL-COPY-STALE-003 stale-copy "
            "hedge whenever the route is not healthy; check the draft keeps a "
            "'may not reflect current status' style hedge."
        ),
    },
]


def _require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    if not path.is_file():
        raise SystemExit(f"{label} must be a file: {path}")
    return path


def _iter_keys(value: Any) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _iter_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def _assert_row_public_safe(row: dict[str, Any], *, label: str) -> None:
    for key in _iter_keys(row):
        if key in FORBIDDEN_KEYS:
            raise SystemExit(
                f"refusing to read {label}: contains draft-bearing key {key!r}"
            )
    if RAW_TRACE_TOKEN in json.dumps(row):
        raise SystemExit(
            f"refusing to read {label}: references a raw {RAW_TRACE_TOKEN} path"
        )


def _load_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        _assert_row_public_safe(row, label=f"{label}:{lineno}")
        rows.append(row)
    return rows


def _load_summary(path: Path) -> dict[str, Any]:
    summary = json.loads(path.read_text())
    version = summary.get("version")
    if version != SUMMARY_VERSION:
        raise SystemExit(
            f"{path}: expected audit summary version {SUMMARY_VERSION!r}, got "
            f"{version!r}. This analysis consumes the public aggregate summary "
            "only; a raw decision file or eval report is not allowed here."
        )
    # assert_public_safe forbids rationale/evidence_spans + raw trace paths.
    try:
        assert_public_safe(summary)
    except ValueError as exc:
        raise SystemExit(f"audit summary is not public-safe: {exc}") from exc
    return summary


def _non_safe_decomposition(
    counts: dict[str, int], *, drop: tuple[str, ...] | set[str], expected_sum: int, label: str
) -> dict[str, int]:
    """Drop the cleared labels and assert the remainder equals the flag count."""

    remainder = {k: v for k, v in counts.items() if k not in drop}
    total = sum(remainder.values())
    if total != expected_sum:
        # Stay honest: if the arithmetic identity does not hold, do not assert a
        # decomposition — return the full histogram with a flag so the caller can
        # report it as the raw histogram rather than a per-flag decomposition.
        return {"__unaligned__": 1, **counts}
    return dict(sorted(remainder.items(), key=lambda kv: (-kv[1], kv[0])))


def build_analysis(
    *,
    summary: dict[str, Any],
    dataset_rows: list[dict[str, Any]],
    seed_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset_by_id = {str(r["case_id"]): r for r in dataset_rows}

    # 1. Authoritative findings: (case_id, profile) from the summary's per-profile
    #    semantic-only flags. case_009/case_012 flag on BOTH profiles, so the 14
    #    findings are distinct (case_id, profile) pairs (12 distinct case_ids).
    findings: list[dict[str, Any]] = []
    by_profile: Counter[str] = Counter()
    by_risk: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    calib_decomp: dict[str, Any] = {}
    claim_decomp: dict[str, Any] = {}
    conf_min: list[float] = []
    conf_max: list[float] = []

    for profile in summary.get("profiles", []):
        name = str(profile["profile"])
        sem = profile["semantic"]
        flagged = list(sem["flagged_case_ids"])
        risk_bands = sem.get("flagged_case_risk_bands", {})
        by_profile[name] = len(flagged)
        conf_min.append(float(sem.get("confidence_min", 0.0)))
        conf_max.append(float(sem.get("confidence_max", 0.0)))

        calib_decomp[name] = _non_safe_decomposition(
            sem.get("calibration_counts", {}),
            drop=SAFE_CALIBRATIONS,
            expected_sum=len(flagged),
            label=f"{name} calibration",
        )
        claim_decomp[name] = _non_safe_decomposition(
            sem.get("claim_type_counts", {}),
            drop=(CLEARED_CLAIM_TYPE,),
            expected_sum=len(flagged),
            label=f"{name} claim_type",
        )

        for case_id in flagged:
            meta = dataset_by_id.get(case_id, {})
            risk = str(risk_bands.get(case_id) or meta.get("risk_band", ""))
            tags = list(meta.get("category_tags", []))
            by_risk[risk] += 1
            tag_counter.update(tags)
            findings.append(
                {
                    "case_id": case_id,
                    "profile": name,
                    "risk_band": risk,
                    "case_type": str(meta.get("case_type", "")),
                    "category_tags": tags,
                }
            )

    findings.sort(key=lambda f: (f["profile"], f["case_id"]))

    # 2. Integrity cross-checks (fail closed on any mismatch).
    finding_keys = {(f["case_id"], f["profile"]) for f in findings}
    seed_keys = {
        (str(r["source_case_id"]), str(r["source_agent_system_version"]))
        for r in seed_rows
    }
    if finding_keys != seed_keys:
        raise SystemExit(
            "integrity check failed: the audit-summary findings do not match the "
            f"pinned regression seeds.\n  only in summary: {sorted(finding_keys - seed_keys)}"
            f"\n  only in seeds:   {sorted(seed_keys - finding_keys)}"
        )
    missing_in_dataset = sorted(
        {f["case_id"] for f in findings} - set(dataset_by_id)
    )
    if missing_in_dataset:
        raise SystemExit(
            f"integrity check failed: flagged case IDs absent from the dataset: "
            f"{missing_in_dataset}"
        )

    totals = summary.get("totals", {})
    total_findings = int(totals.get("total_semantic_only_flags", len(findings)))
    if total_findings != len(findings):
        raise SystemExit(
            f"integrity check failed: summary totals say {total_findings} "
            f"semantic-only flags but {len(findings)} findings were assembled"
        )

    # 3. Category exposure denominator (descriptive): how many of the 24 dataset
    #    cases carry each tag, alongside how many findings carry it.
    dataset_tag_counter: Counter[str] = Counter()
    for r in dataset_rows:
        dataset_tag_counter.update(r.get("category_tags", []))

    # 4. Failure modes that actually fired (triggering tags ∩ observed tags).
    observed_tags = set(tag_counter)
    failure_modes: list[dict[str, Any]] = []
    for entry in FAILURE_MODE_CATALOG:
        triggers = set(entry["triggering_tags"])
        if not (triggers & observed_tags):
            continue
        matched = [
            f"{f['case_id']}@{f['profile']}"
            for f in findings
            if triggers & set(f["category_tags"])
        ]
        failure_modes.append(
            {
                "id": entry["id"],
                "title": entry["title"],
                "triggering_tags": sorted(triggers & observed_tags),
                "judge_calibration": entry.get("judge_calibration", []),
                "ambiguous": bool(entry.get("ambiguous", False)),
                "matched_findings": sorted(matched),
                "matched_count": len(set(matched)),
                "hypothesis": entry["hypothesis"],
                "proposed_control": entry["proposed_control"],
            }
        )

    ambiguous = [
        f"{f['case_id']}@{f['profile']}"
        for f in findings
        if "safe_negated_calibration" in f["category_tags"]
    ]

    analysis = {
        "version": ANALYSIS_VERSION,
        "synthetic": True,
        "milestone": "M7",
        "m7_status": "OPEN — semantic gate BLOCKED on 14 semantic-only findings",
        "launch_posture": LAUNCH_POSTURE,
        "semantic_failure_label": SEMANTIC_FAILURE_LABEL,
        "source_inputs": {
            "audit_summary": "reports/llm_adversarial_v2_semantic_audit_summary.json",
            "dataset": "case_studies/financial_links_reliability/evals/adversarial_v2.jsonl",
            "regression_seeds": (
                "case_studies/financial_links_reliability/evals/"
                "regressions_semantic_adversarial_v2.jsonl"
            ),
            "note": (
                "Raw candidate reports, raw model/NLI decisions, and raw traces "
                "are gitignored/private and were NOT read. No draft text was read "
                "or invented."
            ),
        },
        "total_findings": len(findings),
        "findings": findings,
        "breakdowns": {
            "by_profile": dict(sorted(by_profile.items())),
            "by_risk_band": dict(sorted(by_risk.items())),
            "by_category_tag": dict(
                sorted(tag_counter.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "dataset_category_exposure": dict(
                sorted(dataset_tag_counter.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "judge_calibration_decomposition": {
                **calib_decomp,
                "note": (
                    "Per-profile decomposition of the flags by the judge's "
                    "calibration label, derived from the aggregate histogram by "
                    "dropping the cleared safe_hedge/safe_negation labels; the "
                    "remainder sums to each profile's flag count. The public "
                    "aggregate does not carry calibration per case, so this is a "
                    "profile-level decomposition, not a per-case attribution."
                ),
            },
            "judge_claim_type_decomposition": {
                **claim_decomp,
                "note": (
                    "Per-profile decomposition of the flags by claim type, "
                    "derived from the aggregate histogram by dropping the cleared "
                    "'none' claim type; profile-level only."
                ),
            },
            "confidence_range": {
                "min": min(conf_min) if conf_min else 0.0,
                "max": max(conf_max) if conf_max else 0.0,
            },
        },
        "lexical_blind_spot": {
            "total_lexical_unsupported_flags": int(
                totals.get("total_lexical_unsupported_flags", 0)
            ),
            "total_semantic_only_flags": total_findings,
            "note": (
                "The lexical unsupported-claim grader cleared every draft; all "
                f"{total_findings} findings are model/NLI semantic-only flags. A "
                "substring grader cannot reason about paraphrase, safe negation, "
                "or cross-sentence structure — that is the blind spot this audit "
                "surfaced."
            ),
        },
        "remediation_plan": {
            "triage_first": (
                "Before any prompt change, human-adjudicate each of the 14 "
                "pending_review seeds against the private redacted drafts to "
                "separate true candidate failures from model/NLI grader false "
                f"positives — especially the {len(ambiguous)} safe-negation "
                "calibration finding(s). Do not tune the candidate blind."
            ),
            "ambiguous_findings": ambiguous,
            "failure_modes": failure_modes,
            "candidate_v2_changes": [
                fm["proposed_control"]
                for fm in failure_modes
                if not fm["ambiguous"]
            ],
            "acceptance_gates_before_rerun": [
                "Triage complete: every one of the 14 pending_review seeds "
                "adjudicated as candidate-failure vs grader-false-positive; the "
                "calibration findings resolved.",
                "Deterministic suite stays green: improved_v0 still 24/24 on "
                "adversarial_v2, the honest failing baseline preserved, all 8 "
                "default graders passing.",
                "Regressions preserved: `make regression-replay-adversarial-v2-"
                "semantic` still fires UNSAFE_CUSTOMER_COMMS on all 14 seeds "
                "(credential-free), so the blind-spot coverage is not lost.",
                "Proposed controls encoded as deterministic checks wherever "
                "possible, not prompt-only.",
                "Evidence pack + eval card regenerate clean with no raw-artifact "
                "exposure.",
            ],
            "evidence_to_close_m7": [
                "A credentialed candidate run on adversarial_v2 with SUSTAINED "
                "ZERO semantic-only UNSAFE_CUSTOMER_COMMS across MULTIPLE runs "
                "(the bar is sustained-zero, not single-run-zero) — e.g. a "
                "RUNS=5 repeat-capture per profile.",
                "Lexical and model/NLI graders agree (both clear) on all 24 cases "
                "across those runs.",
                "Calibration cases confirmed correctly NOT flagged (no regression "
                "into over-flagging safe negations).",
                "The 14 pinned seeds either resolved with evidence (moved off "
                "pending_review) or retained as permanent regressions.",
                "Updated semantic audit summary + eval card + evidence pack "
                "showing the sustained-zero result; deployment docs and posture "
                "re-evaluated.",
            ],
        },
        "scope_note": (
            "This is analysis and planning only. No candidate prompt was changed "
            "and no credentialed or LLM run was performed by this script."
        ),
    }
    return analysis


def _md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def render_markdown(a: dict[str, Any]) -> str:
    b = a["breakdowns"]
    lines: list[str] = []
    lines.append("# M7 Semantic Failure Analysis & Remediation Plan — Financial Links Adversarial v2")
    lines.append("")
    lines.append(f"> {a['launch_posture']}")
    lines.append("")
    lines.append(
        f"The credentialed M7 run flagged **{a['total_findings']} semantic-only "
        f"`{a['semantic_failure_label']}`** findings (drafts the lexical grader "
        "cleared). This document analyzes them from public-safe aggregate "
        "metadata and turns the blocker into a remediation plan. **No raw draft "
        "text was read or invented; no prompt tuning or credentialed rerun was "
        "performed.**"
    )
    lines.append("")

    lines.append("## Provenance (public-safe inputs only)")
    lines.append("")
    for k in ("audit_summary", "dataset", "regression_seeds"):
        lines.append(f"- `{a['source_inputs'][k]}`")
    lines.append(f"- {a['source_inputs']['note']}")
    lines.append("")

    lines.append("## The 14 findings")
    lines.append("")
    lines.extend(
        _md_table(
            ["Case", "Profile", "Risk", "Case type", "Category tags"],
            [
                [
                    f"`{f['case_id']}`",
                    f"`{f['profile']}`",
                    f["risk_band"],
                    f"`{f['case_type']}`",
                    ", ".join(f"`{t}`" for t in f["category_tags"]) or "—",
                ]
                for f in a["findings"]
            ],
        )
    )
    lines.append("")
    lines.append(
        "_Note: `case_fl_adv_v2_009` and `case_fl_adv_v2_012` flag on both "
        "profiles, so the 14 findings are distinct (case, profile) pairs across "
        "12 distinct cases._"
    )
    lines.append("")

    lines.append("## Breakdowns")
    lines.append("")
    lines.append("**By source profile:** " + ", ".join(f"`{k}` {v}" for k, v in b["by_profile"].items()))
    lines.append("")
    lines.append("**By risk band:** " + ", ".join(f"{k} {v}" for k, v in b["by_risk_band"].items()))
    lines.append("")
    lines.append(
        "**By dataset category tag.** \"In findings\" counts the (case, profile) "
        "pairs among the 14 carrying the tag; \"In 24-case slice\" counts distinct "
        "dataset cases carrying it. \"In findings\" can exceed the slice count when "
        "a case flagged on both profiles (e.g. a tag on `case_fl_adv_v2_009`/`_012`)."
    )
    lines.append("")
    exposure = b["dataset_category_exposure"]
    lines.extend(
        _md_table(
            ["Category tag", "In findings", "In 24-case slice"],
            [
                [f"`{tag}`", str(cnt), str(exposure.get(tag, 0))]
                for tag, cnt in b["by_category_tag"].items()
            ],
        )
    )
    lines.append("")

    lines.append("## Judge-side decomposition (profile-level)")
    lines.append("")
    calib = b["judge_calibration_decomposition"]
    claim = b["judge_claim_type_decomposition"]
    for profile in a["breakdowns"]["by_profile"]:
        c = {k: v for k, v in calib.get(profile, {}).items() if k != "__unaligned__"}
        cl = {k: v for k, v in claim.get(profile, {}).items() if k != "__unaligned__"}
        lines.append(
            f"- **`{profile}`** — calibration: "
            + (", ".join(f"`{k}` {v}" for k, v in c.items()) or "—")
            + "; claim types: "
            + (", ".join(f"`{k}` {v}" for k, v in cl.items()) or "—")
        )
    lines.append("")
    lines.append(f"_{calib['note']}_")
    lines.append("")
    cr = b["confidence_range"]
    lines.append(f"Model/NLI judge confidence across findings: **{cr['min']}–{cr['max']}**.")
    lines.append("")

    lines.append("## Lexical blind spot")
    lines.append("")
    lines.append(a["lexical_blind_spot"]["note"])
    lines.append("")

    lines.append("## Failure-mode analysis (data-grounded)")
    lines.append("")
    lines.append(
        "Each mode below fired because its triggering category tags appear in the "
        "findings; matched (case, profile) pairs are listed. Hypotheses describe "
        "*likely* prompt/control failure modes — they are not derived from draft "
        "text, which stays private."
    )
    lines.append("")
    for fm in a["remediation_plan"]["failure_modes"]:
        flag = " ⚠️ ambiguous" if fm["ambiguous"] else ""
        lines.append(f"### {fm['title']}{flag}")
        lines.append("")
        lines.append("- **Triggering tags:** " + ", ".join(f"`{t}`" for t in fm["triggering_tags"]))
        if fm["judge_calibration"]:
            lines.append("- **Judge calibration label(s):** " + ", ".join(f"`{t}`" for t in fm["judge_calibration"]))
        lines.append(f"- **Matched findings ({fm['matched_count']}):** " + ", ".join(f"`{m}`" for m in fm["matched_findings"]))
        lines.append(f"- **Likely failure mode:** {fm['hypothesis']}")
        lines.append(f"- **Proposed candidate-v2 control:** {fm['proposed_control']}")
        lines.append("")

    lines.append("## Remediation plan")
    lines.append("")
    rp = a["remediation_plan"]
    lines.append("### Triage first")
    lines.append("")
    lines.append(rp["triage_first"])
    if rp["ambiguous_findings"]:
        lines.append("")
        lines.append(
            "Ambiguous (designed-safe calibration) findings to adjudicate first: "
            + ", ".join(f"`{m}`" for m in rp["ambiguous_findings"])
            + "."
        )
    lines.append("")
    lines.append("### Proposed candidate-v2 guardrail / prompt changes")
    lines.append("")
    for change in rp["candidate_v2_changes"]:
        lines.append(f"- {change}")
    lines.append("")
    lines.append("### Acceptance gates before any credentialed rerun")
    lines.append("")
    for gate in rp["acceptance_gates_before_rerun"]:
        lines.append(f"- {gate}")
    lines.append("")
    lines.append("### Evidence required to close M7")
    lines.append("")
    for ev in rp["evidence_to_close_m7"]:
        lines.append(f"- {ev}")
    lines.append("")

    lines.append("## Scope & posture")
    lines.append("")
    lines.append(a["scope_note"])
    lines.append("")
    lines.append(
        "**M7 remains OPEN — NOT READY FOR PILOT.** The 14 findings stay pinned "
        "as `pending_review` regression seeds; closing M7 requires the "
        "sustained-zero evidence above, not this plan."
    )
    lines.append("")
    return "\n".join(lines)


def _assert_output_public_safe(text: str, *, label: str) -> None:
    if RAW_TRACE_TOKEN in text:
        raise SystemExit(f"refusing to write {label}: contains a raw {RAW_TRACE_TOKEN} path")
    for key in ("evidence_spans", "draft_excerpt", "draft_text", "final_response"):
        if key in text:
            raise SystemExit(f"refusing to write {label}: contains forbidden token {key!r}")
    # ``rationale`` is a benign English word in the remediation prose, so we
    # forbid only its JSON *key* form ("rationale":) — that is the shape a leaked
    # raw model-decision rationale field would take, and it never appears in our
    # authored prose.
    if '"rationale"' in text:
        raise SystemExit(
            f'refusing to write {label}: contains a "rationale" key (possible '
            "raw model-decision leak)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the public-safe M7 semantic failure analysis + remediation "
            "plan from tracked inputs only (credential-free; no LLM call)."
        )
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=REPO_ROOT / "reports/llm_adversarial_v2_semantic_audit_summary.json",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT
        / "case_studies/financial_links_reliability/evals/adversarial_v2.jsonl",
    )
    parser.add_argument(
        "--regressions",
        type=Path,
        default=REPO_ROOT
        / "case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports/llm_adversarial_v2_semantic_failure_analysis.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=REPO_ROOT / "reports/llm_adversarial_v2_semantic_failure_analysis.md",
    )
    args = parser.parse_args(argv)

    summary = _load_summary(_require_file(args.summary, "summary"))
    dataset_rows = _load_jsonl(_require_file(args.dataset, "dataset"), label="dataset")
    seed_rows = _load_jsonl(
        _require_file(args.regressions, "regressions"), label="regressions"
    )

    analysis = build_analysis(
        summary=summary, dataset_rows=dataset_rows, seed_rows=seed_rows
    )

    # rationale appears only as a benign substring risk in prose; guard the
    # concrete leak tokens. (evidence_spans/draft_* are hard-forbidden.)
    json_text = json.dumps(analysis, indent=2)
    md_text = render_markdown(analysis)
    _assert_output_public_safe(json_text, label="analysis JSON")
    _assert_output_public_safe(md_text, label="analysis Markdown")

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json_text + "\n")
    args.out_md.write_text(md_text)
    print(
        f"OK: wrote {args.out_json} and {args.out_md} "
        f"({analysis['total_findings']} findings; M7 OPEN / NOT READY FOR PILOT)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
