"""Assemble a public-safe evidence pack for the opt-in LLM adversarial run.

The opt-in ``llm_candidate_v0`` path produces real model traces under
``traces/local/llm_adversarial/`` and a JSON eval report at
``reports/llm_adversarial_eval.json`` that embeds raw LLM ``draft_text``
/ ``draft_excerpt`` content. Both are treated as raw evidence and are
**not** tracked in git. This script publishes only public-safe,
redacted artifacts:

- the redacted summary of the LLM eval report
  (``llm_candidate_eval.redacted.json`` + ``.redaction_report.json``);
- previously-redacted LLM traces under ``traces/redacted/``;
- the deterministic reference report (already public-safe);
- the corrected before/after eval card (which carries no raw draft
  payloads);
- the pinned ``regressions_llm_v0.jsonl`` seed file.

No external credentials are required to run this script: it operates
purely on on-disk artifacts.
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


EVIDENCE_PACK_VERSION = "evidence_pack_llm_v0"


SYNTHETIC_DISCLAIMER = (
    "This evidence pack is generated from a fully synthetic local eval "
    "run. Identifiers, policies, partner configurations, and risk bands "
    "are fabricated for this deployment-readiness lab. The candidate "
    "profile (`llm_candidate_v0`) calls a real LLM via the credential-"
    "gated path, but every case in the dataset is synthetic and no real "
    "customer data is involved. Raw LLM traces and the raw JSON eval "
    "report are intentionally excluded from this pack and from git "
    "tracking; only redacted artifacts ship here. Nothing in this pack "
    "implies model safety, production readiness, regulatory compliance, "
    "or partner endorsement."
)


def _require_file(path: Path, label: str) -> Path:
    if path is None:
        raise SystemExit(f"missing required input: --{label}")
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    if not path.is_file():
        raise SystemExit(f"{label} must be a file: {path}")
    return path


def _require_dir(path: Path, label: str) -> Path:
    if path is None:
        raise SystemExit(f"missing required input: --{label}")
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    if not path.is_dir():
        raise SystemExit(f"{label} must be a directory: {path}")
    return path


def _collect_redacted_traces(directory: Path) -> tuple[list[Path], list[Path]]:
    redacted = sorted(directory.glob("*.redacted.json"))
    reports = sorted(directory.glob("*.redaction_report.json"))
    if not redacted:
        raise SystemExit(
            f"no *.redacted.json files in {directory}; run "
            "`make redact-llm-adversarial` first"
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
    return f"""# Evidence Pack — Financial Links LLM Adversarial v0

> {SYNTHETIC_DISCLAIMER}

## What this pack contains

This is a public-safe view of the local synthetic Financial Links
**adversarial** v0 eval comparing the deterministic `improved_v0`
profile (reference) against the credential-gated `llm_candidate_v0`
profile (candidate). Every artifact below is generated from on-disk
inputs:

{file_lines}

