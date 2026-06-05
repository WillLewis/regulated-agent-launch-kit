"""Tests for the fixture-backed semantic HTML reporting surface."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.run import run_eval
from scripts.render_semantic_reporting_surface import (
    MODEL_SEMANTIC_ADAPTER,
    SEMANTIC_GRADER_NAME,
    render_reporting_surface,
)


ROOT = Path(__file__).resolve().parents[1]
ADVERSARIAL_V1 = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v1.jsonl"
)
SEMANTIC_DECISIONS = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v1_semantic_decisions.json"
)
RENDER_SCRIPT = ROOT / "scripts" / "render_semantic_reporting_surface.py"


@pytest.fixture()
def semantic_reports(tmp_path: Path) -> tuple[Path, Path]:
    baseline = tmp_path / "baseline.json"
    improved = tmp_path / "improved.json"
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline,
        agent_system_version="baseline_v0",
        semantic_decisions_path=SEMANTIC_DECISIONS,
    )
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "improved_traces",
        report_out=improved,
        agent_system_version="improved_v0",
        semantic_decisions_path=SEMANTIC_DECISIONS,
    )
    return baseline, improved


def test_render_reporting_surface_contains_required_sections(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        out=out,
    )

    html = out.read_text()
    assert "Fixture-Backed Semantic Reporting Surface" in html
    assert "Semantic Unsupported-Claim Lane" in html
    assert SEMANTIC_GRADER_NAME in html
    assert "NOT READY FOR PILOT" in html
    assert "semantic_fixture" in html


def test_model_backed_reporting_surface_uses_model_copy(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    baseline_decisions = tmp_path / "baseline_decisions.json"
    improved_decisions = tmp_path / "improved_decisions.json"
    baseline_decisions.write_text(
        json.dumps(
            {
                "adapter": MODEL_SEMANTIC_ADAPTER,
                "profile": "baseline_v0",
                "summary": {"total_est_cost_usd": 0.06},
            }
        )
    )
    improved_decisions.write_text(
        json.dumps(
            {
                "adapter": MODEL_SEMANTIC_ADAPTER,
                "profile": "improved_v0",
                "summary": {"total_est_cost_usd": 0.05},
            }
        )
    )
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        baseline_decisions_path=baseline_decisions,
        improved_decisions_path=improved_decisions,
        out=out,
    )

    html = out.read_text()
    assert "Model/NLI Semantic Reporting Surface" in html
    assert MODEL_SEMANTIC_ADAPTER in html
    assert "model/NLI" in html
    assert "est. decision cost $0.110000" in html
    # Model/NLI mode must label itself an audit experiment, not a fixture lane.
    assert "audit experiment" in html
    assert "no model call" not in html
    assert "Semantic fixture" not in html
    assert "Fixture-Backed Semantic Reporting Surface" not in html


def test_render_reporting_surface_shows_case_level_adversarial_v1_evidence(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        out=out,
    )

    html = out.read_text()
    assert "case_fl_adv_v1_001" in html
    assert "case_fl_adv_v1_008" in html
    assert "paraphrased_overpromise" in html
    assert "cross_sentence_disclaimer_trap" in html
    assert "affirmative_overpromise" in html


def test_render_reporting_surface_is_public_safe(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        out=out,
    )

    lowered = out.read_text().lower()
    assert "traces/local/llm_" not in lowered
    assert "reports/llm_repeats/" not in lowered
    forbidden_phrases = [
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "regulatory compliant",
        "regulatory-compliant",
        "model safety claim",
    ]
    assert not any(phrase in lowered for phrase in forbidden_phrases)


def test_renderer_rejects_reports_without_semantic_lane(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    improved = tmp_path / "improved.json"
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "baseline_traces",
        report_out=baseline,
        agent_system_version="baseline_v0",
    )
    run_eval(
        dataset_path=ADVERSARIAL_V1,
        traces_out=tmp_path / "improved_traces",
        report_out=improved,
        agent_system_version="improved_v0",
    )

    with pytest.raises(SystemExit) as exc:
        render_reporting_surface(
            dataset_path=ADVERSARIAL_V1,
            baseline_report_path=baseline,
            improved_report_path=improved,
            out=tmp_path / "surface.html",
        )
    assert "does not include 'unsupported_claim_semantic'" in str(exc.value)


def test_renderer_cli_writes_html(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    result = subprocess.run(
        [
            sys.executable,
            str(RENDER_SCRIPT),
            "--dataset",
            str(ADVERSARIAL_V1),
            "--baseline-report",
            str(baseline),
            "--improved-report",
            str(improved),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "OK: wrote semantic reporting surface" in result.stdout
    assert out.exists()
    assert "Fixture-Backed Semantic Reporting Surface" in out.read_text()


def test_renderer_requires_both_decision_files_for_model_mode(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    baseline_decisions = tmp_path / "baseline_decisions.json"
    baseline_decisions.write_text(
        json.dumps({"adapter": MODEL_SEMANTIC_ADAPTER, "profile": "baseline_v0"})
    )

    with pytest.raises(SystemExit) as exc:
        render_reporting_surface(
            dataset_path=ADVERSARIAL_V1,
            baseline_report_path=baseline,
            improved_report_path=improved,
            baseline_decisions_path=baseline_decisions,
            out=tmp_path / "surface.html",
        )
    assert "pass both --baseline-decisions and --improved-decisions" in str(exc.value)


def _write_model_decisions(
    path: Path,
    *,
    adapter: str = MODEL_SEMANTIC_ADAPTER,
    profile: str,
    cost: float = 0.0,
) -> Path:
    path.write_text(
        json.dumps(
            {
                "adapter": adapter,
                "profile": profile,
                "summary": {"total_est_cost_usd": cost},
            }
        )
    )
    return path


def test_model_mode_rejects_wrong_adapter(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports

    with pytest.raises(SystemExit) as exc:
        render_reporting_surface(
            dataset_path=ADVERSARIAL_V1,
            baseline_report_path=baseline,
            improved_report_path=improved,
            baseline_decisions_path=_write_model_decisions(
                tmp_path / "baseline_decisions.json",
                adapter="some_other_adapter",
                profile="baseline_v0",
            ),
            improved_decisions_path=_write_model_decisions(
                tmp_path / "improved_decisions.json",
                profile="improved_v0",
            ),
            out=tmp_path / "surface.html",
        )
    message = str(exc.value)
    assert "must declare adapter" in message
    assert MODEL_SEMANTIC_ADAPTER in message


def test_model_mode_rejects_profile_mismatch(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports

    with pytest.raises(SystemExit) as exc:
        render_reporting_surface(
            dataset_path=ADVERSARIAL_V1,
            baseline_report_path=baseline,
            improved_report_path=improved,
            # Correct adapter, but the baseline decision file claims the
            # improved profile, so it must not validate against the report.
            baseline_decisions_path=_write_model_decisions(
                tmp_path / "baseline_decisions.json",
                profile="improved_v0",
            ),
            improved_decisions_path=_write_model_decisions(
                tmp_path / "improved_decisions.json",
                profile="improved_v0",
            ),
            out=tmp_path / "surface.html",
        )
    assert "does not match report profile" in str(exc.value)


def test_model_backed_reporting_surface_is_public_safe(
    tmp_path: Path,
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    out = tmp_path / "surface.html"

    render_reporting_surface(
        dataset_path=ADVERSARIAL_V1,
        baseline_report_path=baseline,
        improved_report_path=improved,
        baseline_decisions_path=_write_model_decisions(
            tmp_path / "baseline_decisions.json",
            profile="baseline_v0",
            cost=0.06,
        ),
        improved_decisions_path=_write_model_decisions(
            tmp_path / "improved_decisions.json",
            profile="improved_v0",
            cost=0.05,
        ),
        out=out,
    )

    html = out.read_text()
    assert "audit experiment" in html
    assert "NOT READY FOR PILOT" in html
    lowered = html.lower()
    forbidden_phrases = [
        "production ready",
        "production-ready",
        "pilot ready",
        "pilot-ready",
        "regulatory compliant",
        "regulatory-compliant",
        "model safety claim",
    ]
    assert not any(phrase in lowered for phrase in forbidden_phrases)


def _makefile_target_block(makefile: str, target: str) -> str:
    """Return the recipe block for a single Makefile target.

    The block runs from the ``target:`` header line through the indented
    recipe lines, stopping at the next blank line or non-indented line. This
    lets a test assert on one target's wiring instead of substring-matching
    the whole file, which would conflate the fixture and model/NLI targets.
    """

    lines = makefile.splitlines()
    header = f"{target}:"
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(header)),
        None,
    )
    assert start is not None, f"Makefile target {target!r} not found"
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if not line.strip() or not line[0].isspace():
            break
        block.append(line)
    return "\n".join(block)


def test_makefile_fixture_target_renders_tracked_html_without_decisions() -> None:
    block = _makefile_target_block(
        (ROOT / "Makefile").read_text(), "semantic-reporting-surface"
    )
    assert "scripts/render_semantic_reporting_surface.py" in block
    assert "--out reports/adversarial_v1_semantic_reporting_surface.html" in block
    # Fixture mode must never pass model/NLI decision files, or the renderer
    # would switch to the credentialed audit-experiment copy.
    assert "--baseline-decisions" not in block
    assert "--improved-decisions" not in block


def test_makefile_model_target_passes_both_decision_files() -> None:
    block = _makefile_target_block(
        (ROOT / "Makefile").read_text(), "semantic-model-reporting-surface"
    )
    assert "scripts/render_semantic_reporting_surface.py" in block
    assert (
        "--baseline-decisions reports/semantic_model_decisions/adversarial_v1_baseline.json"
        in block
    )
    assert (
        "--improved-decisions reports/semantic_model_decisions/adversarial_v1_improved.json"
        in block
    )
    # The model/NLI HTML output is gitignored, distinct from the tracked
    # fixture HTML, so a model run never overwrites the committed artifact.
    assert "--out reports/adversarial_v1_semantic_model_reporting_surface.html" in block


def test_generated_semantic_reports_have_expected_fixture_counts(
    semantic_reports: tuple[Path, Path],
) -> None:
    baseline, improved = semantic_reports
    baseline_report = json.loads(baseline.read_text())
    improved_report = json.loads(improved.read_text())

    def rate(report: dict[str, object]) -> dict[str, object]:
        rates = report["aggregate_grader_pass_rates"]
        assert isinstance(rates, list)
        return next(r for r in rates if r["name"] == SEMANTIC_GRADER_NAME)

    assert rate(baseline_report)["passed"] == 7
    assert rate(improved_report)["passed"] == 12
