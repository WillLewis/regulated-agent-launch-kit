"""Apply a synthetic redaction policy to a local trace JSON.

The redactor walks the trace recursively. For every dict key it sees:

- if the key is in ``remove_fields`` → the key is deleted;
- if the key is in ``abstract_fields`` → its value is replaced with the
  configured placeholder string;
- otherwise the original value is kept.

After redaction, the script also reports:

- which top-level fields listed in ``preserve_fields`` are present
  (``preserved_top_level_fields``);
- which top-level fields listed in ``preserve_fields`` are *not* in the
  trace (``preserve_fields_missing`` — drift signal between the policy
  and the trace schema);
- which top-level keys in the trace are not classified by the policy
  (``uncovered_top_level_fields`` — the policy doesn't say whether to
  keep, drop, or abstract them; an analyst should review).

No external credentials required. The redaction discipline is the same
for synthetic and real traces; this lab applies it to synthetic data so
the discipline stays exercised.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


REDACTION_REPORT_VERSION = "redaction_report_v0"


def _walk(
    node: Any,
    remove: set[str],
    abstract: dict[str, dict[str, Any]],
    removed_paths: list[str],
    abstracted_paths: list[str],
    path: str = "$",
) -> Any:
    if isinstance(node, dict):
        result: dict[str, Any] = {}
        for key, value in node.items():
            sub_path = f"{path}.{key}"
            if key in remove:
                removed_paths.append(sub_path)
                continue
            if key in abstract:
                replacement = abstract[key].get("replacement", "<redacted>")
                abstracted_paths.append(sub_path)
                result[key] = replacement
                continue
            result[key] = _walk(value, remove, abstract, removed_paths, abstracted_paths, sub_path)
        return result
    if isinstance(node, list):
        return [
            _walk(item, remove, abstract, removed_paths, abstracted_paths, f"{path}[{idx}]")
            for idx, item in enumerate(node)
        ]
    return node


def redact(
    trace: Any,
    policy: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    """Apply ``policy`` to ``trace`` and return ``(redacted, report)``."""

    remove: set[str] = set(policy.get("remove_fields") or [])
    abstract: dict[str, dict[str, Any]] = dict(policy.get("abstract_fields") or {})
    preserve: list[str] = list(policy.get("preserve_fields") or [])

    removed_paths: list[str] = []
    abstracted_paths: list[str] = []
    redacted = _walk(trace, remove, abstract, removed_paths, abstracted_paths)

    preserved: list[str] = []
    preserve_missing: list[str] = []
    if isinstance(redacted, dict):
        for key in preserve:
            (preserved if key in redacted else preserve_missing).append(key)

    classified = set(remove) | set(abstract) | set(preserve)
    uncovered: list[str] = []
    if isinstance(redacted, dict):
        for key in redacted:
            if key not in classified:
                uncovered.append(key)

    report = {
        "version": REDACTION_REPORT_VERSION,
        "synthetic": True,
        "policy_version": policy.get("version"),
        "removed_paths": removed_paths,
        "abstracted_paths": abstracted_paths,
        "preserved_top_level_fields": preserved,
        "preserve_fields_missing": preserve_missing,
        "uncovered_top_level_fields": uncovered,
        "summary": {
            "removed_count": len(removed_paths),
            "abstracted_count": len(abstracted_paths),
            "preserved_count": len(preserved),
            "preserve_missing_count": len(preserve_missing),
            "uncovered_count": len(uncovered),
        },
    }
    return redacted, report


def _load_trace(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"trace not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON ({exc})")


def _load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"policy not found: {path}")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: redaction policy must be a YAML mapping")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply a synthetic redaction policy to a local trace JSON."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--policy",
        required=True,
        type=Path,
        help="Path to the redaction policy YAML (e.g. configs/redaction_policy.yaml).",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--report-out",
        type=Path,
        default=None,
        help="Optional path to write the JSON redaction report.",
    )
    args = parser.parse_args(argv)

    trace = _load_trace(args.input)
    policy = _load_policy(args.policy)
    redacted, report = redact(trace, policy)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(redacted, indent=2))

    if args.report_out is not None:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2))

    print(
        f"OK: redacted {args.input.name} -> {args.output} "
        f"(removed={report['summary']['removed_count']}, "
        f"abstracted={report['summary']['abstracted_count']}, "
        f"uncovered={report['summary']['uncovered_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
