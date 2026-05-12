"""Tests for the public-safe evidence packager."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from evals.run import run_eval
from scripts.generate_eval_card import generate_eval_card
from scripts.package_evidence import EVIDENCE_PACK_VERSION, package
from scripts.redact_trace import redact


ROOT = Path(__file__).resolve().parents[1]
FULL_V0_PATH = ROOT / "case_studies" / "financial_links_reliability" / "data" / "cases_v0.jsonl"
COMMITTED_REGRESSIONS = (
    ROOT / "case_studies" / "financial_links_reliability" / "evals" / "regressions_v0.jsonl"
)
POLICY_PATH = ROOT / "configs" / "redaction_policy.yaml"
PACKAGE_SCRIPT = ROOT / "scripts" / "package_evidence.py"


@pytest.fixture(scope="module")
def assembled_pack(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    """Build a complete evidence pack from a fresh local eval run."""

    work = tmp_path_factory.mktemp("evidence_pack")
    baseline_dir = work / "traces_baseline"
    improved_dir = work / "traces_improved"

    baseline_report = work / "baseline.json"
    improved_report = work / "improved.json"

    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=baseline_dir,
        report_out=baseline_report,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=FULL_V0_PATH,
        traces_out=improved_dir,
        report_out=improved_report,
        agent_system_version="improved_v0",
    )

    card = work / "card.md"
    generate_eval_card(
        baseline_report=baseline_report,
        improved_report=improved_report,
        out=card,
        regressions=COMMITTED_REGRESSIONS,
    )

    redacted_dir = work / "redacted"
    redacted_dir.mkdir()
    import yaml
    policy = yaml.safe_load(POLICY_PATH.read_text())
    for case_id in ("case_fl_v0_005", "case_fl_v0_006", "case_fl_v0_010"):
        raw = json.loads((baseline_dir / f"{case_id}.json").read_text())
        redacted, report = redact(raw, policy)
        (redacted_dir / f"{case_id}.redacted.json").write_text(json.dumps(redacted, indent=2))
        (redacted_dir / f"{case_id}.redaction_report.json").write_text(json.dumps(report, indent=2))

    pack_out = work / "pack"
    package(
        eval_card=card,
        baseline_report=baseline_report,
        improved_report=improved_report,
        regressions=COMMITTED_REGRESSIONS,
        redacted_traces=redacted_dir,
        out=pack_out,
    )

    manifest = json.loads((pack_out / "manifest.json").read_text())
    return pack_out, manifest


def test_pack_directory_contains_core_artifacts(
    assembled_pack: tuple[Path, dict[str, Any]],
) -> None:
    pack, _ = assembled_pack
    for expected in (
        "README.md",
        "manifest.json",
        "eval_card.md",
        "baseline_eval.json",
        "improved_eval.json",
        "regressions.jsonl",
    ):
        assert (pack / expected).exists(), f"pack missing {expected!r}"


def test_manifest_lists_expected_artifacts(
    assembled_pack: tuple[Path, dict[str, Any]],
) -> None:
    _, manifest = assembled_pack
    assert manifest["version"] == EVIDENCE_PACK_VERSION
    assert manifest["synthetic"] is True
    paths = [entry["path"] for entry in manifest["files"]]
    for expected in (
        "README.md",
        "eval_card.md",
        "baseline_eval.json",
        "improved_eval.json",
        "regressions.jsonl",
    ):
        assert expected in paths, f"manifest missing {expected!r}"
    # at least one redacted trace path
    assert any(p.startswith("traces/redacted/") and p.endswith(".redacted.json") for p in paths)


def test_manifest_has_no_raw_trace_paths(
    assembled_pack: tuple[Path, dict[str, Any]],
) -> None:
    pack, manifest = assembled_pack
    for entry in manifest["files"]:
        rel = entry["path"]
        assert not rel.startswith("traces/local/"), entry
        assert ".redacted" in rel or "redaction_report" in rel or "/redacted/" not in rel, entry

    # belt-and-braces: walk the directory and confirm nothing under
    # traces/local/ exists in the pack root.
    for path in pack.rglob("*"):
        if path.is_file():
            relative = path.relative_to(pack).as_posix()
            assert not relative.startswith("traces/local/"), relative


def test_readme_includes_synthetic_only_language(
    assembled_pack: tuple[Path, dict[str, Any]],
) -> None:
    pack, _ = assembled_pack
    readme = (pack / "README.md").read_text()
    lower = readme.lower()
    assert "synthetic" in lower
    assert "public-safe" in lower or "public safe" in lower
    # narrow positive-claim guard (same shape as the eval-card test)
    for phrase in ("production ready", "production-ready", "pilot ready", "pilot-ready"):
        assert phrase not in lower, f"evidence-pack README must not claim {phrase!r}"


def test_redacted_traces_are_actually_redacted(
    assembled_pack: tuple[Path, dict[str, Any]],
) -> None:
    pack, _ = assembled_pack
    redacted_paths = list((pack / "traces" / "redacted").glob("*.redacted.json"))
    assert redacted_paths
    for path in redacted_paths:
        data = json.loads(path.read_text())
        # core diagnostic fields preserved
        for required in ("case_id", "workflow", "tool_calls", "evaluator_report", "approval"):
            assert required in data, (path, required)
        # raw IDs scrubbed
        for tool_call in data["tool_calls"]:
            for forbidden in ("user_id", "institution_id", "partner_id"):
                assert forbidden not in tool_call["arguments"], path
        # draft abstracted
        assert data.get("final_response") == "<draft_text_abstracted>"


def test_redaction_reports_present_for_every_redacted_trace(
    assembled_pack: tuple[Path, dict[str, Any]],
) -> None:
    pack, _ = assembled_pack
    redacted = sorted((pack / "traces" / "redacted").glob("*.redacted.json"))
    reports = sorted((pack / "traces" / "redacted").glob("*.redaction_report.json"))
    assert len(redacted) == len(reports)
    redacted_stems = {p.name.removesuffix(".redacted.json") for p in redacted}
    report_stems = {p.name.removesuffix(".redaction_report.json") for p in reports}
    assert redacted_stems == report_stems


# ---------------------------------------------------------------------------
# Missing input rejection
# ---------------------------------------------------------------------------

def test_package_rejects_missing_eval_card(tmp_path: Path) -> None:
    redacted_dir = tmp_path / "redacted"
    redacted_dir.mkdir()
    (redacted_dir / "case_fl_v0_005.redacted.json").write_text("{}")

    result = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_SCRIPT),
            "--eval-card",
            str(tmp_path / "missing.md"),
            "--baseline-report",
            str(tmp_path / "missing_baseline.json"),
            "--improved-report",
            str(tmp_path / "missing_improved.json"),
            "--regressions",
            str(COMMITTED_REGRESSIONS),
            "--redacted-traces",
            str(redacted_dir),
            "--out",
            str(tmp_path / "pack"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "eval-card not found" in result.stderr


def test_package_rejects_empty_redacted_dir(tmp_path: Path) -> None:
    redacted_dir = tmp_path / "redacted"
    redacted_dir.mkdir()  # exists but no *.redacted.json files

    card = tmp_path / "card.md"
    card.write_text("# Card")
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{}")
    improved = tmp_path / "improved.json"
    improved.write_text("{}")

    result = subprocess.run(
        [
            sys.executable,
            str(PACKAGE_SCRIPT),
            "--eval-card",
            str(card),
            "--baseline-report",
            str(baseline),
            "--improved-report",
            str(improved),
            "--regressions",
            str(COMMITTED_REGRESSIONS),
            "--redacted-traces",
            str(redacted_dir),
            "--out",
            str(tmp_path / "pack"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "no *.redacted.json files" in result.stderr
