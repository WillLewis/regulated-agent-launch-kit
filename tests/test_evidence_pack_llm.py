"""Tests for the LLM adversarial redacted evidence pack.

These tests cover three concerns:

1. The pack assembly itself: every required artifact lands in the
   right place, the manifest reflects them, no raw-trace path is
   shipped, and the README + manifest preserve the synthetic / no-
   readiness posture.
2. The redacted LLM traces: diagnostic top-level fields are preserved,
   raw ``draft_text`` / ``draft_excerpt`` / ``final_response`` values
   are replaced with the policy's placeholder, and identifier fields
   are removed.
3. The redacted JSON eval report (the candidate's summary): same
   abstraction rule — no raw draft text leaks through.

Every test in this module builds a fresh pack in ``tmp_path`` from
fixture inputs so the suite is robust to whether ``make
redact-llm-adversarial`` / ``make evidence-pack-llm-adversarial`` have
been run against the on-disk artifacts yet. The fixture creates
minimally-shaped raw inputs that exercise the same redaction codepath
the real run uses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.package_evidence_llm import (
    SYNTHETIC_DISCLAIMER,
    package_llm_evidence,
)
from scripts.redact_trace import redact


ROOT = Path(__file__).resolve().parents[1]
REDACTION_POLICY = ROOT / "configs" / "redaction_policy.yaml"


# ---------------------------------------------------------------------------
# Fixtures — synthetic inputs that match the script's expected shape
# ---------------------------------------------------------------------------


def _write(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=2))
    else:
        path.write_text(payload)
    return path


@pytest.fixture()
def synthetic_pack_inputs(tmp_path: Path) -> dict[str, Path]:
    """Build a complete set of inputs the pack script needs."""

    raw_report = {
        "version": "local_eval_v0",
        "synthetic": True,
        "agent_system_version": "llm_candidate_v0",
        "dataset_path": "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl",
        "case_count": 1,
        "passed_case_count": 0,
        "failed_case_count": 1,
        "aggregate_grader_pass_rates": [],
        "failure_label_counts": {"UNSAFE_CUSTOMER_COMMS": 1},
        "synthetic_latency_envelope": {},
        "synthetic_cost_summary": {"total_est_cost_usd": 0.0},
        "per_case": [
            {
                "case_id": "case_fl_adv_v0_002",
                "workflow": "financial_links_reliability",
                "risk_band": "L1",
                "trace_path": "traces/local/llm_adversarial/case_fl_adv_v0_002.json",
                "grader_results": [
                    {
                        "passed": False,
                        "score": 0.0,
                        "severity": "L2",
                        "failure_label": "UNSAFE_CUSTOMER_COMMS",
                        "explanation": "Draft contains unsupported-claim phrase(s).",
                        "evidence": {
                            "matched_patterns": ["is guaranteed"],
                            "draft_excerpt": (
                                "Your linked account is guaranteed to refresh "
                                "in real time — RAW MODEL OUTPUT THAT MUST BE "
                                "ABSTRACTED."
                            ),
                        },
                    }
                ],
                "failure_labels": ["UNSAFE_CUSTOMER_COMMS"],
                "passed": False,
                "latency_ms": 6500,
                "est_cost_usd": 0.0,
            }
        ],
    }
    raw_report_path = _write(tmp_path / "reports" / "llm_adversarial_eval.json", raw_report)

    reference_report = dict(raw_report)
    reference_report["agent_system_version"] = "improved_v0"
    reference_report["passed_case_count"] = 1
    reference_report["failed_case_count"] = 0
    reference_report["failure_label_counts"] = {}
    reference_report["per_case"] = []
    reference_report_path = _write(
        tmp_path / "reports" / "improved_adversarial_eval.json", reference_report
    )

    eval_card_path = _write(
        tmp_path / "reports" / "llm_adversarial_eval_card.md",
        "# Local Eval Card — Financial Links Vertical Slice\n\n"
        "> At least one profile compared here calls a real LLM via "
        "the credential-gated `llm_candidate_v0` path.\n",
    )

    regressions_path = _write(
        tmp_path / "case_studies" / "regressions_llm_v0.jsonl",
        json.dumps(
            {
                "regression_case_id": "case_fl_adv_v0_002__regression_v0",
                "source_agent_system_version": "llm_candidate_v0",
                "review_status": "pending_review",
                "failure_labels": ["UNSAFE_CUSTOMER_COMMS"],
            }
        )
        + "\n",
    )

    # Build a synthetic trace shape that mirrors what the policy
    # preserves / abstracts / removes.
    policy_data = yaml.safe_load(REDACTION_POLICY.read_text())
    synthetic_trace = {
        "trace_id": "trace_test_001",
        "dataset_id": "dummy",
        "case_id": "case_fl_adv_v0_002",
        "workflow": "financial_links_reliability",
        "risk_band": "L1",
        "agent_system_version": "llm_candidate_v0",
        "policy_version": "v0",
        "orchestrator_decision": {"to_agent": "FinancialLinksReliabilityAgent"},
        "specialist_path": ["FinancialLinksReliabilityAgent"],
        "handoff": {"from_node": "OrchestratorAgent"},
        "tool_calls": [],
        "evaluator_report": {"ok": True},
        "approval": {"required": False},
        "grader_results": [],
        "failure_labels": [],
        "latency_ms": 5000,
        "est_cost_usd": 0.0,
        # Fields the policy will redact:
        "user_id": "user_synth_002",
        "partner_id": "partner_synth_a",
        "institution_id": "inst_synth_b",
        "draft_text": "RAW DRAFT TEXT MUST BE ABSTRACTED",
        "final_response": "RAW FINAL RESPONSE MUST BE ABSTRACTED",
    }
    redacted_dir = tmp_path / "traces" / "redacted" / "llm_adversarial"
    for case_id in (
        "case_fl_adv_v0_001",
        "case_fl_adv_v0_002",
        "case_fl_adv_v0_003",
        "case_fl_adv_v0_004",
        "case_fl_adv_v0_005",
        "case_fl_adv_v0_006",
    ):
        per_case = dict(synthetic_trace)
        per_case["case_id"] = case_id
        per_case["trace_id"] = f"trace_test_{case_id}"
        redacted_trace, redaction_report = redact(per_case, policy_data)
        _write(redacted_dir / f"{case_id}.redacted.json", redacted_trace)
        _write(redacted_dir / f"{case_id}.redaction_report.json", redaction_report)

    return {
        "raw_report": raw_report_path,
        "eval_card": eval_card_path,
        "reference_report": reference_report_path,
        "regressions": regressions_path,
        "redacted_traces": redacted_dir,
        "policy": REDACTION_POLICY,
    }


@pytest.fixture()
def packed(tmp_path: Path, synthetic_pack_inputs: dict[str, Path]) -> Path:
    out = tmp_path / "evidence_packs" / "financial_links_llm_v0"
    package_llm_evidence(out=out, **synthetic_pack_inputs)
    return out


# ---------------------------------------------------------------------------
# Pack layout
# ---------------------------------------------------------------------------


REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "manifest.json",
    "eval_card.md",
    "reference_eval.json",
    "llm_candidate_eval.redacted.json",
    "llm_candidate_eval.redaction_report.json",
    "regressions_llm_v0.jsonl",
)


def test_pack_has_every_required_file(packed: Path) -> None:
    for rel in REQUIRED_FILES:
        assert (packed / rel).exists(), f"pack missing required file: {rel!r}"
    redacted_dir = packed / "traces" / "redacted"
    assert redacted_dir.is_dir()
    assert sorted(p.name for p in redacted_dir.glob("*.redacted.json")) == [
        f"case_fl_adv_v0_00{n}.redacted.json" for n in range(1, 7)
    ]
    assert sorted(p.name for p in redacted_dir.glob("*.redaction_report.json")) == [
        f"case_fl_adv_v0_00{n}.redaction_report.json" for n in range(1, 7)
    ]


def test_pack_manifest_indexes_every_required_file(packed: Path) -> None:
    manifest = json.loads((packed / "manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert manifest["disclaimer"] == SYNTHETIC_DISCLAIMER
    paths = {entry["path"] for entry in manifest["files"]}
    # manifest.json is the manifest itself; it's not expected to list
    # itself. Every other required file must be present.
    for rel in REQUIRED_FILES:
        if rel == "manifest.json":
            continue
        assert rel in paths, f"manifest missing entry for {rel!r}"
    # All redacted-trace paths must be under traces/redacted/.
    for entry in manifest["files"]:
        path = entry["path"]
        if path.endswith(".redacted.json") and path != "llm_candidate_eval.redacted.json":
            assert path.startswith("traces/redacted/")


def test_pack_contains_no_raw_trace_paths(packed: Path) -> None:
    """The defining invariant of the pack — no raw trace path may
    appear under any file or any manifest entry."""

    for path in packed.rglob("*"):
        rel = path.relative_to(packed).as_posix()
        assert "traces/local/" not in rel, (
            f"raw-trace path leaked into pack: {rel}"
        )

    manifest = json.loads((packed / "manifest.json").read_text())
    for entry in manifest["files"]:
        assert "traces/local/" not in entry["path"]


def test_pack_readme_keeps_synthetic_and_not_ready_posture(packed: Path) -> None:
    readme = (packed / "README.md").read_text()
    lower = readme.lower()
    assert SYNTHETIC_DISCLAIMER in readme
    assert "not ready for pilot" in lower
    # Narrow positive-claim guard (mirrors tests/test_evidence_pack.py).
    # Phrases like "regulatory compliance" / "production readiness" are
    # NOT in this list because the disclaimer itself uses them in the
    # phrase "Nothing in this pack implies production readiness or
    # regulatory compliance" — i.e. a *negation*.
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"LLM pack README must not claim {phrase!r}"


def test_pack_refuses_to_ship_raw_trace_input(
    tmp_path: Path, synthetic_pack_inputs: dict[str, Path]
) -> None:
    """If a caller mis-wires the script to point at traces/local/...,
    the script must refuse rather than silently shipping raw payloads."""

    bad_dir = tmp_path / "traces" / "local" / "llm_adversarial"
    bad_dir.mkdir(parents=True)
    # Copy one redacted file into the bad location and rename to make
    # it look like a redacted trace. This simulates an analyst pointing
    # the script at the wrong directory.
    src = next((synthetic_pack_inputs["redacted_traces"]).glob("*.redacted.json"))
    (bad_dir / src.name).write_text(src.read_text())

    args = dict(synthetic_pack_inputs)
    args["redacted_traces"] = bad_dir
    out = tmp_path / "bad_pack"
    with pytest.raises(SystemExit) as exc:
        package_llm_evidence(out=out, **args)
    assert "raw-LLM trace dir" in str(exc.value)


# ---------------------------------------------------------------------------
# Redacted candidate report
# ---------------------------------------------------------------------------


def test_redacted_candidate_eval_has_no_raw_draft_text(packed: Path) -> None:
    candidate = json.loads(
        (packed / "llm_candidate_eval.redacted.json").read_text()
    )
    for case in candidate["per_case"]:
        for grader in case.get("grader_results", []):
            excerpt = grader.get("evidence", {}).get("draft_excerpt")
            if excerpt is None:
                continue
            # The redaction policy abstracts draft_excerpt to a fixed
            # placeholder. Raw model output must never appear.
            assert excerpt == "<draft_text_abstracted>", (
                f"raw draft_excerpt leaked into redacted candidate eval: "
                f"case={case['case_id']!r} excerpt={excerpt!r}"
            )
            assert "RAW MODEL OUTPUT" not in excerpt


def test_redaction_report_lists_abstracted_draft_excerpt(packed: Path) -> None:
    report = json.loads(
        (packed / "llm_candidate_eval.redaction_report.json").read_text()
    )
    abstracted = report["abstracted_paths"]
    assert any("draft_excerpt" in path for path in abstracted), (
        "redaction report must record that draft_excerpt was abstracted; "
        f"abstracted_paths={abstracted}"
    )


# ---------------------------------------------------------------------------
# Redacted traces
# ---------------------------------------------------------------------------


_DIAGNOSTIC_FIELDS: tuple[str, ...] = (
    "trace_id",
    "dataset_id",
    "case_id",
    "workflow",
    "risk_band",
    "agent_system_version",
    "policy_version",
    "orchestrator_decision",
    "specialist_path",
    "handoff",
    "tool_calls",
    "evaluator_report",
    "approval",
    "grader_results",
    "failure_labels",
    "latency_ms",
    "est_cost_usd",
)


def test_redacted_traces_preserve_diagnostic_fields(packed: Path) -> None:
    for trace_path in (packed / "traces" / "redacted").glob("*.redacted.json"):
        trace = json.loads(trace_path.read_text())
        for field in _DIAGNOSTIC_FIELDS:
            assert field in trace, (
                f"{trace_path.name}: redacted trace missing diagnostic field "
                f"{field!r}; the analyst can't read the trace alongside the "
                "card without it"
            )


def test_redacted_traces_abstract_draft_text_and_final_response(packed: Path) -> None:
    placeholder = "<draft_text_abstracted>"
    for trace_path in (packed / "traces" / "redacted").glob("*.redacted.json"):
        trace = json.loads(trace_path.read_text())
        # Both fields were present in the fixture trace; both should now
        # be the policy placeholder, not raw model output.
        assert trace.get("draft_text") == placeholder
        assert trace.get("final_response") == placeholder


def test_redacted_traces_remove_identifier_fields(packed: Path) -> None:
    for trace_path in (packed / "traces" / "redacted").glob("*.redacted.json"):
        trace = json.loads(trace_path.read_text())
        for forbidden in ("user_id", "partner_id", "institution_id"):
            assert forbidden not in trace, (
                f"{trace_path.name}: redacted trace still carries identifier "
                f"field {forbidden!r}"
            )
