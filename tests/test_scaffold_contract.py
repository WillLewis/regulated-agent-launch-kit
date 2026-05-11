from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_starter_docs_exist() -> None:
    required = [
        "README.md",
        "PLAN.md",
        "PLAN_v3_openai_tdl_fde.md",
        "AGENTS.md",
        "AGENT.md",
        "CLAUDE.md",
        ".gitignore",
    ]

    for relative_path in required:
        assert (ROOT / relative_path).exists(), relative_path


def test_private_thesis_is_referenced_but_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text()
    plan = (ROOT / "PLAN_v3_openai_tdl_fde.md").read_text()
    claude = (ROOT / "CLAUDE.md").read_text()
    agents = (ROOT / "AGENTS.md").read_text()

    assert ".project-memory/" in gitignore
    assert ".project-memory/goal-thesis.md" in plan
    assert ".project-memory/goal-thesis.md" in claude
    assert ".project-memory/goal-thesis.md" in agents


def test_required_scaffold_paths_exist() -> None:
    required_dirs = [
        "app/agents",
        "app/tools",
        "case_studies/financial_links_reliability",
        "case_studies/credit_wellness_offer_activation",
        "case_studies/privacy_identity_alert_triage",
        "configs",
        "deployment",
        "evals",
        "scripts",
        "reports",
        "evidence_packs",
        "web",
        ".claude/agents",
        ".claude/hooks",
    ]

    for relative_path in required_dirs:
        assert (ROOT / relative_path).is_dir(), relative_path


def test_env_example_documents_braintrust() -> None:
    env_example = ROOT / ".env.example"
    assert env_example.exists(), ".env.example missing"
    content = env_example.read_text()
    assert "BRAINTRUST_API_KEY" in content
    assert "BRAINTRUST_PROJECT" in content


def test_agents_md_has_codex_review_section() -> None:
    """Codex cannot read .claude/agents/, so review responsibilities must
    live in AGENTS.md as well."""
    agents = (ROOT / "AGENTS.md").read_text()
    assert "Codex review responsibilities" in agents
    for required_subsection in (
        "Deployment architecture critic",
        "Eval-loop reviewer",
        "Redaction / evidence reviewer",
    ):
        assert required_subsection in agents, required_subsection
    # AGENT.md (singular alias) must stay in sync with AGENTS.md so tools
    # that look for the singular form get the same content.
    assert (ROOT / "AGENT.md").read_text() == agents


def test_evaluator_and_grader_skeletons_importable() -> None:
    from app import evaluator, schemas
    from evals import graders

    assert callable(getattr(evaluator, "evaluate", None))
    assert callable(getattr(graders, "grade_schema_validity", None))
    assert hasattr(schemas, "EvaluatorReport")
    assert hasattr(schemas, "GraderResult")


def test_evaluator_output_distinct_from_grader_output() -> None:
    """Architecture rule from AGENTS.md: runtime evaluator output and
    offline grader output must be different structured types."""
    from app.evaluator import evaluate
    from app.schemas import EvaluatorReport, GraderResult
    from evals.graders import grade_schema_validity

    assert EvaluatorReport is not GraderResult

    grader_fields = set(GraderResult.model_fields)
    assert {
        "passed",
        "score",
        "severity",
        "failure_label",
        "explanation",
        "evidence",
    } <= grader_fields, "GraderResult missing AGENTS.md required shape"

    evaluator_fields = set(EvaluatorReport.model_fields)
    assert "passed" not in evaluator_fields
    assert "score" not in evaluator_fields

    output = {"summary": "ok"}
    required = ["summary", "risk_band"]
    runtime_report = evaluate(output, required_fields=required)
    offline_result = grade_schema_validity(output, required_fields=required)
    assert isinstance(runtime_report, EvaluatorReport)
    assert isinstance(offline_result, GraderResult)
    assert not runtime_report.all_ok
    assert offline_result.failure_label == "SCHEMA_VIOLATION"
