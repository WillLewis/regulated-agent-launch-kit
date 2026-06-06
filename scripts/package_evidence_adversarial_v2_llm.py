"""Assemble a public-safe evidence pack for the executed adversarial v2 LLM run (M7).

Unlike the adversarial v1 packager — which *derives* the aggregate semantic
audit from the gitignored raw model/NLI decision files and therefore needs the
credentialed run's raw artifacts on disk — this v2 packager is **credential-free
by construction**. Its required inputs are the artifacts the M7 run already
promoted to tracked, public-safe surfaces:

- the Before/After comparison eval card
  (``reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md``);
- the aggregate-only model/NLI semantic audit summary, JSON + Markdown
  (``reports/llm_adversarial_v2_semantic_audit_summary.{json,md}``);
- the 14 ``pending_review`` semantic-only regression seeds
  (``regressions_semantic_adversarial_v2.jsonl``); and
- the credential-free ``SemanticDecision`` replay fixture
  (``regressions_semantic_adversarial_v2_decisions.json``).

None of those require a model call, a credential, or the raw run artifacts, so
the pack's core is reproducible by any reviewer from tracked inputs alone.

When the gitignored raw v2 candidate eval reports and raw per-candidate traces
*happen to be present locally* (i.e. on the machine that executed M7), the
packager additionally ships **redacted** candidate eval summaries and redacted
traces — exactly as the v1 packager does. It never ships them raw: the eval
reports are passed through ``configs/redaction_policy.yaml`` (abstracting
``draft_text`` / ``draft_excerpt`` / ``final_response``) and only redacted
traces are copied. When the raw artifacts are absent, the pack is simply the
credential-free core; the Make target degrades gracefully.

The reusable, security-critical guard helpers are imported from the v1 packager
so v2 enforces byte-for-byte identical public-safety invariants (no broad
refactor, no divergence risk). On top of those, this module fails closed if the
"semantic aggregate" slot is fed anything other than the public summary — a raw
``reports/semantic_model_decisions/*.json`` decision file, a raw candidate eval
report, or a replay / semantic-model eval report (e.g.
``reports/regression_semantic_adversarial_v2_eval.json`` or
``reports/llm_adversarial_v2_candidate_v1_semantic_model_eval.json``) — by
requiring the public summary's ``version`` and re-running the public-safety
guard.

It does **not** call the LLM and requires no credentials.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.semantic_audit import (  # noqa: E402
    SUMMARY_VERSION,
    assert_public_safe,
)
from scripts.redact_trace import redact  # noqa: E402

# Reuse the v1 packager's vetted, pure guard/copy helpers verbatim so the v2
# pack enforces identical public-safety invariants. Importing them (rather than
# duplicating ~150 lines of security-critical logic) keeps the two packs from
# ever drifting apart and avoids a broad refactor of the v1 module.
from scripts.package_evidence_adversarial_v1_llm import (  # noqa: E402
    _assert_no_draft_payload_keys,
    _collect_redacted_traces,
    _copy,
    _guard_no_raw_paths,
    _guard_semantic_markdown,
    _guard_semantic_regression_seeds,
    _guard_semantic_replay_fixture,
    _require_dir,
    _require_file,
    _rewrite_llm_report_notes,
    _rewrite_trace_paths_to_pack_redacted,
    _write_json,
)


EVIDENCE_PACK_VERSION = "evidence_pack_llm_adversarial_v2"


SYNTHETIC_DISCLAIMER = (
    "This evidence pack is generated from a fully synthetic local eval run on "
    "the 24-case Financial Links adversarial v2 slice (milestone M7). "
    "Identifiers, policies, partner configurations, and risk bands are "
    "fabricated for this deployment-readiness lab. Both compared profiles call "
    "a real LLM via the credential-gated path, but every case in the dataset is "
    "synthetic and no real customer data is involved. M7 was executed once with "
    "a real key and the credential-free semantic gate BLOCKED: the model/NLI "
    "audit found 14 semantic-only UNSAFE_CUSTOMER_COMMS drafts the lexical "
    "grader cleared, so M7 remains OPEN. Raw LLM traces, the raw JSON eval "
    "reports, and the raw model/NLI decision files are intentionally excluded "
    "from this pack and from git tracking; only redacted and aggregate-only "
    "artifacts ship here. Nothing in this pack implies model safety, production "
    "readiness, regulatory compliance, partner endorsement, or pilot readiness. "
    "One credentialed run on a 24-case synthetic slice is not enough evidence "
    "to claim a prompt is robust — and this run blocked."
)


def _guard_semantic_aggregate_copy(path: Path) -> dict[str, Any]:
    """Load + fail-closed validate the tracked public summary JSON before it is
    copied into the pack as ``semantic_audit_aggregate.json``.

    The "semantic aggregate" slot is for the *public aggregate-only* summary
    only. This refuses anything else fed into it:

    - a raw ``reports/semantic_model_decisions/*.json`` decision file (quotes
      draft spans; wrong ``version``; carries ``rationale`` / ``evidence_spans``);
    - a raw candidate eval report or a replay / semantic-model eval report
      (e.g. ``reports/regression_semantic_adversarial_v2_eval.json``,
      ``reports/llm_adversarial_v2_candidate_v1_semantic_model_eval.json``) —
      these are ``local_eval_v0`` reports, not the audit summary;
    - anything referencing a raw ``traces/local/llm_`` path or carrying a
      raw draft-bearing key.
    """

    text = path.read_text()
    if "traces/local/llm_" in text:
        raise SystemExit(
            f"refusing to ship semantic aggregate referencing a raw trace path: "
            f"{path}"
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{path}: semantic aggregate is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: semantic aggregate must be a JSON object")
    version = payload.get("version")
    if version != SUMMARY_VERSION:
        raise SystemExit(
            f"refusing to ship {path} as the semantic aggregate: version "
            f"{version!r} != {SUMMARY_VERSION!r}. This slot accepts only the "
            f"public aggregate-only audit summary; a raw model/NLI decision "
            f"file, candidate eval report, or replay/semantic-model eval report "
            f"is not allowed here."
        )
    # rationale/evidence_spans (assert_public_safe) + draft_text/draft_excerpt/
    # final_response (no-draft-payload) — belt-and-suspenders over the version
    # check.
    _assert_no_draft_payload_keys(payload, label=f"semantic aggregate {path}")
    try:
        assert_public_safe(payload)
    except ValueError as exc:
        raise SystemExit(f"refusing to ship semantic aggregate: {exc}") from exc
    return payload


def _readme(manifest: dict[str, Any], *, has_redacted_candidates: bool) -> str:
    file_lines = "\n".join(
        f"- `{entry['path']}` — {entry['purpose']}"
        for entry in manifest["files"]
    )
    if has_redacted_candidates:
        redacted_candidates_note = (
            "This pack was assembled on a machine that still held the "
            "gitignored raw M7 artifacts, so it **also** ships redacted "
            "candidate eval summaries (`llm_candidate_v{0,1}_eval.redacted.json`) "
            "and redacted per-candidate traces under "
            "`traces/redacted/candidate_v{0,1}/`. Raw `draft_text` / "
            "`draft_excerpt` / `final_response` values were abstracted via "
            "`configs/redaction_policy.yaml`; the raw reports and raw traces "
            "themselves are never copied. When the raw artifacts are absent "
            "(any fresh clone), the credential-free core above is still "
            "assembled byte-for-byte from tracked inputs — the redacted "
            "candidate artifacts are simply omitted."
        )
    else:
        redacted_candidates_note = (
            "The gitignored raw M7 artifacts were not present at assembly time, "
            "so this pack is the **credential-free core** only: it ships no "
            "redacted candidate eval summaries or traces. The core is "
            "reproducible byte-for-byte from tracked inputs by any reviewer, "
            "with no credentials and no model call."
        )
    return f"""# Evidence Pack — Financial Links LLM Adversarial v2 (M7, gate BLOCKED)

> {SYNTHETIC_DISCLAIMER}

## What this pack contains

This is a public-safe view of the **executed** Financial Links adversarial v2
(24-case) LLM milestone (**M7**). The compared profiles are `llm_candidate_v0`
(Before) and `llm_candidate_v1` (After). M7 **ran once** with a real key; the
deterministic comparison improved (`v0` 20/24 → `v1` 24/24), but the
credential-free model/NLI **semantic gate BLOCKED** on 14 semantic-only
`UNSAFE_CUSTOMER_COMMS` drafts (8 in `v0`, 6 in `v1`) that the lexical
unsupported-claim grader cleared — a lexical blind spot. **M7 remains OPEN.**

Every artifact below is generated from on-disk inputs:

{file_lines}

{redacted_candidates_note}

## What this pack does **not** contain

- raw LLM traces (the gitignored per-candidate raw-trace directories) —
  intentionally excluded; when present locally only their *redacted* form ships;
- the raw JSON candidate eval reports (gitignored) — never copied; when present
  locally only their *redacted* summaries ship;
- raw model/NLI semantic-decision payloads (gitignored under the
  `semantic_model_decisions` reports directory) — those quote short draft spans.
  Only the aggregate-only `semantic_audit_aggregate.json` (counts, enum
  histograms, synthetic case IDs/risk bands, confidence ranges, cost) and the
  public `semantic_audit_summary.md` ship;
- the regenerable replay / semantic-model eval reports (gitignored check
  outputs, not evidence);
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable Before/After comparison
   (`llm_candidate_v0` 20/24 → `llm_candidate_v1` 24/24) on the 24-case slice.
   The deterministic graders all pass; the semantic gate is what blocks.
2. `semantic_audit_aggregate.json` is the aggregate-only model/NLI audit:
   counts, calibration/claim-type histograms, synthetic case IDs/risk bands,
   confidence ranges, and list-price cost. No draft text, model reasoning, or
   quoted spans.
3. `semantic_audit_summary.md` is the human-readable version of the same
   aggregate, including the 14 semantic-only flags that blocked the gate.
4. `regressions/regressions_semantic_adversarial_v2.jsonl` and
   `regressions/regressions_semantic_adversarial_v2_decisions.json` are covered
   below.
5. `manifest.json` is the machine-readable index.

## Semantic regression seeds + credential-free replay fixture

- `regressions/regressions_semantic_adversarial_v2.jsonl` pins all **14**
  model/NLI **semantic-only** `UNSAFE_CUSTOMER_COMMS` findings as
  `pending_review` synthetic regression seeds — customer-facing drafts the
  lexical `unsupported_claim` grader cleared. Each seed is a case-superset
  record sourced only from the public summary's `semantic_only_flag_case_ids`
  plus the synthetic dataset, and linked to
  `reports/llm_adversarial_v2_semantic_audit_summary.json`; none carries a raw
  trace path or raw draft text.
- `regressions/regressions_semantic_adversarial_v2_decisions.json` is the
  tracked `SemanticDecision` **replay fixture**. Feeding it to the offline
  precomputed-decision lane (`run_eval.py --semantic-decisions`) with the
  deterministic `improved_v0` profile fires the offline
  `unsupported_claim_semantic` grader (`UNSAFE_CUSTOMER_COMMS`) on all 14 seeds
  **with no credentials and no model call** — it proves the offline grader
  fires; it does not re-derive the claim from a live draft. The fixture pins the
  audit verdict (`makes_unsupported_claim: true`); `evidence_spans` is empty and
  `rationale` is an authored provenance string, so no raw draft text, model
  reasoning, or quoted spans ship. It feeds only the offline grader, never the
  runtime EvaluatorNode (evaluator/grader separation preserved).
- These seeds are `pending_review`, not a fix; they are a reason the slice stays
  **NOT READY FOR PILOT**.

## Launch posture

**M7 ran once and the semantic gate BLOCKED — M7 remains OPEN; NOT READY FOR
PILOT.** The acceptance bar is *sustained zero* semantic-only flags across
multiple runs; one credentialed run produced 14, so the gate blocked. This pack
shows the deterministic v2 comparison closes locally on real LLM traces while
the semantic audit surfaces a real blind spot; it does **not** prove
`llm_candidate_v1` is robust, pilot grade, regulatory compliant, partner
endorsed, or production grade. A single credentialed run on a 24-case synthetic
slice cannot establish prompt robustness — and this one blocked.
"""


def package_adversarial_v2_llm_evidence(
    *,
    eval_card: Path,
    semantic_summary_json: Path,
    semantic_summary_md: Path,
    semantic_regressions: Path,
    semantic_replay_decisions: Path,
    out: Path,
    policy: Path | None = None,
    raw_v0_report: Path | None = None,
    raw_v1_report: Path | None = None,
    redacted_traces_v0: Path | None = None,
    redacted_traces_v1: Path | None = None,
) -> Path:
    # --- Required, credential-free, tracked public-safe inputs ----------------
    eval_card = _require_file(eval_card, "eval-card")
    summary_json = _require_file(semantic_summary_json, "semantic-summary-json")
    summary_md = _require_file(semantic_summary_md, "semantic-summary-md")
    seeds_path = _require_file(semantic_regressions, "semantic-regressions")
    replay_path = _require_file(
        semantic_replay_decisions, "semantic-replay-decisions"
    )

    aggregate_payload = _guard_semantic_aggregate_copy(summary_json)
    _guard_semantic_markdown(summary_md)
    _guard_semantic_regression_seeds(seeds_path)
    _guard_semantic_replay_fixture(replay_path)

    # --- Optional redacted candidate eval summaries + traces ------------------
    # Shipped only when the gitignored raw M7 artifacts are present locally. All
    # four (both reports + both redacted-trace dirs) must be supplied together,
    # or none. The raw reports are redacted, never copied.
    optional_paths = (
        raw_v0_report,
        raw_v1_report,
        redacted_traces_v0,
        redacted_traces_v1,
    )
    has_redacted_candidates = any(p is not None for p in optional_paths)
    if has_redacted_candidates and not all(p is not None for p in optional_paths):
        raise SystemExit(
            "pass all of --raw-v0-report, --raw-v1-report, --redacted-traces-v0, "
            "and --redacted-traces-v1 together, or none"
        )

    redacted_v0 = redaction_v0 = redacted_v1 = redaction_v1 = None
    v0_trace_files = v0_trace_reports = v1_trace_files = v1_trace_reports = []
    if has_redacted_candidates:
        raw_v0_report = _require_file(raw_v0_report, "raw-v0-report")
        raw_v1_report = _require_file(raw_v1_report, "raw-v1-report")
        redacted_v0_dir = _require_dir(redacted_traces_v0, "redacted-traces-v0")
        redacted_v1_dir = _require_dir(redacted_traces_v1, "redacted-traces-v1")
        policy_path = _require_file(policy, "policy")
        policy_data = yaml.safe_load(policy_path.read_text())
        if not isinstance(policy_data, dict):
            raise SystemExit(
                f"{policy_path}: redaction policy must be a YAML mapping"
            )

        raw_v0 = json.loads(raw_v0_report.read_text())
        redacted_v0, redaction_v0 = redact(raw_v0, policy_data)
        _rewrite_trace_paths_to_pack_redacted(redacted_v0, candidate="candidate_v0")
        _rewrite_llm_report_notes(redacted_v0)

        raw_v1 = json.loads(raw_v1_report.read_text())
        redacted_v1, redaction_v1 = redact(raw_v1, policy_data)
        _rewrite_trace_paths_to_pack_redacted(redacted_v1, candidate="candidate_v1")
        _rewrite_llm_report_notes(redacted_v1)

        v0_trace_files, v0_trace_reports = _collect_redacted_traces(redacted_v0_dir)
        v1_trace_files, v1_trace_reports = _collect_redacted_traces(redacted_v1_dir)

    # --- Assemble the pack ----------------------------------------------------
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    manifest: dict[str, Any] = {
        "version": EVIDENCE_PACK_VERSION,
        "synthetic": True,
        "milestone": "M7",
        "m7_status": "OPEN — semantic gate BLOCKED on 14 semantic-only findings",
        "disclaimer": SYNTHETIC_DISCLAIMER,
        "files": [],
    }

    def _add_copy(src: Path, rel: str, purpose: str) -> None:
        _copy(src, out / rel)
        manifest["files"].append(
            {"path": rel, "purpose": purpose, "source": str(src)}
        )

    def _add_payload(payload: Any, rel: str, purpose: str, source: str) -> None:
        _write_json(out / rel, payload)
        manifest["files"].append({"path": rel, "purpose": purpose, "source": source})

    _add_copy(
        eval_card,
        "eval_card.md",
        "Before/After candidate_v0-vs-candidate_v1 comparison eval card "
        "(markdown) on the 24-case adversarial v2 slice (v0 20/24 → v1 24/24).",
    )
    _add_copy(
        summary_json,
        "semantic_audit_aggregate.json",
        "Aggregate-only model/NLI semantic audit: counts, enum histograms, "
        "synthetic case IDs/risk bands, confidence ranges, and cost. The 14 "
        "semantic-only UNSAFE_CUSTOMER_COMMS flags that BLOCKED the M7 gate. No "
        "draft text, model reasoning, or quoted spans.",
    )
    _add_copy(
        summary_md,
        "semantic_audit_summary.md",
        "Human-readable public-safe model/NLI semantic audit summary "
        "(aggregate-only).",
    )

    if has_redacted_candidates:
        _add_payload(
            redacted_v0,
            "llm_candidate_v0_eval.redacted.json",
            "candidate_v0 (Before) JSON eval report with raw draft text "
            "abstracted and IDs removed.",
            source=str(raw_v0_report),
        )
        _add_payload(
            redaction_v0,
            "llm_candidate_v0_eval.redaction_report.json",
            "Redaction report for the candidate_v0 JSON eval.",
            source=str(raw_v0_report),
        )
        _add_payload(
            redacted_v1,
            "llm_candidate_v1_eval.redacted.json",
            "candidate_v1 (After) JSON eval report with raw draft text "
            "abstracted and IDs removed.",
            source=str(raw_v1_report),
        )
        _add_payload(
            redaction_v1,
            "llm_candidate_v1_eval.redaction_report.json",
            "Redaction report for the candidate_v1 JSON eval.",
            source=str(raw_v1_report),
        )
        for candidate, trace_files, trace_reports in (
            ("candidate_v0", v0_trace_files, v0_trace_reports),
            ("candidate_v1", v1_trace_files, v1_trace_reports),
        ):
            for trace_path in trace_files:
                _add_copy(
                    trace_path,
                    f"traces/redacted/{candidate}/{trace_path.name}",
                    f"Redacted synthetic {candidate} LLM trace.",
                )
            for report_path in trace_reports:
                _add_copy(
                    report_path,
                    f"traces/redacted/{candidate}/{report_path.name}",
                    "Per-trace redaction report (removed/abstracted/preserved/"
                    "uncovered fields).",
                )

    _add_copy(
        seeds_path,
        f"regressions/{seeds_path.name}",
        "Pending_review synthetic semantic-only regression seeds — the 14 "
        "model/NLI UNSAFE_CUSTOMER_COMMS drafts the lexical grader cleared (a "
        "lexical blind spot). Case-superset records linked to the public "
        "semantic audit summary; no raw trace path or raw draft text.",
    )
    _add_copy(
        replay_path,
        f"regressions/{replay_path.name}",
        "Credential-free SemanticDecision replay fixture: feeding it to "
        "run_eval.py --semantic-decisions with the deterministic improved_v0 "
        "profile fires the offline unsupported_claim_semantic grader on every "
        "seed with no model call. evidence_spans empty; rationale is authored "
        "provenance, not raw draft text.",
    )

    _guard_no_raw_paths(manifest)

    readme_path = out / "README.md"
    readme_path.write_text(
        _readme(manifest, has_redacted_candidates=has_redacted_candidates)
    )
    manifest["files"].insert(
        0,
        {
            "path": "README.md",
            "purpose": "Pack overview + synthetic-only / M7-blocked / "
            "no-readiness disclaimer.",
            "source": "<generated>",
        },
    )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    # Surface the aggregate's headline count to callers/tests without re-reading.
    manifest["_aggregate_total_semantic_only_flags"] = (
        aggregate_payload.get("totals", {}).get("total_semantic_only_flags")
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble a public-safe evidence pack for the executed adversarial "
            "v2 (24-case) LLM milestone (M7). Credential-free; the optional "
            "redacted candidate artifacts ship only when the gitignored raw "
            "run artifacts are present locally."
        )
    )
    parser.add_argument("--eval-card", required=True, type=Path)
    parser.add_argument("--semantic-summary-json", required=True, type=Path)
    parser.add_argument("--semantic-summary-md", required=True, type=Path)
    parser.add_argument("--semantic-regressions", required=True, type=Path)
    parser.add_argument("--semantic-replay-decisions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help=(
            "Redaction policy YAML. Required only when the optional raw "
            "candidate reports/traces are supplied."
        ),
    )
    parser.add_argument(
        "--raw-v0-report",
        type=Path,
        default=None,
        help=(
            "Optional gitignored raw candidate_v0 eval report. When supplied "
            "(with the other three optional flags), it is redacted and shipped "
            "as llm_candidate_v0_eval.redacted.json; it is never copied raw."
        ),
    )
    parser.add_argument("--raw-v1-report", type=Path, default=None)
    parser.add_argument("--redacted-traces-v0", type=Path, default=None)
    parser.add_argument("--redacted-traces-v1", type=Path, default=None)
    args = parser.parse_args(argv)

    pack_root = package_adversarial_v2_llm_evidence(
        eval_card=args.eval_card,
        semantic_summary_json=args.semantic_summary_json,
        semantic_summary_md=args.semantic_summary_md,
        semantic_regressions=args.semantic_regressions,
        semantic_replay_decisions=args.semantic_replay_decisions,
        out=args.out,
        policy=args.policy,
        raw_v0_report=args.raw_v0_report,
        raw_v1_report=args.raw_v1_report,
        redacted_traces_v0=args.redacted_traces_v0,
        redacted_traces_v1=args.redacted_traces_v1,
    )
    print(f"OK: assembled adversarial v2 LLM evidence pack -> {pack_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
