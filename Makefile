.PHONY: help setup test scaffold-test lint dataset-test eval-smoke eval-smoke-baseline eval-smoke-improved eval-card-smoke eval-v0-baseline eval-v0-improved eval-card-v0

# The basic targets (test, scaffold-test, dataset-test, eval-smoke,
# eval-smoke-baseline, eval-smoke-improved) must succeed without
# external credentials. Braintrust-backed evals require .env (see
# .env.example).

help:
	@echo "Available targets:"
	@echo "  setup                install runtime + dev dependencies via uv"
	@echo "  test                 run the full pytest suite"
	@echo "  scaffold-test        run only the scaffold contract test"
	@echo "  dataset-test         validate synthetic Financial Links JSONL datasets"
	@echo "  eval-smoke           run the local offline eval on the smoke slice (improved profile)"
	@echo "  eval-smoke-baseline  run the smoke eval against the deliberately weak baseline profile"
	@echo "  eval-smoke-improved  run the smoke eval against the policy-compliant improved profile"
	@echo "  eval-card-smoke      run baseline + improved smoke evals, then render the comparison eval card"
	@echo "  eval-v0-baseline     run the full v0 dataset eval against the baseline profile"
	@echo "  eval-v0-improved     run the full v0 dataset eval against the improved profile"
	@echo "  eval-card-v0         run baseline + improved v0 evals, then render the comparison eval card"
	@echo "  lint                 run ruff over the repo"
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

eval-smoke-baseline:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/smoke.jsonl \
		--traces-out traces/local/baseline_smoke \
		--report-out reports/baseline_smoke_eval.json \
		--agent-system-version baseline_v0

eval-smoke-improved:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/smoke.jsonl \
		--traces-out traces/local/improved_smoke \
		--report-out reports/improved_smoke_eval.json \
		--agent-system-version improved_v0

eval-card-smoke: eval-smoke-baseline eval-smoke-improved
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/baseline_smoke_eval.json \
		--improved-report reports/improved_smoke_eval.json \
		--out reports/smoke_eval_card.md

eval-v0-baseline:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/data/cases_v0.jsonl \
		--traces-out traces/local/baseline_v0 \
		--report-out reports/baseline_v0_eval.json \
		--agent-system-version baseline_v0

eval-v0-improved:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/data/cases_v0.jsonl \
		--traces-out traces/local/improved_v0 \
		--report-out reports/improved_v0_eval.json \
		--agent-system-version improved_v0

eval-card-v0: eval-v0-baseline eval-v0-improved
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/baseline_v0_eval.json \
		--improved-report reports/improved_v0_eval.json \
		--out reports/v0_eval_card.md

lint:
	uv run ruff check .
