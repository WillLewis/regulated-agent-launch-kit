"""Optional LLM adapter for the Financial Links candidate profile.

The deterministic ``baseline_v0`` / ``improved_v0`` proof loop never
touches this module. It exists only to support the
``llm_candidate_v0`` profile (see ``app.agents.profiles``): when that
profile is selected, the specialist agent delegates *only* the
customer-facing ``draft_text`` to this adapter while keeping every
other decision (tool calls, policy citations, approval boundary,
prohibited-action avoidance) deterministic.

Discipline rules this module enforces:

- **Credential-gated.** Missing ``ANTHROPIC_API_KEY`` raises
  ``LLMAdapterConfigError`` with a clear message. No silent fallback.
- **Optional dependency.** The ``anthropic`` SDK is imported lazily so
  the rest of the kit runs without it. If the SDK is missing,
  ``LLMAdapterConfigError`` says how to install it.
- **Never decides approval.** The adapter only generates draft prose;
  approval, escalation, and policy decisions stay in the deterministic
  specialist.

For tests, replace ``generate_financial_links_draft`` on this module
via ``monkeypatch.setattr`` — the specialist always looks the function
up through the module so the patch takes effect.
"""

from __future__ import annotations

import os
from typing import Any


ANTHROPIC_KEY_ENV: str = "ANTHROPIC_API_KEY"
DEFAULT_MODEL_ENV: str = "AGENT_MODEL_DEFAULT"
DEFAULT_FALLBACK_MODEL: str = "claude-sonnet-4-5"


class LLMAdapterConfigError(RuntimeError):
    """Raised when the LLM adapter is invoked without configured credentials.

    The deterministic profiles never touch this module, so this error
    only fires when a caller has explicitly opted into
    ``llm_candidate_v0`` without setting up credentials or the SDK.
    """


def _require_credentials() -> str:
    api_key = os.environ.get(ANTHROPIC_KEY_ENV)
    if not api_key:
        raise LLMAdapterConfigError(
            f"llm_candidate_v0 profile requires {ANTHROPIC_KEY_ENV} in the environment. "
            "See .env.example. The deterministic baseline_v0 / improved_v0 profiles "
            "do not need any credentials."
        )
    return api_key


def _require_sdk() -> Any:
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise LLMAdapterConfigError(
            "llm_candidate_v0 profile requires the 'anthropic' Python SDK. "
            "Install it locally (e.g. `uv pip install anthropic`) and re-run. "
            "The deterministic baseline_v0 / improved_v0 profiles do not need it."
        ) from exc
    return anthropic


def generate_financial_links_draft(
    prompt: str,
    *,
    model: str | None = None,
    timeout_s: float = 30.0,
    max_tokens: int = 512,
) -> str:
    """Generate hedged synthetic draft text for a Financial Links case.

    Always raises ``LLMAdapterConfigError`` unless both an API key and
    the ``anthropic`` SDK are available. On success, returns the
    extracted text content from the model response.
    """

    api_key = _require_credentials()
    anthropic_module = _require_sdk()

    chosen_model = (
        model
        or os.environ.get(DEFAULT_MODEL_ENV)
        or DEFAULT_FALLBACK_MODEL
    )

    client = anthropic_module.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=chosen_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        timeout=timeout_s,
    )

    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    text = "\n".join(part for part in parts if part).strip()
    if not text:
        raise LLMAdapterConfigError(
            "LLM adapter returned an empty response. Check model name / quotas."
        )
    return text
