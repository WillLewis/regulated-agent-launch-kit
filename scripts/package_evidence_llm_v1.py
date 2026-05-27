"""Assemble a public-safe evidence pack for the v1 prompt-improvement loop.

The credentialed ``llm_candidate_v1`` adversarial run produces real
model traces under ``traces/local/llm_adversarial_v1/`` and a JSON
eval report at ``reports/llm_adversarial_v1_eval.json``. Both embed
raw LLM ``draft_text`` / ``draft_excerpt`` content and are gitignored.

This script publishes the public-safe view of the v0 → v1 prompt-
improvement loop:

- the comparison eval card (already public-safe — links only to
  redacted-trace paths);
- redacted summaries of BOTH the v0 (Before) and v1 (After) raw eval
  reports;
- previously-redacted v1 traces under ``traces/redacted/llm_adversarial_v1/``;
- the pinned LLM regression seeds (committed in
  ``case_studies/financial_links_reliability/evals/regressions_llm_v0.jsonl``);
- the prompt-improvement memo (when present at
  ``reports/llm_prompt_improvement_memo.md``);
- README + manifest with the synthetic-only / no-readiness disclaimer.

It does **not** call the LLM and requires no credentials. It refuses
to ship anything sourced from ``traces/local/llm_*`` paths as a
defense-in-depth guard.
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


EVIDENCE_PACK_VERSION = "evidence_pack_llm_v1"


SYNTHETIC_DISCLAIMER = (
    "This evidence pack is generated from a fully synthetic local eval "
    "run on a 6-case adversarial slice. Identifiers, policies, partner "
    "configurations, and risk bands are fabricated for this deployment-"
    "readiness lab. Both compared profiles call a real LLM via the "
    "credential-gated path, but every case in the dataset is synthetic and "
    "no real customer data is involved. Raw LLM traces and the raw JSON eval "
    "reports are intentionally excluded from this pack and from git "
    "tracking; only redacted artifacts ship here. Nothing in this pack "
    "implies model safety, production readiness, regulatory compliance, "
    "or partner endorsement. One credentialed run on a 6-case synthetic "
    "slice is not enough evidence to claim a prompt is robust."
)


def _require_file(path: Path, label: str) -> Path:
    if path is None:
        raise SystemExit(f"missing required input: --{label}")
    if not path.exists():
        raise SystemExit(
            f"{label} not found: {path}\n"
            f"  Hint: re-run the credentialed v1 path with "
            "`make eval-card-adversarial-llm-v1` to regenerate it."
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
            f"  Hint: run `make redact-llm-adversarial-v1` first."
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
            "`make redact-llm-adversarial-v1` first"
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


def _readme(manifest: dict[str, Any]) -> str:
    file_lines = "\n".join(
        f"- `{entry['path']}` — {entry['purpose']}"
        for entry in manifest["files"]
    )
    return f"""# Evidence Pack — Financial Links LLM Prompt-Improvement v1

> {SYNTHETIC_DISCLAIMER}

## What this pack contains

This is a public-safe view of the local synthetic Financial Links
**adversarial v0 → v1 prompt-improvement loop**. The compared profiles
are `llm_candidate_v0` (Before) and `llm_candidate_v1` (After). Every
artifact below is generated from on-disk inputs:

{file_lines}

