"""Validate the adversarial v2 semantic regression seeds — on disk, no model.

Mirrors ``scripts/check_semantic_regressions_adversarial_v1.py`` for the v2
slice. The validation/linkage logic is genuinely generic, so this script reuses
``check`` and ``check_replay_report`` from the v1 checker and only supplies the
v2 default paths. It asserts:

1. structural integrity (one record per semantic-only flag, unique IDs,
   replayable case-superset shape, ``pending_review``, semantic grader +
   UNSAFE_CUSTOMER_COMMS label, ``replayable_deterministically == False``);
2. **linkage** — the seeded ``(source_case_id, source_agent_system_version)``
   pairs exactly match the semantic-only flags in the public v2 audit summary;
3. **public safety** — no raw trace path, no model-decision rationale/evidence
   keys, no readiness overclaim.

With ``--replay-report`` it also verifies the offline ``unsupported_claim_semantic``
grader fired ``UNSAFE_CUSTOMER_COMMS`` on every seed in a credential-free replay
report. Credential-free and deterministic — no model call.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_semantic_regressions_adversarial_v1 import (  # noqa: E402
    check,
    check_replay_report,
)
from scripts.seed_semantic_regressions_adversarial_v2 import (  # noqa: E402
    DEFAULT_OUT,
    DEFAULT_SUMMARY,
)

from scripts.build_semantic_replay_fixture_adversarial_v2 import (  # noqa: E402
    _load_jsonl,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the adversarial v2 semantic regression seeds and their "
            "linkage to the public v2 semantic audit summary. With "
            "--replay-report, also verify the semantic grader fired on every "
            "seed in a credential-free replay report. No model call."
        )
    )
    parser.add_argument("--regressions", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--replay-report", type=Path, default=None)
    args = parser.parse_args(argv)

    errors = check(args.regressions, args.summary)
    if args.replay_report is not None:
        errors += check_replay_report(args.regressions, args.replay_report)
    if errors:
        print(f"INVALID: {args.regressions}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    records = _load_jsonl(args.regressions)
    replay_note = (
        " + semantic grader fired on every seed in the replay report"
        if args.replay_report is not None
        else ""
    )
    print(
        f"OK: {args.regressions} ({len(records)} semantic-only regression seed(s); "
        f"all pending_review; linked to the v2 semantic audit summary{replay_note}; "
        "no model call)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
