"""Tests for the opt-in credentialed repeat-run capture script.

``scripts/run_llm_repeats.py`` runs the credentialed eval pipeline
``--runs N`` times against the same dataset for one
``llm_candidate_v*`` profile. These tests exercise the wiring without
calling Anthropic — ``run_eval`` is injected as a fake.

Coverage:

1. Deterministic / unknown profiles are rejected by default.
2. The ``--allow-non-llm-profile`` escape hatch only accepts known
   profiles.
3. The preflight short-circuits when credentials are missing.
4. Per-run paths follow the documented layout that the aggregator
   consumes.
5. The aggregator can consume the runner's outputs without changes.
6. Make targets are opt-in (not dependencies of ``make test``) and the
   credentialed ones depend on ``check-llm-env``.
7. ``.gitignore`` excludes the raw repeat output tree.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from scripts.aggregate_llm_repeats import aggregate_files
from scripts.run_llm_repeats import (
    RepeatRunnerError,
    plan_run_paths,
    run_repeats,
)


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
GITIGNORE = ROOT / ".gitignore"
ADVERSARIAL_PATH = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "evals"
    / "adversarial_v0.jsonl"
)


# ---------------------------------------------------------------------------
# Fake run_eval — never calls the LLM, just writes a real-shaped report
# ---------------------------------------------------------------------------


def _fake_report_payload(profile: str) -> dict[str, Any]:
    return {
        "version": "local_eval_v0",
        "synthetic": True,
        "agent_system_version": profile,
        "dataset_path": "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl",
        "case_count": 1,
        "passed_case_count": 1,
        "failed_case_count": 0,
        "aggregate_grader_pass_rates": [],
        "failure_label_counts": {},
        "synthetic_latency_envelope": {
            "comparison_by_risk_band": {
                "L1": {
                    "count": 1,
                    "measured_mean_ms": 9000,
                    "measured_max_ms": 9000,
                    "p50_ms": 2000,
                    "p95_ms": 4000,
                    "verdict": "exceeds_p95",
                    "mean_vs_p95_ratio": 2.25,
                }
            }
        },
        "synthetic_cost_summary": {"total_est_cost_usd": 0.0042, "per_case_count": 1},
        "per_case": [
            {
                "case_id": "case_fl_adv_v0_001",
                "workflow": "financial_links_reliability",
                "risk_band": "L1",
                "trace_path": "x",
                "grader_results": [],
                "failure_labels": [],
                "evaluator_all_ok": True,
                "approval_required": False,
                "passed": True,
                "latency_ms": 9000,
                "est_cost_usd": 0.0042,
            }
        ],
    }


class _FakeReport:
    """Minimal stand-in for the EvalReport pydantic model. The runner
    only calls ``.model_dump(mode="json")`` on its return value."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:  # noqa: ARG002
        return dict(self._payload)


def make_fake_run_eval(profile: str):
    """Build a fake ``run_eval`` that writes a real-shaped report to
    ``report_out`` and returns a ``_FakeReport``. Captures call args so
    tests can introspect what the runner asked for."""

    calls: list[dict[str, Any]] = []

    def _fake(
        dataset_path: Path,
        traces_out: Path,
        report_out: Path | None = None,
        *,
        agent_system_version: str,
        approval_matrix: Any | None = None,  # noqa: ARG001
    ) -> _FakeReport:
        calls.append(
            {
                "dataset_path": Path(dataset_path),
                "traces_out": Path(traces_out),
                "report_out": Path(report_out) if report_out else None,
                "agent_system_version": agent_system_version,
            }
        )
        payload = _fake_report_payload(agent_system_version or profile)
        if report_out is not None:
            Path(report_out).parent.mkdir(parents=True, exist_ok=True)
            Path(report_out).write_text(json.dumps(payload, indent=2))
        Path(traces_out).mkdir(parents=True, exist_ok=True)
        return _FakeReport(payload)

    _fake.calls = calls  # type: ignore[attr-defined]
    return _fake


# ---------------------------------------------------------------------------
# Profile gating
# ---------------------------------------------------------------------------


def test_deterministic_profile_rejected_by_default(tmp_path: Path) -> None:
    with pytest.raises(RepeatRunnerError) as exc:
        run_repeats(
            dataset=ADVERSARIAL_PATH,
            profile="improved_v0",
            runs=1,
            out_dir=tmp_path,
            skip_preflight=True,
            run_eval_fn=make_fake_run_eval("improved_v0"),
        )
    assert "not an LLM-candidate profile" in str(exc.value)


def test_unknown_profile_rejected_even_with_override(tmp_path: Path) -> None:
    with pytest.raises(RepeatRunnerError) as exc:
        run_repeats(
            dataset=ADVERSARIAL_PATH,
            profile="totally_made_up",
            runs=1,
            out_dir=tmp_path,
            allow_non_llm_profile=True,
            skip_preflight=True,
            run_eval_fn=make_fake_run_eval("totally_made_up"),
        )
    assert "unknown profile" in str(exc.value)


