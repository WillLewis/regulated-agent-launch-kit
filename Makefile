.PHONY: help setup test scaffold-test lint dataset-test dataset-test-adversarial dataset-test-adversarial-v1 eval-smoke eval-smoke-baseline eval-smoke-improved eval-card-smoke eval-v0-baseline eval-v0-improved eval-card-v0 eval-adversarial-baseline eval-adversarial-improved eval-card-adversarial eval-adversarial-v1-baseline eval-adversarial-v1-improved eval-card-adversarial-v1 eval-adversarial-v1-baseline-semantic eval-adversarial-v1-improved-semantic semantic-reporting-surface semantic-model-decisions-adversarial-v1-baseline semantic-model-decisions-adversarial-v1-improved eval-adversarial-v1-baseline-semantic-model eval-adversarial-v1-improved-semantic-model semantic-model-reporting-surface regression-seed-v0 regression-check-v0 redact-v0 evidence-pack-v0 check-llm-env eval-smoke-llm eval-card-llm-smoke eval-adversarial-llm eval-card-adversarial-llm redact-llm-adversarial evidence-pack-llm-adversarial eval-adversarial-llm-v1 eval-card-adversarial-llm-v1 redact-llm-adversarial-v1 evidence-pack-llm-adversarial-v1 variance-report-fixture repeat-adversarial-llm-v0 repeat-adversarial-llm-v1 repeat-adversarial-llm-summary

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
	@echo "  dataset-test-adversarial validate the adversarial v0 JSONL slice"
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
	@echo "  eval-adversarial-baseline  run the adversarial slice against baseline_v0"
	@echo "  eval-adversarial-improved  run the adversarial slice against improved_v0"
	@echo "  eval-card-adversarial      run both adversarial evals, then render the comparison eval card"
	@echo "  dataset-test-adversarial-v1  validate the expanded adversarial v1 JSONL slice (12 cases)"
	@echo "  eval-adversarial-v1-baseline  run the adversarial v1 slice against baseline_v0 (deterministic)"
	@echo "  eval-adversarial-v1-improved  run the adversarial v1 slice against improved_v0 (deterministic)"
	@echo "  eval-card-adversarial-v1   run both adversarial v1 evals, then render the comparison eval card"
	@echo "  eval-adversarial-v1-baseline-semantic  run baseline_v0 with fixture-backed semantic audit lane"
	@echo "  eval-adversarial-v1-improved-semantic  run improved_v0 with fixture-backed semantic audit lane"
	@echo "  semantic-reporting-surface render the fixture-backed semantic audit lane as static HTML"
	@echo "  semantic-model-decisions-adversarial-v1-baseline generate opt-in model/NLI semantic decisions for baseline_v0"
	@echo "  semantic-model-decisions-adversarial-v1-improved generate opt-in model/NLI semantic decisions for improved_v0"
	@echo "  eval-adversarial-v1-baseline-semantic-model run baseline_v0 with model/NLI semantic decisions"
	@echo "  eval-adversarial-v1-improved-semantic-model run improved_v0 with model/NLI semantic decisions"
	@echo "  semantic-model-reporting-surface render the opt-in model/NLI semantic audit lane as static HTML"
	@echo ""
	@echo "Opt-in LLM targets (require ANTHROPIC_API_KEY and the anthropic SDK; not in the public proof loop):"
	@echo "  check-llm-env        actionable preflight: verifies ANTHROPIC_API_KEY + anthropic SDK"
	@echo "  eval-smoke-llm       run the smoke eval with profile=llm_candidate_v0 (fails clean if creds missing)"
	@echo "  eval-card-llm-smoke  render improved_v0 vs llm_candidate_v0 comparison card from the smoke reports"
	@echo "  eval-adversarial-llm     run the adversarial slice against llm_candidate_v0 (fails clean if creds missing)"
	@echo "  eval-card-adversarial-llm render improved_v0 vs llm_candidate_v0 comparison card on the adversarial slice"
	@echo "  redact-llm-adversarial   redact every raw LLM adversarial trace under traces/redacted/llm_adversarial/"
	@echo "  evidence-pack-llm-adversarial  assemble the public-safe LLM evidence pack at evidence_packs/financial_links_llm_v0/"
	@echo "  eval-adversarial-llm-v1  run the adversarial slice against llm_candidate_v1 (improved prompt)"
	@echo "  eval-card-adversarial-llm-v1  render the llm_candidate_v0 (Before) vs llm_candidate_v1 (After) prompt-improvement card"
	@echo "  redact-llm-adversarial-v1  redact every raw v1 LLM trace under traces/redacted/llm_adversarial_v1/ (no LLM call)"
	@echo "  evidence-pack-llm-adversarial-v1  assemble the public-safe v1 evidence pack at evidence_packs/financial_links_llm_v1/ (no LLM call)"
	@echo "  variance-report-fixture  demo: aggregate tests/fixtures/llm_repeats/*.json (no LLM call; demo output gitignored)"
	@echo ""
	@echo "Opt-in CREDENTIALED repeat-run capture (real Anthropic API calls; costs money; not in CI):"
	@echo "  RUNS=5 make repeat-adversarial-llm-v0  capture N llm_candidate_v0 adversarial runs (RUNS defaults to 5)"
	@echo "  RUNS=5 make repeat-adversarial-llm-v1  capture N llm_candidate_v1 adversarial runs (RUNS defaults to 5)"
	@echo "  make repeat-adversarial-llm-summary    aggregate every captured repeat run into a public-safe summary"
	@echo ""
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

