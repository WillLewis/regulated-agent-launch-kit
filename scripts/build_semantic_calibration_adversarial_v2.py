"""Build credential-free grader-calibration fixtures for the 4 M7 over-flags.

The M7 semantic adjudication
(``reports/llm_adversarial_v2_semantic_adjudication.json``) marked **4** of the
14 findings ``grader_calibration_review`` — the model/NLI judge appears to have
over-flagged substantively safe / hedged drafts (including one case where it
flagged the agent *correctly* stating the consent gate). Those are not candidate
failures; they are a model/NLI calibration question.

This script emits two **tracked, public-safe** fixtures that represent exactly
those 4 findings as **non-claims** (the calibrated-correct verdict), so the
offline ``unsupported_claim_semantic`` lane can prove a safe/hedged case clears:

- ``calibration_semantic_adversarial_v2.jsonl`` — a 4-case dataset, each record
  cloned from the matching v2 regression seed (so it stays runnable and
  validates) and re-keyed to a ``__semantic_calibration_v2`` case id, annotated
  with the adjudicated reason code and ``expected_semantic_claim: false``.
- ``calibration_semantic_adversarial_v2_decisions.json`` — a ``SemanticDecision``
  fixture keyed by the deterministic ``improved_v0`` vehicle with
  ``makes_unsupported_claim: false`` (``calibration: safe_hedge``) for every
  case, empty ``evidence_spans``, and an authored provenance ``rationale``. No
  raw draft text, model reasoning, or quoted spans are emitted.

Coverage is derived from the adjudication, so the fixtures cannot cover anything
other than exactly the 4 ``grader_calibration_review`` findings. The
``needs_human_review`` finding (``case_fl_adv_v2_024@llm_candidate_v1``) is
deliberately excluded — it is not forced into calibration. This script reads no
raw candidate report, decision file, or trace, and makes no model/LLM call.
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

EVALS_DIR = REPO_ROOT / "case_studies" / "financial_links_reliability" / "evals"
DEFAULT_ADJUDICATION = (
    REPO_ROOT / "reports" / "llm_adversarial_v2_semantic_adjudication.json"
)
DEFAULT_SEEDS = EVALS_DIR / "regressions_semantic_adversarial_v2.jsonl"
DEFAULT_RESIDUAL_ADJUDICATION = (
    REPO_ROOT / "reports" / "llm_adversarial_v2_candidate_v2_residual_adjudication.json"
)
DEFAULT_DATASET = EVALS_DIR / "adversarial_v2.jsonl"
DEFAULT_DATASET_OUT = EVALS_DIR / "calibration_semantic_adversarial_v2.jsonl"
DEFAULT_DECISIONS_OUT = EVALS_DIR / "calibration_semantic_adversarial_v2_decisions.json"

GRADER_CALIBRATION_REVIEW = "grader_calibration_review"
# Residual grader_calibration_review findings come from the candidate-v2 run, so
# their runnable record is sourced from the dataset (they have no regression seed)
# and labelled with this profile.
RESIDUAL_PROFILE = "llm_candidate_v2"
CALIBRATION_DATASET_ID = "financial_links_calibration_semantic_adversarial_v2"
REPLAY_PROFILE = "improved_v0"
FIXTURE_VERSION = "semantic_decisions_v0"
CONFIDENCE = 0.85

# Fields carried over from the regression seed so each calibration record stays a
# runnable, schema-valid case (the runner builds a Case from these).
_RUNNABLE_FIELDS = (
    "workflow",
    "risk_band",
    "case_type",
    "consent_sensitive",
    "synthetic_facts",
    "expected_route",
    "required_tools",
    "required_policy_ids",
    "expected_approval",
    "expected_behavior",
    "prohibited_behavior",
    "category_tags",
)

# Draft-bearing keys that must never appear in a tracked calibration fixture.
# ``evidence_spans`` is a required SemanticDecision field, so it is allowed ONLY
# when empty (a populated value would quote a raw draft span) — checked
# separately below.
_FORBIDDEN_KEYS = (
    "draft_text",
    "draft_excerpt",
    "final_response",
)


def _load_adjudication(path: Path) -> list[tuple[str, str, str]]:
    """Return the (case_id, profile, reason_code) of each grader_calibration_review."""

    if not path.exists():
        raise SystemExit(
            f"adjudication not found: {path}\n"
            "  Hint: run `make semantic-adjudication-adversarial-v2` first."
        )
    payload = json.loads(path.read_text())
    out: list[tuple[str, str, str]] = []
    for f in payload.get("findings", []):
        if f.get("adjudication_status") == GRADER_CALIBRATION_REVIEW:
            out.append(
                (str(f["case_id"]), str(f["profile"]), str(f["public_reason_code"]))
            )
    if not out:
        raise SystemExit(
            f"{path}: no grader_calibration_review findings to build fixtures from"
        )
    return out


def _load_seeds_by_pair(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"regression seeds not found: {path}")
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (
            str(row.get("source_case_id")),
            str(row.get("source_agent_system_version")),
        )
        by_pair[key] = row
    return by_pair


def _load_residual_grader_calibration(path: Path) -> list[tuple[str, str]]:
    """(case_id, reason_code) for each candidate-v2 residual marked
    grader_calibration_review. Returns [] when the residual adjudication is absent."""

    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    out: list[tuple[str, str]] = []
    for r in payload.get("residuals", []):
        if r.get("residual_status") == GRADER_CALIBRATION_REVIEW:
            out.append((str(r["case_id"]), str(r["public_reason_code"])))
    return out


def _dataset_by_id(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"dataset not found: {path}")
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[str(row["case_id"])] = row
    return out


def _make_entry(
    *,
    source_case: str,
    profile: str,
    reason_code: str,
    runnable_source: dict[str, Any],
    source_adjudication: str,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Build one (calibration_case_id, dataset_record, non-claim decision).

    ``runnable_source`` is a regression seed (original adjudication) or a dataset
    row (residual adjudication); only the allow-listed runnable fields are copied,
    so no draft-bearing field can ride along."""

    calibration_case_id = f"{source_case}__{profile}__semantic_calibration_v2"
    record: dict[str, Any] = {
        "case_id": calibration_case_id,
        "calibration_case_id": calibration_case_id,
        "dataset_id": CALIBRATION_DATASET_ID,
    }
    for field in _RUNNABLE_FIELDS:
        if field in runnable_source:
            record[field] = runnable_source[field]
    record.update(
        {
            "synthetic": True,
            "source_case_id": source_case,
            "source_agent_system_version": profile,
            "source_adjudication": source_adjudication,
            "adjudication_status": GRADER_CALIBRATION_REVIEW,
            "adjudication_reason_code": reason_code,
            "grader": "unsupported_claim_semantic",
            "expected_semantic_claim": False,
            "failure_labels": [],
            "review_status": GRADER_CALIBRATION_REVIEW,
            "notes": (
                f"Grader-calibration target: source case {source_case} on {profile} "
                f"was adjudicated grader_calibration_review (reason {reason_code}) — "
                "the model/NLI judge appears to have over-flagged a draft that "
                "should clear (safe/hedged copy, or a true tool-verified statement "
                "the draft-only judge could not corroborate). This fixture "
                "represents it as a NON-claim (makes_unsupported_claim=false) so the "
                "offline unsupported_claim_semantic lane clears it. Synthetic; no "
                "raw draft text, model reasoning, or quoted spans are stored."
            ),
        }
    )
    decision = {
        "makes_unsupported_claim": False,
        "claim_type": "none",
        "confidence": CONFIDENCE,
        "rationale": (
            "Authored grader-calibration target: this finding was adjudicated "
            f"grader_calibration_review (reason {reason_code}); the offline lane "
            "should clear it. Authored provenance; no raw draft text or quoted "
            "spans."
        ),
        "evidence_spans": [],
        "calibration": "safe_hedge",
    }
    return calibration_case_id, record, decision


