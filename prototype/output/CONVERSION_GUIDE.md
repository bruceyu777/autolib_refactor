# DSL to Pytest Conversion Guide

This guide explains how to convert DSL test files (from group files) into pytest format and run them using the provided Makefile.

## Table of Contents
- [Quick Start](#quick-start)
- [Converting DSL Tests](#converting-dsl-tests)
- [Running Tests](#running-tests)
- [Clean Conversions](#clean-conversions)
- [Understanding Generated Files](#understanding-generated-files)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Convert and Run Tests

```bash
# 1. Convert DSL tests from a group file
make convert-grp GRP=grp.ips.crit

# 2. Run the converted tests
make test-grp GRP=grp.ips.crit
```

### Clean Conversion (Fresh Start)

```bash
# Remove cached conversion files and start fresh
make clean-conversion
make convert-grp GRP=grp.ips.crit
```

---

## Converting DSL Tests

### Basic Conversion

Convert tests from a group file:

```bash
make convert-grp GRP=<group-file-name>
```

**Example:**
```bash
make convert-grp GRP=grp.ips.crit
```

This will:
- Read the DSL group file from `/home/fosqa/autolibv3/autolib_v3/testcase/ips/<group-file>`
- Convert DSL tests to pytest format
- Generate test files in `testcases/` directory
- Create helper modules in `testcases/helpers/` directory
- Update conversion registry (`.conversion_registry.json`)
- Generate test execution order (`.pytest-order.txt`)
- Update `conftest.py` with pytest fixtures

### Clean Conversion (Recommended for Fresh Start)

If you encounter issues or want to ensure a clean conversion:

```bash
# Option 1: Clean then convert (two commands)
make clean-conversion
make convert-grp GRP=grp.ips.crit

# Option 2: Clean and convert in one command
make clean-conversion convert-grp GRP=grp.ips.crit
```

**When to use clean conversion:**
- First time converting a new group file
- After modifying include files (helper dependencies)
- When helper functions need regeneration
- Troubleshooting conversion issues
- Switching between different group files

### Conversion Process Details

The transpiler performs these steps:

1. **Parse DSL Files**: Reads test cases and include files
2. **Generate Helpers**: Converts DSL includes to Python helper functions
3. **Create Test Files**: Generates pytest test functions
4. **Track Dependencies**: Updates registry with helper usage
5. **Modularize Helpers**: Each helper in separate module (`testcases/helpers/helper_*.py`)
6. **Generate Fixtures**: Creates conftest.py with testbed fixtures
7. **Set Test Order**: Creates .pytest-order.txt for execution sequence

---

## Running Tests

### Run All Tests from Group File

```bash
make test-grp GRP=grp.ips.crit
```

This enforces the test execution order from the group file using `.pytest-order.txt`.

### Run Specific Test by QAID

```bash
make test QAID=205812
```

This runs the test file `testcases/test__205812.py`.

### Run All Tests (No Specific Order)

```bash
make test
```

### Run Tests with Verbose Output

```bash
make test-verbose
```

Equivalent to: `pytest -vv -s testcases/`

### Run Tests with Debug Logging

```bash
make test-debug
```

Equivalent to: `pytest -vv -s --log-cli-level=DEBUG testcases/`

### Run Tests with Marker

```bash
make test MARKER=smoke
```

### Run Tests Matching Pattern

```bash
make test TEST_FILTER='-k 205'
```

This runs all tests with "205" in their name.

### Stop on First Failure

```bash
make test-x
```

### Re-run Failed Tests

```bash
make test-failed
```

### Show Test Execution Order

```bash
make show-grp-order
```

Displays the order of tests as defined in `.pytest-order.txt`.

---

## Clean Conversions

### Clean Conversion Cache

Remove cached conversion files for a fresh start:

```bash
make clean-conversion
```

**This removes:**
- `.conversion_registry.json` - tracks converted includes
- `conftest.py` - pytest fixtures file
- `testcases/helpers/` - all helper modules
- `.pytest-order.txt` - test execution order

**Note:** Test files (`testcases/test_*.py`) are preserved.

### Complete Clean (Including Tests)

Remove all generated files including tests:

```bash
make clean-all
```

**This removes:**
- All files from `clean-conversion`
- All test files in `testcases/test_*.py`
- All Python cache files (`__pycache__`, `*.pyc`)

### Clean Test Reports Only

```bash
make clean-reports
```

Removes:
- `reports/` directory
- `.pytest_cache/` directory

---

## Understanding Generated Files

### Directory Structure

After conversion, your workspace looks like this:

```
prototype/output/
├── .conversion_registry.json    # Tracks converted includes
├── .pytest-order.txt             # Test execution order
├── conftest.py                   # Pytest fixtures
├── pytest.ini                    # Pytest configuration
├── Makefile                      # Build and test commands
├── testcases/                    # Generated test files
│   ├── helpers/                  # Helper modules (one per include)
│   │   ├── __init__.py
│   │   ├── helper_purge.py
│   │   ├── helper_enable.py
│   │   ├── helper_govdom1.py
│   │   └── ...
│   ├── test__205812.py
│   ├── test__205813.py
│   └── ...
└── reports/                      # Test execution reports
    ├── test_report.html
    ├── test_report.xml
    └── test_execution.log
```

### Key Files

#### `.conversion_registry.json`

Tracks which DSL includes have been converted to Python helpers. Contains:
- **converted**: List of converted include files
- **used_by**: Mapping of helpers to tests that use them
- **timestamp**: Last conversion time

**Example:**
```json
{
  "converted": [
    "testcase/trunk/ips/topology1/purge.txt",
    "testcase/trunk/ips/topology1/enable.txt"
  ],
  "used_by": {
    "helper_purge": ["test__205812", "test__205813"],
    "helper_enable": ["test__205812"]
  },
  "timestamp": "2026-02-25T18:15:30"
}
```

#### `conftest.py`

Pytest fixture file that provides the `testbed` fixture to all tests. This is auto-generated and minimal (just the fixture header).

#### `testcases/helpers/`

Each DSL include file is converted to a separate Python helper module:

```python
# testcases/helpers/helper_purge.py
def helper_purge(testbed):
    """Purge settings on FortiGate"""
    with testbed.device('FGT_A') as device:
        # ... helper logic
```

Tests import specific helpers:
```python
from helpers.helper_purge import helper_purge
```

#### `.pytest-order.txt`

Defines test execution order from the group file:

```
1:test__205812
2:test__205813
3:test__205814
```

---

## Troubleshooting

### Import Errors

**Problem:** `ImportError: cannot import name 'helper_X' from 'conftest'`

**Solution:** Run clean conversion
```bash
make clean-conversion
make convert-grp GRP=grp.ips.crit
```

### Conversion Registry Issues

**Problem:** Helpers not regenerating or using old code

**Solution:** Clean the conversion cache
```bash
make clean-conversion
make convert-grp GRP=grp.ips.crit
```

### Test Order Not Enforced

**Problem:** Tests run in wrong order

**Solution:** Ensure `.pytest-order.txt` exists
```bash
make show-grp-order  # Check if file exists
make convert-grp GRP=grp.ips.crit  # Regenerate if missing
```

### Syntax Errors in Generated Tests

**Problem:** Python syntax errors in test files (e.g., hyphens in names)

**Solution:** The transpiler auto-sanitizes identifiers. If you still see errors:
1. Check if test manually edited (shouldn't be)
2. Re-run clean conversion
3. Report issue to transpiler maintainer

### Helper Function Missing Parameters

**Problem:** Helper expects `hardware_type` but doesn't receive it

**Solution:** Helper generation now handles dynamic vs static variables automatically. Run clean conversion to regenerate:
```bash
make clean-conversion
make convert-grp GRP=grp.ips.crit
```

---

## Advanced Usage

### List Available Tests

```bash
make list-tests
```

### Show Test Collection

```bash
make test-collect
```

Shows which tests pytest would run without executing them.

### Run with Coverage

```bash
make coverage
```

Generates HTML coverage report in `reports/coverage/`.

### View HTML Report

```bash
make report
```

Opens the HTML test report in your browser.

### Environment Information

```bash
make info
```

Shows Python version, pytest version, and test count.

---

## Best Practices

1. **Always use clean conversion for new group files**
   ```bash
   make clean-conversion convert-grp GRP=grp.new.file
   ```

2. **Check test order before running**
   ```bash
   make show-grp-order
   ```

3. **Use verbose mode for debugging**
   ```bash
   make test-debug QAID=205812
   ```

4. **Review reports after test runs**
   ```bash
   make report
   ```

5. **Don't manually edit generated files**
   - Test files in `testcases/`
   - Helper files in `testcases/helpers/`
   - `.conversion_registry.json`
   - `conftest.py`

6. **Version control considerations**
   - Commit: Makefile, pytest.ini, CONVERSION_GUIDE.md
   - Gitignore: `.conversion_registry.json`, `conftest.py`, `testcases/`, `reports/`, `.pytest_cache/`

---

## Quick Reference

| Task | Command |
|------|---------|
| Convert group file | `make convert-grp GRP=grp.ips.crit` |
| Clean conversion cache | `make clean-conversion` |
| Run all tests from group | `make test-grp GRP=grp.ips.crit` |
| Run specific test | `make test QAID=205812` |
| Run with verbose output | `make test-verbose` |
| Run with debug logging | `make test-debug` |
| Show test order | `make show-grp-order` |
| Re-run failed tests | `make test-failed` |
| Clean all files | `make clean-all` |
| View test report | `make report` |
| List all tests | `make list-tests` |
| Show help | `make help` |

---

## Support

For issues or questions:
- Check this guide's [Troubleshooting](#troubleshooting) section
- Review [Understanding Generated Files](#understanding-generated-files)
- Examine transpiler logs during conversion
- Run with debug logging: `make test-debug`

---

**Last Updated:** February 25, 2026
