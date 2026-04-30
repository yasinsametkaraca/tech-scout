# tech-scout — developer Makefile
# Targets are POSIX-compatible. On Windows, use Git Bash or WSL.

.PHONY: help install install-dev install-plugin lint format typecheck test test-unit test-integration coverage doctor clean

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
MYPY ?= $(PYTHON) -m mypy

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	$(PIP) install -e .

install-dev:  ## Install runtime + development dependencies
	$(PIP) install -e ".[dev]"
	pre-commit install

install-plugin:  ## Symlink/copy this repo's .claude into ~/.claude/plugins/tech-scout (Claude Code reads it at startup)
	@echo "Use Claude Code's native plugin loading instead — open this repo in Claude Code and it auto-detects .claude/."
	@echo "If you want global activation, copy the .claude/ directory into ~/.claude/plugins/tech-scout/ manually."

lint:  ## Run ruff lint
	$(RUFF) check src scripts tests

format:  ## Run ruff format
	$(RUFF) format src scripts tests
	$(RUFF) check --fix src scripts tests

typecheck:  ## Run mypy strict
	$(MYPY) src scripts

test:  ## Run all tests with coverage
	$(PYTEST)

test-unit:  ## Run unit tests only
	$(PYTEST) -m unit

test-integration:  ## Run integration tests only
	$(PYTEST) -m integration

coverage:  ## Generate HTML coverage report
	$(PYTEST) --cov-report=html
	@echo "Open htmlcov/index.html"

doctor:  ## Run environment check (Python, deps, paths, locale templates)
	$(PYTHON) scripts/ts_doctor.py

clean:  ## Remove build artifacts and caches
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
