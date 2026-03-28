.PHONY: install test smoke regression slow cov report lint typecheck ci clean all

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest

# ─── Setup ──────────────────────────────────────────────────────────────────
install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

# ─── Test Targets ───────────────────────────────────────────────────────────
test:  ## Run all tests with verbose output
	$(PYTEST) -v

smoke:  ## Run smoke tests only (fast sanity check)
	$(PYTEST) -v -m smoke

regression:  ## Run regression tests
	$(PYTEST) -v -m regression

slow:  ## Run slow tests
	$(PYTEST) -v -m slow

unit:  ## Run unit tests only
	$(PYTEST) -v tests/unit/

integration:  ## Run integration tests only
	$(PYTEST) -v tests/integration/

# ─── Coverage ───────────────────────────────────────────────────────────────
cov:  ## Run tests with coverage, fail if under 80%
	$(PYTEST) --cov=src --cov-report=term-missing --cov-fail-under=80

# ─── Reporting ──────────────────────────────────────────────────────────────
report:  ## Generate HTML + JSON test reports
	$(PYTEST) \
		--html=report.html --self-contained-html \
		--json-report --json-report-file=report.json \
		-v

# ─── Code Quality ──────────────────────────────────────────────────────────
lint:  ## Run flake8 linter
	$(PYTHON) -m flake8 src/ tests/ --max-line-length=120 --exclude=__pycache__

typecheck:  ## Run mypy type checker
	$(PYTHON) -m mypy src/ --ignore-missing-imports

# ─── Parallel Tests ────────────────────────────────────────────────────────
parallel:  ## Run tests in parallel with xdist
	$(PYTEST) -n auto -v

# ─── CI (all checks) ───────────────────────────────────────────────────────
ci: lint typecheck cov report  ## Run full CI pipeline locally

# ─── Cleanup ────────────────────────────────────────────────────────────────
clean:  ## Remove build artifacts, caches, reports
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov .coverage
	rm -f report.html report.json coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# ─── Help ───────────────────────────────────────────────────────────────────
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