def _assert_no_forbidden_keys(obj: Any, *, label: str) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _FORBIDDEN_KEYS:
                raise SystemExit(
                    f"refusing to emit {label}: contains draft-bearing key {key!r}"
                )
            if key == "evidence_spans" and value:
                raise SystemExit(
                    f"refusing to emit {label}: evidence_spans must be empty "
                    f"(a populated value would quote a raw draft span)"
                )
            _assert_no_forbidden_keys(value, label=label)
    elif isinstance(obj, list):
        for item in obj:
            _assert_no_forbidden_keys(item, label=label)


def build_fixtures(
    *,
    adjudication_path: Path,
    seeds_path: Path,
    residual_adjudication_path: Path | None = None,
    dataset_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs = _load_adjudication(adjudication_path)
    seeds = _load_seeds_by_pair(seeds_path)

    dataset_records: list[dict[str, Any]] = []
    decisions: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()

    # (1) Original adjudication's grader_calibration_review findings — runnable
    #     record cloned from the matching regression seed.
    for source_case, profile, reason_code in sorted(pairs):
        seed = seeds.get((source_case, profile))
        if seed is None:
            raise SystemExit(
                f"no regression seed for grader_calibration_review finding "
                f"({source_case}, {profile}); cannot build a runnable calibration "
                f"case. Re-run `make regression-seed-adversarial-v2-semantic`."
            )
        cid, record, decision = _make_entry(
            source_case=source_case,
            profile=profile,
            reason_code=reason_code,
            runnable_source=seed,
            source_adjudication="reports/llm_adversarial_v2_semantic_adjudication.json",
        )
        seen.add(cid)
        dataset_records.append(record)
        decisions[cid] = decision

    # (2) candidate-v2 residual adjudication's grader_calibration_review findings
    #     (e.g. case_006) — no regression seed, so the runnable record is sourced
    #     from the tracked 24-case dataset.
    residual_pairs = (
        _load_residual_grader_calibration(residual_adjudication_path)
        if residual_adjudication_path is not None
        else []
    )
    if residual_pairs:
        if dataset_path is None:
            raise SystemExit(
                "residual grader_calibration_review findings require --dataset to "
                "build a runnable record"
            )
        dataset_by_id = _dataset_by_id(dataset_path)
        for source_case, reason_code in sorted(residual_pairs):
            row = dataset_by_id.get(source_case)
            if row is None:
                raise SystemExit(
                    f"residual calibration case {source_case} absent from dataset "
                    f"{dataset_path}"
                )
            cid, record, decision = _make_entry(
                source_case=source_case,
                profile=RESIDUAL_PROFILE,
                reason_code=reason_code,
                runnable_source=row,
                source_adjudication=(
                    "reports/llm_adversarial_v2_candidate_v2_residual_adjudication.json"
                ),
            )
            if cid in seen:
                raise SystemExit(f"duplicate calibration case id {cid}")
            seen.add(cid)
            dataset_records.append(record)
            decisions[cid] = decision

    n = len(dataset_records)
    decisions_fixture = {
        "version": FIXTURE_VERSION,
        "dataset_id": CALIBRATION_DATASET_ID,
        "synthetic": True,
        "replay_profile": REPLAY_PROFILE,
        "source_adjudications": [
            "reports/llm_adversarial_v2_semantic_adjudication.json",
            "reports/llm_adversarial_v2_candidate_v2_residual_adjudication.json",
        ],
        "note": (
            f"Credential-free grader-calibration fixture for the {n} adversarial v2 "
            "grader_calibration_review findings — the original adjudication's "
            "safe/hedged over-flags plus the candidate-v2 residual adjudication's "
            "tool-verified-fact over-flag (case_006). Every decision pins "
            "makes_unsupported_claim=false (calibration=safe_hedge) so the offline "
            "unsupported_claim_semantic grader CLEARS the case — proving these "
            "should-clear drafts can be represented as non-claims. evidence_spans "
            "is empty and rationale is authored provenance; no raw draft text. "
            "Consumed by scripts/run_eval.py --semantic-decisions with "
            f"--agent-system-version {REPLAY_PROFILE} (a deterministic vehicle). "
            "This does NOT change default GRADERS and is NOT a model-safety or "
            "readiness claim; it is a calibration target pending model/NLI review."
        ),
        "decisions": {REPLAY_PROFILE: decisions},
    }

    _assert_no_forbidden_keys(dataset_records, label="calibration dataset")
    _assert_no_forbidden_keys(decisions_fixture, label="calibration decisions")
    return dataset_records, decisions_fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build credential-free grader-calibration fixtures for the 4 M7 "
            "grader_calibration_review findings (on-disk only; no model call)."
        )
    )
    parser.add_argument("--adjudication", type=Path, default=DEFAULT_ADJUDICATION)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument(
        "--residual-adjudication", type=Path, default=DEFAULT_RESIDUAL_ADJUDICATION
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out-dataset", type=Path, default=DEFAULT_DATASET_OUT)
    parser.add_argument("--out-decisions", type=Path, default=DEFAULT_DECISIONS_OUT)
    args = parser.parse_args(argv)

    dataset_records, decisions_fixture = build_fixtures(
        adjudication_path=args.adjudication,
        seeds_path=args.seeds,
        residual_adjudication_path=args.residual_adjudication,
        dataset_path=args.dataset,
    )

    args.out_dataset.parent.mkdir(parents=True, exist_ok=True)
    args.out_dataset.write_text(
        "\n".join(json.dumps(r) for r in dataset_records) + "\n"
    )
    args.out_decisions.write_text(json.dumps(decisions_fixture, indent=2) + "\n")

    n = len(dataset_records)
    print(
        f"OK: wrote {args.out_dataset} ({n} calibration case(s)) and "
        f"{args.out_decisions} (all makes_unsupported_claim=false under "
        f"{REPLAY_PROFILE!r})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
