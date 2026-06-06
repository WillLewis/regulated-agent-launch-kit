"""Public-safe aggregation of opt-in model/NLI semantic decisions.

Pure functions that turn

1. a candidate eval report's lexical ``unsupported_claim`` grader results, and
2. a model/NLI ``SemanticDecision`` file (see
   ``scripts/generate_semantic_decisions.py``)

into an **aggregate-only** audit summary. The summary never carries raw draft
text: the per-decision ``rationale`` and ``evidence_spans`` fields (which quote
the customer-facing draft) are dropped. Only counts, enum histograms, synthetic
case IDs / risk bands, confidence ranges, and cost/token totals survive.

This module makes no model or network call. It is consumed by:

- ``scripts/summarize_semantic_audit_adversarial_v1_llm.py`` (writes the public
  audit summary JSON + Markdown), and
- ``scripts/package_evidence_adversarial_v1_llm.py`` (ships the aggregate inside
  the public-safe evidence pack).

Invariant violations raise ``ValueError`` so callers can translate them into a
clean CLI ``SystemExit``.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

# Re-declared locally (matching scripts/render_semantic_reporting_surface.py) so
# this module stays import-light and does not pull in the credentialed adapter.
SEMANTIC_ADAPTER_NAME = "anthropic_nli_semantic_v0"
LEXICAL_GRADER_NAME = "unsupported_claim"
SEMANTIC_GRADER_NAME = "unsupported_claim_semantic"
SEMANTIC_FAILURE_LABEL = "UNSAFE_CUSTOMER_COMMS"

SUMMARY_VERSION = "semantic_audit_summary_v0"

# Decision-file fields that quote the draft and must never reach a public
# artifact. The public summary copies enums/counts only; this tuple is also the
# allow-list the public-safety guard checks against.
DRAFT_BEARING_DECISION_KEYS = ("rationale", "evidence_spans")

LAUNCH_POSTURE = (
    "NOT READY FOR PILOT — local synthetic vertical slice only. This model/NLI "
    "semantic audit is an opt-in experiment over drafts already on disk, not a "
    "model-safety, production-readiness, regulatory-compliance, or partner claim."
)
# The audit slice label (e.g. "adversarial v2") is derived from the dataset path
# at render time, so the title and note never hardcode the wrong slice version.
SUMMARY_NOTE_TEMPLATE = (
    "Aggregate-only model/NLI semantic audit of customer-facing drafts already "
    "on disk. No raw draft text, model reasoning, or quoted draft spans are "
    "included — only counts, enum histograms, synthetic case IDs/risk bands, "
    "confidence ranges, and list-price cost estimates. Synthetic Financial "
    "Links {slice_label} data only."
)


def _slice_label(dataset_paths: Any) -> str:
    """Derive the adversarial-slice label (e.g. ``adversarial v2``) from the
    dataset path(s). Falls back to ``adversarial`` when no versioned slice is
    present, so the audit summary is never mislabeled with the wrong version."""

    for path in dataset_paths or []:
        match = re.search(r"adversarial_v(\d+)", str(path))
        if match:
            return f"adversarial v{match.group(1)}"
    return "adversarial"
COST_NOTE = (
    "Public list-price planning estimate read from the decision file; not a "
    "billing number, partner commitment, or production forecast."
)


def _grader_names(report: dict[str, Any]) -> list[str]:
    rates = report.get("aggregate_grader_pass_rates")
    if not isinstance(rates, list):
        raise ValueError("eval report missing aggregate_grader_pass_rates list")
    return [str(rate["name"]) for rate in rates]


def lexical_unsupported_flags(report: dict[str, Any]) -> dict[str, bool]:
    """Map case_id -> True when the lexical unsupported-claim grader flagged it.

    The per-case ``grader_results`` align positionally with
    ``aggregate_grader_pass_rates`` (the same contract the reporting surface
    relies on). A grader result is a *flag* when it did not pass.
    """

    names = _grader_names(report)
    if LEXICAL_GRADER_NAME not in names:
        raise ValueError(
            f"eval report does not include the {LEXICAL_GRADER_NAME!r} grader"
        )
    index = names.index(LEXICAL_GRADER_NAME)
    flags: dict[str, bool] = {}
    for case in report.get("per_case", []):
        results = case.get("grader_results", [])
        if len(results) != len(names):
            raise ValueError(
                f"{case.get('case_id')!r}: grader_results count {len(results)} "
                f"does not match grader-name count {len(names)}"
            )
        flags[str(case["case_id"])] = not bool(results[index]["passed"])
    return flags


def _case_risk_bands(report: dict[str, Any]) -> dict[str, str]:
    return {
        str(case["case_id"]): str(case.get("risk_band", ""))
        for case in report.get("per_case", [])
    }


def _validate_decision_file(decision_file: dict[str, Any], *, profile: str) -> None:
    adapter = decision_file.get("adapter")
    if adapter != SEMANTIC_ADAPTER_NAME:
        raise ValueError(
            f"semantic decision file must declare adapter "
            f"{SEMANTIC_ADAPTER_NAME!r}; got {adapter!r}"
        )
    declared = decision_file.get("profile")
    if declared != profile:
        raise ValueError(
            f"semantic decision profile {declared!r} does not match eval-report "
            f"profile {profile!r}"
        )


def build_profile_audit(
    report: dict[str, Any],
    decision_file: dict[str, Any],
) -> dict[str, Any]:
    """Build the aggregate-only audit block for one candidate profile."""

    profile = str(report.get("agent_system_version", ""))
    if not profile:
        raise ValueError("eval report missing agent_system_version")
    _validate_decision_file(decision_file, profile=profile)

    decisions = (decision_file.get("decisions") or {}).get(profile)
    if not isinstance(decisions, dict):
        raise ValueError(
            f"decision file has no decisions for profile {profile!r}"
        )

    lexical_flags = lexical_unsupported_flags(report)
    report_ids = set(lexical_flags)
    decision_ids = set(decisions)
    if report_ids != decision_ids:
        raise ValueError(
            "eval-report case IDs do not match decision-file case IDs; the "
            "decision file must be generated from the same report."
        )

    risk_bands = _case_risk_bands(report)
    claim_types: Counter[str] = Counter()
    calibrations: Counter[str] = Counter()
    confidences: list[float] = []
    semantic_flagged: list[str] = []

    for case_id, decision in decisions.items():
        claim_types[str(decision.get("claim_type", "none"))] += 1
        calibrations[str(decision.get("calibration", "unknown"))] += 1
        confidences.append(float(decision.get("confidence", 0.0)))
        if bool(decision.get("makes_unsupported_claim")):
            semantic_flagged.append(case_id)

    semantic_flagged.sort()

    # Lexical vs semantic agreement.
    both_flag = sorted(
        cid for cid in decision_ids
        if lexical_flags[cid] and cid in semantic_flagged
    )
    semantic_only = sorted(
        cid for cid in decision_ids
        if not lexical_flags[cid] and cid in semantic_flagged
    )
    lexical_only = sorted(
        cid for cid in decision_ids
        if lexical_flags[cid] and cid not in semantic_flagged
    )
    both_clear = sorted(
        cid for cid in decision_ids
        if not lexical_flags[cid] and cid not in semantic_flagged
    )

    lexical_flag_count = sum(1 for flagged in lexical_flags.values() if flagged)
    case_count = len(decision_ids)

    summary = decision_file.get("summary") or {}
    # Abstentions/errors: a present decision file means every report case
    # received a decision (the adapter fails closed on any per-case failure).
    abstention_or_error = case_count - len(decisions)

    model = None
    metadata = (decision_file.get("adapter_metadata") or {}).get(profile) or {}
    for entry in metadata.values():
        if isinstance(entry, dict) and entry.get("model"):
            model = str(entry["model"])
            break

    return {
        "profile": profile,
        "model": model,
        "case_count": case_count,
        "source_eval_report": str(decision_file.get("source_eval_report", "")),
        "semantic": {
            "unsafe_customer_comms_count": len(semantic_flagged),
            "flagged_case_ids": semantic_flagged,
            "flagged_case_risk_bands": {
                cid: risk_bands.get(cid, "") for cid in semantic_flagged
            },
            "claim_type_counts": dict(sorted(claim_types.items())),
            "calibration_counts": dict(sorted(calibrations.items())),
            "confidence_min": round(min(confidences), 4) if confidences else 0.0,
            "confidence_max": round(max(confidences), 4) if confidences else 0.0,
            "abstention_or_error_count": abstention_or_error,
        },
        "lexical": {
            "unsupported_claim_flag_count": lexical_flag_count,
            "pass_count": case_count - lexical_flag_count,
            "total": case_count,
        },
        "lexical_vs_semantic": {
            "both_flag": len(both_flag),
            "semantic_only_flag": len(semantic_only),
            "lexical_only_flag": len(lexical_only),
            "both_clear": len(both_clear),
            "semantic_only_flag_case_ids": semantic_only,
        },
        "cost": {
            "total_est_cost_usd": round(
                float(summary.get("total_est_cost_usd", 0.0)), 6
            ),
            "total_input_tokens": int(summary.get("total_input_tokens", 0)),
            "total_output_tokens": int(summary.get("total_output_tokens", 0)),
            "cost_note": COST_NOTE,
        },
    }


def _headline(profiles: list[dict[str, Any]]) -> str:
    total_blind_spot = sum(
        p["lexical_vs_semantic"]["semantic_only_flag"] for p in profiles
    )
    per_profile = ", ".join(
        f"{p['lexical_vs_semantic']['semantic_only_flag']} in {p['profile']}"
        for p in profiles
    )
    if total_blind_spot == 0:
        return (
            "The model/NLI semantic grader agreed with the lexical "
            "unsupported-claim grader on every draft already on disk; it "
            "surfaced no additional unsupported-claim drafts in this slice."
        )
    return (
        f"The model/NLI semantic grader flagged {total_blind_spot} customer-facing "
        f"draft(s) ({per_profile}) that the lexical unsupported-claim grader "
        "passed — a lexical blind spot. These are exactly the paraphrase, "
        "safe-negation, and cross-sentence-trap cases a substring grader cannot "
        "reason about, and they are why this slice stays pre-pilot."
    )


def build_semantic_audit_summary(
    profile_inputs: list[tuple[dict[str, Any], dict[str, Any], str]],
) -> dict[str, Any]:
    """Build the full public-safe audit summary.

    ``profile_inputs`` is a list of ``(report, decision_file,
    decision_file_path)`` tuples, one per compared candidate. The
    ``decision_file_path`` is recorded as provenance only (it points at the
    gitignored raw decision file); no decision-file *content* beyond aggregate
    counts is copied.
    """

    if not profile_inputs:
        raise ValueError("at least one profile is required for the audit summary")

    profiles: list[dict[str, Any]] = []
    dataset_paths: set[str] = set()
    for report, decision_file, decision_path in profile_inputs:
        audit = build_profile_audit(report, decision_file)
        audit["source_decision_file"] = decision_path
        profiles.append(audit)
        dataset_paths.add(str(decision_file.get("dataset_path", "")))

    totals = {
        "profiles": len(profiles),
        "total_semantic_unsafe_customer_comms": sum(
            p["semantic"]["unsafe_customer_comms_count"] for p in profiles
        ),
        "total_semantic_only_flags": sum(
            p["lexical_vs_semantic"]["semantic_only_flag"] for p in profiles
        ),
        "total_lexical_unsupported_flags": sum(
            p["lexical"]["unsupported_claim_flag_count"] for p in profiles
        ),
        "total_semantic_judge_cost_usd": round(
            sum(p["cost"]["total_est_cost_usd"] for p in profiles), 6
        ),
        "total_input_tokens": sum(p["cost"]["total_input_tokens"] for p in profiles),
        "total_output_tokens": sum(
            p["cost"]["total_output_tokens"] for p in profiles
        ),
        "abstention_or_error_count": sum(
            p["semantic"]["abstention_or_error_count"] for p in profiles
        ),
    }

    dataset_path_list = sorted(p for p in dataset_paths if p)
    summary = {
        "version": SUMMARY_VERSION,
        "synthetic": True,
        "adapter": SEMANTIC_ADAPTER_NAME,
        "lexical_grader": LEXICAL_GRADER_NAME,
        "semantic_grader": SEMANTIC_GRADER_NAME,
        "dataset_path": dataset_path_list,
        "launch_posture": LAUNCH_POSTURE,
        "note": SUMMARY_NOTE_TEMPLATE.format(slice_label=_slice_label(dataset_path_list)),
        "headline": _headline(profiles),
        "profiles": profiles,
        "totals": totals,
    }
    assert_public_safe(summary)
    return summary


def _iter_keys(value: Any) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _iter_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def assert_public_safe(payload: dict[str, Any]) -> None:
    """Fail closed if the summary could leak draft text or raw trace paths.

    The audit summary is a public artifact, so it must never carry the
    draft-bearing decision fields (``rationale`` / ``evidence_spans``) nor a
    raw ``traces/local/llm_`` path.
    """

    for key in _iter_keys(payload):
        if key in DRAFT_BEARING_DECISION_KEYS:
            raise ValueError(
                f"public semantic audit summary must not contain the "
                f"draft-bearing key {key!r}"
            )
    import json

    serialized = json.dumps(payload)
    if "traces/local/llm_" in serialized:
        raise ValueError(
            "public semantic audit summary must not reference a raw "
            "traces/local/llm_ path"
        )


def _hist_line(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"`{name}` {count}" for name, count in counts.items())


def render_markdown(summary: dict[str, Any]) -> str:
    """Render the public-safe audit summary as Markdown."""

    profiles = summary["profiles"]
    totals = summary["totals"]
    dataset = ", ".join(summary.get("dataset_path") or []) or "(synthetic)"

    slice_label = _slice_label(summary.get("dataset_path") or [])
    title_label = slice_label[:1].upper() + slice_label[1:]  # e.g. "Adversarial v2"
    lines: list[str] = []
    lines.append(
        f"# Model/NLI Semantic Audit — Financial Links {title_label} LLM Candidates"
    )
    lines.append("")
    lines.append(f"> {summary['launch_posture']}")
    lines.append("")
    lines.append(summary["note"])
    lines.append("")
    lines.append(
        f"- **Adapter:** `{summary['adapter']}`  "
        f"\n- **Lexical grader:** `{summary['lexical_grader']}`  "
        f"\n- **Semantic grader:** `{summary['semantic_grader']}`  "
        f"\n- **Dataset:** `{dataset}`  "
        f"\n- **Profiles audited:** {totals['profiles']}"
    )
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(summary["headline"])
    lines.append("")

    lines.append("## Decision counts by profile")
    lines.append("")
    lines.append(
        "| Profile | Cases | Lexical unsupported-claim flags | "
        "Semantic UNSAFE_CUSTOMER_COMMS | Semantic-only (lexical blind spot) | "
        "Abstentions/errors | Semantic-judge cost (est., USD) |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for p in profiles:
        lines.append(
            f"| `{p['profile']}` | {p['case_count']} | "
            f"{p['lexical']['unsupported_claim_flag_count']} | "
            f"{p['semantic']['unsafe_customer_comms_count']} | "
            f"{p['lexical_vs_semantic']['semantic_only_flag']} | "
            f"{p['semantic']['abstention_or_error_count']} | "
            f"${p['cost']['total_est_cost_usd']:.6f} |"
        )
    lines.append(
        f"| **Total** | — | {totals['total_lexical_unsupported_flags']} | "
        f"{totals['total_semantic_unsafe_customer_comms']} | "
        f"{totals['total_semantic_only_flags']} | "
        f"{totals['abstention_or_error_count']} | "
        f"${totals['total_semantic_judge_cost_usd']:.6f} |"
    )
    lines.append("")

    lines.append("## Lexical grader vs. model/NLI semantic grader")
    lines.append("")
    lines.append(
        "| Profile | Both clear | Both flag | Semantic-only flag | Lexical-only flag |"
    )
    lines.append("| --- | --- | --- | --- | --- |")
    for p in profiles:
        lv = p["lexical_vs_semantic"]
        lines.append(
            f"| `{p['profile']}` | {lv['both_clear']} | {lv['both_flag']} | "
            f"{lv['semantic_only_flag']} | {lv['lexical_only_flag']} |"
        )
    lines.append("")

    lines.append("## Calibration & claim-type histograms")
    lines.append("")
    for p in profiles:
        sem = p["semantic"]
        lines.append(f"### `{p['profile']}`")
        lines.append("")
        lines.append(f"- **Model:** `{p.get('model') or 'unknown'}`")
        lines.append(f"- **Calibrations:** {_hist_line(sem['calibration_counts'])}")
        lines.append(f"- **Claim types:** {_hist_line(sem['claim_type_counts'])}")
        lines.append(
            f"- **Confidence range:** {sem['confidence_min']}–{sem['confidence_max']}"
        )
        bands = sem["flagged_case_risk_bands"]
        flagged_render = ", ".join(
            f"`{cid}`" + (f" ({bands.get(cid)})" if bands.get(cid) else "")
            for cid in sem["flagged_case_ids"]
        ) or "none"
        lines.append(f"- **Semantic-flagged cases:** {flagged_render}")
        lines.append("")

    lines.append("## Cost")
    lines.append("")
    lines.append(
        f"Total estimated model/NLI semantic-judge cost across "
        f"{totals['profiles']} profiles: **${totals['total_semantic_judge_cost_usd']:.6f}** "
        f"({totals['total_input_tokens']} input + {totals['total_output_tokens']} "
        f"output tokens). {COST_NOTE}"
    )
    lines.append("")

    lines.append("## Method & provenance")
    lines.append("")
    lines.append(
        "This audit judges the customer-facing drafts **already on disk** from a "
        "prior credentialed candidate run; it does not re-run the candidate "
        "agent. The model/NLI adapter classifies draft text only — it does not "
        "decide routing, tool use, policy citation, consent, or approval "
        "boundaries. Raw model decisions — which quote short customer-draft "
        "spans — stay gitignored under `reports/semantic_model_decisions/`; "
        "only the aggregate counts above are public-safe."
    )
    lines.append("")
    for p in profiles:
        lines.append(
            f"- `{p['profile']}` ← decisions: `{p['source_decision_file']}` "
            f"(gitignored), report: `{p['source_eval_report']}` (gitignored)"
        )
    lines.append("")
    return "\n".join(lines)
