"""
Conftest Generator Module
Handles generation of pytest conftest.py with fixtures and hooks
"""

from pathlib import Path
from typing import Optional


class ConftestGenerator:
    """Generate pytest conftest.py with fixtures and pytest hooks"""
    
    def __init__(self):
        """Initialize conftest generator"""
        pass
    
    def generate_header(self, env_file: Optional[Path] = None) -> str:
        """
        Generate conftest.py header with environment configuration
        
        Args:
            env_file: Path to environment configuration file
            
        Returns:
            String containing the complete conftest.py header with imports,
            testbed fixture, and all pytest hooks
        """
        # Base imports and setup
        header = self._generate_imports()
        
        # Add testbed fixture
        header += self._generate_testbed_fixture(env_file)
        
        # Add pytest hooks
        header += self._generate_pytest_hooks()
        
        # Add logger fixture
        header += self._generate_logger_fixture()
        
        # Add placeholder for auto-generated fixtures
        header += self._generate_fixtures_placeholder()
        
        return header
    
    def _generate_imports(self) -> str:
        """Generate import statements for conftest.py"""
        return '''"""
Auto-generated conftest.py
Contains fixtures converted from DSL include files
"""

import pytest
from pathlib import Path
import sys

# Add fluent API to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'fluent_api'))

from fluent import TestBed
'''
    
    def _generate_testbed_fixture(self, env_file: Optional[Path] = None) -> str:
        """
        Generate testbed fixture with environment configuration
        
        Args:
            env_file: Path to environment configuration file
            
        Returns:
            String containing testbed fixture code
        """
        if env_file:
            # Convert to absolute path for reliability
            abs_env_file = env_file.resolve() if isinstance(env_file, Path) else Path(env_file).resolve()
            
            return f'''
# Add tools to path for env parser
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from env_parser import parse_env_file


# Environment configuration file
ENV_FILE = r'{abs_env_file}'


@pytest.fixture
def testbed():
    """
    TestBed fixture with device connections
    Loads environment from {abs_env_file.name}
    
    Note: Set use_mock=True for prototype testing with mock devices.
          Set use_mock=False (or remove parameter) for real device testing.
          Can also set environment variable: USE_MOCK_DEVICES=true
    """
    # Load environment configuration from file
    env_config = parse_env_file(ENV_FILE)
    
    # For prototype: use mock devices
    # For production: use_mock=False or remove parameter to use real devices
    testbed = TestBed(env_config, use_mock=True)
    return testbed
'''
        else:
            # Fallback to minimal hardcoded config
            return '''

@pytest.fixture
def testbed():
    """
    TestBed fixture with device connections
    Uses minimal default configuration
    
    Note: Set use_mock=True for prototype testing with mock devices.
          Set use_mock=False (or remove parameter) for real device testing.
          Can also set environment variable: USE_MOCK_DEVICES=true
          
    Warning: No environment file specified! Using minimal defaults.
             For real testing, specify -e/--env parameter with env config file.
    """
    # Create minimal env config for devices
    env_config = {
        'FGT_A': {'hostname': 'FGT_A', 'type': 'fortigate'},
        'FGT_B': {'hostname': 'FGT_B', 'type': 'fortigate'},
        'FGT_C': {'hostname': 'FGT_C', 'type': 'fortigate'},
        'PC_01': {'hostname': 'PC_01', 'type': 'linux'},
        'PC_02': {'hostname': 'PC_02', 'type': 'linux'},
        'PC_05': {'hostname': 'PC_05', 'type': 'linux'},
    }
    
    # For prototype: use mock devices
    # For production: use_mock=False or remove parameter to use real devices
    testbed = TestBed(env_config, use_mock=True)
    return testbed
'''
    
    def _generate_pytest_hooks(self) -> str:
        """Generate pytest hooks for test execution control"""
        return '''
import logging
from datetime import datetime
import json


# ===== Pytest Hooks =====

def pytest_addoption(parser):
    """Add custom command line options for group file support"""
    parser.addoption(
        "--grp-file",
        action="store",
        default=None,
        help="Group file name to enforce test execution order"
    )


def pytest_collection_modifyitems(config, items):
    """
    Reorder tests based on group file order and filter out tests not in group
    Reads .pytest-order.txt to determine test execution sequence
    """
    # Check if order file exists
    order_file = Path(__file__).parent / '.pytest-order.txt'
    
    if not order_file.exists():
        # No order file, use default pytest collection order
        return
    
    # Read test order from file
    # Format: order:pytest_filename
    # Example: 0:test__205812.py
    test_order = {}
    grp_file_name = None
    
    try:
        with open(order_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    # Try to extract grp file name from comment
                    if 'from:' in line:
                        parts = line.split('from:')
                        if len(parts) > 1:
                            grp_file_name = parts[1].strip()
                    continue
                
                # Parse order:filename
                if ':' in line:
                    order, filename = line.split(':', 1)
                    test_order[filename.strip()] = int(order.strip())
    
    except Exception as e:
        print(f"Warning: Failed to read test order file: {e}")
        return
    
    # If order file is empty, return
    if not test_order:
        return
    
    # Reorder items based on order file and filter out tests not in group
    def get_order(item):
        """Get order for a test item"""
        # Extract filename from item nodeid
        # Example: testcases/test__205812.py::test__205812 -> test__205812.py
        nodeid_file = item.nodeid.split('::')[0]
        # Get just the filename without directory path
        filename = Path(nodeid_file).name
        
        # Return order if found, otherwise -1 to mark for deselection
        return test_order.get(filename, -1)
    
    # Deselect tests not in the group file
    items_to_remove = []
    for item in items:
        if get_order(item) == -1:
            items_to_remove.append(item)
    
    for item in items_to_remove:
        items.remove(item)
    
    # Sort remaining items by order
    items[:] = sorted(items, key=get_order)
    
    # Print reordering info if verbose
    if config.option.verbose > 0 and grp_file_name:
        print(f"\\n📋 Test execution order from: {grp_file_name}")
        print(f"   Reordered {len(items)} tests from group file")
        print(f"   Deselected {len(items_to_remove)} tests not in group\\n")


# ===== Test Execution Tracking =====

# Global list to track test execution order and outcomes
_test_execution_order = []
_test_execution_counter = 0
_test_outcomes = {}  # Dictionary to store test outcomes


def pytest_runtest_makereport(item, call):
    """
    Hook to track test execution order and outcomes
    """
    global _test_execution_counter, _test_outcomes
    
    if call.when == "call":
        # Increment counter when test is about to run
        _test_execution_counter += 1
        item.execution_sequence = _test_execution_counter
        item.user_properties.append(("execution_order", f"#{_test_execution_counter}"))
    
    # Capture outcome from any phase (setup, call, or teardown)
    test_file = Path(item.nodeid.split('::')[0]).name.replace('.py', '')
    
    if call.excinfo is not None:
        # If there's an exception in any phase, mark as failed
        _test_outcomes[test_file] = {
            'outcome': 'FAILED',
            'nodeid': item.nodeid
        }
    elif call.when == "call" and call.excinfo is None:
        # Only mark as passed after successful call phase
        # Don't overwrite a failure from setup
        if test_file not in _test_outcomes or _test_outcomes[test_file]['outcome'] != 'FAILED':
            _test_outcomes[test_file] = {
                'outcome': 'PASSED',
                'nodeid': item.nodeid
            }


def pytest_sessionfinish(session, exitstatus):
    """
    Generate execution order summary after all tests complete
    Also save test results to JSON for report generation
    """
    
    # Create reports directory if it doesn't exist
    reports_dir = Path(__file__).parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    # Save test results to JSON
    results_file = reports_dir / 'test_results.json'
    try:
        with open(results_file, 'w') as f:
            json.dump(_test_outcomes, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save test results: {e}")
    
    # Print execution order summary
    print("\\n" + "="*70)
    print("TEST EXECUTION ORDER SUMMARY")
    print("="*70)
    
    # Check if order file exists to show what was enforced
    order_file = Path(__file__).parent / '.pytest-order.txt'
    if order_file.exists():
        try:
            with open(order_file, 'r') as f:
                # Read first few lines to show order was enforced
                lines = f.readlines()[:3]
                print("\\n✓ Test execution order from .pytest-order.txt was enforced:")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) == 2:
                            print(f"  {parts[0]:>3}. {parts[1]}")
                print(f"  ... and {len([l for l in lines if ':' in l and not l.startswith('#')])-3} more tests\\n")
        except:
            pass
    
    print("📊 HTML Report: reports/test_report.html")
    print("   Note: HTML report displays by outcome (passed/failed)")
    print("   Execution order is enforced in console output above\\n")
    print("="*70)

'''
    
    def _generate_logger_fixture(self) -> str:
        """Generate logger fixture for test cases"""
        return '''
@pytest.fixture
def logger(request):
    """
    Logger fixture for test cases
    Provides a logger instance with test-specific context
    
    Usage in tests:
        def test_example(testbed, logger):
            logger.info("Starting test execution")
            logger.debug("Device configuration: %s", config)
            logger.warning("Unexpected behavior detected")
            logger.error("Test failed due to exception")
    """
    # Get test name from request
    test_name = request.node.name
    test_file = request.node.fspath.basename
    
    # Create logger with test-specific name
    log = logging.getLogger(f"{test_file}::{test_name}")
    
    # Add test metadata to logger
    log.test_name = test_name
    log.test_file = test_file
    log.start_time = datetime.now()
    
    # Log test start
    log.info("="*60)
    log.info("Test started: %s", test_name)
    log.info("="*60)
    
    yield log
    
    # Log test end
    duration = (datetime.now() - log.start_time).total_seconds()
    log.info("="*60)
    log.info("Test completed: %s (%.2fs)", test_name, duration)
    log.info("="*60)

'''
    
    def _generate_fixtures_placeholder(self) -> str:
        """Generate placeholder comment for auto-generated fixtures"""
        return '''
# ===== Auto-generated fixtures from include files =====
'''

    def generate_pytest_ini(self) -> str:
        """
        Generate pytest.ini content for the output folder.

        Features:
        - HTML report with full tracebacks (--tb=long) so failed test body is shown
        - XML report (JUnit) for CI integration
        - Log file at DEBUG level under reports/
        - Live CLI logging at INFO level
        - Filters out collection/deprecation warnings
        """
        return '''\
[pytest]
# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = testcases

# Default options
junit_family = legacy
addopts =
    --verbose
    --tb=long
    --strict-markers
    --html=reports/test_report.html
    --self-contained-html
    --junitxml=reports/test_report.xml

# Live console logging
log_cli = True
log_cli_level = INFO
log_cli_format = %(asctime)s [%(levelname)-8s] %(name)s: %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# Persistent log file (DEBUG level — captures everything)
log_file = reports/test_execution.log
log_file_level = DEBUG
log_file_format = %(asctime)s.%(msecs)03d [%(levelname)-8s] [%(name)s] %(message)s (%(filename)s:%(lineno)s)
log_file_date_format = %Y-%m-%d %H:%M:%S

# Filter noisy warnings
filterwarnings =
    ignore::DeprecationWarning
    ignore::pytest.PytestCollectionWarning

# Markers
markers =
    slow: marks tests as slow
    regression: regression tests
    smoke: smoke tests
    integration: integration tests
    qaid(id): QAID identifier

minversion = 6.0
'''

    def generate_makefile(self) -> str:
        """
        Generate Makefile for the output folder.

        Provides simple `make test`, `make report`, `make clean` targets
        that wrap the full pytest command with HTML + XML + log file output.
        """
        return '''\
.PHONY: test test-verbose test-debug test-failed test-x clean clean-all report help

SHELL := /bin/bash

# Directories
TESTCASES_DIR := testcases
REPORTS_DIR   := reports
VENV_DIR      := ../../venv

# Auto-detect venv
ifeq ($(shell test -d $(VENV_DIR) && echo yes),yes)
    PYTHON := $(VENV_DIR)/bin/python
    PYTEST := $(VENV_DIR)/bin/pytest
else
    PYTHON := python3
    PYTEST := python3 -m pytest
endif

QAID   ?=
MARKER ?=
K      ?=

.DEFAULT_GOAL := help

# ── Targets ──────────────────────────────────────────────────────────────────

help: ## Show available targets
\t@grep -E \'^[a-zA-Z_-]+:.*?##\' $(MAKEFILE_LIST) | \\
\t  awk \'BEGIN {FS=":.*?##"}; {printf "  \\033[32m%-18s\\033[0m %s\\n", $$1, $$2}\'

test: _prep ## Run all tests (HTML + XML + log)
\t@echo "▶ Running tests…"
ifdef QAID
\t-$(PYTEST) $(TESTCASES_DIR)/test__$(QAID).py
else ifdef MARKER
\t-$(PYTEST) -m $(MARKER) $(TESTCASES_DIR)/
else ifdef K
\t-$(PYTEST) -k "$(K)" $(TESTCASES_DIR)/
else
\t-$(PYTEST) $(TESTCASES_DIR)/
endif
\t@echo ""
\t@echo "✅ Done — reports:"
\t@echo "   HTML : $(REPORTS_DIR)/test_report.html"
\t@echo "   XML  : $(REPORTS_DIR)/test_report.xml"
\t@echo "   LOG  : $(REPORTS_DIR)/test_execution.log"

test-verbose: _prep ## Run with extra verbosity (-vv -s)
\t-$(PYTEST) -vv -s $(TESTCASES_DIR)/

test-debug: _prep ## Run with DEBUG log level
\t-$(PYTEST) -vv -s --log-cli-level=DEBUG $(TESTCASES_DIR)/

test-failed: _prep ## Re-run previously failed tests
\t-$(PYTEST) --lf $(TESTCASES_DIR)/

test-x: _prep ## Stop on first failure
\t-$(PYTEST) -x $(TESTCASES_DIR)/

report: ## Open HTML report in browser
\t@if [ -f $(REPORTS_DIR)/test_report.html ]; then \\
\t  xdg-open $(REPORTS_DIR)/test_report.html 2>/dev/null || \\
\t  open    $(REPORTS_DIR)/test_report.html 2>/dev/null || \\
\t  echo "Report: $(REPORTS_DIR)/test_report.html"; \\
\telse \\
\t  echo "No report yet — run: make test"; \\
\tfi

clean: ## Remove reports and pytest cache
\t@rm -rf $(REPORTS_DIR) .pytest_cache
\t@find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
\t@echo "✓ Cleaned"

clean-all: clean ## Remove reports + all generated test files
\t@rm -f .conversion_registry.json conftest.py pytest.ini .pytest-order.txt
\t@rm -rf $(TESTCASES_DIR)/test_*.py $(TESTCASES_DIR)/helpers
\t@echo "✓ Full clean done"

list: ## List all test files
\t@find $(TESTCASES_DIR) -name "test_*.py" | sort | sed "s|$(TESTCASES_DIR)/||"

info: ## Show environment info
\t@echo "Python : $(shell $(PYTHON) --version)"
\t@echo "Pytest : $(shell $(PYTEST) --version)"
\t@echo "Tests  : $(shell find $(TESTCASES_DIR) -name \'test_*.py\' | wc -l) files"

_prep:
\t@mkdir -p $(REPORTS_DIR)
'''
