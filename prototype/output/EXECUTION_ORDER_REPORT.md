# Understanding Test Execution Order Reports

## Problem Statement

The pytest-html plugin groups tests by outcome (passed/failed) rather than displaying them in execution order. If you're following test dependencies or debugging sequencing issues, the HTML report doesn't show the order tests actually ran.

## Solution: Dual Reports

We now generate **two separate reports** for complete visibility:

### 1. ✅ `test_report.html` (Pytest HTML Report)
**Purpose:** Traditional test results grouped by pass/fail status

**Contains:**
- Pass/Fail statistics
- Test environment info
- Results grouped by outcome
- Detailed error messages for failures
- Execution time per test

**Limitations:**
- Tests grouped by outcome, NOT execution order
- Can't see test dependencies
- Doesn't show sequencing relationships

**When to Use:**
- Quick overview of pass/fail status
- Debugging individual test failures
- Sharing results in CI/CD pipelines

---

### 2. 📋 `execution_order.html` (New Execution Order Report)
**Purpose:** Show tests in exact execution order as defined by `.pytest-order.txt`

**Contains:**
- Test execution number (1, 2, 3, ...)
- Test name from group file
- Test status (enforced from grp file order)
- Summary statistics
- Group file metadata

**Benefits:**
- Tests shown in EXACT execution order
- See test sequencing relationships
- Understand test dependencies
- Verify group file order was respected

**When to Use:**
- Understand test dependencies
- Debug sequencing issues
- Verify .pytest-order.txt was applied
- Analyze test execution flow

---

## Side-by-Side Comparison

| Aspect | test_report.html | execution_order.html |
|--------|------------------|----------------------|
| **Grouping** | By outcome (Pass/Fail) | By execution order |
| **Order** | Outcome order | 1, 2, 3, ... (from grp file) |
| **Purpose** | Overall test health | Test sequencing/dependencies |
| **Size** | Large (~600KB) | Small (~8-10KB) |
| **Detail** | Very detailed | Summary information |
| **File** | `reports/test_report.html` | `reports/execution_order.html` |

---

## How Execution Order is Applied

### 1. Source: `.pytest-order.txt`
```
# Test execution order from: grp.ips.crit
0:test__topology1_nat.py
1:test__topology1_FGT_C.py
2:test__updateSSH_nat.py
3:test__205814.py
...
```

### 2. Applied by: `pytest_collection_modifyitems` hook in conftest.py
- Reads `.pytest-order.txt` during test collection
- Reorders pytest items before execution
- Shows message: "📋 Test execution order from: grp.ips.crit"
- Reordered 67 tests

### 3. Display: Both reports show the order
- **Console**: "(67 tests reordered)" shown during collection
- **execution_order.html**: Visual table showing execution sequence
- **test_report.html**: Grouped by outcome (not sequential)

---

## Where to Find Test Execution Order

### ✅ Recommended Places (in order of usefulness):

1. **execution_order.html** (NEW)
   - Visual table showing test numbers and sequence
   - Open in browser for interactive view
   - Located: `reports/execution_order.html`

2. **Console Output During Test Run**
   ```
   📋 Test execution order from: grp.ips.crit
      Reordered 67 tests
   ```
   - Shows that order was enforced
   - Lists first test in sequence

3. **.pytest-order.txt** (Raw source file)
   ```
   0:test__topology1_nat.py
   1:test__topology1_FGT_C.py
   2:test__updateSSH_nat.py
   ...
   ```
   - Location: `.pytest-order.txt`
   - Shows complete ordered list

4. **test_execution.log** (Timestamped log)
   - Shows timestamps for each test
   - Can calculate execution time per test
   - Location: `reports/test_execution.log`

❌ **NOT recommended:**
- Don't use `test_report.html` for understanding test order (it groups by outcome)

---

## Using the Execution Order Report

### Open in Browser
```bash
# From output directory
open reports/execution_order.html

# Or use make command
make report  # Opens test_report.html
# For execution order: manually open reports/execution_order.html
```

### Key Information in Report

| Column | Meaning | Example |
|--------|---------|---------|
| **Order** | Test execution sequence | #1, #2, #3... |
| **Test Name** | DSL test file name | test__topology1_nat |
| **Status** | Expected pass/fail | PASSED |

### Summary Cards
- **Total Tests**: Count of all tests from group file
- **Passed**: Tests that passed
- **Failed**: Tests that failed

---

## Verifying Order Was Applied

### Method 1: Check Console Output
```bash
make test-grp GRP=grp.ips.crit

# Look for this message in output:
# 📋 Test execution order from: grp.ips.crit
#    Reordered 67 tests
```

### Method 2: Compare Files
```bash
# Check .pytest-order.txt exists
ls -l .pytest-order.txt

# First entry should be test 0 (first test to run)
head -5 .pytest-order.txt
# Output:
# # Test execution order from: grp.ips.crit
# 0:test__topology1_nat.py
# 1:test__topology1_FGT_C.py
```

### Method 3: Check HTML Reports
- `execution_order.html`: Shows tests in numbered order
- `test_report.html`: Shows same tests grouped by pass/fail (not sequential)

---

## Troubleshooting

### execution_order.html not Generated
**Problem:** Report file doesn't exist after test run

**Solution:**
```bash
# Manually generate it
python generate_execution_html.py

# Or run tests which auto-generates it
make test-grp GRP=grp.ips.crit
```

### Order Not Enforced
**Problem:** Tests run in different order than expected

**Check:**
1. Is `.pytest-order.txt` present?
   ```bash
   ls -l .pytest-order.txt
   ```
2. Does it have entries?
   ```bash
   wc -l .pytest-order.txt  # Should be ~80+ lines
   ```
3. Is conftest.py present with hooks?
   ```bash
   grep "pytest_collection_modifyitems" conftest.py
   ```

**Fix:** Regenerate convergence
```bash
make clean-conversion
make convert-grp GRP=grp.ips.crit
make test-grp GRP=grp.ips.crit
```

### Execution Order Shows in Console But Not HTML
This is expected! The HTML report is separate from console output.

**Console output** shows: "Reordered 67 tests"

**HTML reports** show:
- `test_report.html`: Grouped by outcome
- `execution_order.html`: Shows numbered sequence

---

## Generate Execution Order Report Manually

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Generate execution order HTML from existing .pytest-order.txt
python generate_execution_html.py

# Output
# ✓ Execution order HTML report generated: reports/execution_order.html
```

---

## Summary

| What | Where | How to View |
|------|-------|------------|
| Ordered test list | `execution_order.html` | Open in browser |
| Test health | `test_report.html` | Open in browser |
| Raw order | `.pytest-order.txt` | Text editor / cat |
| Timestamps | `test_execution.log` | Text editor / tail |
| Console verification | STDOUT | Make command output |

**Key Takeaway:** Use **execution_order.html** to see test execution order. Use **test_report.html** for pass/fail status.

---

**Last Updated:** February 25, 2026
