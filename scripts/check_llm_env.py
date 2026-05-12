"""Actionable preflight for the opt-in ``llm_candidate_v0`` profile.

This script does **not** make any network call. It only verifies that:

- ``ANTHROPIC_API_KEY`` is set in the environment;
- the ``anthropic`` Python SDK is importable.

It is wired ahead of ``scripts/run_eval.py`` in the LLM-specific Make
targets so a user gets a clear, local failure message before any eval
is attempted. The deterministic ``baseline_v0`` / ``improved_v0`` proof
loop never invokes this script.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Callable


REQUIRED_ENV_VAR: str = "ANTHROPIC_API_KEY"
REQUIRED_SDK: str = "anthropic"

OK_LINE: str = "OK: llm_candidate_v0 environment is ready."


@dataclass(frozen=True)
class EnvCheckResult:
    """Result of a credential-only LLM-environment preflight."""

    ok: bool
    messages: tuple[str, ...]

    def render(self) -> str:
        if self.ok:
            return OK_LINE
        return "\n".join(self.messages)


def check_llm_env(
    *,
    env: dict[str, str] | None = None,
    import_module: Callable[[str], object] = importlib.import_module,
) -> EnvCheckResult:
    """Pure preflight check.

    ``env`` and ``import_module`` are injection points so tests can
    exercise every branch without touching real environment variables
    or importing a real SDK.
    """

    effective_env = env if env is not None else dict(os.environ)
    failures: list[str] = []

    api_key = effective_env.get(REQUIRED_ENV_VAR)
    if not api_key:
        failures.append(
            f"FAIL: {REQUIRED_ENV_VAR} is not set. The llm_candidate_v0 "
            "profile requires it; the deterministic baseline_v0 / "
            "improved_v0 profiles do not. See .env.example."
        )

    try:
        import_module(REQUIRED_SDK)
    except ImportError:
        failures.append(
            f"FAIL: the '{REQUIRED_SDK}' Python SDK is not importable. "
            f"Install it locally (for example `uv pip install {REQUIRED_SDK}`). "
            "The deterministic profiles do not need it."
        )

    return EnvCheckResult(ok=not failures, messages=tuple(failures))


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
    result = check_llm_env()
    print(result.render())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
