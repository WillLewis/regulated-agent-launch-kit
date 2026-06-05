"""Assemble a public-safe evidence pack for the adversarial v1 LLM loop.

The credentialed adversarial v1 LLM candidate runs produce real model
traces under ``traces/local/llm_adversarial_v1_candidate_v0/`` and
``..._candidate_v1/`` plus JSON eval reports at
``reports/llm_adversarial_v1_candidate_v0_eval.json`` and
``..._candidate_v1_eval.json``. All four embed raw LLM ``draft_text`` /
``draft_excerpt`` / ``final_response`` content and are gitignored.

This script publishes the public-safe view of the 12-case adversarial v1
``llm_candidate_v0`` (Before) → ``llm_candidate_v1`` (After) comparison:

- the comparison eval card (already public-safe — links only to
  redacted-trace paths);
- redacted summaries of BOTH candidate raw eval reports;
- redacted traces for BOTH candidates (subdir'd by candidate);
- the prompt-improvement memo (when present);
- README + manifest with the synthetic-only / no-readiness disclaimer.

It does **not** call the LLM and requires no credentials. It refuses to
ship anything sourced from ``traces/local/llm_*`` paths as defense-in-
depth against accidental misuse.
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

from scripts.redact_trace import redact  # noqa: E402


EVIDENCE_PACK_VERSION = "evidence_pack_llm_adversarial_v1"


SYNTHETIC_DISCLAIMER = (
    "This evidence pack is generated from a fully synthetic local eval "
    "run on the 12-case Financial Links adversarial v1 slice. Identifiers, "
    "policies, partner configurations, and risk bands are fabricated for "
    "this deployment-readiness lab. Both compared profiles call a real LLM "
    "via the credential-gated path, but every case in the dataset is "
    "synthetic and no real customer data is involved. Raw LLM traces and the "
    "raw JSON eval reports are intentionally excluded from this pack and from "
    "git tracking; only redacted artifacts ship here. Nothing in this pack "
    "implies model safety, production readiness, regulatory compliance, or "
    "partner endorsement. One credentialed run on a 12-case synthetic slice "
    "is not enough evidence to claim a prompt is robust."
)


def _require_file(path: Path, label: str) -> Path:
    if path is None:
        raise SystemExit(f"missing required input: --{label}")
    if not path.exists():
        raise SystemExit(
            f"{label} not found: {path}\n"
            f"  Hint: re-run the credentialed adversarial v1 LLM path with "
            "`make eval-card-adversarial-v1-llm` to regenerate it."
        )
    if not path.is_file():
        raise SystemExit(f"{label} must be a file: {path}")
    return path


def _require_dir(path: Path, label: str) -> Path:
    if path is None:
        raise SystemExit(f"missing required input: --{label}")
    if not path.exists():
        raise SystemExit(
            f"{label} not found: {path}\n"
            f"  Hint: run `make redact-adversarial-v1-llm` first."
        )
    if not path.is_dir():
        raise SystemExit(f"{label} must be a directory: {path}")
    return path


def _collect_redacted_traces(directory: Path) -> tuple[list[Path], list[Path]]:
    redacted = sorted(directory.glob("*.redacted.json"))
    reports = sorted(directory.glob("*.redaction_report.json"))
    if not redacted:
        raise SystemExit(
            f"no *.redacted.json files in {directory}; run "
            "`make redact-adversarial-v1-llm` first"
        )
    return redacted, reports


def _copy(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def _write_json(dst: Path, payload: Any) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, indent=2))
    return dst


def _rewrite_trace_paths_to_pack_redacted(
    report: dict[str, Any],
    *,
    candidate: str,
) -> None:
    """Point redacted eval-summary case rows at pack-relative traces.

    Raw eval reports carry ``traces/local/llm_*`` paths because those
    are the runner outputs. Public evidence packs should not preserve
    those local raw-evidence locations; the per-case evidence pointer is
    rewritten to the redacted trace shipped inside the pack.
    """

    per_case = report.get("per_case")
    if not isinstance(per_case, list):
        return
    for case in per_case:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        if isinstance(case_id, str) and case_id:
            case["trace_path"] = (
                f"traces/redacted/{candidate}/{case_id}.redacted.json"
            )


def _rewrite_llm_report_notes(report: dict[str, Any]) -> None:
    """Normalize stale deterministic notes on redacted LLM eval summaries."""

    cost_summary = report.get("synthetic_cost_summary")
    if isinstance(cost_summary, dict):
        total_cost = float(cost_summary.get("total_est_cost_usd", 0.0) or 0.0)
        if total_cost > 0.0:
            cost_summary["note"] = (
                "Estimated cost is aggregated from credential-gated LLM trace "
                "metadata for this synthetic run. It is a public-list-price "
                "planning estimate, not a billing number, partner commitment, "
                "or production forecast."
            )

    latency_envelope = report.get("synthetic_latency_envelope")
    if isinstance(latency_envelope, dict):
        measured = latency_envelope.get("measured_ms")
        if isinstance(measured, dict):
            measured["note"] = (
                "Wall-clock latency for the graph path, including "
                "credential-gated LLM draft generation for opt-in LLM "
                "profiles. These are local synthetic measurements, not "
                "production SLAs."
            )


def _readme(manifest: dict[str, Any]) -> str:
    file_lines = "\n".join(
        f"- `{entry['path']}` — {entry['purpose']}"
        for entry in manifest["files"]
    )
    return f"""# Evidence Pack — Financial Links LLM Adversarial v1

