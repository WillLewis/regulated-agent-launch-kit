"""Tests for the v1 prompt-improvement evidence pack.

The pack at ``evidence_packs/financial_links_llm_v1/`` is the public-
safe view of the credentialed v0 → v1 prompt-improvement loop. Like
the v0 pack, it must redact raw model output from both the v1 trace
JSONs AND the v1 / v0 eval reports, and must refuse to ship any path
under ``traces/local/``.

These tests cover:

1. The pack assembler runs end-to-end against synthetic in-memory
   inputs and emits every required artifact + a manifest entry per
   file.
2. No file in the pack and no manifest path begins with
   ``traces/local/``.
3. The redacted v1 trace artifacts preserve diagnostic top-level
   fields and abstract / remove raw drafts and identifiers per the
   committed redaction policy.
4. Both the v0 and v1 redacted summary reports have raw
   ``draft_excerpt`` content abstracted to the policy placeholder.
5. The pack README keeps the synthetic / NOT READY FOR PILOT posture
   and avoids positive readiness claims.
6. The assembler refuses inputs that would route raw-trace paths into
   the pack (defense-in-depth).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.package_evidence_llm_v1 import (
    SYNTHETIC_DISCLAIMER,
    package_llm_v1_evidence,
)
from scripts.redact_trace import redact


ROOT = Path(__file__).resolve().parents[1]
REDACTION_POLICY = ROOT / "configs" / "redaction_policy.yaml"


def _write(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, indent=2))
    else:
        path.write_text(payload)
    return path


def _synthetic_eval_report(profile: str, fail: bool) -> dict:
    grader_results = []
    if fail:
        grader_results.append(
            {
                "passed": False,
                "score": 0.0,
                "severity": "L2",
                "failure_label": "UNSAFE_CUSTOMER_COMMS",
                "explanation": "Draft contains unsupported-claim phrase(s).",
                "evidence": {
                    "matched_patterns": ["is guaranteed"],
                    "draft_excerpt": (
                        "RAW MODEL OUTPUT FROM " + profile + " THAT MUST BE ABSTRACTED."
                    ),
                },
            }
        )
    return {
        "version": "local_eval_v0",
        "synthetic": True,
        "agent_system_version": profile,
        "dataset_path": "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl",
        "case_count": 1,
        "passed_case_count": 0 if fail else 1,
        "failed_case_count": 1 if fail else 0,
        "aggregate_grader_pass_rates": [],
        "failure_label_counts": {"UNSAFE_CUSTOMER_COMMS": 1} if fail else {},
        "synthetic_latency_envelope": {},
        "synthetic_cost_summary": {"total_est_cost_usd": 0.001},
        "per_case": [
            {
                "case_id": "case_fl_adv_v0_002",
                "workflow": "financial_links_reliability",
                "risk_band": "L1",
                "trace_path": "traces/local/llm_adversarial_v1/case_fl_adv_v0_002.json",
                "grader_results": grader_results,
                "failure_labels": ["UNSAFE_CUSTOMER_COMMS"] if fail else [],
                "passed": not fail,
                "latency_ms": 6500,
                "est_cost_usd": 0.001,
            }
        ],
    }


@pytest.fixture()
def synthetic_v1_pack_inputs(tmp_path: Path) -> dict[str, Path]:
    raw_v0 = _synthetic_eval_report("llm_candidate_v0", fail=True)
    raw_v0_path = _write(tmp_path / "reports" / "llm_adversarial_eval.json", raw_v0)
    raw_v1 = _synthetic_eval_report("llm_candidate_v1", fail=False)
    raw_v1_path = _write(
        tmp_path / "reports" / "llm_adversarial_v1_eval.json", raw_v1
    )

    eval_card_path = _write(
        tmp_path / "reports" / "llm_adversarial_v1_vs_v0_card.md",
        "# Local Eval Card — Financial Links Vertical Slice\n\n"
        "> Comparison card: llm_candidate_v0 (Before) vs llm_candidate_v1 (After).\n",
    )

    memo_path = _write(
        tmp_path / "reports" / "llm_prompt_improvement_memo.md",
        "# LLM Prompt-Improvement Memo\n\nSynthetic improvement memo.\n",
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

    policy_data = yaml.safe_load(REDACTION_POLICY.read_text())
    synthetic_trace = {
        "trace_id": "trace_test_001",
        "dataset_id": "dummy",
        "case_id": "case_fl_adv_v0_002",
        "workflow": "financial_links_reliability",
        "risk_band": "L1",
        "agent_system_version": "llm_candidate_v1",
        "policy_version": "v0",
        "orchestrator_decision": {"to_agent": "FinancialLinksReliabilityAgent"},
        "specialist_path": ["FinancialLinksReliabilityAgent"],
        "handoff": {"from_node": "OrchestratorAgent"},
        "tool_calls": [],
        "evaluator_report": {"ok": True},
        "approval": {"required": False},
        "grader_results": [],
        "failure_labels": [],
        "latency_ms": 9500,
        "est_cost_usd": 0.005,
        "user_id": "user_synth_002",
        "partner_id": "partner_synth_a",
        "institution_id": "inst_synth_b",
        "draft_text": "RAW V1 DRAFT TEXT MUST BE ABSTRACTED",
        "final_response": "RAW V1 FINAL RESPONSE MUST BE ABSTRACTED",
    }
    redacted_dir = tmp_path / "traces" / "redacted" / "llm_adversarial_v1"
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
        "raw_v0_report": raw_v0_path,
        "raw_v1_report": raw_v1_path,
        "eval_card": eval_card_path,
        "regressions": regressions_path,
        "redacted_traces": redacted_dir,
        "policy": REDACTION_POLICY,
        "improvement_memo": memo_path,
    }


@pytest.fixture()
def packed(tmp_path: Path, synthetic_v1_pack_inputs: dict[str, Path]) -> Path:
    out = tmp_path / "evidence_packs" / "financial_links_llm_v1"
    package_llm_v1_evidence(out=out, **synthetic_v1_pack_inputs)
    return out


REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "manifest.json",
    "eval_card.md",
    "improvement_memo.md",
    "llm_candidate_v0_eval.redacted.json",
    "llm_candidate_v0_eval.redaction_report.json",
    "llm_candidate_v1_eval.redacted.json",
    "llm_candidate_v1_eval.redaction_report.json",
    "regressions_llm_v0.jsonl",
)


# ---------------------------------------------------------------------------
# Pack layout
# ---------------------------------------------------------------------------


def test_v1_pack_has_every_required_file(packed: Path) -> None:
    for rel in REQUIRED_FILES:
        assert (packed / rel).exists(), f"v1 pack missing {rel!r}"
    redacted_dir = packed / "traces" / "redacted"
    assert sorted(p.name for p in redacted_dir.glob("*.redacted.json")) == [
        f"case_fl_adv_v0_00{n}.redacted.json" for n in range(1, 7)
    ]
    assert sorted(p.name for p in redacted_dir.glob("*.redaction_report.json")) == [
        f"case_fl_adv_v0_00{n}.redaction_report.json" for n in range(1, 7)
    ]


def test_v1_pack_manifest_indexes_required_files(packed: Path) -> None:
    manifest = json.loads((packed / "manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert manifest["disclaimer"] == SYNTHETIC_DISCLAIMER
    paths = {entry["path"] for entry in manifest["files"]}
    for rel in REQUIRED_FILES:
        if rel == "manifest.json":
            continue
        assert rel in paths, f"manifest missing entry for {rel!r}"


def test_v1_pack_has_no_raw_local_trace_paths(packed: Path) -> None:
    for path in packed.rglob("*"):
        rel = path.relative_to(packed).as_posix()
        assert "traces/local/" not in rel, (
            f"raw-trace path leaked into v1 pack: {rel}"
        )
    manifest = json.loads((packed / "manifest.json").read_text())
    for entry in manifest["files"]:
        assert "traces/local/" not in entry["path"]


def test_v1_pack_readme_keeps_synthetic_and_not_ready_posture(packed: Path) -> None:
    readme = (packed / "README.md").read_text()
    lower = readme.lower()
    assert SYNTHETIC_DISCLAIMER in readme
    assert "not ready for pilot" in lower
    forbidden = (
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
    )
    for phrase in forbidden:
        assert phrase not in lower, f"v1 pack README must not claim {phrase!r}"


def test_v1_pack_refuses_raw_trace_input(
    tmp_path: Path, synthetic_v1_pack_inputs: dict[str, Path]
) -> None:
    bad_dir = tmp_path / "traces" / "local" / "llm_adversarial_v1"
    bad_dir.mkdir(parents=True)
    src = next((synthetic_v1_pack_inputs["redacted_traces"]).glob("*.redacted.json"))
    (bad_dir / src.name).write_text(src.read_text())

    args = dict(synthetic_v1_pack_inputs)
    args["redacted_traces"] = bad_dir
    out = tmp_path / "bad_pack"
    with pytest.raises(SystemExit) as exc:
        package_llm_v1_evidence(out=out, **args)
    assert "raw-LLM trace dir" in str(exc.value)


# ---------------------------------------------------------------------------
# Redacted summary reports
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel",
    [
        "llm_candidate_v0_eval.redacted.json",
        "llm_candidate_v1_eval.redacted.json",
    ],
)
def test_redacted_eval_summaries_have_no_raw_draft_text(packed: Path, rel: str) -> None:
    payload = json.loads((packed / rel).read_text())
    for case in payload["per_case"]:
        for grader in case.get("grader_results", []):
            excerpt = grader.get("evidence", {}).get("draft_excerpt")
            if excerpt is None:
                continue
            assert excerpt == "<draft_text_abstracted>", (
                f"{rel}: raw draft_excerpt leaked: {excerpt!r}"
            )
            assert "RAW MODEL OUTPUT" not in excerpt


# ---------------------------------------------------------------------------
# Redacted v1 traces
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


def test_redacted_v1_traces_preserve_diagnostic_fields(packed: Path) -> None:
    for trace_path in (packed / "traces" / "redacted").glob("*.redacted.json"):
        trace = json.loads(trace_path.read_text())
        for field in _DIAGNOSTIC_FIELDS:
            assert field in trace, (
                f"{trace_path.name}: redacted trace missing diagnostic field "
                f"{field!r}"
            )


def test_redacted_v1_traces_abstract_drafts_and_remove_ids(packed: Path) -> None:
    placeholder = "<draft_text_abstracted>"
    for trace_path in (packed / "traces" / "redacted").glob("*.redacted.json"):
        trace = json.loads(trace_path.read_text())
        assert trace.get("draft_text") == placeholder
        assert trace.get("final_response") == placeholder
        for forbidden in ("user_id", "partner_id", "institution_id"):
            assert forbidden not in trace, (
                f"{trace_path.name}: identifier {forbidden!r} not removed"
            )


# ---------------------------------------------------------------------------
# Committed v1 pack on disk (when present)
# ---------------------------------------------------------------------------


COMMITTED_V1_PACK = ROOT / "evidence_packs" / "financial_links_llm_v1"


def test_committed_v1_pack_has_no_raw_trace_paths_if_present() -> None:
    """If the v1 pack has been built locally, scan it for raw-trace
    leaks. Skipped silently when the pack hasn't been built yet — the
    Make target produces it."""

    if not COMMITTED_V1_PACK.exists():
        pytest.skip("v1 pack not built locally; run `make evidence-pack-llm-adversarial-v1`")
    for path in COMMITTED_V1_PACK.rglob("*"):
        rel = path.relative_to(COMMITTED_V1_PACK).as_posix()
        assert "traces/local/" not in rel, f"raw-trace path leak: {rel}"


# ---------------------------------------------------------------------------
# Optional repeat-run summary integration
# ---------------------------------------------------------------------------


def _write_public_safe_summary(dirpath: Path) -> tuple[Path, Path]:
    dirpath.mkdir(parents=True, exist_ok=True)
    md = dirpath / "summary.md"
    md.write_text(
        "# LLM Repeat-Run Variance Summary\n\n"
        "> Synthetic local eval runs only. NOT READY FOR PILOT.\n\n"
        "## Pass / fail variance\n\n"
        "| Metric | Per-run sequence |\n"
        "|---|---|\n"
        "| Passed | [5, 6] |\n"
        "| Failed | [1, 0] |\n\n"
        "**NOT READY FOR PILOT — synthetic slice.**\n"
    )
    js = dirpath / "summary.json"
    js.write_text(
        json.dumps(
            {
                "version": "llm_repeat_summary_v0",
                "synthetic": True,
                "not_ready_for_pilot": True,
                "run_count": 2,
                "profile_family": ["llm_candidate_v0"],
                "pass_per_run": [5, 6],
            },
            indent=2,
        )
    )
    return md, js


def test_v1_pack_with_repeat_summary_indexes_and_ships_files(
    tmp_path: Path, synthetic_v1_pack_inputs: dict[str, Path]
) -> None:
    md, js = _write_public_safe_summary(tmp_path / "summary_inputs")
    out = tmp_path / "pack_with_repeats"
    package_llm_v1_evidence(
        out=out,
        repeat_summary_md=md,
        repeat_summary_json=js,
        **synthetic_v1_pack_inputs,
    )
    assert (out / "repeat_run_summary.md").exists()
    assert (out / "repeat_run_summary.json").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    paths = {entry["path"] for entry in manifest["files"]}
    assert "repeat_run_summary.md" in paths
    assert "repeat_run_summary.json" in paths


def test_v1_pack_refuses_repeat_summary_md_with_raw_paths(
    tmp_path: Path, synthetic_v1_pack_inputs: dict[str, Path]
) -> None:
    md, js = _write_public_safe_summary(tmp_path / "summary_inputs")
    md.write_text(md.read_text() + "\nleaked: traces/local/llm_adversarial/foo.json\n")
    out = tmp_path / "pack_leak"
    with pytest.raises(SystemExit) as exc:
        package_llm_v1_evidence(
            out=out,
            repeat_summary_md=md,
            repeat_summary_json=js,
            **synthetic_v1_pack_inputs,
        )
    assert "traces/local/llm_" in str(exc.value)


def test_v1_pack_refuses_repeat_summary_md_without_not_ready_for_pilot(
    tmp_path: Path, synthetic_v1_pack_inputs: dict[str, Path]
) -> None:
    md, js = _write_public_safe_summary(tmp_path / "summary_inputs")
    md.write_text("# repeat summary\n\n(no posture line)\n")
    out = tmp_path / "pack_no_posture"
    with pytest.raises(SystemExit) as exc:
        package_llm_v1_evidence(
            out=out,
            repeat_summary_md=md,
            repeat_summary_json=js,
            **synthetic_v1_pack_inputs,
        )
    assert "NOT READY FOR PILOT" in str(exc.value)


def test_v1_pack_refuses_repeat_summary_json_without_not_ready_flag(
    tmp_path: Path, synthetic_v1_pack_inputs: dict[str, Path]
) -> None:
    md, js = _write_public_safe_summary(tmp_path / "summary_inputs")
    payload = json.loads(js.read_text())
    payload["not_ready_for_pilot"] = False
    js.write_text(json.dumps(payload, indent=2))
    out = tmp_path / "pack_bad_json"
    with pytest.raises(SystemExit) as exc:
        package_llm_v1_evidence(
            out=out,
            repeat_summary_md=md,
            repeat_summary_json=js,
            **synthetic_v1_pack_inputs,
        )
    assert "not_ready_for_pilot" in str(exc.value)
