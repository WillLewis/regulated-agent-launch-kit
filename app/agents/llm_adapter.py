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
- **Returns usage + estimated cost alongside the text.**
  ``generate_financial_links_draft`` returns an :class:`LLMResponse`
  carrying the model's reply text, input/output token counts, the
  resolved model name, and an estimated USD cost derived from
  ``configs/llm_cost_rates.yaml`` (public list prices; not
  partner-negotiated rates).

For tests, replace ``generate_financial_links_draft`` on this module
via ``monkeypatch.setattr`` — the specialist always looks the function
up through the module so the patch takes effect. Use the
:class:`LLMResponse` helper :meth:`from_text` to wrap a fixed-text fake.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ANTHROPIC_KEY_ENV: str = "ANTHROPIC_API_KEY"
DEFAULT_MODEL_ENV: str = "AGENT_MODEL_DEFAULT"
DEFAULT_FALLBACK_MODEL: str = "claude-sonnet-4-5"
COST_RATES_PATH: Path = Path(__file__).resolve().parents[2] / "configs" / "llm_cost_rates.yaml"
COST_NOTE_RATE_USED: str = "rate_used"
COST_NOTE_FALLBACK: str = "fallback_rate_used"


class LLMAdapterConfigError(RuntimeError):
    """Raised when the LLM adapter is invoked without configured credentials.

    The deterministic profiles never touch this module, so this error
    only fires when a caller has explicitly opted into
    ``llm_candidate_v0`` without setting up credentials or the SDK.
    """


@dataclass(frozen=True)
class LLMResponse:
    """Wraps the LLM adapter's reply: text + token usage + estimated cost.

    ``est_cost_usd`` is computed from ``configs/llm_cost_rates.yaml``
    (Anthropic public list prices). It is **not** a partner-negotiated
    or enterprise-discounted rate; it is a deterministic estimate
    derived from ``response.usage`` tokens.

    ``cost_estimation_note`` is ``"rate_used"`` when the configured model
    is in the rate table, or ``"fallback_rate_used"`` when the adapter
    fell back to ``fallback_model`` because the configured model was
    unknown. Tests and traces should surface the note so an analyst can
    spot drift.
    """

    text: str
    input_tokens: int
    output_tokens: int
    model: str
    est_cost_usd: float
    cost_estimation_note: str = COST_NOTE_RATE_USED

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        model: str = DEFAULT_FALLBACK_MODEL,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> "LLMResponse":
        """Build an :class:`LLMResponse` from a fixed text, used by tests.

        When ``input_tokens`` and ``output_tokens`` are both zero, the
        estimated cost is exactly zero — a clean signal that this
        response did not come from a real model call.
        """

        rate_table = _load_rate_table()
        est_cost_usd, _resolved_model, note = _estimate_cost_usd(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            rate_table=rate_table,
        )
        return cls(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            est_cost_usd=est_cost_usd,
            cost_estimation_note=note,
        )


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


def _load_rate_table(path: Path | None = None) -> dict[str, Any]:
    """Load ``configs/llm_cost_rates.yaml`` and validate its shape.

    The path is overridable so tests can point at a fixture rate
    table without depending on the committed file. Validation is
    intentionally strict: a malformed or missing table fails closed.
    """

    table_path = path or COST_RATES_PATH
    if not table_path.exists():
        raise LLMAdapterConfigError(
            f"llm cost rate table not found at {table_path}; "
            "the llm_candidate_v0 profile cannot estimate cost without it."
        )
    data = yaml.safe_load(table_path.read_text())
    if not isinstance(data, dict):
        raise LLMAdapterConfigError(f"{table_path}: rate table must be a YAML mapping")
    if "models" not in data or not isinstance(data["models"], dict):
        raise LLMAdapterConfigError(
            f"{table_path}: rate table must declare a `models` mapping"
        )
    return data


def _estimate_cost_usd(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    rate_table: dict[str, Any],
) -> tuple[float, str, str]:
    """Return ``(est_cost_usd, resolved_model, note)`` for one usage record.

    Raises :class:`LLMAdapterConfigError` if the model is unknown and the
    rate table declares no usable ``fallback_model``.
    """

    per_tokens_divisor = int(rate_table.get("per_tokens", 1_000_000))
    models: dict[str, Any] = rate_table["models"]

    if model in models:
        rate = models[model]
        note = COST_NOTE_RATE_USED
        resolved = model
    else:
        fallback = rate_table.get("fallback_model")
        if not fallback or fallback not in models:
            raise LLMAdapterConfigError(
                f"llm cost rate table has no entry for model {model!r} and no "
                "usable fallback_model. Add the model under `models:` in "
                f"{COST_RATES_PATH.name} or set `fallback_model` to a known model."
            )
        rate = models[fallback]
        note = COST_NOTE_FALLBACK
        resolved = fallback

    input_usd = float(rate.get("input_usd_per_mtok", 0.0))
    output_usd = float(rate.get("output_usd_per_mtok", 0.0))

    est_cost = (
        input_tokens * input_usd + output_tokens * output_usd
    ) / per_tokens_divisor
    return round(est_cost, 6), resolved, note


def _extract_usage(response: Any) -> tuple[int, int]:
    """Pull ``input_tokens`` / ``output_tokens`` from an Anthropic response.

    Defensive against minor SDK shape drift: missing attributes or
    non-numeric values fall back to zero rather than raising. A
    follow-up could turn that fallback into a hard error once we have
    a richer test fixture, but the current discipline is "always
    report a non-negative integer."
    """

    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0

    def _coerce(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    return _coerce(getattr(usage, "input_tokens", 0)), _coerce(
        getattr(usage, "output_tokens", 0)
    )


def generate_financial_links_draft(
    prompt: str,
    *,
    model: str | None = None,
    timeout_s: float = 30.0,
    max_tokens: int = 512,
) -> LLMResponse:
    """Generate hedged synthetic draft text for a Financial Links case.

    Always raises :class:`LLMAdapterConfigError` unless both an API key
    and the ``anthropic`` SDK are available. On success, returns an
    :class:`LLMResponse` carrying:

    - the extracted text content from the model response;
    - the input/output token counts reported by ``response.usage``;
    - the resolved model name (after fallback resolution if needed);
    - an estimated USD cost derived from the rate table;
    - a ``cost_estimation_note`` that flags fallback-rate usage.
    """

    api_key = _require_credentials()
    anthropic_module = _require_sdk()
    rate_table = _load_rate_table()

    requested_model = (
        model
        or os.environ.get(DEFAULT_MODEL_ENV)
        or rate_table.get("default_model")
        or DEFAULT_FALLBACK_MODEL
    )

    client = anthropic_module.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=requested_model,
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

    input_tokens, output_tokens = _extract_usage(response)
    est_cost_usd, resolved_model, note = _estimate_cost_usd(
        model=requested_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        rate_table=rate_table,
    )
    return LLMResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=resolved_model,
        est_cost_usd=est_cost_usd,
        cost_estimation_note=note,
    )