> {SYNTHETIC_DISCLAIMER}

## What this pack contains

This is a public-safe view of the local synthetic Financial Links
**adversarial v1 (12-case) LLM candidate comparison**. The compared
profiles are `llm_candidate_v0` (Before) and `llm_candidate_v1` (After),
both run against the expanded 12-case adversarial v1 slice. Every artifact
below is generated from on-disk inputs:

{file_lines}

The redacted traces under `traces/redacted/candidate_v0/` and
`traces/redacted/candidate_v1/` are paired with redaction reports
(`*.redaction_report.json`) that list removed, abstracted, preserved, and
uncovered top-level fields. The same applies to each candidate's redacted
JSON eval summary. The redaction policy used is
`configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw LLM traces (the gitignored per-candidate raw-trace directories) —
  intentionally excluded;
- the raw JSON eval reports (both candidate reports are gitignored; the
  pack ships only their redacted summaries) — intentionally excluded as
  raw payloads;
- model/NLI semantic-decision payloads — those remain gitignored local
  audit artifacts under `reports/semantic_model_decisions/`;
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable Before/After comparison
   (`llm_candidate_v0` vs `llm_candidate_v1`) on the 12-case slice. It
   links only to redacted-trace paths.
2. `improvement_memo.md` (when present) is the concise evidence-backed
   write-up of what changed in the prompt and what the delta was.
3. `llm_candidate_v0_eval.redacted.json` is the v0 (Before) JSON eval
   report after applying `configs/redaction_policy.yaml`. Raw
   `draft_text` / `draft_excerpt` / `final_response` values have been
   replaced with the policy's abstraction placeholder.
4. `llm_candidate_v1_eval.redacted.json` is the v1 (After) eval report
   under the same redaction policy.
5. `traces/redacted/candidate_v0/*.redacted.json` and
   `traces/redacted/candidate_v1/*.redacted.json` show the synthetic
   trace shape an analyst can reason about without raw model output.
6. `manifest.json` is the machine-readable index.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only.** This pack
shows the adversarial v1 candidate comparison closes locally on real LLM
traces; it does **not** prove `llm_candidate_v1` is robust, pilot grade,
regulatory compliant, partner endorsed, or production grade. A single
credentialed run on a 12-case synthetic slice cannot establish prompt
robustness — real evaluation needs many more runs and many more cases.
"""


def package_adversarial_v1_llm_evidence(
    *,
    raw_v0_report: Path,
    raw_v1_report: Path,
    eval_card: Path,
    redacted_traces_v0: Path,
    redacted_traces_v1: Path,
    policy: Path,
    out: Path,
    improvement_memo: Path | None = None,
) -> Path:
    raw_v0_report = _require_file(raw_v0_report, "raw-v0-report")
    raw_v1_report = _require_file(raw_v1_report, "raw-v1-report")
    eval_card = _require_file(eval_card, "eval-card")
    redacted_v0_dir = _require_dir(redacted_traces_v0, "redacted-traces-v0")
    redacted_v1_dir = _require_dir(redacted_traces_v1, "redacted-traces-v1")
    policy_path = _require_file(policy, "policy")

    policy_data = yaml.safe_load(policy_path.read_text())
    if not isinstance(policy_data, dict):
        raise SystemExit(f"{policy_path}: redaction policy must be a YAML mapping")

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

    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    manifest: dict[str, Any] = {
        "version": EVIDENCE_PACK_VERSION,
        "synthetic": True,
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
        "(markdown) on the 12-case adversarial v1 slice.",
    )
    if improvement_memo is not None and improvement_memo.exists():
        _add_copy(
            improvement_memo,
            "improvement_memo.md",
            "Concise evidence-backed prompt-improvement memo.",
        )
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

    _guard_no_raw_paths(manifest)

    readme_path = out / "README.md"
    readme_path.write_text(_readme(manifest))
    manifest["files"].insert(
        0,
        {
            "path": "README.md",
            "purpose": "Pack overview + synthetic-only / no-readiness disclaimer.",
            "source": "<generated>",
        },
    )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out


def _guard_no_raw_paths(manifest: dict[str, Any]) -> None:
    """Refuse to ship any file whose pack-relative path begins with
    ``traces/local/`` or whose ``source`` points at a raw-LLM location on
    disk. Defense-in-depth against accidental misuse."""

    forbidden_rel_prefixes = ("traces/local/",)
    forbidden_source_substrings = ("traces/local/llm_",)
    for entry in manifest["files"]:
        rel = entry.get("path", "")
        if any(rel.startswith(p) for p in forbidden_rel_prefixes):
            raise SystemExit(
                f"refusing to ship raw-trace path inside pack: {rel}"
            )
        source = entry.get("source", "")
        if any(s in source for s in forbidden_source_substrings):
            raise SystemExit(
                f"refusing to ship file sourced from raw-LLM trace dir: "
                f"{source!r} (rel={rel!r})"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble a public-safe evidence pack for the adversarial v1 "
            "(12-case) LLM candidate comparison."
        )
    )
    parser.add_argument("--raw-v0-report", required=True, type=Path)
    parser.add_argument("--raw-v1-report", required=True, type=Path)
    parser.add_argument("--eval-card", required=True, type=Path)
    parser.add_argument("--redacted-traces-v0", required=True, type=Path)
    parser.add_argument("--redacted-traces-v1", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--improvement-memo",
        type=Path,
        default=None,
        help=(
            "Optional path to the prompt-improvement memo. When present, "
            "it's copied into the pack as improvement_memo.md."
        ),
    )
    args = parser.parse_args(argv)

    pack_root = package_adversarial_v1_llm_evidence(
        raw_v0_report=args.raw_v0_report,
        raw_v1_report=args.raw_v1_report,
        eval_card=args.eval_card,
        redacted_traces_v0=args.redacted_traces_v0,
        redacted_traces_v1=args.redacted_traces_v1,
        policy=args.policy,
        out=args.out,
        improvement_memo=args.improvement_memo,
    )
    print(f"OK: assembled adversarial v1 LLM evidence pack -> {pack_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