dataset-test-adversarial:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/adversarial_v0.jsonl

dataset-test-adversarial-v1:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/adversarial_v1.jsonl

# ---- Deterministic adversarial v1 targets (credential-free) ---------------
# These targets run the deterministic baseline_v0 / improved_v0 profiles
# against the expanded 12-case adversarial v1 slice. They never call an
# LLM and never depend on credentials. The corresponding LLM target for
# this slice is intentionally NOT wired in this chunk — adversarial v1
# is opt-in territory for a future credentialed run.

eval-adversarial-v1-baseline:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/baseline_adversarial_v1 \
		--report-out reports/baseline_adversarial_v1_eval.json \
		--agent-system-version baseline_v0

eval-adversarial-v1-improved:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/improved_adversarial_v1 \
		--report-out reports/improved_adversarial_v1_eval.json \
		--agent-system-version improved_v0

eval-card-adversarial-v1: eval-adversarial-v1-baseline eval-adversarial-v1-improved
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/baseline_adversarial_v1_eval.json \
		--improved-report reports/improved_adversarial_v1_eval.json \
		--out reports/adversarial_v1_eval_card.md

eval-adversarial-v1-baseline-semantic:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/baseline_adversarial_v1_semantic \
		--report-out reports/baseline_adversarial_v1_semantic_eval.json \
		--agent-system-version baseline_v0 \
		--semantic-decisions case_studies/financial_links_reliability/evals/adversarial_v1_semantic_decisions.json

eval-adversarial-v1-improved-semantic:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/improved_adversarial_v1_semantic \
		--report-out reports/improved_adversarial_v1_semantic_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions case_studies/financial_links_reliability/evals/adversarial_v1_semantic_decisions.json

semantic-reporting-surface: eval-adversarial-v1-baseline-semantic eval-adversarial-v1-improved-semantic
	uv run python scripts/render_semantic_reporting_surface.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--baseline-report reports/baseline_adversarial_v1_semantic_eval.json \
		--improved-report reports/improved_adversarial_v1_semantic_eval.json \
		--out reports/adversarial_v1_semantic_reporting_surface.html

# ---- Opt-in model/NLI semantic adapter targets (credentialed) ---------------
# These targets use ANTHROPIC_API_KEY via scripts/generate_semantic_decisions.py
# to produce SemanticDecision JSON for the already-generated deterministic
# adversarial v1 reports. Outputs are gitignored by default because they are
# model-generated local audit artifacts.

semantic-model-decisions-adversarial-v1-baseline: check-llm-env eval-adversarial-v1-baseline
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--eval-report reports/baseline_adversarial_v1_eval.json \
		--out reports/semantic_model_decisions/adversarial_v1_baseline.json

semantic-model-decisions-adversarial-v1-improved: check-llm-env eval-adversarial-v1-improved
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--eval-report reports/improved_adversarial_v1_eval.json \
		--out reports/semantic_model_decisions/adversarial_v1_improved.json

