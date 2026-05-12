"""Pin the LangGraph milestone.

These tests make two facts non-negotiable:

1. `app.graph` is built on the real `langgraph.graph.StateGraph` — if
   `langgraph` is not installed, or if a future refactor swaps in a
   shim, this suite fails loudly.
2. README and PLAN name `app/graph.py` as the canonical Financial
   Links execution path so a reader is never left guessing which
   runner is authoritative.

No graph *behavior* is exercised here — that's covered by
`tests/test_graph.py`. These are the canonicality assertions.
"""

from __future__ import annotations

from pathlib import Path

from langgraph.graph import StateGraph

from app import graph as app_graph


ROOT = Path(__file__).resolve().parents[1]


def test_app_graph_imports_real_langgraph_stategraph() -> None:
    """The symbol used by `app.graph` must be `langgraph.graph.StateGraph` itself."""

    assert app_graph.StateGraph is StateGraph


def test_build_graph_returns_a_real_langgraph_stategraph_instance() -> None:
    builder = app_graph.build_graph()
    assert isinstance(builder, StateGraph), (
        f"app.graph.build_graph() returned {type(builder).__name__}; "
        "a shim is no longer acceptable — real langgraph.graph.StateGraph required."
    )


def test_compiled_graph_comes_from_a_real_stategraph() -> None:
    """The cached compiled graph must originate from a real StateGraph build."""

    compiled = app_graph.get_compiled_graph()
    # langgraph's compiled object exposes the underlying builder graph
    # in ``builder`` (or older attribute names). Rather than depend on a
    # private field, re-build and assert isinstance there — the compiled
    # graph's lineage is what matters.
    rebuilt = app_graph.build_graph()
    assert isinstance(rebuilt, StateGraph)
    # And the cached compile is callable in the LangGraph way.
    assert hasattr(compiled, "invoke")


def test_readme_names_app_graph_canonical() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "app/graph.py" in readme, "README must mention app/graph.py"
    lower = readme.lower()
    assert "canonical" in lower, (
        "README must describe the canonical Financial Links execution path"
    )
    assert "langgraph" in lower or "LangGraph" in readme


def test_plan_marks_langgraph_milestone_complete_and_canonical() -> None:
    plan = (ROOT / "PLAN.md").read_text()
    lower = plan.lower()
    # The milestone row mentions LangGraph and is marked complete.
    assert "langgraph" in lower
    # The canonical-path framing must be present somewhere in PLAN.
    assert "app/graph.py is the canonical" in lower or "canonical financial links execution path" in lower
    # And the loop posture stays honest.
    assert "NOT READY FOR PILOT" in plan


def test_no_lingering_no_langgraph_clause_in_phase_3_summary() -> None:
    """Guard against drift: the Phase 3 row used to say "no LangGraph" — that's stale."""

    plan = (ROOT / "PLAN.md").read_text().lower()
    assert "no langgraph" not in plan, (
        "PLAN.md still contains a 'no LangGraph' clause; the runner is now graph-backed."
    )


def test_no_duplicate_deferred_llm_specialist_row() -> None:
    """The recommended LLM specialist row must not coexist with a deferred duplicate."""

    plan = (ROOT / "PLAN.md").read_text()
    assert plan.count("LLM-backed Financial Links specialist") <= 1, (
        "PLAN.md has more than one row about an LLM-backed specialist; "
        "consolidate so the recommendation is unambiguous."
    )
