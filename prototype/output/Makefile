.PHONY: test test-all test-verbose test-debug clean clean-reports help install-deps

# Shell settings
SHELL := /bin/bash

# Directories
TESTCASES_DIR := testcases
REPORTS_DIR := reports
VENV_DIR := ../../venv

# Python interpreter (use venv if available)
PYTHON := python3
ifeq ($(shell test -d $(VENV_DIR) && echo yes),yes)
    PYTHON := $(VENV_DIR)/bin/python
    PYTEST := $(VENV_DIR)/bin/pytest
else
    PYTEST := pytest
endif

# Test selection
TEST_FILTER ?=
MARKER ?=
QAID ?=

# Color output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
RESET := \033[0m

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)DSL Test Suite - Available Targets$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)Examples:$(RESET)"
	@echo "  make test                     # Run all tests"
	@echo "  make test QAID=205812         # Run specific test by QAID"
	@echo "  make test MARKER=smoke        # Run tests with marker"
	@echo "  make test TEST_FILTER='-k 205' # Run tests matching pattern"
	@echo "  make test-verbose             # Run with verbose output"
	@echo "  make test-debug               # Run with debug logging"
	@echo "  make clean-conversion         # Clean conversion cache for fresh start"
	@echo "  make convert-grp GRP=grp.ips_nat.full  # Convert tests from grp file"
	@echo "  make test-grp GRP=grp.ips_nat.full     # Run tests in grp order"
	@echo "  make show-grp-order           # Show current test execution order"
	@echo ""

test: clean-reports ## Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
ifdef QAID
	-$(PYTEST) $(TESTCASES_DIR)/test__$(QAID).py
else ifdef MARKER
	-$(PYTEST) -m $(MARKER) $(TESTCASES_DIR)/
else
	-$(PYTEST) $(TEST_FILTER) $(TESTCASES_DIR)/
endif
	@sleep 1 && python3 /home/fosqa/autolibv3/autolib_v3/prototype/output/generate_execution_html_v2.py 2>/dev/null || python3 generate_execution_html.py 2>/dev/null || true
	@echo "$(GREEN)✓ Tests complete!$(RESET)"
	@echo "$(YELLOW)Reports available at:$(RESET)"
	@echo "  HTML: $(REPORTS_DIR)/test_report.html"
	@echo "  Execution Order: $(REPORTS_DIR)/execution_order.html (with actual results)"
	@echo "  XML:  $(REPORTS_DIR)/test_report.xml"
	@echo "  Log:  $(REPORTS_DIR)/test_execution.log"

test-all: clean-reports ## Run all tests with full output
	@echo "$(BLUE)Running all tests with full output...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) -v -s $(TESTCASES_DIR)/
	@echo "$(GREEN)✓ All tests complete!$(RESET)"

test-verbose: clean-reports ## Run tests with verbose output
	@echo "$(BLUE)Running tests (verbose mode)...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) -vv -s $(TESTCASES_DIR)/

test-debug: clean-reports ## Run tests with debug logging
	@echo "$(BLUE)Running tests with debug logging...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) -vv -s --log-cli-level=DEBUG $(TESTCASES_DIR)/

test-smoke: clean-reports ## Run smoke tests only
	@echo "$(BLUE)Running smoke tests...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) -m smoke $(TESTCASES_DIR)/

test-regression: clean-reports ## Run regression tests only
	@echo "$(BLUE)Running regression tests...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) -m regression $(TESTCASES_DIR)/

test-grp: ## Run tests from group file (usage: make test-grp GRP=grp.ips_nat.full)
	@if [ -z "$(GRP)" ]; then \
		echo "$(RED)Error: GRP parameter required$(RESET)"; \
		echo "$(YELLOW)Usage: make test-grp GRP=grp.ips_nat.full$(RESET)"; \
		exit 1; \
	fi
	@if [ ! -f .pytest-order.txt ]; then \
		echo "$(RED)Error: .pytest-order.txt not found$(RESET)"; \
		echo "$(YELLOW)Run transpiler first: python ../run_transpiler.py -g path/to/$(GRP)$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running tests from group file: $(GRP)$(RESET)"
	@echo "$(YELLOW)Test execution order enforced by .pytest-order.txt$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	-$(PYTEST) -v $(TESTCASES_DIR)/
	@sleep 1 && python3 /home/fosqa/autolibv3/autolib_v3/prototype/output/generate_execution_html_v2.py 2>/dev/null || python3 generate_execution_html.py 2>/dev/null || true
	@echo "$(GREEN)✓ Group file tests complete!$(RESET)"
	@echo "$(YELLOW)Reports available at:$(RESET)"
	@echo "  HTML: $(REPORTS_DIR)/test_report.html (grouped by pass/fail)"
	@echo "  Execution Order: $(REPORTS_DIR)/execution_order.html (ordered with actual results)"
	@echo "  XML:  $(REPORTS_DIR)/test_report.xml"
	@echo "  Log:  $(REPORTS_DIR)/test_execution.log"

