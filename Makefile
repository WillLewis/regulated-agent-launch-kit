.PHONY: help setup test scaffold-test lint dataset-test dataset-test-adversarial dataset-test-adversarial-v1 dataset-test-adversarial-v2 eval-smoke eval-smoke-baseline eval-smoke-improved eval-card-smoke eval-v0-baseline eval-v0-improved eval-card-v0 eval-adversarial-baseline eval-adversarial-improved eval-card-adversarial eval-adversarial-v1-baseline eval-adversarial-v1-improved eval-card-adversarial-v1 eval-adversarial-v2-baseline eval-adversarial-v2-improved eval-card-adversarial-v2 action-suspension-demo eval-adversarial-v1-baseline-semantic eval-adversarial-v1-improved-semantic semantic-reporting-surface semantic-model-decisions-adversarial-v1-baseline semantic-model-decisions-adversarial-v1-improved eval-adversarial-v1-baseline-semantic-model eval-adversarial-v1-improved-semantic-model semantic-model-reporting-surface regression-seed-v0 regression-check-v0 redact-v0 evidence-pack-v0 check-llm-env eval-smoke-llm eval-card-llm-smoke eval-adversarial-llm eval-card-adversarial-llm redact-llm-adversarial evidence-pack-llm-adversarial eval-adversarial-llm-v1 eval-card-adversarial-llm-v1 redact-llm-adversarial-v1 evidence-pack-llm-adversarial-v1 eval-adversarial-v1-llm-v0 eval-adversarial-v1-llm-v1 eval-card-adversarial-v1-llm semantic-model-decisions-adversarial-v1-llm-v0 semantic-model-decisions-adversarial-v1-llm-v1 redact-adversarial-v1-llm semantic-audit-summary-adversarial-v1-llm eval-adversarial-v2-llm-v0 eval-adversarial-v2-llm-v1 eval-card-adversarial-v2-llm semantic-model-decisions-adversarial-v2-llm-v0 semantic-model-decisions-adversarial-v2-llm-v1 semantic-audit-summary-adversarial-v2-llm semantic-gate-adversarial-v2-llm eval-adversarial-v2-llm-v2 eval-card-adversarial-v2-llm-v2-vs-v1 semantic-model-decisions-adversarial-v2-llm-v2 semantic-gate-adversarial-v2-llm-v2 eval-adversarial-v2-llm-v2-1 eval-card-adversarial-v2-llm-v2-1-vs-v2 semantic-model-decisions-adversarial-v2-llm-v2-1 semantic-gate-adversarial-v2-llm-v2-1 eval-adversarial-v2-llm-v2-2 eval-card-adversarial-v2-llm-v2-2-vs-v2-1 semantic-model-decisions-adversarial-v2-llm-v2-2 semantic-gate-adversarial-v2-llm-v2-2 calibration-seed-adversarial-v2-semantic calibration-replay-adversarial-v2-semantic regression-seed-adversarial-v1-semantic regression-check-adversarial-v1-semantic regression-replay-adversarial-v1-semantic regression-seed-adversarial-v2-semantic regression-check-adversarial-v2-semantic regression-replay-adversarial-v2-semantic semantic-failure-analysis-adversarial-v2 semantic-adjudication-adversarial-v2 candidate-v2-residual-adjudication-adversarial-v2 reground-adjudication-adversarial-v2 semantic-gate-adversarial-v1-regressions semantic-gate-adversarial-v1-improved evidence-pack-adversarial-v1-llm evidence-pack-adversarial-v2-llm variance-report-fixture repeat-adversarial-llm-v0 repeat-adversarial-llm-v1 repeat-adversarial-llm-summary repeat-adversarial-v1-llm-v0 repeat-adversarial-v1-llm-v1 repeat-adversarial-v1-llm-summary dataset-test-adversarial-v3 eval-adversarial-v3-baseline eval-adversarial-v3-improved eval-card-adversarial-v3 eval-adversarial-v3-llm-v2-2 eval-card-adversarial-v3-llm-v2-2 semantic-model-decisions-adversarial-v3-llm-v2-2 semantic-gate-adversarial-v3-llm-v2-2 grader-gold-score-demo grader-gold-pass grader-gold-replay grader-reliability-report reground-adjudication-adversarial-v2 eval-adversarial-v2-llm-v2-3 eval-card-adversarial-v2-llm-v2-3-vs-v2-2 semantic-model-decisions-adversarial-v2-llm-v2-3 semantic-gate-adversarial-v2-llm-v2-3 eval-adversarial-v3-llm-v2-3 semantic-model-decisions-adversarial-v3-llm-v2-3 semantic-gate-adversarial-v3-llm-v2-3

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
	@echo "  dataset-test-adversarial-v2  validate the broader adversarial v2 JSONL slice (24 cases)"
	@echo "  eval-adversarial-v2-baseline  run the adversarial v2 slice against baseline_v0 (deterministic)"
	@echo "  eval-adversarial-v2-improved  run the adversarial v2 slice against improved_v0 (deterministic)"
	@echo "  eval-card-adversarial-v2   run both adversarial v2 evals, then render the comparison eval card"
	@echo "  action-suspension-demo  [M9] prove HumanApprovalNode suspends a synthetic side-effecting action before execution (credential-free)"
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
	@echo "Opt-in adversarial v1 (12-case) LLM candidate evidence loop (credentialed; not in CI):"
	@echo "  eval-adversarial-v1-llm-v0  run the adversarial v1 slice against llm_candidate_v0 (raw report gitignored)"
	@echo "  eval-adversarial-v1-llm-v1  run the adversarial v1 slice against llm_candidate_v1 (raw report gitignored)"
	@echo "  eval-card-adversarial-v1-llm  render the candidate_v0 (Before) vs candidate_v1 (After) prompt-improvement card"
	@echo "  semantic-model-decisions-adversarial-v1-llm-v0  model/NLI semantic decisions for the candidate_v0 report (gitignored)"
	@echo "  semantic-model-decisions-adversarial-v1-llm-v1  model/NLI semantic decisions for the candidate_v1 report (gitignored)"
	@echo "  semantic-audit-summary-adversarial-v1-llm  aggregate model/NLI decisions into a public-safe summary (no LLM call)"
	@echo "  [M7b] eval-adversarial-v2-llm-v0 / -v1  run the 24-case adversarial v2 slice against llm_candidate_v0 / v1 (credentialed; raw report gitignored)"
	@echo "  [M7b] eval-card-adversarial-v2-llm  render the v2 candidate_v0 (Before) vs candidate_v1 (After) card"
	@echo "  [M7b] semantic-model-decisions-adversarial-v2-llm-v0 / -v1  model/NLI semantic decisions for the v2 candidate drafts on disk (gitignored)"
	@echo "  [M7b] semantic-audit-summary-adversarial-v2-llm  aggregate v2 model/NLI decisions into a public-safe summary (no LLM call)"
	@echo "  [M7b] semantic-gate-adversarial-v2-llm  credential-free semantic gate over the v2 candidate_v1 verdicts (blocks on any flagged case; no model call)"
	@echo "  [M7 remediation] eval-adversarial-v2-llm-v2  run the M7 remediation prompt (llm_candidate_v2) on the 24-case slice (credentialed; WIRED, NOT RUN; raw report gitignored)"
	@echo "  [M7 remediation] eval-card-adversarial-v2-llm-v2-vs-v1  render the v1 (Before) vs v2 (After) remediation card (credentialed; not run)"
	@echo "  [M7 remediation] semantic-model-decisions-adversarial-v2-llm-v2  model/NLI decisions for the v2 candidate drafts on disk (credentialed; not run; gitignored)"
	@echo "  [M7 remediation] semantic-gate-adversarial-v2-llm-v2  credential-free semantic gate over the v2 candidate verdicts (blocks on any flag; needs on-disk decisions)"
	@echo "  [M7 residual]    eval-adversarial-v2-llm-v2-1  run the candidate-v2.1 prompt (017 missing-metadata fix) on the 24-case slice (credentialed; WIRED, NOT RUN; raw report gitignored)"
	@echo "  [M7 residual]    eval-card-adversarial-v2-llm-v2-1-vs-v2  render the v2 (Before) vs v2.1 (After) residual card (credentialed; not run)"
	@echo "  [M7 residual]    semantic-model-decisions-adversarial-v2-llm-v2-1  model/NLI decisions for the v2.1 candidate drafts on disk (credentialed; not run; gitignored)"
	@echo "  [M7 residual]    semantic-gate-adversarial-v2-llm-v2-1  credential-free semantic gate over the v2.1 candidate verdicts (blocks on any flag; needs on-disk decisions)"
	@echo "  [M7 residual]    eval-adversarial-v2-llm-v2-2  run the candidate-v2.2 prompt (generalized closed-gate timing fix) on the 24-case slice (credentialed; WIRED, NOT RUN; raw report gitignored)"
	@echo "  [M7 residual]    eval-card-adversarial-v2-llm-v2-2-vs-v2-1  render the v2.1 (Before) vs v2.2 (After) residual card (credentialed; not run)"
	@echo "  [M7 residual]    semantic-model-decisions-adversarial-v2-llm-v2-2  model/NLI decisions for the v2.2 candidate drafts on disk (credentialed; not run; gitignored)"
	@echo "  [M7 residual]    semantic-gate-adversarial-v2-llm-v2-2  credential-free semantic gate over the v2.2 candidate verdicts (blocks on any flag; needs on-disk decisions)"
	@echo "  [M7c held-out]   eval-adversarial-v3-llm-v2-2  test v2.2 on the 28-case HELD-OUT v3 set (credentialed; raw gitignored; only generalization surface)"
	@echo "  [M7c held-out]   eval-card-adversarial-v3-llm-v2-2  improved_v0 vs v2.2 card on held-out slice"
	@echo "  [M7c held-out]   semantic-model-decisions-adversarial-v3-llm-v2-2  model/NLI decisions for v2.2 on v3 (credentialed; gitignored)"
	@echo "  [M7c held-out]   semantic-gate-adversarial-v3-llm-v2-2  credential-free gate on v3 held-out slice (blocks on any flag)"
	@echo "  [M7d grader]     grader-gold-score-demo  credential-free end-to-end demo of the grader-reliability harness on synthetic verdicts"
	@echo "  [M7d grader]     grader-gold-pass  run the model/NLI grader over the gold drafts ONCE (credentialed; WIRED, NOT RUN; raw gitignored; answer key withheld)"
	@echo "  [M7d grader]     grader-gold-replay  strip raw gold-pass verdicts to a public-safe fixture (no model call)"
	@echo "  [M7d grader]     grader-reliability-report  score the grader vs the gold set -> precision/RECALL + what-a-clean-gate-proves report (no model call)"
	@echo "  [M7e v2.3]       eval-adversarial-v2-llm-v2-3  run candidate-v2.3 (universal forward-looking ban) on the 24-case slice (credentialed; WIRED, NOT RUN; raw gitignored)"
	@echo "  [M7e v2.3]       eval-card-adversarial-v2-llm-v2-3-vs-v2-2  render the v2.2 (Before) vs v2.3 (After) card"
	@echo "  [M7e v2.3]       semantic-model-decisions / semantic-gate -adversarial-v2-llm-v2-3  model/NLI decisions + credential-free gate over v2.3 drafts"
	@echo "  [M7e v2.3]       eval-adversarial-v3-llm-v2-3 (+ semantic-model-decisions / -gate)  v2.3 on the HELD-OUT v3 slice (credentialed; WIRED, NOT RUN)"
	@echo "  [M7e v2.3]       reground-adjudication-adversarial-v2  regenerate the resolved re-grounding adjudication (no LLM call)"
	@echo "  [M7 remediation] calibration-seed-adversarial-v2-semantic  build credential-free grader-calibration fixtures for the 4 grader_calibration_review findings (no LLM call)"
	@echo "  [M7 remediation] calibration-replay-adversarial-v2-semantic  credential-free replay: prove the 4 over-flag cases clear as non-claims in the offline semantic lane (no LLM call)"
	@echo "  regression-seed-adversarial-v1-semantic  pin the 3 semantic-only failures as pending_review regression seeds (no LLM call)"
	@echo "  regression-check-adversarial-v1-semantic  validate the semantic regression seeds + summary linkage (no LLM call)"
	@echo "  regression-replay-adversarial-v1-semantic  credential-free replay: prove the semantic grader fires on the 3 seeds (no LLM call)"
	@echo "  regression-seed-adversarial-v2-semantic  pin the 14 v2 semantic-only failures as pending_review regression seeds + replay fixture (no LLM call)"
	@echo "  regression-check-adversarial-v2-semantic  validate the v2 semantic regression seeds + summary linkage (no LLM call)"
	@echo "  regression-replay-adversarial-v2-semantic  credential-free replay: prove the semantic grader fires on all 14 v2 seeds (no LLM call)"
	@echo "  semantic-failure-analysis-adversarial-v2  generate the public-safe M7 failure analysis + remediation plan for the 14 findings (no LLM call)"
	@echo "  semantic-adjudication-adversarial-v2  generate the public-safe M7 adjudication of the 14 findings (candidate vs grader-calibration vs human review; no LLM call)"
	@echo "  candidate-v2-residual-adjudication-adversarial-v2  generate the public-safe adjudication of the 3 candidate-v2 residual flags (no LLM call)"
	@echo "  reground-adjudication-adversarial-v2  adjudicate the hardened-gate flags on candidate-v2/v2.1 after the answer-key firewall (no LLM call)"
	@echo "  semantic-gate-adversarial-v1-regressions  negative control: assert the blocking semantic gate fails on the 3 known-bad seeds (no LLM call)"
	@echo "  semantic-gate-adversarial-v1-improved  pass-path demo: run the blocking semantic gate on the synthetic clean improved fixture (no LLM call)"
	@echo "  redact-adversarial-v1-llm  redact both candidates' raw v1 LLM traces (no LLM call)"
	@echo "  evidence-pack-adversarial-v1-llm  assemble evidence_packs/financial_links_llm_adversarial_v1/ (no LLM call)"
	@echo "  evidence-pack-adversarial-v2-llm  assemble evidence_packs/financial_links_llm_adversarial_v2/ for the BLOCKED M7 run (credential-free; no LLM call)"
	@echo ""
	@echo "Opt-in CREDENTIALED repeat-run capture (real Anthropic API calls; costs money; not in CI):"
	@echo "  RUNS=5 make repeat-adversarial-llm-v0  capture N llm_candidate_v0 adversarial runs (RUNS defaults to 5)"
	@echo "  RUNS=5 make repeat-adversarial-llm-v1  capture N llm_candidate_v1 adversarial runs (RUNS defaults to 5)"
	@echo "  make repeat-adversarial-llm-summary    aggregate every captured repeat run into a public-safe summary"
	@echo ""
	@echo "Opt-in CREDENTIALED repeat-run capture — adversarial v1 (12-case; real API calls; not in CI):"
	@echo "  RUNS=5 make repeat-adversarial-v1-llm-v0  capture N llm_candidate_v0 adversarial v1 runs -> reports/llm_repeats/adversarial_v1/"
	@echo "  RUNS=5 make repeat-adversarial-v1-llm-v1  capture N llm_candidate_v1 adversarial v1 runs -> reports/llm_repeats/adversarial_v1/"
	@echo "  make repeat-adversarial-v1-llm-summary    aggregate adversarial v1 repeat runs into reports/llm_adversarial_v1_repeat_summary.{md,json}"
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

