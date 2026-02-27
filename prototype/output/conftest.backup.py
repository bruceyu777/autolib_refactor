"""
Auto-generated conftest.py
Contains fixtures converted from DSL include files
"""

import pytest
import logging
from pathlib import Path
import sys
from datetime import datetime

# Add fluent API to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'fluent_api'))

from fluent import TestBed

# Add tools to path for env parser
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

from env_parser import parse_env_file


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
    Reorder tests based on group file order
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
    
    # Reorder items based on order file
    def get_order(item):
        """Get order for a test item"""
        # Extract filename from item nodeid
        # Example: testcases/test__205812.py::test__205812 -> test__205812.py
        nodeid_file = item.nodeid.split('::')[0]
        # Get just the filename without directory path
        filename = Path(nodeid_file).name
        
        # Return order if found, otherwise use large number to put at end
        return test_order.get(filename, 99999)
    
    # Sort items by order
    items[:] = sorted(items, key=get_order)
    
    # Print reordering info if verbose
    if config.option.verbose > 0 and grp_file_name:
        reordered_count = len([i for i in items if get_order(i) < 99999])
        print(f"\n📋 Test execution order from: {grp_file_name}")
        print(f"   Reordered {reordered_count} tests\n")


# ===== Configuration =====

# Environment configuration file
ENV_FILE = r'/home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf'


# ===== Fixtures =====

@pytest.fixture
def testbed():
    """
    TestBed fixture with device connections
    Loads environment from env.fortistack.ips.conf
    
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
    
    if call.when == "teardown":
        # Capture outcome after test completes
        test_file = Path(item.nodeid.split('::')[0]).name.replace('.py', '')
        _test_outcomes[test_file] = {
            'outcome': call.excinfo is None and 'PASSED' or 'FAILED',
            'nodeid': item.nodeid
        }


def pytest_sessionfinish(session, exitstatus):
    """
    Generate execution order summary after all tests complete
    Also save test results to JSON for report generation
    """
    import json
    
    # Create reports directory if it doesn't exist
    reports_dir = Path(__file__).parent / 'reports'
    reports_dir.mkdir(exist_ok=True)
    
    # Save test results to JSON for our v2 report generator
    results_file = reports_dir / 'test_results.json'
    try:
        with open(results_file, 'w') as f:
            json.dump(_test_outcomes, f, indent=2)
        #print(f"✓ Test results saved to: {results_file} ({len(_test_outcomes)} tests)")
    except Exception as e:
        pass  # Silently ignore - not critical
    
    # Print execution order summary
    print("\n" + "="*70)
    print("TEST EXECUTION ORDER SUMMARY")
    print("="*70)
    
    # Check if order file exists to show what was enforced
    order_file = Path(__file__).parent / '.pytest-order.txt'
    if order_file.exists():
        try:
            with open(order_file, 'r') as f:
                # Read first few lines to show order was enforced
                lines = f.readlines()[:3]
                print("\n✓ Test execution order from .pytest-order.txt was enforced:")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) == 2:
                            print(f"  {parts[0]:>3}. {parts[1]}")
                print(f"  ... and {len([l for l in lines if ':' in l and not l.startswith('#')])-3} more tests\n")
        except:
            pass
    
    print("📊 HTML Report: reports/test_report.html")
    print("   Note: HTML report displays by outcome (passed/failed)")
    print("   Execution order is enforced in console output above\n")
    print("="*70)


# ===== Auto-generated fixtures from include files =====
