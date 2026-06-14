"""Compute and render the synthetic launch-gate decision.

This script is the I/O layer around ``evals.launch_decision.decide``. It
loads only git-tracked artifacts referenced by ``configs/launch_gates.yaml``,
hashes those inputs, and writes machine/human launch-decision artifacts.
It makes no production-readiness, regulatory-compliance, or partner claim.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.schemas import LaunchDecision  # noqa: E402
from evals.launch_decision import decide  # noqa: E402


EVAL_RUN_SIGNALS = {
    "l3_evaluator_miss_count",
    "l3_consent_violation_count",
    "min_deterministic_grader_pass_rate",
    "risk_weighted_pass_rate",
    "l3_unsupported_miss_count",
}
REGRESSION_SIGNALS = {
    "high_risk_regression_failure_count",
    "regression_total_failed_count",
}
SEMANTIC_AUDIT_SIGNALS = {
    "l3_semantic_only_unsafe_count",
    "l3_unsupported_miss_count",
}
REDACTION_SIGNALS = {"min_redaction_coverage"}
RISK_WEIGHT_SIGNALS = {"risk_weighted_pass_rate"}
PILOT_REVIEW_SIGNALS = {"pilot_review_present"}

EVAL_RUN_PATH = "reports/improved_adversarial_v1_eval.json"
REGRESSION_PATTERN = "reports/regression*_eval.json"
SEMANTIC_AUDIT_PATTERN = "reports/llm_adversarial_v*_semantic_audit_summary.json"
REDACTION_REPORT_PATTERN = "evidence_packs/**/traces/redacted/**/*.redaction_report.json"
RISK_WEIGHTS_PATH = "configs/risk_weights.yaml"
PILOT_REVIEW_PATH = "deployment/pilot_readiness_review.md"

SYNTHETIC_RIDER = (
    "This launch decision is generated from synthetic local artifacts only. "
    "No production-readiness, regulatory-compliance, model-safety, partner, "
    "or customer launch claim is made by this document."
)


def load_inputs(
    gates_config: dict,
    *,
    gates_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load decide() role inputs from git-tracked gate backing artifacts."""

    tracked = _git_tracked_files()

    eval_paths = _paths_for_signals(
        gates_config,
        EVAL_RUN_SIGNALS,
        tracked,
        predicate=lambda path: path == EVAL_RUN_PATH,
    )
    if len(eval_paths) != 1:
        raise SystemExit(
            "expected exactly one tracked eval_run artifact "
            f"({EVAL_RUN_PATH}); resolved {eval_paths or 'none'}"
        )

    risk_weight_paths = _paths_for_signals(
        gates_config,
        RISK_WEIGHT_SIGNALS,
        tracked,
        predicate=lambda path: path == RISK_WEIGHTS_PATH,
    )
    if len(risk_weight_paths) != 1:
        raise SystemExit(
            "expected exactly one tracked risk_weights artifact "
            f"({RISK_WEIGHTS_PATH}); resolved {risk_weight_paths or 'none'}"
        )

    regression_paths = _paths_for_signals(
        gates_config,
        REGRESSION_SIGNALS,
        tracked,
        predicate=lambda path: fnmatch.fnmatchcase(path, REGRESSION_PATTERN),
    )
    semantic_paths = _paths_for_signals(
        gates_config,
        SEMANTIC_AUDIT_SIGNALS,
        tracked,
        predicate=lambda path: fnmatch.fnmatchcase(path, SEMANTIC_AUDIT_PATTERN),
    )
    redaction_paths = _paths_for_signals(
        gates_config,
        REDACTION_SIGNALS,
        tracked,
        predicate=lambda path: fnmatch.fnmatchcase(path, REDACTION_REPORT_PATTERN),
    )
    pilot_review_paths = _paths_for_signals(
        gates_config,
        PILOT_REVIEW_SIGNALS,
        tracked,
        predicate=lambda path: path == PILOT_REVIEW_PATH,
    )

    loaded_paths = {
        *eval_paths,
        *risk_weight_paths,
        *regression_paths,
        *semantic_paths,
        *redaction_paths,
        *pilot_review_paths,
    }
    if gates_path is not None:
        gates_rel = _relative_repo_path(gates_path)
        if gates_rel in tracked:
            loaded_paths.add(gates_rel)

    return {
        "eval_run": _load_json_object(eval_paths[0]),
        "regression_runs": [_load_json_object(path) for path in regression_paths],
        "semantic_audits": [_load_json_object(path) for path in semantic_paths],
        "redaction_reports": [_load_json_object(path) for path in redaction_paths],
        "risk_weights": _load_yaml_object(risk_weight_paths[0]),
        "pilot_review_present": _pilot_review_present(pilot_review_paths),
        "inputs_digest": _inputs_digest(sorted(loaded_paths)),
    }


