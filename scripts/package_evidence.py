"""Assemble a public-safe evidence pack from existing local artifacts.

Inputs:

- ``--eval-card`` — markdown card from ``scripts/generate_eval_card.py``;
- ``--baseline-report`` / ``--improved-report`` — JSON eval reports;
- ``--regressions`` — JSONL regression-seed file;
- ``--redacted-traces`` — directory containing ``*.redacted.json`` and
  ``*.redaction_report.json`` files produced by ``scripts/redact_trace.py``;
- ``--out`` — output directory for the assembled pack.

Outputs (under ``--out``):

- ``README.md`` — synthetic-only / public-safety disclaimer + index;
- ``eval_card.md``, ``baseline_eval.json``, ``improved_eval.json``,
  ``regressions.jsonl`` — copied artifacts;
- ``traces/redacted/`` — every ``*.redacted.json`` and
  ``*.redaction_report.json`` from the source directory;
- ``manifest.json`` — listing of included files with a short purpose
  string each.

The script refuses missing inputs with a clear error. Raw traces are
never copied in.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


EVIDENCE_PACK_VERSION = "evidence_pack_v0"


SYNTHETIC_DISCLAIMER = (
    "This evidence pack is generated from a fully synthetic local eval "
    "run. Identifiers, policies, partner configurations, and risk bands "
    "are fabricated for this deployment-readiness lab. Nothing in this "
    "pack implies production readiness, regulatory compliance, partner "
    "endorsement, or real-world performance. Raw traces are intentionally "
    "excluded; only redacted artifacts ship in this directory."
)


def _require_input(path: Path, label: str) -> Path:
    if path is None:
        raise SystemExit(f"missing required input: --{label}")
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    return path


def _collect_redacted_traces(directory: Path) -> tuple[list[Path], list[Path]]:
    if not directory.exists():
        raise SystemExit(f"redacted-traces directory not found: {directory}")
    if not directory.is_dir():
        raise SystemExit(f"redacted-traces must be a directory: {directory}")

    redacted = sorted(directory.glob("*.redacted.json"))
    reports = sorted(directory.glob("*.redaction_report.json"))
    if not redacted:
        raise SystemExit(
            f"no *.redacted.json files in {directory}; run scripts/redact_trace.py first"
        )
    return redacted, reports


def _copy(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def _readme(pack_root: Path, manifest: dict[str, Any]) -> str:
    file_lines = "\n".join(
        f"- `{entry['path']}` — {entry['purpose']}"
        for entry in manifest["files"]
    )
    return f"""# Evidence Pack — Financial Links v0

> {SYNTHETIC_DISCLAIMER}

## What this pack contains

This is a public-safe view of the local synthetic Financial Links v0
eval. Every file in it is generated from artifacts already on disk:

{file_lines}

The redacted traces in `traces/redacted/` are paired with redaction
reports (`*.redaction_report.json`) that list removed, abstracted,
preserved, and uncovered top-level fields. The redaction policy used to
produce them is `configs/redaction_policy.yaml`.

## What this pack does **not** contain

- raw traces (under `traces/local/...`) — intentionally excluded;
- private project context (`.project-memory/`) — never published;
- any pilot, production-readiness, or regulatory claim.

## How to read the pack

1. `eval_card.md` is the human-readable summary; it links to the
   underlying baseline/improved reports.
2. `baseline_eval.json` / `improved_eval.json` carry per-case grader
   results and the synthetic latency / cost summary.
3. `regressions.jsonl` lists the pinned regression seeds derived from
   baseline failures (see `scripts/incident_to_regression.py`).
4. `traces/redacted/*.redacted.json` show the synthetic trace shape an
   analyst can reason about without raw IDs or raw draft text.
5. `manifest.json` is the machine-readable index of the above.
"""


def package(
    eval_card: Path,
    baseline_report: Path,
    improved_report: Path,
    regressions: Path,
    redacted_traces: Path,
    out: Path,
) -> Path:
    eval_card = _require_input(eval_card, "eval-card")
    baseline_report = _require_input(baseline_report, "baseline-report")
    improved_report = _require_input(improved_report, "improved-report")
    regressions = _require_input(regressions, "regressions")
    _require_input(redacted_traces, "redacted-traces")

    redacted_files, redaction_reports = _collect_redacted_traces(redacted_traces)

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

    def _add(src: Path, rel: str, purpose: str) -> None:
        _copy(src, out / rel)
        manifest["files"].append({"path": rel, "purpose": purpose, "source": str(src)})

    _add(eval_card, "eval_card.md", "Before/after eval card (markdown).")
    _add(baseline_report, "baseline_eval.json", "Baseline profile JSON eval report.")
    _add(improved_report, "improved_eval.json", "Improved profile JSON eval report.")
    _add(regressions, "regressions.jsonl", "Pinned regression seeds derived from baseline failures.")

    for trace_path in redacted_files:
        _add(
            trace_path,
            f"traces/redacted/{trace_path.name}",
            "Redacted synthetic trace.",
        )
    for report_path in redaction_reports:
        _add(
            report_path,
            f"traces/redacted/{report_path.name}",
            "Redaction report (removed/abstracted/preserved/uncovered fields).",
        )

    # README is written last so its file listing matches the manifest.
    readme_path = out / "README.md"
    readme_path.write_text(_readme(out, manifest))
    manifest["files"].insert(
        0,
        {
            "path": "README.md",
            "purpose": "Pack overview + synthetic-only disclaimer.",
            "source": "<generated>",
        },
    )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a public-safe evidence pack from local artifacts."
    )
    parser.add_argument("--eval-card", required=True, type=Path)
    parser.add_argument("--baseline-report", required=True, type=Path)
    parser.add_argument("--improved-report", required=True, type=Path)
    parser.add_argument("--regressions", required=True, type=Path)
    parser.add_argument("--redacted-traces", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    pack_root = package(
        eval_card=args.eval_card,
        baseline_report=args.baseline_report,
        improved_report=args.improved_report,
        regressions=args.regressions,
        redacted_traces=args.redacted_traces,
        out=args.out,
    )
    print(f"OK: assembled evidence pack -> {pack_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
