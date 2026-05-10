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