The redacted traces in `traces/redacted/` are paired with redaction
reports (`*.redaction_report.json`) that list removed, abstracted,
preserved, and uncovered top-level fields. The same applies to the
candidate's redacted JSON eval summary (`llm_candidate_eval.redacted.json`
+ `llm_candidate_eval.redaction_report.json`). The redaction policy used
is `configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw LLM traces (gitignored under the `llm_adversarial/` traces directory) —
  intentionally excluded;
- the raw JSON eval report `reports/llm_adversarial_eval.json` —
  intentionally excluded and gitignored (it embeds raw draft text);
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, regulatory, or model-safety claim.

## How to read the pack

1. `eval_card.md` is the human-readable before/after summary
   (`improved_v0` reference vs `llm_candidate_v0` candidate). It uses
   the corrected disclaimer that names the real LLM call.
2. `reference_eval.json` is the deterministic reference's JSON eval
   report. It is unchanged from `reports/improved_adversarial_eval.json`
   and carries no raw model output.
3. `llm_candidate_eval.redacted.json` is the candidate's JSON eval
   report after applying `configs/redaction_policy.yaml`. Raw
   `draft_text` / `draft_excerpt` / `final_response` values have been
   replaced with the policy's abstraction placeholder.
4. `regressions_llm_v0.jsonl` lists the pinned `pending_review`
   regression seeds derived from the candidate's failing cases.
5. `traces/redacted/*.redacted.json` show the synthetic trace shape an
   analyst can reason about without raw model output.
6. `manifest.json` is the machine-readable index.

## Launch posture

**NOT READY FOR PILOT — local synthetic vertical slice only.** This
pack proves the redaction-and-evidence loop closes on real LLM traces;
it does **not** prove model safety, pilot readiness, regulatory
compliance, partner endorsement, or production behavior.
"""


def package_llm_evidence(
    *,
    raw_report: Path,
    eval_card: Path,
    reference_report: Path,
    regressions: Path,
    redacted_traces: Path,
    policy: Path,
    out: Path,
) -> Path:
    raw_report = _require_file(raw_report, "raw-report")
    eval_card = _require_file(eval_card, "eval-card")
    reference_report = _require_file(reference_report, "reference-report")
    regressions = _require_file(regressions, "regressions")
    redacted_dir = _require_dir(redacted_traces, "redacted-traces")
    policy_path = _require_file(policy, "policy")

    policy_data = yaml.safe_load(policy_path.read_text())
    if not isinstance(policy_data, dict):
        raise SystemExit(f"{policy_path}: redaction policy must be a YAML mapping")

    raw_report_payload = json.loads(raw_report.read_text())
    redacted_report, redaction_report = redact(raw_report_payload, policy_data)

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

    _add_copy(eval_card, "eval_card.md", "Corrected before/after eval card (markdown).")
    _add_copy(
        reference_report,
        "reference_eval.json",
        "Deterministic reference profile JSON eval report (already public-safe).",
    )
    _add_payload(
        redacted_report,
        "llm_candidate_eval.redacted.json",
        "Candidate profile JSON eval report with raw draft text abstracted "
        "and IDs removed.",
        source=str(raw_report),
    )
    _add_payload(
        redaction_report,
        "llm_candidate_eval.redaction_report.json",
        "Redaction report for the candidate JSON eval (removed / abstracted "
        "/ preserved / uncovered fields).",
        source=str(raw_report),
    )
    _add_copy(
        regressions,
        "regressions_llm_v0.jsonl",
        "Pinned pending_review regression seeds derived from the candidate's "
        "failing cases.",
    )

    for trace_path in redacted_trace_files:
        _add_copy(
            trace_path,
            f"traces/redacted/{trace_path.name}",
            "Redacted synthetic LLM trace.",
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


def _guard_no_raw_paths(manifest: dict[str, Any]) -> None:
    """Refuse to ship any file whose pack-relative path begins with
    ``traces/local/`` or whose ``source`` points at the raw-LLM
    locations on disk. Defense-in-depth against accidental misuse."""

    forbidden_rel_prefixes = ("traces/local/",)
    forbidden_source_substrings = ("traces/local/llm_adversarial/",)
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
            "Assemble a public-safe evidence pack for the opt-in LLM "
            "adversarial run."
        )
    )
    parser.add_argument("--raw-report", required=True, type=Path)
    parser.add_argument("--eval-card", required=True, type=Path)
    parser.add_argument("--reference-report", required=True, type=Path)
    parser.add_argument("--regressions", required=True, type=Path)
    parser.add_argument("--redacted-traces", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    pack_root = package_llm_evidence(
        raw_report=args.raw_report,
        eval_card=args.eval_card,
        reference_report=args.reference_report,
        regressions=args.regressions,
        redacted_traces=args.redacted_traces,
        policy=args.policy,
        out=args.out,
    )
    print(f"OK: assembled LLM evidence pack -> {pack_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