def render_markdown(decision: LaunchDecision) -> str:
    """Render a human-readable launch-decision artifact."""

    lines = [
        "# Launch Decision",
        "",
        f"**Verdict:** `{decision.verdict.value}`",
        "",
        f"> {decision.posture_line}",
        "",
        SYNTHETIC_RIDER,
        "",
        "## Gate Results",
        "",
        "| Gate | Tier | Status | Observed vs threshold | Gating | Backing artifact |",
        "|---|---|---|---|---:|---|",
    ]
    for result in decision.gate_results:
        lines.append(
            "| "
            f"`{result.gate_id}` | "
            f"`{result.tier.value}` | "
            f"`{result.status.value}` | "
            f"{_observed_vs_threshold(result)} | "
            f"{str(result.gating).lower()} | "
            f"{_artifact_links(result.backing_artifact)} |"
        )

    lines.extend(
        [
            "",
            "## Blockers",
            "",
            _blocker_block(decision.blockers),
            "",
            "## Rationale",
            "",
            decision.rationale,
            "",
            "## Review Boundary",
            "",
            (
                "This artifact is a deterministic launch-gate computation over "
                "local synthetic evidence. It does not assert regulatory "
                "compliance, production readiness, customer readiness, partner "
                "approval, or model safety."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gates", default="configs/launch_gates.yaml")
    parser.add_argument("--out-json", default="reports/launch_decision.json")
    parser.add_argument("--out-md", default="reports/launch_decision.md")
    args = parser.parse_args(argv)

    gates_path = _repo_path(args.gates)
    gates_config = _load_yaml_file(gates_path)
    inputs = load_inputs(gates_config, gates_path=gates_path)
    decision = decide(gates_config, **inputs)

    out_json = _repo_path(args.out_json)
    out_md = _repo_path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(decision.model_dump(mode="json"), indent=2) + "\n")
    out_md.write_text(render_markdown(decision))
    return 0


def _git_tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _paths_for_signals(
    gates_config: dict,
    signals: set[str],
    tracked_files: set[str],
    *,
    predicate: Any,
) -> list[str]:
    patterns = [
        artifact
        for gate in gates_config.get("gates", []) or []
        if gate.get("signal") in signals
        for artifact in _artifact_list(gate.get("backing_artifact"))
    ]
    return [
        path
        for path in _resolve_tracked_patterns(patterns, tracked_files)
        if predicate(path)
    ]


def _artifact_list(value: Any) -> list[str]:
    if value == "(all gate backing artifacts)" or value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _resolve_tracked_patterns(patterns: list[str], tracked_files: set[str]) -> list[str]:
    matches: set[str] = set()
    for pattern in patterns:
        if _has_glob(pattern):
            matches.update(
                path for path in tracked_files if fnmatch.fnmatchcase(path, pattern)
            )
        elif pattern in tracked_files:
            matches.add(pattern)
    return sorted(matches)


def _has_glob(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


def _load_json_object(path: str) -> dict[str, Any]:
    try:
        data = json.loads((REPO_ROOT / path).read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return data


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"gate config not found: {path}")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: top-level YAML must be a mapping")
    return data


def _load_yaml_object(path: str) -> dict[str, Any]:
    return _load_yaml_file(REPO_ROOT / path)


def _pilot_review_present(paths: list[str]) -> bool:
    for path in paths:
        full_path = REPO_ROOT / path
        if full_path.exists() and full_path.read_text().strip():
            return True
    return False


def _inputs_digest(paths: list[str]) -> dict[str, str]:
    return {
        path: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()
        for path in paths
    }


def _repo_path(path: str | Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else REPO_ROOT / resolved


def _relative_repo_path(path: str | Path) -> str:
    resolved = _repo_path(path).resolve()
    return resolved.relative_to(REPO_ROOT.resolve()).as_posix()


def _observed_vs_threshold(result: Any) -> str:
    observed = _format_value(result.observed)
    if result.comparator == "advisory":
        return f"{observed} (advisory)"
    return f"{observed} `{result.comparator}` {_format_value(result.threshold)}"


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return f"`{json.dumps(value, sort_keys=True)}`"


def _artifact_links(value: str | list[str]) -> str:
    artifacts = [value] if isinstance(value, str) else value
    return "<br>".join(_artifact_link(artifact) for artifact in artifacts)


def _artifact_link(path: str) -> str:
    if path.startswith("(") and path.endswith(")"):
        return f"`{path}`"
    return f"[`{path}`]({path})"


def _blocker_block(blockers: list[str]) -> str:
    if not blockers:
        return "_No launch blockers from gating results._"
    return "\n".join(f"- `{blocker}`" for blocker in blockers)


if __name__ == "__main__":
    raise SystemExit(main())