@pytest.mark.parametrize("profile", ["llm_candidate_v0", "llm_candidate_v1"])
def test_llm_profile_accepted(profile: str, tmp_path: Path) -> None:
    fake = make_fake_run_eval(profile)
    summary = run_repeats(
        dataset=ADVERSARIAL_PATH,
        profile=profile,
        runs=2,
        out_dir=tmp_path,
        skip_preflight=True,
        run_eval_fn=fake,
        timestamp="20260517_120000",
    )
    assert summary["runs"] == 2
    assert summary["profile"] == profile
    assert len(fake.calls) == 2
    for call in fake.calls:
        assert call["agent_system_version"] == profile


def test_allow_non_llm_profile_accepts_known_deterministic(tmp_path: Path) -> None:
    """The escape hatch lets a known deterministic profile through for
    aggregator regression testing — not for real variance work."""

    fake = make_fake_run_eval("improved_v0")
    summary = run_repeats(
        dataset=ADVERSARIAL_PATH,
        profile="improved_v0",
        runs=1,
        out_dir=tmp_path,
        allow_non_llm_profile=True,
        skip_preflight=True,
        run_eval_fn=fake,
    )
    assert summary["profile"] == "improved_v0"


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def test_preflight_blocks_without_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default code path (skip_preflight=False) must call the real
    preflight; without credentials/SDK it must raise before any
    fake-runner call."""

    import scripts.run_llm_repeats as runner_module

    def _bad_preflight() -> Any:
        class _Bad:
            ok = False

            def render(self) -> str:
                return "FAIL: ANTHROPIC_API_KEY not set\nFAIL: anthropic SDK not importable"

        return _Bad()

    monkeypatch.setattr(runner_module, "check_llm_env", _bad_preflight)

    with pytest.raises(RepeatRunnerError) as exc:
        run_repeats(
            dataset=ADVERSARIAL_PATH,
            profile="llm_candidate_v0",
            runs=1,
            out_dir=tmp_path,
            # skip_preflight=False → must hit the (patched) preflight
            run_eval_fn=make_fake_run_eval("llm_candidate_v0"),
        )
    msg = str(exc.value)
    assert "ANTHROPIC_API_KEY" in msg
    assert "anthropic SDK" in msg


# ---------------------------------------------------------------------------
# Path layout (what the aggregator consumes)
# ---------------------------------------------------------------------------


def test_plan_run_paths_layout(tmp_path: Path) -> None:
    base, plan = plan_run_paths(
        out_dir=tmp_path,
        profile="llm_candidate_v0",
        runs=3,
        timestamp="20260517_120000",
    )
    assert base == tmp_path / "llm_candidate_v0" / "20260517_120000"
    assert len(plan) == 3
    for i, entry in enumerate(plan, start=1):
        assert entry["run_dir"] == base / f"run_{i:03d}"
        assert entry["eval_report"] == base / f"run_{i:03d}" / "eval_report.json"
        assert entry["traces_dir"] == base / f"run_{i:03d}" / "traces"


def test_runs_writes_one_report_per_run(tmp_path: Path) -> None:
    fake = make_fake_run_eval("llm_candidate_v0")
    summary = run_repeats(
        dataset=ADVERSARIAL_PATH,
        profile="llm_candidate_v0",
        runs=3,
        out_dir=tmp_path,
        skip_preflight=True,
        run_eval_fn=fake,
        timestamp="20260517_120000",
    )
    base = Path(summary["base_dir"])
    assert base == tmp_path / "llm_candidate_v0" / "20260517_120000"
    for i in range(1, 4):
        report_path = base / f"run_{i:03d}" / "eval_report.json"
        assert report_path.exists()
        payload = json.loads(report_path.read_text())
        assert payload["agent_system_version"] == "llm_candidate_v0"
    # Per-run metadata bubbles up in the summary.
    assert len(summary["per_run"]) == 3
    assert all(entry["report_path"].endswith("eval_report.json") for entry in summary["per_run"])


def test_aggregator_consumes_runner_output(tmp_path: Path) -> None:
    """The capture and aggregation halves of the loop must compose
    without any rediscovery: the aggregator should accept the runner's
    per-run report paths directly."""

    fake = make_fake_run_eval("llm_candidate_v0")
    summary = run_repeats(
        dataset=ADVERSARIAL_PATH,
        profile="llm_candidate_v0",
        runs=3,
        out_dir=tmp_path,
        skip_preflight=True,
        run_eval_fn=fake,
        timestamp="20260517_120000",
    )
    paths = [Path(entry["report_path"]) for entry in summary["per_run"]]
    agg = aggregate_files(paths)
    assert agg["run_count"] == 3
    assert agg["profile_family"] == ["llm_candidate_v0"]
    # Fake reports all pass cleanly → no instability, no failures.
    assert agg["pass_per_run"] == [1, 1, 1]
    assert agg["fail_per_run"] == [0, 0, 0]
    assert agg["per_case_instability"] == []


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------


def test_missing_dataset_path_rejected(tmp_path: Path) -> None:
    with pytest.raises(RepeatRunnerError) as exc:
        run_repeats(
            dataset=tmp_path / "missing.jsonl",
            profile="llm_candidate_v0",
            runs=1,
            out_dir=tmp_path / "out",
            skip_preflight=True,
            run_eval_fn=make_fake_run_eval("llm_candidate_v0"),
        )
    assert "dataset not found" in str(exc.value)


def test_runs_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(RepeatRunnerError):
        plan_run_paths(
            out_dir=tmp_path, profile="llm_candidate_v0", runs=0, timestamp="x"
        )


# ---------------------------------------------------------------------------
# Make + gitignore wiring
# ---------------------------------------------------------------------------


def _make_targets() -> dict[str, str]:
    """Parse the Makefile into ``{target: prereq_line}`` for the
    targets we care about. Recipe bodies aren't returned."""

    text = MAKEFILE.read_text()
    out: dict[str, str] = {}
    for match in re.finditer(r"^([A-Za-z0-9_\-]+):\s*([^\n]*)$", text, re.MULTILINE):
        target = match.group(1)
        if target in {
            "repeat-adversarial-llm-v0",
            "repeat-adversarial-llm-v1",
            "repeat-adversarial-llm-summary",
            "test",
            "scaffold-test",
        }:
            out[target] = match.group(2).strip()
    return out


