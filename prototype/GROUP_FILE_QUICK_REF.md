# DSL Group File Support - Quick Reference

## What Was Implemented

✅ **Group File Parser** (`tools/grp_parser.py`)
- Parses DSL group files (grp.*) to extract test sequences
- Handles comments, empty lines, and conditional blocks
- Generates pytest filenames from test IDs
- Creates .pytest-order.txt for test execution ordering

✅ **Transpiler Enhancement** (`run_transpiler.py`)
- Added `-g/--grp-file` option for batch conversion
- Automatically converts all tests from group file
- Preserves test execution order
- Shows conversion progress and statistics

✅ **Pytest Test Ordering** (`conftest.py`)
- Added `pytest_collection_modifyitems` hook
- Automatically reorders tests based on .pytest-order.txt
- Prints ordering information in verbose mode
- Seamless integration with existing fixtures

✅ **Makefile Targets**
- `make convert-grp GRP=<file>` - Convert tests from group file
- `make test-grp GRP=<file>` - Run tests in group file order
- `make show-grp-order` - Display current test execution order

✅ **Documentation**
- Complete guide: GROUP_FILE_GUIDE.md
- Examples and troubleshooting
- Integration with existing features

## Quick Start Example

### 1. Create or Use Existing Group File

```bash
# Example: grp.demo.txt in testcase/ips/
205812    topology1/205812.txt    "IPS custom signature create"
205924    topology1/205924.txt    "IPS anomaly detection"
205946    topology1/205946.txt    "IPS rate-based detection"
848296    topology1/848296.txt    "IPS protocol violation"
```

### 2. Convert All Tests from Group File

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Method 1: Using run_transpiler.py
python run_transpiler.py -g ../testcase/ips/grp.demo.txt

# Method 2: Using Makefile (from output dir)
cd output
make convert-grp GRP=grp.demo.txt
```

**Output:**
```
📋 Processing Group File: grp.demo.txt
   📊 Found 4 test(s) in group file

[Conversion progress for each test...]

📊 Group File Conversion Summary:
   ✅ Success: 4
   ❌ Failed:  0
   ⚠️  Skipped: 0

Saved test order to: .pytest-order.txt
```

### 3. View Test Execution Order

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

make show-grp-order
```

**Output:**
```
Test Execution Order:
    0. test__205812.py
    1. test__205924.py
    2. test__205946.py
    3. test__848296.py
```

### 4. Run Tests in Order

```bash
# From output directory
make test-grp GRP=grp.demo.txt
```

**Output:**
```
Running tests from group file: grp.demo.txt
Test execution order enforced by .pytest-order.txt

📋 Test execution order from: grp.demo.txt
   Reordered 4 tests

collected 4 items

testcases/test__205812.py::test__205812 PASSED
testcases/test__205924.py::test__205924 PASSED
testcases/test__205946.py::test__205946 PASSED
testcases/test__848296.py::test__848296 PASSED

====== 4 passed in 0.69s ======

✓ Group file tests complete!
Reports available at:
  HTML: reports/test_report.html
  XML:  reports/test_report.xml
  Log:  reports/test_execution.log
```

### 5. View Reports

```bash
make report  # Opens HTML report in browser
```

## File Naming Convention

| DSL Test ID         | Script Path                  | Pytest Filename           |
|---------------------|------------------------------|---------------------------|
| 205812              | topology1/205812.txt         | test__205812.py          |
| topology1-nat.txt   | topology1/topology1-nat.txt  | test__topology1_nat.py   |
| updateSSH-nat.txt   | topology1/updateSSH-nat.txt  | test__updateSSH_nat.py   |

**Rules:**
- Remove `.txt` extension
- Replace `-` and `.` with `_`
- Add `test__` prefix
- Add `.py` extension

## Test Execution Order

### How It Works

1. **Conversion** creates `.pytest-order.txt`:
   ```
   # Test execution order from: grp.demo.txt
   0:test__205812.py
   1:test__205924.py
   2:test__205946.py
   3:test__848296.py
   ```

2. **pytest Hook** reads `.pytest-order.txt` and reorders collected tests

3. **Tests execute** in the exact order defined in the group file

## Complete Workflow