eval-adversarial-v1-baseline-semantic-model: semantic-model-decisions-adversarial-v1-baseline
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/baseline_adversarial_v1_semantic_model \
		--report-out reports/baseline_adversarial_v1_semantic_model_eval.json \
		--agent-system-version baseline_v0 \
		--semantic-decisions reports/semantic_model_decisions/adversarial_v1_baseline.json

eval-adversarial-v1-improved-semantic-model: semantic-model-decisions-adversarial-v1-improved
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/improved_adversarial_v1_semantic_model \
		--report-out reports/improved_adversarial_v1_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/semantic_model_decisions/adversarial_v1_improved.json

semantic-model-reporting-surface: eval-adversarial-v1-baseline-semantic-model eval-adversarial-v1-improved-semantic-model
	uv run python scripts/render_semantic_reporting_surface.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--baseline-report reports/baseline_adversarial_v1_semantic_model_eval.json \
		--improved-report reports/improved_adversarial_v1_semantic_model_eval.json \
		--baseline-decisions reports/semantic_model_decisions/adversarial_v1_baseline.json \
		--improved-decisions reports/semantic_model_decisions/adversarial_v1_improved.json \
		--out reports/adversarial_v1_semantic_model_reporting_surface.html

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

eval-adversarial-baseline:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v0.jsonl \
		--traces-out traces/local/baseline_adversarial \
		--report-out reports/baseline_adversarial_eval.json \
		--agent-system-version baseline_v0

eval-adversarial-improved:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v0.jsonl \
		--traces-out traces/local/improved_adversarial \
		--report-out reports/improved_adversarial_eval.json \
		--agent-system-version improved_v0

eval-card-adversarial: eval-adversarial-baseline eval-adversarial-improved
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/baseline_adversarial_eval.json \
		--improved-report reports/improved_adversarial_eval.json \
		--out reports/adversarial_eval_card.md

evidence-pack-v0: eval-card-v0 regression-check-v0 redact-v0
	uv run python scripts/package_evidence.py \
		--eval-card reports/v0_eval_card.md \
		--baseline-report reports/baseline_v0_eval.json \
		--improved-report reports/improved_v0_eval.json \
		--regressions case_studies/financial_links_reliability/evals/regressions_v0.jsonl \
		--redacted-traces traces/redacted/baseline_v0 \
		--out evidence_packs/financial_links_v0

# ---- Opt-in LLM candidate targets ------------------------------------------
# These never run in CI and no other Make target depends on them. They
# require ANTHROPIC_API_KEY + the anthropic SDK; the preflight gate fails
# clean if either is missing — no silent fallback to a deterministic
# profile. See README "Optional LLM candidate run" for the exact opt-in
# sequence.

check-llm-env:
	uv run python scripts/check_llm_env.py

eval-smoke-llm: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/smoke.jsonl \
		--traces-out traces/local/llm_smoke \
		--report-out reports/llm_smoke_eval.json \
		--agent-system-version llm_candidate_v0

eval-card-llm-smoke: eval-smoke-improved eval-smoke-llm
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/improved_smoke_eval.json \
		--improved-report reports/llm_smoke_eval.json \
		--out reports/llm_candidate_smoke_card.md

eval-adversarial-llm: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v0.jsonl \
		--traces-out traces/local/llm_adversarial \
		--report-out reports/llm_adversarial_eval.json \
		--agent-system-version llm_candidate_v0

eval-card-adversarial-llm: eval-adversarial-improved eval-adversarial-llm
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/improved_adversarial_eval.json \
		--improved-report reports/llm_adversarial_eval.json \
		--baseline-label Reference \
		--improved-label Candidate \
		--out reports/llm_adversarial_eval_card.md

# ---- Redaction + evidence pack for the opt-in LLM adversarial run ----------
# These targets operate on on-disk artifacts only — they do NOT call the
# LLM or require credentials. They assume `make eval-adversarial-llm`
# has already produced reports/llm_adversarial_eval.json and the raw
# traces under traces/local/llm_adversarial/. Both raw inputs are
# gitignored; the redacted outputs + the assembled pack are the only
# public-safe surface.

