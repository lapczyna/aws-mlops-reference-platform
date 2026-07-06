.DEFAULT_GOAL := help
.PHONY: help install install-hooks format lint typecheck test test-cov clean

VENV_BIN := .venv/Scripts
PYTHON := $(VENV_BIN)/python

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install package with dev dependencies
	python -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

install-hooks: ## Install pre-commit git hooks
	$(VENV_BIN)/pre-commit install

format: ## Auto-format source and tests with Black + Ruff
	$(VENV_BIN)/black src tests
	$(VENV_BIN)/ruff check --fix src tests

lint: ## Lint source and tests with Ruff (no fixes applied)
	$(VENV_BIN)/ruff check src tests
	$(VENV_BIN)/black --check src tests

typecheck: ## Run mypy in strict mode
	$(VENV_BIN)/mypy src

test: ## Run the test suite
	$(VENV_BIN)/pytest

test-cov: ## Run the test suite with coverage report
	$(VENV_BIN)/pytest --cov --cov-report=term-missing --cov-report=xml

clean: ## Remove build, cache and coverage artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov build dist *.egg-info