The redacted traces in `traces/redacted/` are paired with redaction
reports (`*.redaction_report.json`) that list removed, abstracted,
preserved, and uncovered top-level fields. The same applies to each
candidate's redacted JSON eval summary. The redaction policy used is
`configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw LLM traces (gitignored under the `llm_adversarial_v1/` traces
  directory) — intentionally excluded;
- the raw JSON eval reports (the v1 report is gitignored; the v0 report
  is tracked as an audit artifact in the parent repo but the pack only
  ships its redacted summary) — intentionally excluded as raw payloads;
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable Before/After comparison
   (`llm_candidate_v0` vs `llm_candidate_v1`). It links only to
   redacted-trace paths.
2. `improvement_memo.md` (when present) is the concise evidence-backed
   write-up of what changed in the prompt and what the delta was.
3. `llm_candidate_v0_eval.redacted.json` is the v0 (Before) JSON eval
   report after applying `configs/redaction_policy.yaml`. Raw
   `draft_text` / `draft_excerpt` / `final_response` values have been
   replaced with the policy's abstraction placeholder.
4. `llm_candidate_v1_eval.redacted.json` is the v1 (After) eval report
   under the same redaction policy.
5. `regressions_llm_v0.jsonl` lists the pending-review regression seeds
   that captured v0 failure modes; they remain useful context for the
   improvement loop.
6. `repeat_run_summary.md` / `repeat_run_summary.json` (when present)
   are the public-safe aggregated outputs of a credentialed repeat-run
   capture (N runs × the same adversarial slice for each profile).
   They describe run-to-run variance — pass/fail per run, runtime-vs-
   offline asymmetry, per-case instability, per-band latency, and cost
   distribution — without any raw draft text or raw trace path.
7. `traces/redacted/*.redacted.json` show the synthetic v1 trace shape
   an analyst can reason about without raw model output.
8. `manifest.json` is the machine-readable index.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only.** This
pack proves the prompt-improvement loop closes locally on real LLM
traces; it does **not** prove v1 is robust, pilot grade, regulatory
compliant, partner endorsed, or production grade. A single credentialed
run on a 6-case synthetic slice cannot establish prompt robustness —
real evaluation needs many more runs and many more cases.
"""


def package_llm_v1_evidence(
    *,
    raw_v0_report: Path,
    raw_v1_report: Path,
    eval_card: Path,
    regressions: Path,
    redacted_traces: Path,
    policy: Path,
    out: Path,
    improvement_memo: Path | None = None,
    repeat_summary_md: Path | None = None,
    repeat_summary_json: Path | None = None,
) -> Path:
    raw_v0_report = _require_file(raw_v0_report, "raw-v0-report")
    raw_v1_report = _require_file(raw_v1_report, "raw-v1-report")
    eval_card = _require_file(eval_card, "eval-card")
    regressions = _require_file(regressions, "regressions")
    redacted_dir = _require_dir(redacted_traces, "redacted-traces")
    policy_path = _require_file(policy, "policy")

    policy_data = yaml.safe_load(policy_path.read_text())
    if not isinstance(policy_data, dict):
        raise SystemExit(f"{policy_path}: redaction policy must be a YAML mapping")

    raw_v0 = json.loads(raw_v0_report.read_text())
    redacted_v0, redaction_v0 = redact(raw_v0, policy_data)

    raw_v1 = json.loads(raw_v1_report.read_text())
    redacted_v1, redaction_v1 = redact(raw_v1, policy_data)

    redacted_trace_files, redaction_trace_reports = _collect_redacted_traces(
        redacted_dir
    )

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
        "Before/After v0-vs-v1 comparison eval card (markdown).",
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
        "v0 (Before) JSON eval report with raw draft text abstracted "
        "and IDs removed.",
        source=str(raw_v0_report),
    )
    _add_payload(
        redaction_v0,
        "llm_candidate_v0_eval.redaction_report.json",
        "Redaction report for the v0 JSON eval.",
        source=str(raw_v0_report),
    )
    _add_payload(
        redacted_v1,
        "llm_candidate_v1_eval.redacted.json",
        "v1 (After) JSON eval report with raw draft text abstracted "
        "and IDs removed.",
        source=str(raw_v1_report),
    )
    _add_payload(
        redaction_v1,
        "llm_candidate_v1_eval.redaction_report.json",
        "Redaction report for the v1 JSON eval.",
        source=str(raw_v1_report),
    )
    _add_copy(
        regressions,
        "regressions_llm_v0.jsonl",
        "Pinned pending_review regression seeds derived from v0 failures; "
        "still useful context for the improvement loop.",
    )
    if repeat_summary_md is not None and repeat_summary_md.exists():
        _guard_repeat_summary_md(repeat_summary_md)
        _add_copy(
            repeat_summary_md,
            "repeat_run_summary.md",
            "Public-safe repeat-run variance summary aggregated from "
            "credentialed repeat-run capture (no raw draft text, no raw "
            "trace paths).",
        )
    if repeat_summary_json is not None and repeat_summary_json.exists():
        _guard_repeat_summary_json(repeat_summary_json)
        _add_copy(
            repeat_summary_json,
            "repeat_run_summary.json",
            "Machine-readable repeat-run variance summary (per-run pass/fail, "
            "runtime-vs-offline asymmetry, per-case instability, latency by "
            "band, cost distribution).",
        )

    for trace_path in redacted_trace_files:
        _add_copy(
            trace_path,
            f"traces/redacted/{trace_path.name}",
            "Redacted synthetic v1 LLM trace.",
        )
    for report_path in redaction_trace_reports:
        _add_copy(
            report_path,
            f"traces/redacted/{report_path.name}",
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


_REPEAT_SUMMARY_FORBIDDEN_SUBSTRINGS: tuple[str, ...] = (
    "traces/local/llm_",
    "RAW MODEL OUTPUT",
    "draft_text",
    "draft_excerpt",
)


def _guard_repeat_summary_md(path: Path) -> None:
    """Refuse to ship a repeat-summary md that leaks raw paths or raw
    draft text. The aggregator already enforces this, but this is
    defense-in-depth at packaging time."""

    text = path.read_text()
    for needle in _REPEAT_SUMMARY_FORBIDDEN_SUBSTRINGS:
        if needle in text:
            raise SystemExit(
                f"refusing to ship repeat-summary markdown containing "
                f"forbidden substring {needle!r}: {path}"
            )
    if "NOT READY FOR PILOT" not in text:
        raise SystemExit(
            "refusing to ship repeat-summary markdown missing the "
            f"NOT READY FOR PILOT posture line: {path}"
        )


def _guard_repeat_summary_json(path: Path) -> None:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise SystemExit(
            f"repeat-summary JSON must be a JSON object: {path}"
        )
    if payload.get("not_ready_for_pilot") is not True:
        raise SystemExit(
            "refusing to ship repeat-summary JSON without "
            f"not_ready_for_pilot=true: {path}"
        )
    # Re-serialize and check for forbidden substrings.
    blob = json.dumps(payload)
    for needle in _REPEAT_SUMMARY_FORBIDDEN_SUBSTRINGS:
        if needle in blob:
            raise SystemExit(
                f"refusing to ship repeat-summary JSON containing "
                f"forbidden substring {needle!r}: {path}"
            )


def _guard_no_raw_paths(manifest: dict[str, Any]) -> None:
    """Refuse to ship any file whose pack-relative path begins with
    ``traces/local/`` or whose ``source`` points at the raw-LLM
    locations on disk. Defense-in-depth against accidental misuse."""

    forbidden_rel_prefixes = ("traces/local/",)
    forbidden_source_substrings = (
        "traces/local/llm_adversarial/",
        "traces/local/llm_adversarial_v1/",
    )
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
            "Assemble a public-safe evidence pack for the v1 prompt-"
            "improvement loop."
        )
    )
    parser.add_argument("--raw-v0-report", required=True, type=Path)
    parser.add_argument("--raw-v1-report", required=True, type=Path)
    parser.add_argument("--eval-card", required=True, type=Path)
    parser.add_argument("--regressions", required=True, type=Path)
    parser.add_argument("--redacted-traces", required=True, type=Path)
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
    parser.add_argument(
        "--repeat-summary-md",
        type=Path,
        default=None,
        help=(
            "Optional path to the public-safe repeat-run variance Markdown "
            "summary. When present, it's copied into the pack as "
            "repeat_run_summary.md after a public-safety substring guard."
        ),
    )
    parser.add_argument(
        "--repeat-summary-json",
        type=Path,
        default=None,
        help=(
            "Optional path to the machine-readable repeat-run variance JSON "
            "summary. When present, it's copied into the pack as "
            "repeat_run_summary.json after a public-safety guard."
        ),
    )
    args = parser.parse_args(argv)

    pack_root = package_llm_v1_evidence(
        raw_v0_report=args.raw_v0_report,
        raw_v1_report=args.raw_v1_report,
        eval_card=args.eval_card,
        regressions=args.regressions,
        redacted_traces=args.redacted_traces,
        policy=args.policy,
        out=args.out,
        improvement_memo=args.improvement_memo,
        repeat_summary_md=args.repeat_summary_md,
        repeat_summary_json=args.repeat_summary_json,
    )
    print(f"OK: assembled v1 LLM evidence pack -> {pack_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
