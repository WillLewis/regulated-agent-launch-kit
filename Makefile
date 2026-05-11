.PHONY: help setup test scaffold-test lint dataset-test eval-smoke

# The basic targets (test, scaffold-test, dataset-test, eval-smoke) must
# succeed without external credentials. Braintrust-backed evals require
# .env (see .env.example).

help:
	@echo "Available targets:"
	@echo "  setup         install runtime + dev dependencies via uv"
	@echo "  test          run the full pytest suite"
	@echo "  scaffold-test run only the scaffold contract test"
	@echo "  dataset-test  validate synthetic Financial Links JSONL datasets"
	@echo "  eval-smoke    run the local offline eval on the smoke slice"
	@echo "  lint          run ruff over the repo"
	@echo ""
	@echo "If uv is not installed, you can run tests directly:"
	@echo "  python -m pytest"

setup:
	uv sync --extra dev

test:
	uv run pytest

scaffold-test:
	uv run pytest tests/test_scaffold_contract.py -v

dataset-test:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/data/cases_v0.jsonl
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/smoke.jsonl

eval-smoke:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/smoke.jsonl \
		--traces-out traces/local/smoke \
		--report-out reports/local_smoke_eval.json

lint:
	uv run ruff check .