redact-llm-adversarial:
	@mkdir -p traces/redacted/llm_adversarial
	@for case in case_fl_adv_v0_001 case_fl_adv_v0_002 case_fl_adv_v0_003 case_fl_adv_v0_004 case_fl_adv_v0_005 case_fl_adv_v0_006; do \
		uv run python scripts/redact_trace.py \
			--input traces/local/llm_adversarial/$$case.json \
			--policy configs/redaction_policy.yaml \
			--output traces/redacted/llm_adversarial/$$case.redacted.json \
			--report-out traces/redacted/llm_adversarial/$$case.redaction_report.json || exit 1; \
	done

evidence-pack-llm-adversarial: redact-llm-adversarial
	uv run python scripts/package_evidence_llm.py \
		--raw-report reports/llm_adversarial_eval.json \
		--eval-card reports/llm_adversarial_eval_card.md \
		--reference-report reports/improved_adversarial_eval.json \
		--regressions case_studies/financial_links_reliability/evals/regressions_llm_v0.jsonl \
		--redacted-traces traces/redacted/llm_adversarial \
		--policy configs/redaction_policy.yaml \
		--out evidence_packs/financial_links_llm_v0

# ---- Opt-in LLM prompt-improvement candidate (v1) ---------------------------
# llm_candidate_v1 uses the same adapter, model, and deterministic
# decisions as llm_candidate_v0; only the prompt changes. The v1 prompt
# explicitly lists every forbidden phrase from the unsupported_claim
# pattern set and pairs each with a hedged rewrite example. The card
# target compares llm_candidate_v0 (Before) against llm_candidate_v1
# (After) so the prompt-improvement delta is directly readable.

eval-adversarial-llm-v1: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v0.jsonl \
		--traces-out traces/local/llm_adversarial_v1 \
		--report-out reports/llm_adversarial_v1_eval.json \
		--agent-system-version llm_candidate_v1

eval-card-adversarial-llm-v1: eval-adversarial-llm eval-adversarial-llm-v1
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_eval.json \
		--improved-report reports/llm_adversarial_v1_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v1_vs_v0_card.md

# ---- v1 redaction + evidence pack -----------------------------------------
# These targets operate on on-disk artifacts only — they do NOT call the
# LLM. They assume `make eval-card-adversarial-llm-v1` has already
# produced reports/llm_adversarial_v1_eval.json and the raw v1 traces
# under traces/local/llm_adversarial_v1/. Both raw inputs are
# gitignored; the redacted outputs + the assembled pack are the only
# public-safe surface for the v1 prompt-improvement loop.

