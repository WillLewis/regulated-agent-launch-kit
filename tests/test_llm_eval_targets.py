"""Tests for the opt-in LLM eval run path.

The whole point of this suite is to make three facts non-negotiable:

1. There are opt-in Make targets for the LLM profile, with a real
   preflight gate, and no deterministic target depends on them.
2. The preflight helper fails clean without credentials and only
   reports OK when both ``ANTHROPIC_API_KEY`` and the ``anthropic``
   SDK are available.
3. The standard test suite never requires real credentials, never
   imports ``anthropic`` without a monkeypatch, and never depends on a
   generated LLM eval report.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"
SCRIPTS = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"
PRECHECK_SCRIPT = SCRIPTS / "check_llm_env.py"


# ---------------------------------------------------------------------------
# Makefile wiring
# ---------------------------------------------------------------------------

def test_makefile_has_llm_targets() -> None:
    makefile = MAKEFILE.read_text()
    for target in ("check-llm-env:", "eval-smoke-llm:", "eval-card-llm-smoke:"):
        assert target in makefile, f"Makefile missing target {target!r}"


def test_eval_smoke_llm_depends_on_check_llm_env() -> None:
    """The preflight must run before any LLM eval invocation."""

    makefile = MAKEFILE.read_text()
    match = re.search(r"^eval-smoke-llm:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
    assert match is not None, "eval-smoke-llm target not found"
    prereqs = match.group(1).split()
    assert "check-llm-env" in prereqs, (
        f"eval-smoke-llm must list check-llm-env as a prerequisite; got {prereqs}"
    )


def test_eval_card_llm_smoke_depends_on_both_smoke_evals() -> None:
    makefile = MAKEFILE.read_text()
    match = re.search(r"^eval-card-llm-smoke:\s*([^\n]*)$", makefile, flags=re.MULTILINE)
    assert match is not None, "eval-card-llm-smoke target not found"
    prereqs = match.group(1).split()
    assert "eval-smoke-improved" in prereqs
    assert "eval-smoke-llm" in prereqs


_DETERMINISTIC_TARGETS: tuple[str, ...] = (
    "test:",
    "scaffold-test:",
    "dataset-test:",
    "eval-smoke:",
    "eval-smoke-baseline:",
    "eval-smoke-improved:",
    "eval-card-smoke:",
    "eval-v0-baseline:",
    "eval-v0-improved:",
    "eval-card-v0:",
    "regression-seed-v0:",
    "regression-check-v0:",
    "redact-v0:",
    "evidence-pack-v0:",
    "lint:",
)


def test_no_deterministic_target_depends_on_llm_targets() -> None:
    """The deterministic public proof loop must stay credential-free."""

    makefile = MAKEFILE.read_text()
    forbidden_prereqs = {"check-llm-env", "eval-smoke-llm", "eval-card-llm-smoke"}

    for target in _DETERMINISTIC_TARGETS:
        pattern = rf"^{re.escape(target)}\s*([^\n]*)$"
        match = re.search(pattern, makefile, flags=re.MULTILINE)
        if match is None:
            continue
        prereqs = set(match.group(1).split())
        leaked = prereqs & forbidden_prereqs
        assert not leaked, (
            f"deterministic Make target {target} depends on LLM target(s) {leaked}; "
            "the public proof loop must not require credentials."
        )


# ---------------------------------------------------------------------------
# Preflight helper
# ---------------------------------------------------------------------------

def _import_check_llm_env_module():
    """Import ``scripts/check_llm_env.py`` as a module without running its CLI.

    Registers the module in ``sys.modules`` so the ``@dataclass`` inside it
    can resolve its own ``__module__`` during class creation.
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location("check_llm_env", PRECHECK_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_llm_env"] = module
    spec.loader.exec_module(module)
    return module


def test_check_llm_env_fails_when_key_missing_and_sdk_missing() -> None:
    module = _import_check_llm_env_module()

    def _no_sdk(name: str):
        raise ImportError(f"No module named {name!r}")

    result = module.check_llm_env(env={}, import_module=_no_sdk)
    assert result.ok is False
    rendered = result.render()
    assert "ANTHROPIC_API_KEY" in rendered
    assert "anthropic" in rendered
    assert rendered.count("FAIL") == 2


def test_check_llm_env_fails_when_only_key_missing() -> None:
    module = _import_check_llm_env_module()
    fake_sdk = object()
    result = module.check_llm_env(
        env={},
        import_module=lambda name: fake_sdk,
    )
    assert result.ok is False
    assert "ANTHROPIC_API_KEY" in result.render()
    assert "anthropic" not in result.render(), (
        "if the SDK is importable, the failure message should not mention it"
    )


def test_check_llm_env_fails_when_only_sdk_missing() -> None:
    module = _import_check_llm_env_module()

    def _no_sdk(name: str):
        raise ImportError(f"No module named {name!r}")

    result = module.check_llm_env(
        env={"ANTHROPIC_API_KEY": "fake"},
        import_module=_no_sdk,
    )
    assert result.ok is False
    assert "anthropic" in result.render()
    assert "ANTHROPIC_API_KEY" not in result.render()


def test_check_llm_env_passes_with_key_and_importable_sdk() -> None:
    module = _import_check_llm_env_module()
    fake_sdk = object()
    result = module.check_llm_env(
        env={"ANTHROPIC_API_KEY": "fake"},
        import_module=lambda name: fake_sdk,
    )
    assert result.ok is True
    assert result.render() == module.OK_LINE


def test_check_llm_env_cli_fails_clean_without_env(tmp_path: Path) -> None:
    """CLI invocation in a stripped env must exit non-zero with actionable text."""

    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, str(PRECHECK_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "ANTHROPIC_API_KEY" in combined or "anthropic" in combined
    assert "FAIL" in combined


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

def test_readme_documents_optional_llm_run() -> None:
    readme = README.read_text()
    lower = readme.lower()
    # Required commands surface in the README.
    for fragment in (
        "make check-llm-env",
        "make eval-smoke-llm",
        "make eval-card-llm-smoke",
        "ANTHROPIC_API_KEY",
        ".env.example",
        "uv pip install anthropic",
    ):
        assert fragment in readme, f"README missing opt-in instruction: {fragment!r}"
    assert "opt-in" in lower or "optional" in lower
    assert "no silent fallback" in lower


def test_plan_marks_llm_run_path_prepared_but_not_executed() -> None:
    """The smoke-slice LLM opt-in (`make eval-card-llm-smoke`) is still
    un-executed. PLAN must say so even after the adversarial-slice
    credentialed run has been committed.
    """

    plan = PLAN.read_text()
    lower = plan.lower()
    assert (
        "smoke-slice opt-in" in lower
        or "smoke slice still un-run" in lower
        or "smoke slice un-run" in lower
    ), (
        "PLAN must call out that the smoke-slice LLM opt-in has not been run "
        "(the adversarial-slice credentialed run is in-repo, but the smoke "
        "path still isn't)."
    )


# ---------------------------------------------------------------------------
# Standard suite must not require a real LLM run
# ---------------------------------------------------------------------------

_LLM_OUTPUT_PATHS: tuple[str, ...] = (
    "reports/llm_smoke_eval.json",
    "reports/llm_candidate_smoke_card.md",
    "traces/local/llm_smoke",
)


def test_no_test_requires_generated_llm_eval_outputs() -> None:
    """Other tests must not depend on artifacts that only exist after a real run."""

    me = Path(__file__).name
    for test_file in TESTS_DIR.glob("**/*.py"):
        if test_file.name == me:
            continue
        content = test_file.read_text()
        for forbidden in _LLM_OUTPUT_PATHS:
            assert forbidden not in content, (
                f"{test_file.name} references {forbidden!r}; the standard "
                "suite must not depend on LLM-run-only artifacts."
            )


def test_llm_output_artifacts_are_not_committed() -> None:
    """No LLM eval artifact should be on disk in the standard repo state."""

    for relative in _LLM_OUTPUT_PATHS:
        path = ROOT / relative
        if relative.endswith("llm_smoke"):
            # Directory may or may not exist; if it does it must be empty.
            if path.exists():
                assert path.is_dir() and not any(path.iterdir()), (
                    f"{relative} exists with contents; standard suite assumes "
                    "no LLM eval has been run."
                )
        else:
            assert not path.exists(), (
                f"{relative} is committed/present; standard suite assumes no LLM "
                "eval has been run. Remove the file or update the test."
            )


def test_no_standard_test_imports_anthropic_unguarded() -> None:
    """No test should top-level-import anthropic; it isn't installed in CI."""

    pattern = re.compile(r"^\s*(?:import anthropic|from anthropic\b)", re.MULTILINE)
    for test_file in TESTS_DIR.glob("**/*.py"):
        content = test_file.read_text()
        assert not pattern.search(content), (
            f"{test_file.name} imports anthropic directly; the standard suite "
            "must not require it. Use monkeypatch on the adapter module instead."
        )


@pytest.mark.parametrize(
    "env_var", ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "BRAINTRUST_API_KEY"]
)
def test_no_test_module_hard_codes_credential_env_var(env_var: str) -> None:
    """Tests must read these vars only via monkeypatch / fixtures, not hard-coded."""

    me = Path(__file__).name
    # It's fine to mention the env var by name (e.g. in monkeypatch.delenv)
    # but no test should rely on its real value. Concretely: no test should
    # read it via `os.environ[VAR]` or `os.getenv(VAR)` literally.
    forbidden = re.compile(
        rf'(?:os\.environ\[\s*[\'"]?{env_var}[\'"]?\s*\]|os\.getenv\([\'"]?{env_var}[\'"]?)'
    )
    for test_file in TESTS_DIR.glob("**/*.py"):
        if test_file.name == me:
            continue
        content = test_file.read_text()
        assert not forbidden.search(content), (
            f"{test_file.name} reads {env_var!r} directly from the environment; "
            "tests must not depend on real credentials."
        )
