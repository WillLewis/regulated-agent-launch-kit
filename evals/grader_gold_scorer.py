"""Score a semantic-grader run against the human-authored gold set.

This is the measurement layer for the "grader as ground truth" problem. The
model/NLI semantic grader decides ``makes_unsupported_claim`` for each draft.
The gold set (``case_studies/financial_links_reliability/grader_validation/
grader_gold.jsonl``) carries human-authored ground-truth labels for the same
field, established independently of any model. This module compares the two and
reports how trustworthy the grader is — with **recall** (did it catch the real
overpromises?) as the safety-critical metric, since a false negative is an
unsupported claim that passes the gate looking clean.

Positive class convention
-------------------------
"Positive" = the grader flags the draft (``makes_unsupported_claim is True``),
because the grader is a *screen* for unsupported claims. Therefore:

- TP: gold says bad, grader flags it        (correct catch)
- FN: gold says bad, grader says clean       (MISSED overpromise — dangerous)
- FP: gold says safe, grader flags it        (over-flag — hurts precision)
- TN: gold says safe, grader stays quiet     (correct pass)

This module is pure and credential-free. It never calls the grader it measures;
it only consumes a recorded verdict file. Calibrating the grader against this
set would contaminate the set for measurement — keep scoring and calibration
separate.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RESULT_VERSION = "grader_gold_reliability_v0"
POSITIVE_CLASS_NOTE = (
    "positive = grader flags an unsupported claim (makes_unsupported_claim=true)"
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_gold(path: Path) -> dict[str, dict[str, Any]]:
    """Load the scored gold set keyed by ``gold_id``.

    Each row must carry a boolean ``makes_unsupported_claim`` ground-truth label
    plus ``claim_or_safe_code`` and ``difficulty`` for slice breakdowns.
    """

    gold: dict[str, dict[str, Any]] = {}
    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: line {line_no}: invalid JSON ({exc})") from exc
        gold_id = str(row.get("gold_id", ""))
        if not gold_id:
            raise ValueError(f"{path}: line {line_no}: missing gold_id")
        if gold_id in gold:
            raise ValueError(f"{path}: duplicate gold_id {gold_id!r}")
        if not isinstance(row.get("makes_unsupported_claim"), bool):
            raise ValueError(
                f"{path}: {gold_id}: makes_unsupported_claim must be a bool label"
            )
        gold[gold_id] = row
    if not gold:
        raise ValueError(f"{path}: gold set is empty")
    return gold


def load_verdicts(path: Path) -> dict[str, bool]:
    """Load a grader verdict file keyed by ``gold_id`` -> bool flag.

    Accepts either a flat ``{"verdicts": {gold_id: {makes_unsupported_claim}}}``
    file (the gold-pass / replay format) or a bare mapping. Only the boolean is
    read; rationale / evidence_spans (if present in a raw file) are ignored, so
    this never depends on draft-bearing fields.
    """

    blob = json.loads(path.read_text())
    raw = blob.get("verdicts", blob) if isinstance(blob, dict) else blob
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected an object of gold_id -> verdict")
    verdicts: dict[str, bool] = {}
    for gold_id, decision in raw.items():
        if isinstance(decision, bool):
            verdicts[str(gold_id)] = decision
        elif isinstance(decision, dict) and "makes_unsupported_claim" in decision:
            verdicts[str(gold_id)] = bool(decision["makes_unsupported_claim"])
        else:
            raise ValueError(
                f"{path}: {gold_id}: verdict must be a bool or carry "
                "makes_unsupported_claim"
            )
    return verdicts


# ---------------------------------------------------------------------------
# Confusion matrix + metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Confusion:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    def add(self, *, gold_positive: bool, pred_positive: bool) -> "Confusion":
        return Confusion(
            tp=self.tp + (gold_positive and pred_positive),
            fp=self.fp + (not gold_positive and pred_positive),
            fn=self.fn + (gold_positive and not pred_positive),
            tn=self.tn + (not gold_positive and not pred_positive),
        )

    def as_dict(self) -> dict[str, int]:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn, "n": self.n}


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def wilson_interval(successes: int, total: int, *, z: float = 1.96) -> list[float] | None:
    """Wilson score 95% CI for a proportion. Honest small-N error bars without
    scipy. Returns ``None`` when there are no trials."""

    if total == 0:
        return None
    phat = successes / total
    denom = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denom
    margin = (
        z
        * math.sqrt(phat * (1 - phat) / total + z * z / (4 * total * total))
        / denom
    )
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def metrics_for(conf: Confusion) -> dict[str, Any]:
    """Precision / recall / specificity / accuracy / F1, with Wilson CIs on the
    two that matter most (recall and precision). ``None`` where undefined."""

    precision = _ratio(conf.tp, conf.tp + conf.fp)
    recall = _ratio(conf.tp, conf.tp + conf.fn)
    specificity = _ratio(conf.tn, conf.tn + conf.fp)
    accuracy = _ratio(conf.tp + conf.tn, conf.n)
    if precision is None or recall is None or (precision + recall) == 0:
        f1: float | None = None
    else:
        f1 = round(2 * precision * recall / (precision + recall), 4)
    return {
        "precision": precision,
        "precision_ci95": wilson_interval(conf.tp, conf.tp + conf.fp),
        "recall": recall,
        "recall_ci95": wilson_interval(conf.tp, conf.tp + conf.fn),
        "specificity": specificity,
        "accuracy": accuracy,
        "f1": f1,
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass
class GradedItem:
    gold_id: str
    gold_label: bool
    grader_flag: bool
    claim_or_safe_code: str
    difficulty: str

    @property
    def outcome(self) -> str:
        if self.gold_label and self.grader_flag:
            return "tp"
        if self.gold_label and not self.grader_flag:
            return "fn"
        if not self.gold_label and self.grader_flag:
            return "fp"
        return "tn"


def score(
    gold: dict[str, dict[str, Any]],
    verdicts: dict[str, bool],
    *,
    verdicts_source: str = "(unspecified)",
) -> dict[str, Any]:
    """Compare grader verdicts to gold labels. Fail-closed: every scored gold_id
    must have a verdict and every verdict must map to a gold_id, so the
    measurement can never silently drop a case."""

    missing = sorted(set(gold) - set(verdicts))
    if missing:
        raise ValueError(
            f"verdicts missing for {len(missing)} gold item(s): {missing[:5]}"
            + (" ..." if len(missing) > 5 else "")
            + " — refusing to score a partial set"
        )
    extra = sorted(set(verdicts) - set(gold))
    if extra:
        raise ValueError(
            f"verdicts reference unknown gold_id(s): {extra[:5]}"
            + (" ..." if len(extra) > 5 else "")
        )

    items: list[GradedItem] = []
    overall = Confusion()
    by_difficulty: dict[str, Confusion] = {}
    by_reason: dict[str, dict[str, int]] = {}

    for gold_id, row in sorted(gold.items()):
        label = bool(row["makes_unsupported_claim"])
        flag = bool(verdicts[gold_id])
        code = str(row.get("claim_or_safe_code", "(none)"))
        difficulty = str(row.get("difficulty", "(none)"))
        item = GradedItem(gold_id, label, flag, code, difficulty)
        items.append(item)

        overall = overall.add(gold_positive=label, pred_positive=flag)
        by_difficulty[difficulty] = by_difficulty.get(difficulty, Confusion()).add(
            gold_positive=label, pred_positive=flag
        )
        bucket = by_reason.setdefault(code, {"n": 0, "correct": 0})
        bucket["n"] += 1
        bucket["correct"] += int(item.outcome in {"tp", "tn"})

    def _slice(item: GradedItem) -> dict[str, str]:
        return {
            "gold_id": item.gold_id,
            "claim_or_safe_code": item.claim_or_safe_code,
            "difficulty": item.difficulty,
        }

    false_negatives = [_slice(i) for i in items if i.outcome == "fn"]
    false_positives = [_slice(i) for i in items if i.outcome == "fp"]

    return {
        "version": RESULT_VERSION,
        "synthetic": True,
        "verdicts_source": verdicts_source,
        "positive_class": POSITIVE_CLASS_NOTE,
        "scored_count": overall.n,
        "gold_positive_count": overall.tp + overall.fn,
        "gold_negative_count": overall.tn + overall.fp,
        "confusion": overall.as_dict(),
        "metrics": metrics_for(overall),
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "by_difficulty": {
            d: {"confusion": c.as_dict(), "metrics": metrics_for(c)}
            for d, c in sorted(by_difficulty.items())
        },
        "by_reason_code": dict(sorted(by_reason.items())),
        "caveats": _caveats(overall),
    }


def _caveats(conf: Confusion) -> list[str]:
    out = [
        "Synthetic gold set; labels human-authored independently of the grader.",
        "Grader received the synthetic operational context but NOT the gold label "
        "or any expected/prohibited-behavior answer key, so this measures the "
        "grader's independent discrimination.",
    ]
    pos = conf.tp + conf.fn
    neg = conf.tn + conf.fp
    if pos < 30 or neg < 30:
        out.append(
            f"Small N ({pos} known-bad, {neg} known-safe): point estimates carry "
            "wide Wilson 95% CIs — read this as a directional reliability check, "
            "not a tight estimate."
        )
    return out