redact-llm-adversarial-v1:
	@if [ ! -d traces/local/llm_adversarial_v1 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v1/ not found."; \
		echo "  Hint: run \`make eval-card-adversarial-llm-v1\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -f reports/llm_adversarial_v1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v1_eval.json not found."; \
		echo "  Hint: run \`make eval-card-adversarial-llm-v1\` (credentialed) first."; \
		exit 1; \
	fi
	@mkdir -p traces/redacted/llm_adversarial_v1
	@for case in case_fl_adv_v0_001 case_fl_adv_v0_002 case_fl_adv_v0_003 case_fl_adv_v0_004 case_fl_adv_v0_005 case_fl_adv_v0_006; do \
		uv run python scripts/redact_trace.py \
			--input traces/local/llm_adversarial_v1/$$case.json \
			--policy configs/redaction_policy.yaml \
			--output traces/redacted/llm_adversarial_v1/$$case.redacted.json \
			--report-out traces/redacted/llm_adversarial_v1/$$case.redaction_report.json || exit 1; \
	done

evidence-pack-llm-adversarial-v1: redact-llm-adversarial-v1
	@if [ ! -f reports/llm_adversarial_v1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v1_eval.json not found."; \
		echo "  Hint: run \`make eval-card-adversarial-llm-v1\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -f reports/llm_adversarial_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_eval.json not found (Before report)."; \
		echo "  Hint: run \`make eval-adversarial-llm\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/package_evidence_llm_v1.py \
		--raw-v0-report reports/llm_adversarial_eval.json \
		--raw-v1-report reports/llm_adversarial_v1_eval.json \
		--eval-card reports/llm_adversarial_v1_vs_v0_card.md \
		--regressions case_studies/financial_links_reliability/evals/regressions_llm_v0.jsonl \
		--redacted-traces traces/redacted/llm_adversarial_v1 \
		--policy configs/redaction_policy.yaml \
		--improvement-memo reports/llm_prompt_improvement_memo.md \
		--repeat-summary-md reports/llm_repeat_summary.md \
		--repeat-summary-json reports/llm_repeat_summary.json \
		--out evidence_packs/financial_links_llm_v1

# ---- Opt-in credentialed repeat-run capture --------------------------------
# These three targets are the credentialed half of the repeat-run loop.
# They are opt-in, never run in `make test`, and cost real Anthropic
# tokens (each run executes the full adversarial slice once). Default
# RUNS=5; override with `RUNS=10 make repeat-adversarial-llm-v0`.
#
# Output layout (gitignored):
#   reports/llm_repeats/adversarial/<profile>/<timestamp>/run_<i>/eval_report.json
#   reports/llm_repeats/adversarial/<profile>/<timestamp>/run_<i>/traces/<case>.json
#
# repeat-adversarial-llm-summary aggregates EVERY eval_report.json
# under reports/llm_repeats/adversarial/ and writes a public-safe
# Markdown + JSON summary that may be tracked (no raw draft text, no
# traces/local/llm_ paths — verified by tests).

RUNS ?= 5
REPEAT_OUT_DIR ?= reports/llm_repeats/adversarial
REPEAT_SUMMARY_MD ?= reports/llm_repeat_summary.md
REPEAT_SUMMARY_JSON ?= reports/llm_repeat_summary.json

repeat-adversarial-llm-v0: check-llm-env
	uv run python scripts/run_llm_repeats.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v0.jsonl \
		--profile llm_candidate_v0 \
		--runs $(RUNS) \
		--out-dir $(REPEAT_OUT_DIR)

repeat-adversarial-llm-v1: check-llm-env
	uv run python scripts/run_llm_repeats.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v0.jsonl \
		--profile llm_candidate_v1 \
		--runs $(RUNS) \
		--out-dir $(REPEAT_OUT_DIR)

repeat-adversarial-llm-summary:
	@if ! ls $(REPEAT_OUT_DIR)/*/*/run_*/eval_report.json >/dev/null 2>&1; then \
		echo "ERROR: no captured repeat-run eval_report.json files under $(REPEAT_OUT_DIR)/"; \
		echo "  Hint: run `RUNS=5 make repeat-adversarial-llm-v0` (credentialed) first."; \
		exit 1; \
	fi
	uv run python -c "import sys, glob; \
paths = sorted(glob.glob('$(REPEAT_OUT_DIR)/*/*/run_*/eval_report.json')); \
from scripts.aggregate_llm_repeats import aggregate_files, render_markdown; \
import json; from pathlib import Path; \
summary = aggregate_files([Path(p) for p in paths], allow_mixed_profiles=True); \
Path('$(REPEAT_SUMMARY_MD)').write_text(render_markdown(summary)); \
Path('$(REPEAT_SUMMARY_JSON)').write_text(json.dumps(summary, indent=2)); \
print(f'OK: aggregated {summary[\"run_count\"]} repeat runs across profiles={summary[\"profile_family\"]} -> $(REPEAT_SUMMARY_MD)')"

# ---- Repeat-run variance aggregation (no LLM call) -------------------------
# Demo target: aggregate three tracked fixture reports under
# tests/fixtures/llm_repeats/ and write a sample Markdown + JSON
# summary. The fixture reports are HAND-CRAFTED for variance-detection
# testing; they are not real LLM outputs. The demo output paths are
# gitignored so this target can be re-run safely. Real credentialed
# repeat runs are a future opt-in chunk and are not wired into any
# Make target yet.

variance-report-fixture:
	uv run python scripts/aggregate_llm_repeats.py \
		--report tests/fixtures/llm_repeats/run1.json \
		--report tests/fixtures/llm_repeats/run2.json \
		--report tests/fixtures/llm_repeats/run3.json \
		--out-md reports/llm_repeat_summary_fixture.md \
		--out-json reports/llm_repeat_summary_fixture.json

lint:
	uv run ruff check .
