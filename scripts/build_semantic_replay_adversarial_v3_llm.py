"""Build a credential-free replay fixture from a v3 candidate model/NLI audit.

M7b: the reusable semantic gate (``scripts/check_semantic_gate.py``) needs an
eval report that carries the offline ``unsupported_claim_semantic`` lane. The
credentialed model/NLI audit (``scripts/generate_semantic_decisions.py``)
produces a raw decision file keyed by the **candidate** profile
(``llm_candidate_v0`` / ``llm_candidate_v1``) whose ``rationale`` /
``evidence_spans`` quote customer-draft text and stay gitignored.

This script converts that raw decision file into a **public-safe** replay
fixture keyed by the deterministic ``improved_v0`` vehicle, so the gate can be
run **credential-free and token-free** over the v2 dataset:

    run_eval.py --agent-system-version improved_v0 --semantic-decisions <fixture>

The offline ``unsupported_claim_semantic`` grader then fires per case from the
audited ``makes_unsupported_claim`` verdict — without a model call and without
re-running the candidate (which would spend tokens and overwrite the very
drafts the verdicts were made against). Only the per-case boolean verdict and
the aggregate-safe ``confidence`` are carried over; the draft-bearing
``rationale`` / ``evidence_spans`` are **dropped** (rationale replaced by an
authored provenance string, evidence_spans emptied), so the fixture is
public-safe even though its input is not.

This is replay infrastructure, not a readiness claim: a clean gate on this
fixture means one credentialed audit produced no flagged drafts on this
synthetic slice — not model safety, pilot readiness, or M7 completion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FIXTURE_VERSION = "semantic_decisions_v0"
DATASET_ID = "financial_links_reliability_adversarial_v3"
REPLAY_PROFILE_DEFAULT = "improved_v0"

# Every replayed decision's rationale must be this authored provenance string —
# never a value copied from the raw (draft-quoting) decision. Used both to build
# the rationale and to assert public-safety.
RATIONALE_PREFIX = "Replayed model/NLI semantic verdict"

# Fields in a raw decision that quote / paraphrase the customer draft. They are
# never copied into the public-safe replay fixture.
DRAFT_BEARING_KEYS: tuple[str, ...] = ("rationale", "evidence_spans")


def build_replay_fixture(
    decision_file: dict[str, Any],
    *,
    replay_profile: str = REPLAY_PROFILE_DEFAULT,
    source_label: str = "(gitignored model/NLI decision file)",
) -> dict[str, Any]:
    """Re-key a raw candidate decision file under ``replay_profile`` with the
    draft-bearing fields stripped. Pure function over the loaded JSON."""

    candidate_profile = decision_file.get("profile")
    if not isinstance(candidate_profile, str) or not candidate_profile:
        raise SystemExit("decision file missing a top-level 'profile' string")

    decisions_root = decision_file.get("decisions")
    if not isinstance(decisions_root, dict):
        raise SystemExit("decision file missing object field 'decisions'")
    src = decisions_root.get(candidate_profile)
    if not isinstance(src, dict) or not src:
        raise SystemExit(
            f"decision file has no decisions for profile {candidate_profile!r}"
        )

    replay: dict[str, dict[str, Any]] = {}
    for case_id, decision in src.items():
        if not isinstance(decision, dict):
            raise SystemExit(f"{case_id}: decision is not an object")
        replay[str(case_id)] = {
            # Only the audited boolean verdict drives the gate.
            "makes_unsupported_claim": bool(decision.get("makes_unsupported_claim")),
            # claim_type / calibration are aggregate-only in the public summary;
            # not pinned per case here (the grader fires on the boolean alone).
            "claim_type": "none",
            # Clamp to [0, 1] so the builder is the single point of failure (the
            # downstream SemanticDecision model also enforces this bound).
            "confidence": round(
                min(1.0, max(0.0, float(decision.get("confidence", 0.0) or 0.0))), 4
            ),
            "rationale": (
                f"{RATIONALE_PREFIX} for adversarial v3 candidate profile "
                f"{candidate_profile} (credential-free vehicle {replay_profile}). "
                "Aggregate-derived — no raw draft text, model reasoning, or quoted "
                "spans."
            ),
            "evidence_spans": [],
            "calibration": "unknown",
        }

    fixture = {
        "version": FIXTURE_VERSION,
        "dataset_id": DATASET_ID,
        "synthetic": True,
        "replay_profile": replay_profile,
        "source_candidate_profile": candidate_profile,
        "source": source_label,
        "note": (
            "Credential-free replay fixture re-keying the model/NLI audit of the "
            f"adversarial v3 {candidate_profile} drafts under the deterministic "
            f"{replay_profile} vehicle. Consumed by run_eval.py "
            "--semantic-decisions so the offline unsupported_claim_semantic "
            "grader fires per case with no model call and no candidate rerun. "
            "Draft-bearing rationale / evidence_spans are dropped; only the "
            "boolean verdict + aggregate confidence are carried."
        ),
        "decisions": {replay_profile: replay},
    }
    _assert_public_safe(fixture)
    return fixture


def _iter_keys(value: Any) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _iter_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def _assert_public_safe(fixture: dict[str, Any]) -> None:
    """Defense-in-depth: the emitted fixture must carry no non-empty
    evidence_spans and no raw trace path, and every decision's rationale must be
    the authored provenance string (never copied from the raw decision).

    This guards against a future builder change that interpolates a raw,
    draft-quoting field — not just the current code path.
    """

    serialized = json.dumps(fixture)
    if "traces/local/llm_" in serialized:
        raise SystemExit("replay fixture must not reference a raw trace path")
    for profile_decisions in fixture.get("decisions", {}).values():
        for case_id, decision in profile_decisions.items():
            if decision.get("evidence_spans"):
                raise SystemExit(
                    f"{case_id}: replay fixture must keep evidence_spans empty"
                )
            rationale = decision.get("rationale", "")
            if not isinstance(rationale, str) or not rationale.startswith(
                RATIONALE_PREFIX
            ):
                raise SystemExit(
                    f"{case_id}: replay fixture rationale must be the authored "
                    "provenance string, never copied from the raw decision"
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Re-key a raw adversarial v3 candidate model/NLI decision file into a "
            "public-safe, credential-free replay fixture for the semantic gate. "
            "On-disk only; no model call."
        )
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        required=True,
        help="Path to the raw candidate model/NLI decision JSON (gitignored).",
    )
    parser.add_argument("--replay-profile", default=REPLAY_PROFILE_DEFAULT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.decisions.exists():
        raise SystemExit(
            f"decision file not found: {args.decisions}\n"
            "  This target judges drafts already on disk; it does NOT generate "
            "them. Hint: run `make semantic-model-decisions-adversarial-v3-llm-v2-2` "
            "(credentialed) first."
        )
    decision_file = json.loads(args.decisions.read_text())
    fixture = build_replay_fixture(
        decision_file,
        replay_profile=args.replay_profile,
        source_label=f"{args.decisions.name} (gitignored)",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(fixture, indent=2) + "\n")
    decisions = fixture["decisions"][args.replay_profile]
    flagged = sum(1 for d in decisions.values() if d["makes_unsupported_claim"])
    print(
        f"OK: wrote replay fixture -> {args.out} "
        f"({len(decisions)} case(s) under {args.replay_profile!r}; "
        f"{flagged} flagged makes_unsupported_claim=true)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
