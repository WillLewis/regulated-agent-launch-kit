.PHONY: help setup test scaffold-test lint dataset-test eval-smoke eval-smoke-baseline eval-smoke-improved eval-card-smoke eval-v0-baseline eval-v0-improved eval-card-v0 regression-seed-v0 regression-check-v0 redact-v0 evidence-pack-v0

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
	@echo "  regression-seed-v0   regenerate the committed regression JSONL from a fresh baseline v0 eval"
	@echo "  regression-check-v0  validate regressions_v0.jsonl and assert improved_v0 passes every regression"
	@echo "  redact-v0            redact the three baseline v0 failing traces under traces/redacted/baseline_v0/"
	@echo "  evidence-pack-v0     assemble the public-safe evidence pack at evidence_packs/financial_links_v0/"
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
		--regressions case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--out reports/v0_eval_card.md

regression-seed-v0: eval-v0-baseline
	@rm -f case_studies/financial_links_reliability/evals/regressions_v0.jsonl
	uv run python scripts/incident_to_regression.py \
		--eval-report reports/baseline_v0_eval.json \
		--case-id case_fl_v0_005 \
		--out case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--append
	uv run python scripts/incident_to_regression.py \
		--eval-report reports/baseline_v0_eval.json \
		--case-id case_fl_v0_006 \
		--out case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--append
	uv run python scripts/incident_to_regression.py \
		--eval-report reports/baseline_v0_eval.json \
		--case-id case_fl_v0_010 \
		--out case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--append

regression-check-v0:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/regressions_v0.jsonl
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--traces-out traces/local/regression_v0 \
		--report-out reports/regression_v0_eval.json \
		--agent-system-version improved_v0
	uv run python -c "import json,sys;r=json.load(open('reports/regression_v0_eval.json'));sys.exit(0 if r['failed_case_count']==0 else 1)"

redact-v0: eval-v0-baseline
	@mkdir -p traces/redacted/baseline_v0
	uv run python scripts/redact_trace.py \
		--input traces/local/baseline_v0/case_fl_v0_005.json \
		--policy configs/redaction_policy.yaml \
		--output traces/redacted/baseline_v0/case_fl_v0_005.redacted.json \
		--report-out traces/redacted/baseline_v0/case_fl_v0_005.redaction_report.json
	uv run python scripts/redact_trace.py \
		--input traces/local/baseline_v0/case_fl_v0_006.json \
		--policy configs/redaction_policy.yaml \
		--output traces/redacted/baseline_v0/case_fl_v0_006.redacted.json \
		--report-out traces/redacted/baseline_v0/case_fl_v0_006.redaction_report.json
	uv run python scripts/redact_trace.py \
		--input traces/local/baseline_v0/case_fl_v0_010.json \
		--policy configs/redaction_policy.yaml \
		--output traces/redacted/baseline_v0/case_fl_v0_010.redacted.json \
		--report-out traces/redacted/baseline_v0/case_fl_v0_010.redaction_report.json

evidence-pack-v0: eval-card-v0 regression-check-v0 redact-v0
	uv run python scripts/package_evidence.py \
		--eval-card reports/v0_eval_card.md \
		--baseline-report reports/baseline_v0_eval.json \
		--improved-report reports/improved_v0_eval.json \
		--regressions case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--redacted-traces traces/redacted/baseline_v0 \
		--out evidence_packs/financial_links_v0

lint:
	uv run ruff check .
