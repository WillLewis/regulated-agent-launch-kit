.PHONY: help setup test scaffold-test lint

# The basic targets (test, scaffold-test) must succeed without external
# credentials. Braintrust-backed evals require .env (see .env.example).

help:
	@echo "Available targets:"
	@echo "  setup         install runtime + dev dependencies via uv"
	@echo "  test          run the full pytest suite"
	@echo "  scaffold-test run only the scaffold contract test"
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

lint:
	uv run ruff check .