dataset-test-adversarial-v2:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/adversarial_v2.jsonl
dataset-test-adversarial-v3:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/adversarial_v3.jsonl

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

# ---- Deterministic adversarial v2 targets (credential-free) ---------------
# M8: the broader 24-case adversarial v2 slice expands coverage beyond v1
# (multi-policy conflict, stale-data vs consent ambiguity, fallback
# permitted-vs-blocked confusion, missing partner_id / institution_id
# variants, L2/L3 consent pressure with safe copy, and new overpromise
# paraphrases). Like the v1 deterministic targets these run only the
# baseline_v0 / improved_v0 profiles, never call an LLM, and never depend
# on credentials. No adversarial v2 LLM target is wired (M7's semantic
# blocking gate is the next chunk, not this one).

eval-adversarial-v2-baseline:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/baseline_adversarial_v2 \
		--report-out reports/baseline_adversarial_v2_eval.json \
		--agent-system-version baseline_v0

eval-adversarial-v2-improved:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/improved_adversarial_v2 \
		--report-out reports/improved_adversarial_v2_eval.json \
		--agent-system-version improved_v0

eval-card-adversarial-v2: eval-adversarial-v2-baseline eval-adversarial-v2-improved
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/baseline_adversarial_v2_eval.json \
		--improved-report reports/improved_adversarial_v2_eval.json \
		--out reports/adversarial_v2_eval_card.md

# ---- Deterministic adversarial v3 targets (credential-free, HELD-OUT) ------
# M7c: adversarial v3 is the 28-case held-out test set for llm_candidate_v2.2.
# These cases were never read during prompt tuning — a train/test contamination
# guard. Like all deterministic targets these run only baseline_v0 / improved_v0,
# never call an LLM, and never depend on credentials. The corresponding LLM
# target (eval-adversarial-v3-llm-v2-2) is wired for opt-in credentialed
# robustness testing only. M7 stays OPEN / NOT READY FOR PILOT.

eval-adversarial-v3-baseline:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--traces-out traces/local/baseline_adversarial_v3 \
		--report-out reports/baseline_adversarial_v3_eval.json \
		--agent-system-version baseline_v0

eval-adversarial-v3-improved:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--traces-out traces/local/improved_adversarial_v3 \
		--report-out reports/improved_adversarial_v3_eval.json \
		--agent-system-version improved_v0

