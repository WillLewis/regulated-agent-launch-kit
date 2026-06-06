"""Build the credential-free replay fixture for the v2 semantic regression seeds.

Mirrors ``scripts/build_semantic_replay_fixture_adversarial_v1.py`` for the
adversarial v2 slice. The 14 v2 semantic-only regression seeds were detectable
only by the model/NLI semantic grader. This script makes them **replayable
without credentials** by emitting a ``SemanticDecision`` fixture keyed by the
deterministic ``improved_v0`` vehicle, so the pure offline
``unsupported_claim_semantic`` grader fires ``UNSAFE_CUSTOMER_COMMS`` on every
seeded case with **no model call**.

What is pinned, and from where:

- ``makes_unsupported_claim: true`` — taken from the public v2 semantic audit
  summary's ``semantic_only_flag_case_ids``. The script refuses to emit a
  decision for any seed whose ``(source_case_id, source_agent_system_version)``
  is not a semantic-only flag in that summary, so the fixture cannot drift from
  the audit.
- ``confidence`` — the summary's reported confidence floor (aggregate field).
- ``claim_type`` / ``calibration`` — intentionally **not** pinned per case
  (``none`` / ``unknown``): the public summary exposes only per-profile
  histograms, and the grader fires on ``makes_unsupported_claim`` alone.
- ``rationale`` is an authored provenance string; ``evidence_spans`` is empty.
  No raw draft text, model reasoning, or quoted spans are emitted.
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

from scripts.seed_semantic_regressions_adversarial_v1 import (  # noqa: E402
    semantic_only_pairs,
)
from scripts.seed_semantic_regressions_adversarial_v2 import (  # noqa: E402
    DEFAULT_OUT as DEFAULT_REGRESSIONS,
    DEFAULT_SUMMARY,
)

FIXTURE_VERSION = "semantic_decisions_v0"
REGRESSION_DATASET_ID = "financial_links_regressions_semantic_adversarial_v2"
REPLAY_PROFILE_DEFAULT = "improved_v0"
DEFAULT_FIXTURE_OUT = (
    REPO_ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "regressions_semantic_adversarial_v2_decisions.json"
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"regression file not found: {path}")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(
            f"semantic audit summary not found: {path}\n"
            "  Hint: run `make semantic-audit-summary-adversarial-v2-llm` (on-disk)."
        )
    return json.loads(path.read_text())


def _confidence_floor(summary: dict[str, Any]) -> float:
    floors = [
        float(p.get("semantic", {}).get("confidence_min", 0.0))
        for p in summary.get("profiles", [])
        if p.get("semantic", {}).get("confidence_min") is not None
    ]
    floors = [f for f in floors if f > 0.0]
    return round(min(floors), 4) if floors else 0.85


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_fixture(
    *,
    regressions_path: Path,
    summary_path: Path,
    replay_profile: str = REPLAY_PROFILE_DEFAULT,
) -> dict[str, Any]:
    records = _load_jsonl(regressions_path)
    summary = _load_summary(summary_path)
    summary_pairs = {(c, p) for c, p, _ in semantic_only_pairs(summary)}
    confidence = _confidence_floor(summary)

    decisions: dict[str, dict[str, Any]] = {}
    for record in records:
        source_case = str(record.get("source_case_id"))
        source_profile = str(record.get("source_agent_system_version"))
        regression_case_id = str(record.get("regression_case_id"))
        if (source_case, source_profile) not in summary_pairs:
            raise SystemExit(
                f"refusing to pin a fixture for {regression_case_id!r}: "
                f"({source_case}, {source_profile}) is not a semantic-only flag "
                f"in {summary_path}. The fixture must not drift from the audit."
            )
        decisions[regression_case_id] = {
            "makes_unsupported_claim": True,
            "claim_type": "none",
            "confidence": confidence,
            "rationale": (
                "Pinned model/NLI semantic-audit verdict: semantic-only "
                f"UNSAFE_CUSTOMER_COMMS flag for source case {source_case} on "
                f"{source_profile}, per the public v2 semantic audit summary (the "
                "lexical grader cleared it). Aggregate-derived replay fixture — "
                "claim type/calibration not pinned per case; no raw draft text."
            ),
            "evidence_spans": [],
            "calibration": "unknown",
        }

    if not decisions:
        raise SystemExit(f"{regressions_path}: no seeds to build a fixture from")

    return {
        "version": FIXTURE_VERSION,
        "dataset_id": REGRESSION_DATASET_ID,
        "synthetic": True,
        "replay_profile": replay_profile,
        "source_semantic_audit_summary": _relative(summary_path),
        "note": (
            "Credential-free replay fixture for the adversarial v2 semantic "
            "regression seeds. makes_unsupported_claim is pinned true from the "
            "public summary's semantic-only flags; claim_type/calibration are "
            "not pinned per case (aggregate-only); evidence_spans is empty and "
            "rationale is an authored provenance string — no raw draft text, "
            "model reasoning, or quoted spans. Consumed by scripts/run_eval.py "
            f"--semantic-decisions with --agent-system-version {replay_profile} "
            "(a deterministic vehicle); the offline unsupported_claim_semantic "
            "grader then fires UNSAFE_CUSTOMER_COMMS. This proves the grader "
            "pipeline surfaces the finding without a model call; it does not "
            "re-derive the claim from a live draft."
        ),
        "decisions": {replay_profile: decisions},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the credential-free SemanticDecision replay fixture for the "
            "adversarial v2 semantic regression seeds. On-disk only; no model call."
        )
    )
    parser.add_argument("--regressions", type=Path, default=DEFAULT_REGRESSIONS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--replay-profile", default=REPLAY_PROFILE_DEFAULT)
    parser.add_argument("--out", type=Path, default=DEFAULT_FIXTURE_OUT)
    args = parser.parse_args(argv)

    fixture = build_fixture(
        regressions_path=args.regressions,
        summary_path=args.summary,
        replay_profile=args.replay_profile,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, indent=2) + "\n")
    decisions = fixture["decisions"][args.replay_profile]
    print(
        f"OK: wrote replay fixture -> {args.out} "
        f"({len(decisions)} pinned decision(s) under profile "
        f"{args.replay_profile!r}; all makes_unsupported_claim=true)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
