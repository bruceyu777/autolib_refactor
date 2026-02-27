# DSL to Pytest Test Suite

Auto-generated pytest tests from DSL test scripts.

## 📖 Documentation

**[Complete Conversion Guide](CONVERSION_GUIDE.md)** - Full guide on converting DSL tests and running pytest

## Quick Start

### Convert DSL Tests to Pytest
```bash
# Clean conversion (recommended for fresh start)
make clean-conversion
make convert-grp GRP=grp.ips.crit

# Or convert directly
make convert-grp GRP=grp.ips.crit
```

### Run Tests
```bash
# Run all tests from group file (maintains order)
make test-grp GRP=grp.ips.crit

# Run specific test by QAID
make test QAID=205812

# Run with verbose output
make test-verbose
```

## Test Infrastructure

### 📁 Directory Structure
```
output/
├── CONVERSION_GUIDE.md   # Detailed conversion and testing guide
├── README.md            # This file
├── Makefile             # Build and test commands
├── pytest.ini           # Pytest settings and logging
├── conftest.py          # Auto-generated pytest fixtures
├── .conversion_registry.json  # Conversion cache (auto-generated)
├── .pytest-order.txt    # Test execution order (auto-generated)
├── testcases/          # Generated test files
│   ├── helpers/        # Helper modules (one per DSL include)
│   └── test_*.py       # Test files
└── reports/            # Test reports (after running tests)
    ├── test_report.html

### 🔄 Conversion Workflow

#### Clean Conversion (Recommended)

For a fresh start or when switching group files:

```bash
make clean-conversion  # Remove conversion cache
make convert-grp GRP=grp.ips.crit  # Convert tests
```

#### What Gets Cleaned

- `clean-conversion` - Removes conversion cache files:
  - `.conversion_registry.json`
  - `conftest.py`
  - `testcases/helpers/`
  - `.pytest-order.txt`
  - **Test files preserved**

- `clean-all` - Removes everything:
  - All conversion cache files
  - All test files (`testcases/test_*.py`)
  - All reports and Python cache

- `clean` - Removes only Python cache files
- `clean-reports` - Removes only test reports

#### When to Use Clean Conversion

✅ Use `make clean-conversion` when:
- Converting a new group file for the first time
- Helper functions need regeneration
- DSL include files have been modified
- Troubleshooting import errors
- Switching between different group files

### 📊 Test Reports

After running tests, reports are generated in the `reports/` directory:

- **HTML Report**: `reports/test_report.html` - Visual test results with pass/fail status
- **XML Report**: `reports/test_report.xml` - JUnit XML format for CI/CD integration
- **Execution Log**: `reports/test_execution.log` - Detailed execution logs

Open HTML report:
```bash
make report
```

### 📝 Logging in Tests

Tests can use the `logger` fixture for detailed logging:

```python
def test_example(testbed, logger):
    logger.info("Starting test execution")
    logger.debug("Detailed debug information")
    logger.warning("Warning message")
    logger.error("Error message")
```

Log levels:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for unexpected behavior
- **ERROR**: Error messages for failures

### 🛠️ Available Make Targets

#### Conversion Commands
```bash
make convert-grp GRP=<grp-file>  # Convert DSL tests to pytest
make clean-conversion             # Clean conversion cache for fresh start
make clean-all                    # Remove all generated files
make show-grp-order              # Show test execution order
```

#### Test Execution
```bash
make help              # Show all available targets
make test-grp GRP=<grp-file>  # Run tests in group file order
make test              # Run all tests
make test QAID=<id>    # Run specific test by QAID
make test-all          # Run with full output
make test-verbose      # Run with verbose output
make test-debug        # Run with debug logging
make test-smoke        # Run smoke tests only
make test-regression   # Run regression tests only
make test-failed       # Re-run failed tests
make test-x            # Stop on first failure
make test-collect      # Show what tests would run
```

#### Reports and Cleanup
```bash
make report            # Open HTML report
make clean             # Clean Python cache only
make clean-reports     # Clean reports only
make coverage          # Run with coverage report
make list-tests        # List all available tests
make info              # Show environment info
```

### 🔧 Configuration

#### pytest.ini Settings

- **Test Discovery**: Automatically finds `test_*.py` files in `testcases/`
- **Logging**: Console and file logging with timestamps
- **HTML Reports**: Self-contained HTML reports with test results
- **XML Reports**: JUnit XML for CI/CD integration
- **Warnings**: Filters deprecation warnings

#### Environment

The test suite uses the environment configuration from:
```
/home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf
```

Devices configured:
- FGT_A, FGT_B, FGT_C (FortiGate devices)
- PC_01-PC_07, PC_37, PC_40 (Test PCs)
- GLOBAL (Global configuration)

### 📌 Custom Markers

Add markers to categorize tests:

```python
@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.qaid("205812")
def test_example(testbed, logger):
    ...
```

Run tests with specific markers:
```bash
pytest -m smoke        # Run smoke tests
pytest -m regression   # Run regression tests
pytest -m "not slow"   # Skip slow tests
```

### 🎯 Example Test Execution

```bash
# Run all tests
$ make test
Running tests...
======================== test session starts =========================
collected 4 items

test__205812.py::test__205812 PASSED                           [ 25%]
test__205924.py::test__205924 PASSED                           [ 50%]
test__205946.py::test__205946 PASSED                           [ 75%]
test__848296.py::test__848296 PASSED                           [100%]

=================== 4 passed in 0.78s ====================
✓ Tests complete!
Reports available at:
  HTML: reports/test_report.html
  XML:  reports/test_report.xml
  Log:  reports/test_execution.log
```

### 🔍 Debugging Failed Tests

1. **View detailed logs**:
   ```bash
   make test-debug QAID=205812
   ```

2. **Check execution log**:
   ```bash
   cat reports/test_execution.log
   ```

3. **Re-run failed tests only**:
   ```bash
   make test-failed
   ```

4. **Stop on first failure**:
   ```bash
   make test-x
   ```

### 📦 Dependencies

Required Python packages:
- pytest >= 6.0
- pytest-html (for HTML reports)
- pytest-cov (for coverage reports)
- pytest-mock (for mocking)

Install all dependencies:
```bash
make install-deps
```

### 🔄 CI/CD Integration

The XML report can be used in CI/CD pipelines:

```yaml
# Example Jenkins/GitLab CI
test:
  script:
    - cd prototype/output
    - make test
  artifacts:
    reports:
      junit: reports/test_report.xml
    paths:
      - reports/
```

### 📈 Coverage Reports

Generate code coverage:
```bash
make coverage
```

View coverage report:
```
reports/coverage/index.html
```