eval-card-adversarial-v3: eval-adversarial-v3-baseline eval-adversarial-v3-improved
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/baseline_adversarial_v3_eval.json \
		--improved-report reports/improved_adversarial_v3_eval.json \
		--out reports/adversarial_v3_eval_card.md

# ---- M9: synthetic action-suspension gate (credential-free) -----------------
# Separate harness from the Financial Links proof loop (app/graph.py is
# untouched and stays draft_only). Drives a real LangGraph that interrupts
# before HumanApprovalNode and proves a synthetic side-effecting action is
# suspended before execution and gated on a human decision (suspended / rejected
# / approved-exactly-once / missing-fails-closed). No model call, no external
# system, no credentials. Emits public-safe traces under
# traces/local/action_suspension/. M9 infrastructure only — it does not change
# the NOT READY FOR PILOT posture (M7 credentialed semantic audit is still open).
action-suspension-demo:
	uv run python scripts/run_action_suspension_demo.py \
		--out-dir traces/local/action_suspension

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

# ---- Opt-in adversarial v1 (12-case) LLM candidate evidence loop -------------
# These targets promote the 12-case adversarial v1 slice from deterministic /
# fixture coverage into a credentialed LLM candidate loop. They are opt-in,
# never run in CI, and no deterministic target depends on them. They require
# ANTHROPIC_API_KEY + the anthropic SDK; check-llm-env fails clean if either is
# missing (no silent fallback to a deterministic profile).
#
# Naming is disambiguated on purpose. `llm_adversarial_v1_candidate_v0` /
# `_candidate_v1` is candidate prompt v0 / v1 on the adversarial *v1 dataset*
# (12 cases). This is distinct from the older `llm_adversarial_v1` target,
# which is candidate prompt v1 on the adversarial *v0 dataset* (6 cases).
#
# Raw reports (reports/llm_adversarial_v1_candidate_v*_eval.json) and raw
# traces (traces/local/llm_adversarial_v1_candidate_v*/) embed raw model
# draft text and are gitignored. The redacted pack at
# evidence_packs/financial_links_llm_adversarial_v1/ is the only public surface.

eval-adversarial-v1-llm-v0: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/llm_adversarial_v1_candidate_v0 \
		--report-out reports/llm_adversarial_v1_candidate_v0_eval.json \
		--agent-system-version llm_candidate_v0

eval-adversarial-v1-llm-v1: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--traces-out traces/local/llm_adversarial_v1_candidate_v1 \
		--report-out reports/llm_adversarial_v1_candidate_v1_eval.json \
		--agent-system-version llm_candidate_v1

eval-card-adversarial-v1-llm: eval-adversarial-v1-llm-v0 eval-adversarial-v1-llm-v1
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v1_candidate_v0_eval.json \
		--improved-report reports/llm_adversarial_v1_candidate_v1_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md

# ---- Opt-in model/NLI semantic decisions for the adversarial v1 LLM reports --
# Generate SemanticDecision JSON for each credentialed candidate report using
# the same adapter contract as the deterministic lane. These judge the drafts
# ALREADY ON DISK; they must NOT re-run the candidate agent. run_eval has no
# grade-existing-traces mode, so depending on eval-adversarial-v1-llm-v0/v1
# would re-call the candidate model and OVERWRITE the very drafts the decisions
# are made against (and spend candidate tokens again). To prevent that, these
# targets deliberately do NOT depend on the candidate eval targets. They fail
# clean when the candidate report or its raw traces are missing, leaving
# (re)generation as an explicit, separate, credentialed step. The semantic
# judge itself still needs credentials, so check-llm-env stays a prerequisite.
# Decision JSON stays gitignored under reports/semantic_model_decisions/.

