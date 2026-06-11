"""Credential-free tests for the wired-not-run gold-pass + replay builder.

The credentialed grader pass (scripts/run_grader_gold_pass.py) is exercised here
with a FAKE judge (no API key, no tokens) to prove two things hold before any
real spend:

1. The grader prompt withholds the answer key — gold label, reason code, leaking
   category tags, and expected/prohibited behavior never reach the model.
2. The raw->public-safe replay (scripts/build_grader_gold_replay.py) strips
   draft-bearing rationale/evidence_spans and yields a fixture the scorer reads.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.graders import SemanticDecision
from evals.grader_gold_scorer import load_gold, load_verdicts, score
from evals.semantic_model_adapter import SemanticAdapterResponse
from scripts.build_grader_gold_replay import build_replay
from scripts.run_grader_gold_pass import (
    _grader_input_record,
    run_grader_gold_pass,
)

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = (
    ROOT
    / "case_studies"
    / "financial_links_reliability"
    / "grader_validation"
    / "grader_gold.jsonl"
)


def _gold_rows() -> list[dict]:
    return [json.loads(ln) for ln in GOLD_PATH.read_text().splitlines() if ln.strip()]


class _FakeJudge:
    """Records every prompt it sees and returns a canned decision."""

    def __init__(self, verdict_for):
        self.prompts: list[str] = []
        self._verdict_for = verdict_for

    def __call__(self, prompt: str, **kwargs) -> SemanticAdapterResponse:
        self.prompts.append(prompt)
        flag = self._verdict_for(prompt)
        return SemanticAdapterResponse(
            decision=SemanticDecision(
                makes_unsupported_claim=flag,
                confidence=0.9,
                rationale="FAKE rationale quoting the draft text for stripping test",
                evidence_spans=["FAKE span from draft"],
            ),
            input_tokens=100,
            output_tokens=20,
            model="fake-model",
            est_cost_usd=0.001,
            cost_estimation_note="fake",
        )


def test_grader_input_record_carries_state_not_label() -> None:
    row = {
        "gold_id": "gold_fl_001",
        "makes_unsupported_claim": True,
        "claim_or_safe_code": "implied_future_refresh_despite_gate",
        "category_tags": ["paraphrased_overpromise", "future_refresh"],
        "synthetic_context": {
            "consent_state": "expired",
            "aggregator_route_status": "degraded",
            "missing_ids": [],
        },
        "draft_text": "...",
    }
    record = _grader_input_record(row)
    # Only neutral connectivity state survives.
    assert record["synthetic_facts"]["consent_state"] == "expired"
    assert record["synthetic_facts"]["aggregator_route_status"] == "degraded"
    blob = json.dumps(record)
    assert "implied_future_refresh_despite_gate" not in blob
    assert "paraphrased_overpromise" not in blob
    assert "makes_unsupported_claim" not in blob


def test_pass_prompts_never_leak_gold_signal() -> None:
    rows = _gold_rows()
    judge = _FakeJudge(lambda _p: False)
    run_grader_gold_pass(rows, decision_fn=judge)
    assert len(judge.prompts) == len(rows)
    joined = "\n".join(judge.prompts)
    # No gold reason code and no leak-prone gold category tag may appear.
    for row in rows:
        assert row["claim_or_safe_code"] not in joined, (
            f"{row['gold_id']}: reason code leaked into grader prompt"
        )
    for leak in ("paraphrased_overpromise", "multi_gate_closed", "restoration_promise"):
        assert leak not in joined, f"gold category tag {leak!r} leaked into prompt"


def test_perfect_fake_judge_round_trips_through_replay_and_scorer(tmp_path: Path) -> None:
    rows = _gold_rows()
    gold = load_gold(GOLD_PATH)
    # Fake an oracle judge: flag exactly the gold-bad drafts (by draft_text match).
    bad_drafts = {r["draft_text"] for r in rows if r["makes_unsupported_claim"]}

    def oracle(prompt: str) -> bool:
        return any(d in prompt for d in bad_drafts)

    raw = run_grader_gold_pass(rows, decision_fn=_FakeJudge(oracle))
    # Raw retains draft-bearing fields.
    sample = next(iter(raw["verdicts"].values()))
    assert sample["rationale"] and sample["evidence_spans"]

    fixture = build_replay(raw, source_label="fake gold-pass")
    # Public-safe: draft-bearing fields stripped.
    for decision in fixture["verdicts"].values():
        assert "rationale" not in decision
        assert "evidence_spans" not in decision

    out = tmp_path / "verdicts.json"
    out.write_text(json.dumps(fixture))
    result = score(gold, load_verdicts(out), verdicts_source="fake")
    # The oracle judge matches gold exactly -> perfect scores.
    assert result["metrics"]["recall"] == 1.0
    assert result["metrics"]["precision"] == 1.0
    assert result["confusion"]["fn"] == 0


def test_replay_rejects_trace_paths() -> None:
    raw = {
        "verdicts": {
            "gold_fl_001": {
                "makes_unsupported_claim": True,
                "confidence": 0.5,
                "rationale": "see traces/local/llm_x/case.json",
                "evidence_spans": [],
            }
        }
    }
    # rationale is dropped, so the path must not survive into the fixture.
    fixture = build_replay(raw, source_label="x")
    assert "traces/local/" not in json.dumps(fixture)
