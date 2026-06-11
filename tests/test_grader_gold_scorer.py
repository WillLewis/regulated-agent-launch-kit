"""Unit tests for the grader-gold scorer (evals/grader_gold_scorer.py).

Pure, deterministic, credential-free. Verifies the confusion-matrix math, the
fail-closed contract, Wilson CIs, and that the scorer runs end-to-end on the
tracked synthetic demo fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.grader_gold_scorer import (
    Confusion,
    load_gold,
    load_verdicts,
    metrics_for,
    score,
    wilson_interval,
)

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "grader_validation"
    / "grader_gold.jsonl"
)
DEMO_VERDICTS = ROOT / "tests" / "fixtures" / "grader_gold" / "demo_grader_verdicts.json"


def _gold(tmp_path: Path, rows: list[dict]) -> dict[str, dict]:
    path = tmp_path / "g.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return load_gold(path)


def _row(gid: str, label: bool, code: str = "x", difficulty: str = "hard") -> dict:
    return {
        "gold_id": gid,
        "makes_unsupported_claim": label,
        "claim_or_safe_code": code,
        "difficulty": difficulty,
    }


# ---------------------------------------------------------------------------
# Confusion + metrics math
# ---------------------------------------------------------------------------


def test_confusion_classifies_four_outcomes() -> None:
    c = Confusion()
    c = c.add(gold_positive=True, pred_positive=True)   # tp
    c = c.add(gold_positive=True, pred_positive=False)  # fn
    c = c.add(gold_positive=False, pred_positive=True)  # fp
    c = c.add(gold_positive=False, pred_positive=False)  # tn
    assert (c.tp, c.fn, c.fp, c.tn, c.n) == (1, 1, 1, 1, 4)


def test_metrics_basic_values() -> None:
    m = metrics_for(Confusion(tp=8, fp=2, fn=2, tn=8))
    assert m["precision"] == 0.8
    assert m["recall"] == 0.8
    assert m["specificity"] == 0.8
    assert m["accuracy"] == 0.8
    assert m["f1"] == 0.8


def test_metrics_undefined_when_denominator_zero() -> None:
    # No positive predictions at all -> precision undefined, recall 0.
    m = metrics_for(Confusion(tp=0, fp=0, fn=5, tn=5))
    assert m["precision"] is None
    assert m["recall"] == 0.0
    assert m["f1"] is None


def test_recall_is_the_miss_sensitive_metric() -> None:
    # A grader that catches 12/14 bad drafts has recall 12/14 regardless of how
    # many safe drafts it leaves alone.
    m = metrics_for(Confusion(tp=12, fp=0, fn=2, tn=14))
    assert m["recall"] == round(12 / 14, 4)
    assert m["specificity"] == 1.0


def test_wilson_interval_brackets_point_estimate() -> None:
    lo, hi = wilson_interval(14, 14)  # perfect recall, small N
    assert lo < 1.0 <= hi  # upper clamped to 1.0, lower well below -> honest CI
    assert wilson_interval(0, 0) is None


# ---------------------------------------------------------------------------
# score(): fail-closed contract
# ---------------------------------------------------------------------------


def test_score_requires_a_verdict_for_every_gold_item(tmp_path: Path) -> None:
    gold = _gold(tmp_path, [_row("a", True), _row("b", False)])
    with pytest.raises(ValueError, match="missing for 1 gold item"):
        score(gold, {"a": True})


def test_score_rejects_unknown_verdict_ids(tmp_path: Path) -> None:
    gold = _gold(tmp_path, [_row("a", True)])
    with pytest.raises(ValueError, match="unknown gold_id"):
        score(gold, {"a": True, "ghost": False})


def test_score_counts_and_lists_disagreements(tmp_path: Path) -> None:
    gold = _gold(
        tmp_path,
        [
            _row("bad_caught", True, code="freshness"),
            _row("bad_missed", True, code="restoration"),  # -> false negative
            _row("safe_quiet", False, code="hedge"),
            _row("safe_flagged", False, code="consent_gate"),  # -> false positive
        ],
    )
    verdicts = {
        "bad_caught": True,
        "bad_missed": False,
        "safe_quiet": False,
        "safe_flagged": True,
    }
    res = score(gold, verdicts, verdicts_source="unit")
    assert res["confusion"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1, "n": 4}
    assert [f["gold_id"] for f in res["false_negatives"]] == ["bad_missed"]
    assert [f["gold_id"] for f in res["false_positives"]] == ["safe_flagged"]
    assert res["false_negatives"][0]["claim_or_safe_code"] == "restoration"


def test_score_breaks_down_by_difficulty(tmp_path: Path) -> None:
    gold = _gold(
        tmp_path,
        [
            _row("h1", True, difficulty="hard"),
            _row("h2", True, difficulty="hard"),
            _row("e1", True, difficulty="easy"),
        ],
    )
    # Grader misses one hard bad draft -> hard recall 1/2, easy recall 1/1.
    res = score(gold, {"h1": True, "h2": False, "e1": True})
    assert res["by_difficulty"]["hard"]["metrics"]["recall"] == 0.5
    assert res["by_difficulty"]["easy"]["metrics"]["recall"] == 1.0


# ---------------------------------------------------------------------------
# End-to-end on the tracked demo fixture
# ---------------------------------------------------------------------------


def test_perfect_grader_against_real_gold_scores_one() -> None:
    gold = load_gold(GOLD_PATH)
    perfect = {gid: row["makes_unsupported_claim"] for gid, row in gold.items()}
    res = score(gold, perfect, verdicts_source="perfect")
    assert res["metrics"]["recall"] == 1.0
    assert res["metrics"]["precision"] == 1.0
    assert res["confusion"]["fn"] == 0


def test_demo_fixture_exercises_both_error_directions() -> None:
    gold = load_gold(GOLD_PATH)
    res = score(gold, load_verdicts(DEMO_VERDICTS), verdicts_source="demo")
    # The committed demo fixture is intentionally imperfect.
    assert res["confusion"]["fn"] >= 1, "demo should encode at least one miss"
    assert res["confusion"]["fp"] >= 1, "demo should encode at least one over-flag"
    assert 0.0 < res["metrics"]["recall"] < 1.0
    assert res["metrics"]["recall_ci95"][0] < res["metrics"]["recall"]


def test_demo_fixture_is_clearly_marked_not_a_real_measurement() -> None:
    blob = json.loads(DEMO_VERDICTS.read_text())
    assert blob.get("demo") is True
    assert "NOT a real" in blob["source"] or "illustrative" in blob["source"].lower()