```bash
# 1. Navigate to prototype directory
cd /home/fosqa/autolibv3/autolib_v3/prototype

# 2. Convert tests from group file
python run_transpiler.py -g ../testcase/ips/grp.ips_nat.full

# 3. Navigate to output directory
cd output

# 4. View test execution order
make show-grp-order

# 5. Run tests in group file order
make test-grp GRP=grp.ips_nat.full

# 6. View HTML report
make report
```

## Available Group Files

```bash
# List all group files in testcase/ips/
ls /home/fosqa/autolibv3/autolib_v3/testcase/ips/grp.*

# Common group files:
# - grp.ips_nat.full         - Full IPS NAT test suite (313 tests)
# - grp.ips_nat.crit         - Critical IPS tests
# - grp.ips_inlineproxy.full - IPS inline proxy tests
# - grp.demo.txt             - Demo with 4 tests (for testing)
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make convert-grp GRP=<file>` | Convert all tests from group file |
| `make test-grp GRP=<file>` | Run tests in group file order |
| `make show-grp-order` | Display current test execution order |
| `make test QAID=205812` | Run specific test by ID |
| `make test-all` | Run all tests |
| `make report` | Open HTML test report |
| `make help` | Show all available commands |

## Key Features

✨ **Automatic Test Ordering** - Tests run in exact sequence from grp file  
✨ **Batch Conversion** - Convert hundreds of tests with one command  
✨ **Progress Tracking** - See conversion status for each test  
✨ **Error Handling** - Skip missing files, report failures  
✨ **Seamless Integration** - Works with existing fixtures, logging, reports  
✨ **Backward Compatible** - Existing test execution still works  

## File Structure

```
prototype/
├── run_transpiler.py              # Main transpiler with -g option
├── tools/
│   └── grp_parser.py              # Group file parser
├── GROUP_FILE_GUIDE.md            # Comprehensive guide
├── GROUP_FILE_QUICK_REF.md        # This file
└── output/
    ├── conftest.py                # With test ordering hook
    ├── pytest.ini                 # Pytest configuration
    ├── Makefile                   # With grp targets
    ├── .pytest-order.txt          # Test execution order (generated)
    ├── testcases/                 # Generated pytest files
    └── reports/                   # Test reports

testcase/ips/
├── grp.ips_nat.full               # Main IPS test group
├── grp.demo.txt                   # Demo group file
├── env.fortistack.ips.conf        # Environment config
└── topology1/                     # DSL test scripts
    ├── 205812.txt
    ├── 205924.txt
    └── ...
```

## Troubleshooting

### Tests not found during conversion

**Problem:** `⚠️ Skipped: DSL script not found`

**Solution:** Check script paths in grp file are relative to grp file location:
```plaintext
# Correct (relative to grp file location)
205812    topology1/205812.txt

# Incorrect (overly qualified path)
205812    testcase/trunk/ips/topology1/205812.txt
```

### Tests running in wrong order

**Problem:** Tests don't follow grp file sequence

**Solution:** Regenerate `.pytest-order.txt`:
```bash
python run_transpiler.py -g path/to/grp_file.full
```

### Order file not found

**Problem:** `Error: .pytest-order.txt not found`

**Solution:** Convert tests from group file first:
```bash
make convert-grp GRP=grp.demo.txt
```

## Next Steps

1. **Convert Production Group Files**
   ```bash
   python run_transpiler.py -g testcase/ips/grp.ips_nat.full
   ```

2. **Run Full Test Suite**
   ```bash
   cd output
   make test-grp GRP=grp.ips_nat.full
   ```

3. **Integrate with CI/CD**
   - Add grp file conversion to CI pipeline
   - Run tests with `make test-grp GRP=<file>`
   - Collect HTML/XML reports for build artifacts

4. **Review Reports**
   - HTML report shows all test results
   - XML report for CI/CD integration
   - Execution log has detailed DEBUG traces

## Summary

The DSL Group File Support provides a complete solution for:

- ✅ **Batch converting** multiple DSL tests to pytest
- ✅ **Maintaining test execution order** from legacy DSL system
- ✅ **Automating test workflows** with Makefile targets
- ✅ **Seamless integration** with existing test infrastructure

See **GROUP_FILE_GUIDE.md** for comprehensive documentation and advanced features.