convert-grp: ## Convert DSL tests from group file (usage: make convert-grp GRP=grp.ips_nat.full)
	@if [ -z "$(GRP)" ]; then \
		echo "$(RED)Error: GRP parameter required$(RESET)"; \
		echo "$(YELLOW)Usage: make convert-grp GRP=grp.ips_nat.full$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Converting tests from group file: $(GRP)$(RESET)"
	@cd .. && $(PYTHON) run_transpiler.py -g ../../testcase/ips/$(GRP) -o output
	@echo "$(GREEN)✓ Conversion complete!$(RESET)"
	@echo "$(YELLOW)Run tests with: make test-grp GRP=$(GRP)$(RESET)"

show-grp-order: ## Show test execution order from .pytest-order.txt
	@if [ -f .pytest-order.txt ]; then \
		echo "$(BLUE)Test Execution Order:$(RESET)"; \
		cat .pytest-order.txt | grep -v '^#' | grep -v '^$$' | awk -F: '{printf "  %3s. %s\n", $$1, $$2}'; \
	else \
		echo "$(YELLOW)No test order file found (.pytest-order.txt)$(RESET)"; \
		echo "$(YELLOW)Convert a group file first: make convert-grp GRP=grp.ips_nat.full$(RESET)"; \
	fi

test-failed: ## Re-run previously failed tests
	@echo "$(BLUE)Re-running failed tests...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) --lf $(TESTCASES_DIR)/

test-last: ## Run only last failed test
	@echo "$(BLUE)Running last failed test...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) --last-failed-no-failures none $(TESTCASES_DIR)/

test-x: ## Stop on first failure
	@echo "$(BLUE)Running tests (stop on first failure)...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) -x $(TESTCASES_DIR)/

test-collect: ## Show what tests would be run
	@echo "$(BLUE)Collecting tests...$(RESET)"
	$(PYTEST) --collect-only $(TESTCASES_DIR)/

report: ## Open HTML report in browser
	@if [ -f $(REPORTS_DIR)/test_report.html ]; then \
		echo "$(GREEN)Opening test report...$(RESET)"; \
		xdg-open $(REPORTS_DIR)/test_report.html 2>/dev/null || open $(REPORTS_DIR)/test_report.html 2>/dev/null || echo "$(YELLOW)Report: $(REPORTS_DIR)/test_report.html$(RESET)"; \
	else \
		echo "$(RED)No report found. Run tests first.$(RESET)"; \
	fi

clean-reports: ## Clean test reports
	@echo "$(YELLOW)Cleaning reports...$(RESET)"
	@rm -rf $(REPORTS_DIR)
	@rm -rf .pytest_cache

clean-conversion: ## Clean conversion cache files for fresh conversion
	@echo "$(YELLOW)Cleaning conversion cache files...$(RESET)"
	@rm -f .conversion_registry.json
	@rm -f conftest.py
	@rm -rf $(TESTCASES_DIR)/helpers
	@rm -f .pytest-order.txt
	@echo "$(GREEN)✓ Conversion cache cleaned$(RESET)"
	@echo "$(YELLOW)Note: Test files (test_*.py) preserved. Use 'make clean-all' to remove everything.$(RESET)"

clean-all: clean-reports ## Clean all generated files including tests
	@echo "$(YELLOW)Cleaning ALL generated files (including tests)...$(RESET)"
	@rm -f .conversion_registry.json
	@rm -f conftest.py
	@rm -f .pytest-order.txt
	@rm -rf $(TESTCASES_DIR)/test_*.py
	@rm -rf $(TESTCASES_DIR)/helpers
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Complete clean finished$(RESET)"

clean: clean-reports ## Clean Python cache files only
	@echo "$(YELLOW)Cleaning Python cache files...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(RESET)"

install-deps: ## Install required Python packages
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	$(PYTHON) -m pip install pytest pytest-html pytest-cov pytest-mock
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

list-tests: ## List all available tests
	@echo "$(BLUE)Available tests:$(RESET)"
	@find $(TESTCASES_DIR) -name "test_*.py" -type f | sed 's|$(TESTCASES_DIR)/||' | sort

coverage: clean-reports ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	@mkdir -p $(REPORTS_DIR)
	$(PYTEST) --cov=$(TESTCASES_DIR) --cov-report=html:$(REPORTS_DIR)/coverage --cov-report=term $(TESTCASES_DIR)/
	@echo "$(GREEN)✓ Coverage report: $(REPORTS_DIR)/coverage/index.html$(RESET)"

lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(RESET)"
	@$(PYTHON) -m pylint $(TESTCASES_DIR)/ || true
	@$(PYTHON) -m flake8 $(TESTCASES_DIR)/ || true

info: ## Show test environment info
	@echo "$(BLUE)Test Environment Information$(RESET)"
	@echo "  Python: $(shell $(PYTHON) --version)"
	@echo "  Pytest: $(shell $(PYTEST) --version)"
	@echo "  Test directory: $(TESTCASES_DIR)"
	@echo "  Reports directory: $(REPORTS_DIR)"
	@echo "  Test count: $(shell find $(TESTCASES_DIR) -name 'test_*.py' | wc -l)"
