"""Tests for the LLM cost-rate table at ``configs/llm_cost_rates.yaml``.

The rate table is the single source of truth for converting
``response.usage`` tokens into an estimated USD cost. These tests lock
in:

1. The committed table loads and has the shape ``llm_adapter`` expects.
2. The known-model arithmetic is correct (input + output USD per
   million tokens, divided by ``per_tokens``).
3. The fallback model is exercised when the requested model is unknown
   AND the rate table declares a usable ``fallback_model``.
4. An unknown model with no fallback raises ``LLMAdapterConfigError``.
5. A malformed table raises ``LLMAdapterConfigError`` (fails closed).
6. The numbers themselves are labeled as public list prices and
   carry an ``as_of`` date — no partner-negotiated or enterprise rate
   is implied.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.agents.llm_adapter import (
    COST_NOTE_FALLBACK,
    COST_NOTE_RATE_USED,
    COST_RATES_PATH,
    LLMAdapterConfigError,
    _estimate_cost_usd,
    _load_rate_table,
)


ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Committed rate-table shape and labeling
# ---------------------------------------------------------------------------


def test_committed_rate_table_loads() -> None:
    table = _load_rate_table()
    assert isinstance(table, dict)
    assert "models" in table and isinstance(table["models"], dict)
    assert table["models"], "rate table must declare at least one model"


def test_committed_rate_table_is_labeled_as_public_list_price() -> None:
    raw = yaml.safe_load(COST_RATES_PATH.read_text())
    # The disclaimer / labeling is in the YAML comments AND in the
    # structured fields. The structured fields are the part we can
    # assert on without parsing comments.
    assert raw.get("source", "").lower().startswith("anthropic public list prices")
    assert raw.get("as_of"), "rate table must declare an as_of date"
    assert raw.get("currency", "").upper() == "USD"


def test_committed_rate_table_declares_default_and_fallback_models() -> None:
    table = _load_rate_table()
    assert table.get("default_model") in table["models"], (
        "default_model must be in the models map"
    )
    assert table.get("fallback_model") in table["models"], (
        "fallback_model must be in the models map"
    )


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def test_known_model_cost_arithmetic() -> None:
    table = _load_rate_table()
    # Pick the default model to avoid hardcoding a specific tier.
    model = table["default_model"]
    rate = table["models"][model]
    cost, resolved, note = _estimate_cost_usd(
        model=model,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        rate_table=table,
    )
    expected = float(rate["input_usd_per_mtok"]) + float(rate["output_usd_per_mtok"])
    assert cost == round(expected, 6)
    assert resolved == model
    assert note == COST_NOTE_RATE_USED


def test_zero_tokens_yields_zero_cost() -> None:
    table = _load_rate_table()
    cost, resolved, note = _estimate_cost_usd(
        model=table["default_model"],
        input_tokens=0,
        output_tokens=0,
        rate_table=table,
    )
    assert cost == 0.0
    assert resolved == table["default_model"]
    assert note == COST_NOTE_RATE_USED


# ---------------------------------------------------------------------------
# Fallback + unknown-model behavior
# ---------------------------------------------------------------------------


def test_unknown_model_uses_fallback_when_declared(tmp_path: Path) -> None:
    table = {
        "per_tokens": 1_000_000,
        "default_model": "claude-sonnet-4-5",
        "fallback_model": "claude-sonnet-4-5",
        "models": {
            "claude-sonnet-4-5": {
                "input_usd_per_mtok": 3.0,
                "output_usd_per_mtok": 15.0,
            }
        },
    }
    cost, resolved, note = _estimate_cost_usd(
        model="claude-future-tier",
        input_tokens=1_000_000,
        output_tokens=0,
        rate_table=table,
    )
    assert cost == 3.0
    assert resolved == "claude-sonnet-4-5"
    assert note == COST_NOTE_FALLBACK


def test_unknown_model_without_fallback_raises() -> None:
    table = {
        "per_tokens": 1_000_000,
        "models": {
            "claude-sonnet-4-5": {
                "input_usd_per_mtok": 3.0,
                "output_usd_per_mtok": 15.0,
            }
        },
    }
    with pytest.raises(LLMAdapterConfigError) as exc:
        _estimate_cost_usd(
            model="claude-future-tier",
            input_tokens=100,
            output_tokens=50,
            rate_table=table,
        )
    assert "fallback_model" in str(exc.value)


# ---------------------------------------------------------------------------
# Malformed table fails closed
# ---------------------------------------------------------------------------


def test_missing_table_path_raises(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist.yaml"
    with pytest.raises(LLMAdapterConfigError) as exc:
        _load_rate_table(nonexistent)
    assert "rate table not found" in str(exc.value)


def test_non_mapping_table_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- not_a_mapping\n")
    with pytest.raises(LLMAdapterConfigError) as exc:
        _load_rate_table(bad)
    assert "YAML mapping" in str(exc.value)


def test_table_missing_models_section_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("currency: USD\n")
    with pytest.raises(LLMAdapterConfigError) as exc:
        _load_rate_table(bad)
    assert "`models`" in str(exc.value)