def test_repeat_targets_exist_and_capture_targets_depend_on_check_llm_env() -> None:
    targets = _make_targets()
    for t in (
        "repeat-adversarial-llm-v0",
        "repeat-adversarial-llm-v1",
        "repeat-adversarial-llm-summary",
    ):
        assert t in targets, f"Makefile missing target {t!r}"

    # Both capture targets must depend on the preflight.
    for t in ("repeat-adversarial-llm-v0", "repeat-adversarial-llm-v1"):
        assert "check-llm-env" in targets[t].split(), (
            f"{t} must depend on check-llm-env so credentials are validated "
            f"before any token spend; got prereqs={targets[t]!r}"
        )

    # The summary target must NOT depend on check-llm-env — it operates
    # on already-captured local outputs.
    assert "check-llm-env" not in targets["repeat-adversarial-llm-summary"].split()


def test_repeat_targets_are_not_dependencies_of_make_test() -> None:
    """`make test` must stay credential-free."""

    targets = _make_targets()
    test_prereqs = set(targets.get("test", "").split())
    for t in (
        "repeat-adversarial-llm-v0",
        "repeat-adversarial-llm-v1",
        "repeat-adversarial-llm-summary",
    ):
        assert t not in test_prereqs, (
            f"`make test` must not depend on {t!r}; credentialed repeat "
            "capture is opt-in."
        )


def test_repeat_targets_route_through_llm_repeats_script() -> None:
    """The two capture targets must invoke scripts/run_llm_repeats.py
    with the correct profile flag (so the script's own profile
    validation runs)."""

    text = MAKEFILE.read_text()
    body_v0 = re.search(
        r"^repeat-adversarial-llm-v0:[^\n]*\n((?:\t[^\n]*\n)+)", text, re.MULTILINE
    )
    body_v1 = re.search(
        r"^repeat-adversarial-llm-v1:[^\n]*\n((?:\t[^\n]*\n)+)", text, re.MULTILINE
    )
    assert body_v0 and body_v1, "could not extract repeat-* recipe bodies"
    assert "scripts/run_llm_repeats.py" in body_v0.group(1)
    assert "scripts/run_llm_repeats.py" in body_v1.group(1)
    assert "--profile llm_candidate_v0" in body_v0.group(1)
    assert "--profile llm_candidate_v1" in body_v1.group(1)
    # And the dataset is the adversarial slice.
    assert "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl" in body_v0.group(1)
    assert "case_studies/financial_links_reliability/evals/adversarial_v0.jsonl" in body_v1.group(1)


def test_gitignore_excludes_raw_repeat_output_tree() -> None:
    gitignore = GITIGNORE.read_text()
    assert "reports/llm_repeats/" in gitignore, (
        ".gitignore must exclude reports/llm_repeats/ — raw repeat eval "
        "reports embed raw model output and traces, and must never be "
        "tracked. The aggregated public-safe summary may live at "
        "reports/llm_repeat_summary.{md,json} (outside the tree)."
    )


def test_committed_repeat_outputs_are_absent() -> None:
    """Belt-and-braces: nothing under reports/llm_repeats/ is tracked."""

    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "reports/llm_repeats"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], (
        "git is tracking raw repeat-run outputs that must remain local; "
        f"tracked: {tracked}"
    )
