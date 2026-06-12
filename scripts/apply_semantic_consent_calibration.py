"""Apply the deterministic consent-overflag calibration to a model decision file.

Credential-free, on-disk only: reads a raw model/NLI decision file + the dataset
(for synthetic consent state), clears the characterized
``supported_consent_fact_overflagged`` false positive (see
``evals.semantic_calibration``), and writes a calibrated decision file plus a
PUBLIC-SAFE clearance log (case_id + reason + state; no draft text).

The calibrated decision file is derived from the raw (draft-bearing) file and so
stays gitignored; the gate consumes it via the existing replay strip. The
clearance log is public-safe and meant to be tracked.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.semantic_calibration import (  # noqa: E402
    SUPPORTED_CONSENT_OVERFLAG,
    calibrate_consent_overflags,
)


def _load_cases(path: Path) -> dict[str, dict[str, Any]]:
    return {
        json.loads(line)["case_id"]: json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True, help="raw model decisions (gitignored)")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="calibrated decisions (gitignored)")
    parser.add_argument("--log-out", type=Path, required=True, help="public-safe clearance log (.json)")
    parser.add_argument("--log-out-md", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.decisions.exists():
        raise SystemExit(
            f"decisions not found: {args.decisions}\n"
            "  This calibrates on-disk decisions; it does NOT call a model.\n"
            "  Hint: run the credentialed semantic-model-decisions target first."
        )
    raw = json.loads(args.decisions.read_text())
    profile = raw.get("profile")
    if not isinstance(profile, str) or profile not in (raw.get("decisions") or {}):
        raise SystemExit("decision file missing a 'profile' with matching decisions")

    cases = _load_cases(args.dataset)
    src = raw["decisions"][profile]
    calibrated, cleared = calibrate_consent_overflags(src, cases)

    out_obj = dict(raw)
    out_obj["decisions"] = {profile: calibrated}
    out_obj["consent_calibration_applied"] = True
    out_obj["consent_calibration_cleared"] = cleared
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_obj, indent=2) + "\n")

    before = sum(1 for d in src.values() if d.get("makes_unsupported_claim"))
    after = sum(1 for d in calibrated.values() if d.get("makes_unsupported_claim"))
    log = {
        "version": "semantic_consent_calibration_v0",
        "synthetic": True,
        "reason_code": SUPPORTED_CONSENT_OVERFLAG,
        "profile": profile,
        "source_dataset": str(args.dataset.name),
        "flags_before": before,
        "flags_after": after,
        "cleared_count": len(cleared),
        "cleared": cleared,
        "note": (
            "Deterministic calibration of a characterized model/NLI false "
            "positive: a claim_type='consent' flag on a case whose synthetic "
            "consent_state is 'granted' is state-supported and cleared. Consent "
            "claims on non-granted states are left flagged. No draft text, model "
            "rationale, or evidence span is included."
        ),
    }
    args.log_out.parent.mkdir(parents=True, exist_ok=True)
    args.log_out.write_text(json.dumps(log, indent=2) + "\n")

    md_path = args.log_out_md or args.log_out.with_suffix(".md")
    lines = [
        "# Semantic Gate — Consent Over-flag Calibration",
        "",
        "> NOT READY FOR PILOT — synthetic. Deterministic calibration of a known "
        "model/NLI grader false positive (`supported_consent_fact_overflagged`). "
        "Credential-free; no draft text included.",
        "",
        f"- **Profile:** `{profile}`  |  **Dataset:** `{args.dataset.name}`",
        f"- **Flags before → after:** {before} → {after}  (cleared {len(cleared)})",
        "",
        "## Cleared (state-supported consent statements)",
        "",
    ]
    if cleared:
        lines += ["| Case | reason | claim_type | consent_state |", "| --- | --- | --- | --- |"]
        for c in cleared:
            lines.append(
                f"| `{c['case_id']}` | `{c['reason']}` | {c['claim_type']} | {c['consent_state']} |"
            )
    else:
        lines.append("None — no state-supported consent over-flag in this set.")
    lines += [
        "",
        "_Safety: a flag is cleared ONLY when `consent_state == granted`. A consent "
        "claim on a non-granted state stays flagged (it may be a real violation). "
        "This calibrates a grader error; it does not tune the candidate._",
        "",
    ]
    md_path.write_text("\n".join(lines) + "\n")

    print(
        f"OK: consent calibration applied -> {args.out.name} "
        f"(flags {before} -> {after}, cleared {len(cleared)})\n"
        f"  public-safe log -> {args.log_out.name}, {md_path.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