semantic-model-decisions-adversarial-v1-llm-v0: check-llm-env
	@if [ ! -f reports/llm_adversarial_v1_candidate_v0_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v1_candidate_v0_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v1-llm-v0\` (credentialed) once to create"; \
		echo "        the candidate report + raw traces, then re-run this target."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v1_candidate_v0 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v1_candidate_v0/ not found."; \
		echo "  The semantic adapter reads the candidate's on-disk traces; it does NOT"; \
		echo "  regenerate them. Hint: run \`make eval-adversarial-v1-llm-v0\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--eval-report reports/llm_adversarial_v1_candidate_v0_eval.json \
		--out reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json

semantic-model-decisions-adversarial-v1-llm-v1: check-llm-env
	@if [ ! -f reports/llm_adversarial_v1_candidate_v1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v1_candidate_v1_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v1-llm-v1\` (credentialed) once to create"; \
		echo "        the candidate report + raw traces, then re-run this target."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v1_candidate_v1 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v1_candidate_v1/ not found."; \
		echo "  The semantic adapter reads the candidate's on-disk traces; it does NOT"; \
		echo "  regenerate them. Hint: run \`make eval-adversarial-v1-llm-v1\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--eval-report reports/llm_adversarial_v1_candidate_v1_eval.json \
		--out reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json

# ---- Public-safe model/NLI semantic audit summary (adversarial v1 LLM) ------
# On-disk only: NO LLM call, NO credentials. Aggregates the two gitignored
# model/NLI decision files + the two candidate reports into an aggregate-only,
# public-safe summary (counts, enum histograms, synthetic case IDs/risk bands,
# cost). It judges drafts already on disk and never re-runs a candidate eval.
# The summary JSON + Markdown are tracked (public artifacts).

semantic-audit-summary-adversarial-v1-llm:
	@for f in \
		reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json \
		reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json; do \
		if [ ! -f $$f ]; then \
			echo "ERROR: $$f not found."; \
			echo "  This target aggregates existing model/NLI decisions; it does NOT generate them."; \
			echo "  Hint: run \`make semantic-model-decisions-adversarial-v1-llm-v0\` and"; \
			echo "        \`make semantic-model-decisions-adversarial-v1-llm-v1\` (credentialed) first."; \
			exit 1; \
		fi; \
	done
	uv run python scripts/summarize_semantic_audit_adversarial_v1_llm.py \
		--report-v0 reports/llm_adversarial_v1_candidate_v0_eval.json \
		--report-v1 reports/llm_adversarial_v1_candidate_v1_eval.json \
		--decisions-v0 reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json \
		--decisions-v1 reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json \
		--out-json reports/llm_adversarial_v1_semantic_audit_summary.json \
		--out-md reports/llm_adversarial_v1_semantic_audit_summary.md

# ===== M7b: opt-in credentialed adversarial v2 LLM candidate + semantic gate ===
# Direct analogs of the adversarial v1 LLM targets, on the broader 24-case v2
# slice. Credentialed targets gate on check-llm-env (no silent fallback). Raw
# candidate reports, raw traces, and raw model/NLI decisions stay gitignored;
# the public surfaces are the aggregate semantic-audit summary and the pass/fail
# of the credential-free semantic gate. No deterministic / CI target depends on
# these. M7b runs the semantic gate against the v2 candidate drafts; it does NOT
# complete M7 (one credentialed audit is not the delivery-plan bar) and does NOT
# change the NOT READY FOR PILOT posture.

eval-adversarial-v2-llm-v0: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v0 \
		--report-out reports/llm_adversarial_v2_candidate_v0_eval.json \
		--agent-system-version llm_candidate_v0

eval-adversarial-v2-llm-v1: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v1 \
		--report-out reports/llm_adversarial_v2_candidate_v1_eval.json \
		--agent-system-version llm_candidate_v1

eval-card-adversarial-v2-llm: eval-adversarial-v2-llm-v0 eval-adversarial-v2-llm-v1
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v2_candidate_v0_eval.json \
		--improved-report reports/llm_adversarial_v2_candidate_v1_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md

# Model/NLI semantic decisions judging the v2 candidate drafts ALREADY ON DISK.
# They deliberately do NOT depend on the candidate eval targets (that would
# re-run the candidate model and overwrite the very drafts under audit). They
# fail clean if the candidate report or traces are missing. Decision JSON stays
# gitignored under reports/semantic_model_decisions/.
semantic-model-decisions-adversarial-v2-llm-v0: check-llm-env
	@if [ ! -f reports/llm_adversarial_v2_candidate_v0_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v0_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v0\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v2_candidate_v0 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v2_candidate_v0/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v0\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--eval-report reports/llm_adversarial_v2_candidate_v0_eval.json \
		--out reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json

semantic-model-decisions-adversarial-v2-llm-v1: check-llm-env
	@if [ ! -f reports/llm_adversarial_v2_candidate_v1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v1_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v1\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v2_candidate_v1 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v2_candidate_v1/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v1\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--eval-report reports/llm_adversarial_v2_candidate_v1_eval.json \
		--out reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json

# On-disk only: NO LLM call, NO credentials. Aggregates the two gitignored v2
# decision files + candidate reports into the public-safe aggregate summary
# (counts, enum histograms, synthetic case IDs/risk bands, cost). Reuses the
# generic adversarial-v1 summarizer with v2 paths. The summary JSON + Markdown
# are tracked public artifacts.
semantic-audit-summary-adversarial-v2-llm:
	@for f in \
		reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json \
		reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json; do \
		if [ ! -f $$f ]; then \
			echo "ERROR: $$f not found."; \
			echo "  This target aggregates existing model/NLI decisions; it does NOT generate them."; \
			echo "  Hint: run \`make semantic-model-decisions-adversarial-v2-llm-v0\` and"; \
			echo "        \`make semantic-model-decisions-adversarial-v2-llm-v1\` (credentialed) first."; \
			exit 1; \
		fi; \
	done
	uv run python scripts/summarize_semantic_audit_adversarial_v1_llm.py \
		--report-v0 reports/llm_adversarial_v2_candidate_v0_eval.json \
		--report-v1 reports/llm_adversarial_v2_candidate_v1_eval.json \
		--decisions-v0 reports/semantic_model_decisions/adversarial_v2_llm_candidate_v0.json \
		--decisions-v1 reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json \
		--out-json reports/llm_adversarial_v2_semantic_audit_summary.json \
		--out-md reports/llm_adversarial_v2_semantic_audit_summary.md

# Credential-free semantic GATE over the v2 candidate_v1 drafts. Re-keys the
# (gitignored) candidate model/NLI verdicts under the deterministic improved_v0
# vehicle via a public-safe replay fixture, runs the offline semantic lane, and
# BLOCKS (exit non-zero) on any flagged case. No model call, no candidate rerun,
# no token spend. A BLOCK is preserved as evidence (the failing run + the
# tracked aggregate summary); a PASS is one credentialed audit, NOT M7
# completion. NOT a check-llm-env target — it consumes decisions already on disk.
semantic-gate-adversarial-v2-llm:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json not found."; \
		echo "  The gate replays the v2 candidate_v1 model/NLI verdicts; it does NOT generate them."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v2-llm-v1\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v2_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v2_llm_candidate_v1.json \
		--out reports/llm_adversarial_v2_candidate_v1_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v1_semantic_model \
		--report-out reports/llm_adversarial_v2_candidate_v1_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v2_candidate_v1_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v2_candidate_v1_semantic_model_eval.json

# ---- M7 remediation candidate (llm_candidate_v2) — WIRED, NOT RUN -----------
# Opt-in, credential-gated analogs of the v0/v1 candidate loop for the M7
# remediation prompt (llm_candidate_v2). The v2 prompt encodes the controls the
# M7 adjudication marked candidate_actionable + the failure-analysis structural
# controls. These targets are intentionally NOT executed in this chunk: they
# require ANTHROPIC creds (check-llm-env), cost tokens, and produce raw artifacts
# that stay gitignored. Running them is the *next* decision (fund a candidate-v2
# pass), not part of wiring. M7 stays OPEN / NOT READY FOR PILOT until a
# credentialed run produces SUSTAINED-ZERO semantic-only flags across multiple
# runs. No deterministic/CI target depends on any of these.
eval-adversarial-v2-llm-v2: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2 \
		--report-out reports/llm_adversarial_v2_candidate_v2_eval.json \
		--agent-system-version llm_candidate_v2

# Before/After remediation card: v1 (Before) vs v2 (After) on the 24-case slice.
# The card script is credential-free, but the v2 report only exists after the
# credentialed v2 run; this target produces it and requires the tracked-but-
# gitignored v1 report to be present. The card itself is public-safe (pass/fail
# counts only) and may be tracked once generated.
eval-card-adversarial-v2-llm-v2-vs-v1: eval-adversarial-v2-llm-v2
	@if [ ! -f reports/llm_adversarial_v2_candidate_v1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v1_eval.json not found."; \
		echo "  The v2-vs-v1 card needs the v1 candidate report on disk."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v1\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v2_candidate_v1_eval.json \
		--improved-report reports/llm_adversarial_v2_candidate_v2_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v2_candidate_v2_vs_v1_card.md

# Model/NLI semantic decisions judging the v2 candidate drafts ALREADY ON DISK.
# Like the v0/v1 variants it does NOT depend on the eval target (no rerun /
# overwrite of the audited drafts) and fails clean if the report/traces are
# missing. Decision JSON stays gitignored under reports/semantic_model_decisions/.
semantic-model-decisions-adversarial-v2-llm-v2: check-llm-env
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v2_candidate_v2 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v2_candidate_v2/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--eval-report reports/llm_adversarial_v2_candidate_v2_eval.json \
		--out reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2.json

# Credential-free semantic GATE over the v2 candidate drafts (same mechanism as
# semantic-gate-adversarial-v2-llm, applied to the v2 candidate's decisions). It
# re-keys the gitignored v2 verdicts under improved_v0 and BLOCKS on any flag.
# This is how a future candidate-v2 run is checked for the sustained-zero bar.
# NOT a check-llm-env target — it consumes decisions already on disk.
semantic-gate-adversarial-v2-llm-v2:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2.json not found."; \
		echo "  The gate replays the v2 candidate model/NLI verdicts; it does NOT generate them."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v2-llm-v2\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v2_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2.json \
		--out reports/llm_adversarial_v2_candidate_v2_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_semantic_model \
		--report-out reports/llm_adversarial_v2_candidate_v2_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v2_candidate_v2_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v2_candidate_v2_semantic_model_eval.json

# ---- M7 residual remediation candidate (llm_candidate_v2_1) — WIRED, NOT RUN -
# Same opt-in, credential-gated pattern as v2, for the candidate-v2.1 prompt
# (v2 with only the missing-metadata control tightened, per the residual
# adjudication's lone candidate_actionable, case_017). NOT executed in this
# chunk. Running them is the next decision; raw outputs stay gitignored and the
# credentialed targets gate on check-llm-env. M7 stays OPEN / NOT READY FOR PILOT.
eval-adversarial-v2-llm-v2-1: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_1 \
		--report-out reports/llm_adversarial_v2_candidate_v2_1_eval.json \
		--agent-system-version llm_candidate_v2_1

# Before/After residual card: v2 (Before) vs v2.1 (After) on the 24-case slice.
eval-card-adversarial-v2-llm-v2-1-vs-v2: eval-adversarial-v2-llm-v2-1
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_eval.json not found."; \
		echo "  The v2.1-vs-v2 card needs the v2 candidate report on disk."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v2_candidate_v2_eval.json \
		--improved-report reports/llm_adversarial_v2_candidate_v2_1_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v2_candidate_v2_1_vs_v2_card.md

# Model/NLI semantic decisions judging the v2.1 candidate drafts ALREADY ON DISK.
semantic-model-decisions-adversarial-v2-llm-v2-1: check-llm-env
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_1_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-1\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v2_candidate_v2_1 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v2_candidate_v2_1/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-1\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--eval-report reports/llm_adversarial_v2_candidate_v2_1_eval.json \
		--out reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_1.json

# Credential-free semantic GATE over the v2.1 candidate drafts (consumes on-disk
# decisions; BLOCKS on any flag). NOT a check-llm-env target.
semantic-gate-adversarial-v2-llm-v2-1:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_1.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_1.json not found."; \
		echo "  The gate replays the v2.1 candidate model/NLI verdicts; it does NOT generate them."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v2-llm-v2-1\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v2_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_1.json \
		--out reports/llm_adversarial_v2_candidate_v2_1_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_1_semantic_model \
		--report-out reports/llm_adversarial_v2_candidate_v2_1_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v2_candidate_v2_1_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v2_candidate_v2_1_semantic_model_eval.json

# ---- M7 generalized residual candidate (llm_candidate_v2_2) — WIRED, NOT RUN -
# v2.1 cleared case_017 but the same affirmative-timing-on-a-closed-gate failure
# recurred on other gate types (case_010/012/024). v2.2 generalizes that one
# control to every closed-gate state. Same opt-in, credential-gated pattern; NOT
# executed in this chunk; raw outputs gitignored; credentialed targets gate on
# check-llm-env. M7 stays OPEN / NOT READY FOR PILOT.
eval-adversarial-v2-llm-v2-2: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_2 \
		--report-out reports/llm_adversarial_v2_candidate_v2_2_eval.json \
		--agent-system-version llm_candidate_v2_2

# Before/After residual card: v2.1 (Before) vs v2.2 (After) on the 24-case slice.
eval-card-adversarial-v2-llm-v2-2-vs-v2-1: eval-adversarial-v2-llm-v2-2
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_1_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_1_eval.json not found."; \
		echo "  The v2.2-vs-v2.1 card needs the v2.1 candidate report on disk."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-1\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v2_candidate_v2_1_eval.json \
		--improved-report reports/llm_adversarial_v2_candidate_v2_2_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v2_candidate_v2_2_vs_v2_1_card.md

# Model/NLI semantic decisions judging the v2.2 candidate drafts ALREADY ON DISK.
semantic-model-decisions-adversarial-v2-llm-v2-2: check-llm-env
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_2_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_2_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-2\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v2_candidate_v2_2 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v2_candidate_v2_2/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-2\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--eval-report reports/llm_adversarial_v2_candidate_v2_2_eval.json \
		--out reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_2.json

# Credential-free semantic GATE over the v2.2 candidate drafts (consumes on-disk
# decisions; BLOCKS on any flag). NOT a check-llm-env target.
semantic-gate-adversarial-v2-llm-v2-2:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_2.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_2.json not found."; \
		echo "  The gate replays the v2.2 candidate model/NLI verdicts; it does NOT generate them."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v2-llm-v2-2\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v2_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_2.json \
		--out reports/llm_adversarial_v2_candidate_v2_2_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_2_semantic_model \
		--report-out reports/llm_adversarial_v2_candidate_v2_2_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v2_candidate_v2_2_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v2_candidate_v2_2_semantic_model_eval.json

# ---- M7c: adversarial v3 held-out robustness check (credential-gated) -------
# eval-adversarial-v3-llm-v2-2 tests llm_candidate_v2.2 against the 28-case
# held-out test set — the ONLY surface that supports a generalization claim.
# Never used as tuning signal. Raw outputs gitignored. M7 stays OPEN.
eval-adversarial-v3-llm-v2-2: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--traces-out traces/local/llm_adversarial_v3_candidate_v2_2 \
		--report-out reports/llm_adversarial_v3_candidate_v2_2_eval.json \
		--agent-system-version llm_candidate_v2_2

# Comparison card: improved_v0 (floor) vs v2.2 (After) on the held-out slice.
eval-card-adversarial-v3-llm-v2-2: eval-adversarial-v3-llm-v2-2
	@if [ ! -f reports/improved_adversarial_v3_eval.json ]; then \
		echo "ERROR: reports/improved_adversarial_v3_eval.json not found."; \
		echo "  Hint: run \`make eval-adversarial-v3-improved\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/improved_adversarial_v3_eval.json \
		--improved-report reports/llm_adversarial_v3_candidate_v2_2_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v3_candidate_v2_2_vs_improved_card.md

# Model/NLI semantic decisions judging the v2.2 candidate drafts on adversarial v3.
semantic-model-decisions-adversarial-v3-llm-v2-2: check-llm-env
	@if [ ! -f reports/llm_adversarial_v3_candidate_v2_2_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v3_candidate_v2_2_eval.json not found."; \
		echo "  This target judges drafts already on disk; it does NOT generate them."; \
		echo "  Hint: run \`make eval-adversarial-v3-llm-v2-2\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v3_candidate_v2_2 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v3_candidate_v2_2/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v3-llm-v2-2\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--eval-report reports/llm_adversarial_v3_candidate_v2_2_eval.json \
		--out reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_2.json

# Credential-free semantic gate over v2.2 candidate on the held-out v3 slice.
semantic-gate-adversarial-v3-llm-v2-2:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_2.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_2.json not found."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v3-llm-v2-2\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v3_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_2.json \
		--out reports/llm_adversarial_v3_candidate_v2_2_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--traces-out traces/local/llm_adversarial_v3_candidate_v2_2_semantic_model \
		--report-out reports/llm_adversarial_v3_candidate_v2_2_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v3_candidate_v2_2_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v3_candidate_v2_2_semantic_model_eval.json

# ---- M7e: candidate-v2.3 — universal forward-looking-reassurance ban ---------
# v2.3 = v2.2 + the FL-FORWARD-PROMISE-004 ban (no healthy-case carve-out, and
# the contradictory hedging vocab / good example fixed), targeting the
# deterministic grader evals.graders.grade_forward_looking_promise. WIRED, NOT
# RUN. Credentialed targets gate on check-llm-env; raw reports gitignored.
# M7 stays OPEN / NOT READY FOR PILOT.
eval-adversarial-v2-llm-v2-3: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_3 \
		--report-out reports/llm_adversarial_v2_candidate_v2_3_eval.json \
		--agent-system-version llm_candidate_v2_3

eval-card-adversarial-v2-llm-v2-3-vs-v2-2: eval-adversarial-v2-llm-v2-3
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_2_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_2_eval.json not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-2\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v2_candidate_v2_2_eval.json \
		--improved-report reports/llm_adversarial_v2_candidate_v2_3_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v2_candidate_v2_3_vs_v2_2_card.md

semantic-model-decisions-adversarial-v2-llm-v2-3: check-llm-env
	@if [ ! -f reports/llm_adversarial_v2_candidate_v2_3_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_candidate_v2_3_eval.json not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-3\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v2_candidate_v2_3 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v2_candidate_v2_3/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v2-llm-v2-3\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--eval-report reports/llm_adversarial_v2_candidate_v2_3_eval.json \
		--out reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_3.json

semantic-gate-adversarial-v2-llm-v2-3:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_3.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_3.json not found."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v2-llm-v2-3\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v2_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v2_llm_candidate_v2_3.json \
		--out reports/llm_adversarial_v2_candidate_v2_3_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--traces-out traces/local/llm_adversarial_v2_candidate_v2_3_semantic_model \
		--report-out reports/llm_adversarial_v2_candidate_v2_3_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v2_candidate_v2_3_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v2_candidate_v2_3_semantic_model_eval.json

# v2.3 on the HELD-OUT v3 slice — the genuine robustness surface (both fixes:
# held-out data + answer-key-free grader).
eval-adversarial-v3-llm-v2-3: check-llm-env
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--traces-out traces/local/llm_adversarial_v3_candidate_v2_3 \
		--report-out reports/llm_adversarial_v3_candidate_v2_3_eval.json \
		--agent-system-version llm_candidate_v2_3

semantic-model-decisions-adversarial-v3-llm-v2-3: check-llm-env
	@if [ ! -f reports/llm_adversarial_v3_candidate_v2_3_eval.json ]; then \
		echo "ERROR: reports/llm_adversarial_v3_candidate_v2_3_eval.json not found."; \
		echo "  Hint: run \`make eval-adversarial-v3-llm-v2-3\` (credentialed) first."; \
		exit 1; \
	fi
	@if [ ! -d traces/local/llm_adversarial_v3_candidate_v2_3 ]; then \
		echo "ERROR: traces/local/llm_adversarial_v3_candidate_v2_3/ not found."; \
		echo "  Hint: run \`make eval-adversarial-v3-llm-v2-3\` first."; \
		exit 1; \
	fi
	uv run python scripts/generate_semantic_decisions.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--eval-report reports/llm_adversarial_v3_candidate_v2_3_eval.json \
		--out reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_3.json

semantic-gate-adversarial-v3-llm-v2-3:
	@if [ ! -f reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_3.json ]; then \
		echo "ERROR: reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_3.json not found."; \
		echo "  Hint: run \`make semantic-model-decisions-adversarial-v3-llm-v2-3\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_replay_adversarial_v3_llm.py \
		--decisions reports/semantic_model_decisions/adversarial_v3_llm_candidate_v2_3.json \
		--out reports/llm_adversarial_v3_candidate_v2_3_semantic_replay_decisions.json
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v3.jsonl \
		--traces-out traces/local/llm_adversarial_v3_candidate_v2_3_semantic_model \
		--report-out reports/llm_adversarial_v3_candidate_v2_3_semantic_model_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions reports/llm_adversarial_v3_candidate_v2_3_semantic_replay_decisions.json
	uv run python scripts/check_semantic_gate.py \
		--report reports/llm_adversarial_v3_candidate_v2_3_semantic_model_eval.json

# ---- M7d: semantic-grader reliability vs human-authored gold set ------------
# The "grader as ground truth" guard. The model/NLI semantic grader decides
# makes_unsupported_claim; this measures HOW TRUSTWORTHY that grader is against
# a human-authored gold set whose labels are independent of any model. Recall
# (did it catch the real overpromises?) is the safety-critical metric — a false
# negative is an unsupported claim that passes the gate looking clean. Most
# targets are credential-free; only grader-gold-pass spends tokens and is
# WIRED, NOT RUN. M7 stays OPEN / NOT READY FOR PILOT.

# Credential-free end-to-end demo: score the tracked synthetic demo verdicts and
# render the reliability report. Proves the harness works with NO credentials.
# Demo outputs are gitignored (illustrative, not a real grader measurement).
grader-gold-score-demo:
	uv run python scripts/score_grader_gold.py \
		--verdicts tests/fixtures/grader_gold/demo_grader_verdicts.json \
		--out reports/grader_gold_reliability_demo.json
	uv run python scripts/generate_grader_reliability_report.py \
		--result reports/grader_gold_reliability_demo.json \
		--out reports/grader_gold_reliability_demo.md

# Credentialed gold-pass: run the model/NLI grader over the gold drafts ONCE
# (~$0.30-0.60). Grader gets operational context but NOT the gold label/answer
# key. Raw output embeds draft-quoting spans -> GITIGNORED. WIRED, NOT RUN.
grader-gold-pass: check-llm-env
	uv run python scripts/run_grader_gold_pass.py \
		--out reports/grader_gold/raw_decisions.json

# Credential-free: strip the gitignored raw verdicts to a public-safe fixture.
grader-gold-replay:
	@if [ ! -f reports/grader_gold/raw_decisions.json ]; then \
		echo "ERROR: reports/grader_gold/raw_decisions.json not found."; \
		echo "  This strips an existing gold-pass file; it does NOT call the grader."; \
		echo "  Hint: run \`make grader-gold-pass\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python scripts/build_grader_gold_replay.py \
		--raw reports/grader_gold/raw_decisions.json \
		--out reports/grader_gold/verdicts.json

# Credential-free: score the public-safe verdicts and render the reliability
# report. The report + result JSON are public-safe and meant to be tracked.
grader-reliability-report:
	@if [ ! -f reports/grader_gold/verdicts.json ]; then \
		echo "ERROR: reports/grader_gold/verdicts.json not found."; \
		echo "  The report scores public-safe verdicts; it does NOT call the grader."; \
		echo "  Hint: run \`make grader-gold-pass\` then \`make grader-gold-replay\` first."; \
		exit 1; \
	fi
	uv run python scripts/score_grader_gold.py \
		--verdicts reports/grader_gold/verdicts.json \
		--out reports/grader_gold_reliability.json
	uv run python scripts/generate_grader_reliability_report.py \
		--result reports/grader_gold_reliability.json \
		--out reports/grader_gold_reliability.md

# ---- Semantic-only regression seeds (adversarial v1 model/NLI audit) ---------
# On-disk only: NO LLM call, NO credentials, NO candidate rerun. The seeder
# pins the model/NLI semantic-only UNSAFE_CUSTOMER_COMMS failures (drafts the
# lexical grader cleared) as pending_review regression seeds, sourced from the
# tracked public semantic audit summary + the synthetic dataset, and builds a
# matching tracked SemanticDecision replay fixture. The seeds are now
# credential-free replayable: `regression-replay-adversarial-v1-semantic` feeds
# that fixture to the existing precomputed-decision lane (run_eval.py
# --semantic-decisions) with the deterministic improved_v0 profile, so the
# OFFLINE unsupported_claim_semantic grader fires UNSAFE_CUSTOMER_COMMS with no
# model call. The fixture pins the audit's verdict; it does not re-derive the
# claim from a live draft (that would need credentials). Evaluator/grader
# separation is unaffected — only the offline grader is fed, never the runtime
# EvaluatorNode. `regression-check-...` validates shape + summary linkage.

regression-seed-adversarial-v1-semantic:
	@if [ ! -f reports/llm_adversarial_v1_semantic_audit_summary.json ]; then \
		echo "ERROR: reports/llm_adversarial_v1_semantic_audit_summary.json not found."; \
		echo "  The seeder reads the public semantic audit summary; it does NOT call a model."; \
		echo "  Hint: run \`make semantic-audit-summary-adversarial-v1-llm\` (on-disk) first."; \
		exit 1; \
	fi
	uv run python scripts/seed_semantic_regressions_adversarial_v1.py \
		--summary reports/llm_adversarial_v1_semantic_audit_summary.json \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--out case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl
	uv run python scripts/build_semantic_replay_fixture_adversarial_v1.py \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl \
		--summary reports/llm_adversarial_v1_semantic_audit_summary.json \
		--out case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1_decisions.json

regression-check-adversarial-v1-semantic:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl
	uv run python scripts/check_semantic_regressions_adversarial_v1.py \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl \
		--summary reports/llm_adversarial_v1_semantic_audit_summary.json

# Credential-free replay: prove the offline semantic grader fires on all 3
# seeds via the tracked precomputed-decision fixture. Runs the deterministic
# improved_v0 profile (no credentials, no model call, no candidate rerun) and
# asserts the unsupported_claim_semantic grader produced UNSAFE_CUSTOMER_COMMS
# for every seed. Report + deterministic traces are gitignored regenerable
# check outputs.
regression-replay-adversarial-v1-semantic:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl \
		--traces-out traces/local/regression_semantic_adversarial_v1 \
		--report-out reports/regression_semantic_adversarial_v1_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1_decisions.json
	uv run python scripts/check_semantic_regressions_adversarial_v1.py \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl \
		--summary reports/llm_adversarial_v1_semantic_audit_summary.json \
		--replay-report reports/regression_semantic_adversarial_v1_eval.json

# ---- Semantic-only regression seeds (adversarial v2 model/NLI audit, M7) -----
# The credentialed M7 run flagged 14 semantic-only UNSAFE_CUSTOMER_COMMS drafts
# the lexical grader cleared. These targets pin them as pending_review seeds +
# a credential-free replay fixture, on-disk only: NO LLM call, NO credentials,
# NO candidate rerun. Seeds + decisions fixture are tracked public artifacts; the
# replay report + deterministic traces are gitignored regenerable check outputs.

regression-seed-adversarial-v2-semantic:
	@if [ ! -f reports/llm_adversarial_v2_semantic_audit_summary.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_semantic_audit_summary.json not found."; \
		echo "  The seeder reads the public v2 semantic audit summary; it does NOT call a model."; \
		echo "  Hint: run \`make semantic-audit-summary-adversarial-v2-llm\` (on-disk) first."; \
		exit 1; \
	fi
	uv run python scripts/seed_semantic_regressions_adversarial_v2.py \
		--summary reports/llm_adversarial_v2_semantic_audit_summary.json \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--out case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl
	uv run python scripts/build_semantic_replay_fixture_adversarial_v2.py \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--summary reports/llm_adversarial_v2_semantic_audit_summary.json \
		--out case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2_decisions.json

regression-check-adversarial-v2-semantic:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl
	uv run python scripts/check_semantic_regressions_adversarial_v2.py \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--summary reports/llm_adversarial_v2_semantic_audit_summary.json

# Credential-free replay: prove the offline semantic grader fires on all 14
# seeds via the tracked precomputed-decision fixture. Runs the deterministic
# improved_v0 profile (no credentials, no model call, no candidate rerun) and
# asserts the unsupported_claim_semantic grader produced UNSAFE_CUSTOMER_COMMS
# for every seed. Report + deterministic traces are gitignored regenerable
# check outputs.
regression-replay-adversarial-v2-semantic:
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--traces-out traces/local/regression_semantic_adversarial_v2 \
		--report-out reports/regression_semantic_adversarial_v2_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2_decisions.json
	uv run python scripts/check_semantic_regressions_adversarial_v2.py \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--summary reports/llm_adversarial_v2_semantic_audit_summary.json \
		--replay-report reports/regression_semantic_adversarial_v2_eval.json

# ---- Grader-calibration fixtures (the M7 grader_calibration_review over-flags)
# Credential-free, on-disk only: NO LLM call, NO credentials, NO candidate rerun.
# Covers the 4 over-flags the original adjudication marked grader_calibration_review
# PLUS the candidate-v2 residual adjudication's tool-verified-fact over-flag
# (case_006) = 5 cases. These targets represent each as a NON-claim and prove the
# offline semantic lane CLEARS them — the mirror of the regression replay (which
# proves the lane FIRES on the 14). They do not add unsupported_claim_semantic to
# default GRADERS, and they are not a model-safety or readiness claim. The
# needs_human_review findings are intentionally excluded.
calibration-seed-adversarial-v2-semantic:
	@if [ ! -f reports/llm_adversarial_v2_semantic_adjudication.json ]; then \
		echo "ERROR: reports/llm_adversarial_v2_semantic_adjudication.json not found."; \
		echo "  Hint: run \`make semantic-adjudication-adversarial-v2\` (on-disk) first."; \
		exit 1; \
	fi
	uv run python scripts/build_semantic_calibration_adversarial_v2.py \
		--adjudication reports/llm_adversarial_v2_semantic_adjudication.json \
		--seeds case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--residual-adjudication reports/llm_adversarial_v2_candidate_v2_residual_adjudication.json \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--out-dataset case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2.jsonl \
		--out-decisions case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2_decisions.json
	uv run python scripts/check_semantic_calibration_adversarial_v2.py \
		--adjudication reports/llm_adversarial_v2_semantic_adjudication.json \
		--residual-adjudication reports/llm_adversarial_v2_candidate_v2_residual_adjudication.json \
		--dataset case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2.jsonl

# Credential-free replay: prove the offline unsupported_claim_semantic grader
# CLEARS all 5 over-flag cases when they are represented as non-claims. Runs the
# deterministic improved_v0 vehicle with the calibration decisions fixture (no
# model call), then asserts zero UNSAFE_CUSTOMER_COMMS on the 5. Report + traces
# are gitignored regenerable check outputs.
calibration-replay-adversarial-v2-semantic:
	uv run python scripts/validate_dataset.py case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2.jsonl
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2.jsonl \
		--traces-out traces/local/calibration_semantic_adversarial_v2 \
		--report-out reports/calibration_semantic_adversarial_v2_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2_decisions.json
	uv run python scripts/check_semantic_calibration_adversarial_v2.py \
		--adjudication reports/llm_adversarial_v2_semantic_adjudication.json \
		--residual-adjudication reports/llm_adversarial_v2_candidate_v2_residual_adjudication.json \
		--dataset case_studies/financial_links_reliability/evals/calibration_semantic_adversarial_v2.jsonl \
		--replay-report reports/calibration_semantic_adversarial_v2_eval.json

# ---- M7 semantic failure analysis + remediation plan (credential-free) ------
# Turns the BLOCKED M7 audit into an action-oriented remediation plan. Reads only
# tracked public-safe inputs (the aggregate audit summary, the 24-case dataset
# metadata, and the 14 pinned regression seeds); reads NO raw candidate report,
# raw model/NLI decision, or raw trace, and makes NO model/LLM call. It does not
# tune any prompt or trigger a rerun — it documents the blocker. Posture stays
# NOT READY FOR PILOT; M7 stays OPEN.
semantic-failure-analysis-adversarial-v2:
	uv run python scripts/analyze_semantic_failures_adversarial_v2.py \
		--summary reports/llm_adversarial_v2_semantic_audit_summary.json \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--out-json reports/llm_adversarial_v2_semantic_failure_analysis.json \
		--out-md reports/llm_adversarial_v2_semantic_failure_analysis.md

# ---- M7 semantic adjudication of the 14 findings (credential-free) -----------
# Renders the public-safe adjudication of the 14 semantic-only findings:
# candidate_actionable | grader_calibration_review | needs_human_review, with a
# public reason code and whether each drives candidate-v2 changes. The verdicts
# were authored by REVIEW of the private, gitignored raw drafts / decision spans;
# this generator reads NO raw artifact (only the tracked failure-analysis report
# + the 14 pinned seeds) and makes NO model/LLM call. No prompt tuning, no rerun;
# M7 stays OPEN / NOT READY FOR PILOT.
semantic-adjudication-adversarial-v2:
	uv run python scripts/adjudicate_semantic_findings_adversarial_v2.py \
		--failure-analysis reports/llm_adversarial_v2_semantic_failure_analysis.json \
		--regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--out-json reports/llm_adversarial_v2_semantic_adjudication.json \
		--out-md reports/llm_adversarial_v2_semantic_adjudication.md

# ---- candidate-v2 RESIDUAL adjudication (credential-free) --------------------
# After the credentialed candidate-v2 run blocked on 3 residual semantic-only
# flags, this renders the public-safe adjudication of those 3 (candidate_actionable
# | grader_calibration_review | needs_human_review, a public reason code, and
# whether each drives a candidate-v2.1 control). Verdicts were authored by REVIEW
# of the private, gitignored candidate-v2 drafts / decision spans / tool outputs;
# this generator reads NO raw artifact (only the tracked 24-case dataset for
# per-case metadata) and makes NO model/LLM call. No prompt change, no rerun;
# M7 stays OPEN / NOT READY FOR PILOT.
candidate-v2-residual-adjudication-adversarial-v2:
	uv run python scripts/adjudicate_candidate_v2_residuals_adversarial_v2.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v2.jsonl \
		--out-json reports/llm_adversarial_v2_candidate_v2_residual_adjudication.json \
		--out-md reports/llm_adversarial_v2_candidate_v2_residual_adjudication.md

# M7 re-grounding: public-safe adjudication of the hardened-gate flags on
# candidate-v2 / v2.1 (after the build_semantic_prompt answer-key firewall).
# Reads only the tracked dataset; verdicts are authored public-safe constants.
# No model call, no draft text. (no LLM call)
reground-adjudication-adversarial-v2:
	uv run python scripts/generate_reground_adjudication_adversarial_v2.py \
		--out-md reports/llm_adversarial_v2_reground_adjudication.md \
		--out-json reports/llm_adversarial_v2_reground_adjudication.json

# ---- M7a: reusable credential-free semantic blocking gate -------------------
# scripts/check_semantic_gate.py is a reusable blocking gate over any eval
# report that carries the offline unsupported_claim_semantic lane. It calls no
# model and needs no credentials. These two targets exercise it in BOTH
# directions on tracked / regenerable synthetic artifacts. The gate is NOT in
# the default GRADERS / default eval run; the deterministic public proof loop
# is unchanged. M7 stays "gate infrastructure wired (M7a)" — a larger
# CREDENTIALED semantic audit must still run clean before M7 is complete, and
# the posture remains NOT READY FOR PILOT.

# NEGATIVE CONTROL: the gate MUST block the 3 known-failing adversarial v1
# semantic-only regression seeds. This target is GREEN only when the gate
# correctly fails on them (proving the gate has teeth). No model call.
semantic-gate-adversarial-v1-regressions:
	@echo "NEGATIVE CONTROL — the semantic gate MUST block the 3 known-failing adversarial v1 semantic regression seeds (no model call)."
	uv run python scripts/run_eval.py \
		--dataset case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl \
		--traces-out traces/local/regression_semantic_adversarial_v1 \
		--report-out reports/regression_semantic_adversarial_v1_eval.json \
		--agent-system-version improved_v0 \
		--semantic-decisions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1_decisions.json
	@uv run python -c "import json; r=json.load(open('reports/regression_semantic_adversarial_v1_eval.json')); n=[x['name'] for x in r['aggregate_grader_pass_rates']]; assert 'unsupported_claim_semantic' in n, 'semantic lane missing from regenerated report — control would pass for the wrong reason'; row=r['aggregate_grader_pass_rates'][n.index('unsupported_claim_semantic')]; assert row['total']-row['passed']==3, 'expected 3 semantic failures to block; got '+str(row)"
	@echo "  (verified: regenerated report carries the semantic lane with 3 failures — the gate has real bad input to block.)"
	@if uv run python scripts/check_semantic_gate.py --report reports/regression_semantic_adversarial_v1_eval.json; then \
		echo "ERROR: semantic gate PASSED on known-failing seeds — the gate has no teeth."; exit 1; \
	else \
		echo "OK (negative control): semantic gate correctly BLOCKED the 3 known-failing seeds (gate exit non-zero, as required)."; \
	fi

# PASS-PATH DEMO: gate the hand-authored synthetic clean fixture over the
# DETERMINISTIC improved_v0 lane. Proves the gate's pass path on a real on-disk
# report. This is NOT a model-safety or pilot-readiness claim — the fixture is
# authored, not a credentialed model audit.
semantic-gate-adversarial-v1-improved: eval-adversarial-v1-improved-semantic
	@echo "PASS-PATH DEMO — gating a hand-authored SYNTHETIC clean fixture over deterministic improved_v0. Proves the gate's pass path only; NOT a model-safety or pilot-readiness claim. A larger credentialed semantic audit is still required for M7."
	uv run python scripts/check_semantic_gate.py --report reports/improved_adversarial_v1_semantic_eval.json

# ---- Redaction + evidence pack for the adversarial v1 LLM evidence ----------
# On-disk only: these do NOT call the LLM or require credentials. They assume
# `make eval-card-adversarial-v1-llm` (credentialed) already produced the raw
# candidate reports + raw traces. Both candidates' raw traces are redacted and
# the assembled pack at evidence_packs/financial_links_llm_adversarial_v1/ is
# the only public-safe surface for this loop. When the model/NLI decision files
# exist, the pack also ships an aggregate-only semantic audit (no raw decisions).
# The pack always bundles the tracked pending_review semantic regression seeds
# (regressions_semantic_adversarial_v1.jsonl) + the credential-free replay
# fixture (..._decisions.json) under regressions/ — both are committed on-disk
# artifacts, so this stays credential-free (no check-llm-env, no model call).

redact-adversarial-v1-llm:
	@for cand in candidate_v0 candidate_v1; do \
		src=traces/local/llm_adversarial_v1_$$cand; \
		if [ ! -d $$src ]; then \
			echo "ERROR: $$src/ not found."; \
			echo "  Hint: run \`make eval-card-adversarial-v1-llm\` (credentialed) first."; \
			exit 1; \
		fi; \
		dst=traces/redacted/llm_adversarial_v1_$$cand; \
		mkdir -p $$dst; \
		for input in $$src/*.json; do \
			base=$$(basename $$input .json); \
			uv run python scripts/redact_trace.py \
				--input $$input \
				--policy configs/redaction_policy.yaml \
				--output $$dst/$$base.redacted.json \
				--report-out $$dst/$$base.redaction_report.json || exit 1; \
		done; \
	done

evidence-pack-adversarial-v1-llm: redact-adversarial-v1-llm
	@for f in reports/llm_adversarial_v1_candidate_v0_eval.json reports/llm_adversarial_v1_candidate_v1_eval.json; do \
		if [ ! -f $$f ]; then \
			echo "ERROR: $$f not found."; \
			echo "  Hint: run \`make eval-card-adversarial-v1-llm\` (credentialed) first."; \
			exit 1; \
		fi; \
	done
	uv run python scripts/generate_eval_card.py \
		--baseline-report reports/llm_adversarial_v1_candidate_v0_eval.json \
		--improved-report reports/llm_adversarial_v1_candidate_v1_eval.json \
		--baseline-label Before \
		--improved-label After \
		--out reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md
	@v0=reports/semantic_model_decisions/adversarial_v1_llm_candidate_v0.json; \
	v1=reports/semantic_model_decisions/adversarial_v1_llm_candidate_v1.json; \
	sem_args=""; \
	if [ -f $$v0 ] && [ -f $$v1 ]; then \
		uv run python scripts/summarize_semantic_audit_adversarial_v1_llm.py \
			--report-v0 reports/llm_adversarial_v1_candidate_v0_eval.json \
			--report-v1 reports/llm_adversarial_v1_candidate_v1_eval.json \
			--decisions-v0 $$v0 --decisions-v1 $$v1 \
			--out-json reports/llm_adversarial_v1_semantic_audit_summary.json \
			--out-md reports/llm_adversarial_v1_semantic_audit_summary.md || exit 1; \
		sem_args="--semantic-decisions-v0 $$v0 --semantic-decisions-v1 $$v1 --semantic-summary reports/llm_adversarial_v1_semantic_audit_summary.md"; \
	else \
		echo "NOTE: model/NLI decision files absent; packaging WITHOUT the semantic aggregate."; \
		echo "      Run \`make semantic-model-decisions-adversarial-v1-llm-v0\` + \`...-llm-v1\` (credentialed) to include it."; \
	fi; \
	uv run python scripts/package_evidence_adversarial_v1_llm.py \
		--raw-v0-report reports/llm_adversarial_v1_candidate_v0_eval.json \
		--raw-v1-report reports/llm_adversarial_v1_candidate_v1_eval.json \
		--eval-card reports/llm_adversarial_v1_candidate_v1_vs_v0_card.md \
		--redacted-traces-v0 traces/redacted/llm_adversarial_v1_candidate_v0 \
		--redacted-traces-v1 traces/redacted/llm_adversarial_v1_candidate_v1 \
		--policy configs/redaction_policy.yaml \
		--improvement-memo reports/llm_adversarial_v1_improvement_memo.md \
		--semantic-regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1.jsonl \
		--semantic-replay-decisions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v1_decisions.json \
		--out evidence_packs/financial_links_llm_adversarial_v1 $$sem_args

# ---- Public-safe evidence pack for the executed adversarial v2 LLM run (M7) --
# CREDENTIAL-FREE by construction. Its required inputs are the tracked,
# public-safe M7 surfaces — the Before/After comparison card, the aggregate
# semantic audit (json + md), the 14 pending_review regression seeds, and the
# credential-free replay fixture. It does NOT run check-llm-env, candidate
# evals, semantic-model decision generation, the semantic gate, or any LLM /
# model call; those already happened in the credentialed M7 run and produced
# these tracked artifacts. M7 ran once and the gate BLOCKED, so the pack states
# M7 OPEN / NOT READY FOR PILOT.
#
# When the gitignored raw M7 artifacts (raw candidate reports + raw per-candidate
# traces) are present locally, the pack ALSO ships redacted candidate eval
# summaries + redacted traces; redaction is deterministic and credential-free.
# When they are absent (any fresh clone), the pack is the credential-free core
# and the target still succeeds.

evidence-pack-adversarial-v2-llm:
	@for f in \
		reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md \
		reports/llm_adversarial_v2_semantic_audit_summary.json \
		reports/llm_adversarial_v2_semantic_audit_summary.md \
		case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2_decisions.json; do \
		if [ ! -f $$f ]; then \
			echo "ERROR: $$f not found."; \
			echo "  This target packages tracked public-safe M7 artifacts; it runs NO LLM/model call."; \
			echo "  Hint: produce them with eval-card-adversarial-v2-llm, semantic-audit-summary-adversarial-v2-llm, and regression-seed-adversarial-v2-semantic."; \
			exit 1; \
		fi; \
	done
	@raw_args=""; \
	rv0=reports/llm_adversarial_v2_candidate_v0_eval.json; \
	rv1=reports/llm_adversarial_v2_candidate_v1_eval.json; \
	tv0=traces/local/llm_adversarial_v2_candidate_v0; \
	tv1=traces/local/llm_adversarial_v2_candidate_v1; \
	if [ -f $$rv0 ] && [ -f $$rv1 ] && [ -d $$tv0 ] && [ -d $$tv1 ]; then \
		echo "NOTE: raw M7 artifacts present locally; ALSO shipping redacted candidate summaries + traces."; \
		for cand in candidate_v0 candidate_v1; do \
			src=traces/local/llm_adversarial_v2_$$cand; \
			dst=traces/redacted/llm_adversarial_v2_$$cand; \
			mkdir -p $$dst; \
			for input in $$src/*.json; do \
				base=$$(basename $$input .json); \
				uv run python scripts/redact_trace.py \
					--input $$input \
					--policy configs/redaction_policy.yaml \
					--output $$dst/$$base.redacted.json \
					--report-out $$dst/$$base.redaction_report.json || exit 1; \
			done; \
		done; \
		raw_args="--policy configs/redaction_policy.yaml --raw-v0-report $$rv0 --raw-v1-report $$rv1 --redacted-traces-v0 traces/redacted/llm_adversarial_v2_candidate_v0 --redacted-traces-v1 traces/redacted/llm_adversarial_v2_candidate_v1"; \
	else \
		echo "NOTE: raw M7 artifacts absent; packaging the credential-free core only (card + aggregate + summary + regressions)."; \
	fi; \
	uv run python scripts/package_evidence_adversarial_v2_llm.py \
		--eval-card reports/llm_adversarial_v2_candidate_v1_vs_v0_card.md \
		--semantic-summary-json reports/llm_adversarial_v2_semantic_audit_summary.json \
		--semantic-summary-md reports/llm_adversarial_v2_semantic_audit_summary.md \
		--semantic-regressions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2.jsonl \
		--semantic-replay-decisions case_studies/financial_links_reliability/evals/regressions_semantic_adversarial_v2_decisions.json \
		--out evidence_packs/financial_links_llm_adversarial_v2 $$raw_args

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

# ---- Opt-in credentialed repeat-run capture — adversarial v1 (12-case) ------
# Parallel to the adversarial v0 repeat loop above, but for the 12-case
# adversarial v1 slice with non-colliding output paths. Opt-in, never in CI,
# real Anthropic tokens. Default RUNS=5; override with
# `RUNS=10 make repeat-adversarial-v1-llm-v0`.
#
# Output layout (gitignored under reports/llm_repeats/):
#   reports/llm_repeats/adversarial_v1/<profile>/<timestamp>/run_<i>/eval_report.json
#   reports/llm_repeats/adversarial_v1/<profile>/<timestamp>/run_<i>/traces/<case>.json
#
# repeat-adversarial-v1-llm-summary aggregates EVERY eval_report.json under
# reports/llm_repeats/adversarial_v1/ into a public-safe Markdown + JSON
# summary at reports/llm_adversarial_v1_repeat_summary.{md,json}. The
# aggregator defaults to allow_mixed_datasets=False, so a stray adversarial v0
# report under this tree fails the run rather than silently mixing slices.

REPEAT_V1_OUT_DIR ?= reports/llm_repeats/adversarial_v1
REPEAT_V1_SUMMARY_MD ?= reports/llm_adversarial_v1_repeat_summary.md
REPEAT_V1_SUMMARY_JSON ?= reports/llm_adversarial_v1_repeat_summary.json

repeat-adversarial-v1-llm-v0: check-llm-env
	uv run python scripts/run_llm_repeats.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--profile llm_candidate_v0 \
		--runs $(RUNS) \
		--out-dir $(REPEAT_V1_OUT_DIR)

repeat-adversarial-v1-llm-v1: check-llm-env
	uv run python scripts/run_llm_repeats.py \
		--dataset case_studies/financial_links_reliability/evals/adversarial_v1.jsonl \
		--profile llm_candidate_v1 \
		--runs $(RUNS) \
		--out-dir $(REPEAT_V1_OUT_DIR)

repeat-adversarial-v1-llm-summary:
	@if ! ls $(REPEAT_V1_OUT_DIR)/*/*/run_*/eval_report.json >/dev/null 2>&1; then \
		echo "ERROR: no captured repeat-run eval_report.json files under $(REPEAT_V1_OUT_DIR)/"; \
		echo "  Hint: run \`RUNS=5 make repeat-adversarial-v1-llm-v0\` (credentialed) first."; \
		exit 1; \
	fi
	uv run python -c "import sys, glob; \
paths = sorted(glob.glob('$(REPEAT_V1_OUT_DIR)/*/*/run_*/eval_report.json')); \
from scripts.aggregate_llm_repeats import aggregate_files, render_markdown; \
import json; from pathlib import Path; \
summary = aggregate_files([Path(p) for p in paths], allow_mixed_profiles=True); \
Path('$(REPEAT_V1_SUMMARY_MD)').write_text(render_markdown(summary)); \
Path('$(REPEAT_V1_SUMMARY_JSON)').write_text(json.dumps(summary, indent=2)); \
print(f'OK: aggregated {summary[\"run_count\"]} adversarial_v1 repeat runs across profiles={summary[\"profile_family\"]} -> $(REPEAT_V1_SUMMARY_MD)')"

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
