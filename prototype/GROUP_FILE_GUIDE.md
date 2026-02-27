# DSL Group File Support Guide

## Overview

DSL Group Files (grp.*) define test execution sequences for batch test runs. This feature allows you to:

- **Define test execution order** - Tests run in the exact sequence specified in the grp file
- **Batch convert tests** - Convert all tests referenced in a grp file automatically
- **Maintain test dependencies** - Ensure setup tests run before functional tests
- **Match legacy DSL behavior** - Preserve the same test sequencing as the original AutoLib DSL system

## What is a Group File?

A group file (grp.*) is a text file that lists DSL test scripts in their intended execution order. Each line specifies:

- **Test ID**: Identifier for the test (numeric ID or descriptive name)
- **Script Path**: Location of the DSL test script
- **Comment**: Optional description of what the test does

### Example Group File Format

```plaintext
######################################################################
#  IPS trunk Scripts Group file
######################################################################

#ID                     Scripts                                          Comment
#- 00_IPS_Setup -
topology1-nat.txt      testcase/trunk/ips/topology1/topology1-nat.txt   "FGT-A initialization"
topology1-FGT_C.txt    testcase/trunk/ips/topology1/topology1-FGT_C.txt "FGT-C initialization"
updateSSH-nat.txt      testcase/trunk/ips/topology1/updateSSH-nat.txt   "Update SSH keys"
205812                 testcase/trunk/ips/topology1/205812.txt          "Custom signature test"

#- 01_IPS_CLI -
205813                 testcase/trunk/ips/topology1/205813.txt          "Signature modify"
205814                 testcase/trunk/ips/topology1/205814.txt          "Signature delete"
```

### Format Rules

1. **Comments**: Lines starting with `#` are ignored
2. **Empty Lines**: Blank lines are skipped
3. **Conditionals**: Lines with `<if>` ... `<fi>` are currently skipped
4. **Test Entries**: Must have at least Test ID and Script Path
5. **Whitespace**: Tabs or multiple spaces can separate columns

## File Naming Convention

When converting DSL tests to pytest, the Test ID is transformed into a pytest filename:

| Test ID            | Pytest Filename              |
|--------------------|------------------------------|
| 205812             | test__205812.py             |
| topology1-nat.txt  | test__topology1_nat.py      |
| topology1-FGT_C.txt| test__topology1_FGT_C.py    |
| updateSSH-nat.txt  | test__updateSSH_nat.py      |

**Transformation Rules**:
- Remove `.txt` extension
- Replace hyphens (`-`) with underscores (`_`)
- Replace dots (`.`) with underscores (`_`)
- Add `test__` prefix and `.py` extension

## Converting Tests from Group File

### Method 1: Using run_transpiler.py

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Convert all tests from a group file
python run_transpiler.py -g /path/to/testcase/ips/grp.ips_nat.full

# Specify custom output directory
python run_transpiler.py -g grp.ips_nat.full -o custom_output/

# Specify environment file
python run_transpiler.py -g grp.ips_nat.full -e env.fortistack.ips.conf
```

**What happens during conversion:**
1. Parses the group file and extracts all test entries
2. Displays summary of tests to be converted
3. Converts each DSL test script to pytest format (in order)
4. Generates `.pytest-order.txt` file with test execution sequence
5. Skips tests where DSL script file is not found
6. Reports success/failure/skip counts

### Method 2: Using Makefile

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Convert all tests from group file
make convert-grp GRP=grp.ips_nat.full
```

## Running Tests in Group File Order

### Method 1: Using Makefile (Recommended)

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Run all tests in the order defined by the group file
make test-grp GRP=grp.ips_nat.full
```

**Prerequisites:**
- Tests must be converted first using `make convert-grp` or `run_transpiler.py -g`
- `.pytest-order.txt` file must exist in the output directory

### Method 2: Using pytest directly

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Tests will automatically run in order if .pytest-order.txt exists
pytest -v testcases/
```

## Test Execution Order

### How Test Ordering Works

1. **Order File**: When you convert a group file, a `.pytest-order.txt` file is generated:
   ```
   # Test execution order from: grp.ips_nat.full
   # Generated automatically - do not edit manually
   
   0:test__735501.py
   1:test__topology1_nat.py
   2:test__topology1_FGT_C.py
   3:test__updateSSH_nat.py
   4:test__205812.py
   5:test__205813.py
   ```

2. **pytest Hook**: The `conftest.py` file contains a `pytest_collection_modifyitems` hook that:
   - Reads the `.pytest-order.txt` file
   - Reorders collected test items to match the specified sequence
   - Prints ordering information in verbose mode

3. **Automatic Reordering**: Whenever pytest runs, if `.pytest-order.txt` exists, tests are automatically reordered

### Viewing Test Order

```bash
# Show current test execution order
make show-grp-order

# Output:
# Test Execution Order:
#   0. test__735501.py
#   1. test__topology1_nat.py
#   2. test__topology1_FGT_C.py
#   ...
```

## Complete Workflow Example

Here's a complete example of converting and running tests from a group file:

```bash
# Step 1: Navigate to prototype directory
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Step 2: Convert all tests from group file
python run_transpiler.py -g ../testcase/ips/grp.ips_nat.full

# Output shows:
# - Summary of tests found in grp file
# - Conversion progress for each test
# - Success/failure/skip counts
# - Location of .pytest-order.txt file

# Step 3: Navigate to output directory
cd output

# Step 4: View the test execution order
make show-grp-order

# Step 5: Run tests in group file order
make test-grp GRP=grp.ips_nat.full

# Step 6: View HTML report
make report
```

## Using with Makefile Targets

The Makefile includes several grp-related targets:

### convert-grp
Convert all DSL tests from a group file to pytest format.

```bash
make convert-grp GRP=grp.ips_nat.full
```

### test-grp
Run all tests in the order defined by the group file.

```bash
make test-grp GRP=grp.ips_nat.full
```

### show-grp-order
Display the current test execution order from `.pytest-order.txt`.

```bash
make show-grp-order
```

## Group File Parser CLI

The grp_parser.py tool can be used standalone to inspect group files:

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype/tools

# Parse and show summary
python grp_parser.py /path/to/grp.ips_nat.full --summary

# Save test order to file
python grp_parser.py /path/to/grp.ips_nat.full --save-order --output-dir /tmp

# Just list pytest names
python grp_parser.py /path/to/grp.ips_nat.full
```

## Advanced Features

### Conditional Test Blocks

Group files may contain conditional blocks for platform-specific tests:

```plaintext
<if FGT_A:IPSRESCPU eq yes>
797076                  testcase/trunk/ips/topology1/797076.txt  "IPS reserve CPU test"
<fi>
```

**Current Status**: Conditional blocks are **skipped** during parsing. Tests inside conditional blocks are not converted or executed.

**Future Enhancement**: Support conditional evaluation based on environment variables or device capabilities.

### Partial Group File Conversion

To convert only specific tests from a group file:

1. Create a custom group file with only the tests you want
2. Run the transpiler with your custom group file

```bash
# Create custom group file
cat > grp.my_tests.txt <<EOF
205812     testcase/trunk/ips/topology1/205812.txt     "Test 1"
205813     testcase/trunk/ips/topology1/205813.txt     "Test 2"
EOF

# Convert only those tests
python run_transpiler.py -g grp.my_tests.txt
```

## Troubleshooting

### "DSL script not found" warnings

**Problem**: Some tests in the group file cannot be found.

**Causes**:
- Script path in grp file is incorrect
- DSL script has been moved or deleted
- Using testcase/trunk/ips prefix but running from different directory

**Solution**:
- Check that DSL script files exist at the specified paths
- Group file script paths should be relative to the grp file location
- Update grp file paths if test files have moved

### Tests running in wrong order

**Problem**: Tests are not running in the order specified in the group file.

**Causes**:
- `.pytest-order.txt` file is missing or outdated
- Running from wrong directory

**Solution**:
```bash
# Regenerate order file by re-converting
python run_transpiler.py -g path/to/grp_file.full

# Verify order file exists
ls -la .pytest-order.txt

# Check order
make show-grp-order
```

### No tests collected

**Problem**: pytest doesn't find any tests to run.

**Causes**:
- Tests haven't been converted yet
- Running from wrong directory

**Solution**:
```bash
# Make sure you're in the output directory
cd /home/fosqa/autolibv3/autolib_v3/prototype/output

# Verify test files exist
ls testcases/test__*.py

# If no files, convert first
cd ..
python run_transpiler.py -g path/to/grp_file.full
```

## Integration with Existing Features

Group file support integrates seamlessly with existing test infrastructure:

- **HTML Reports**: All reports work normally with grp-ordered tests
- **Logging**: Logger fixture available to all tests
- **Markers**: Tests can still use pytest markers (smoke, regression, etc.)
- **Fixtures**: testbed and logger fixtures work as usual
- **Helper Functions**: Include-based helpers work normally

## Best Practices

### 1. Group File Organization

Organize tests in logical groups with clear section headers:

```plaintext
#- 00_Setup -
topology1-nat.txt      ...    "Device initialization"

#- 01_Feature_Config -
205812                 ...    "Configure feature"
205813                 ...    "Modify configuration"

#- 02_Functional_Tests -
205951                 ...    "Test basic functionality"
205952                 ...    "Test advanced features"

#- 99_Cleanup -
teardown.txt           ...    "Cleanup configuration"
```

### 2. Test Dependencies

Place dependent tests in order:
- Setup tests at the beginning
- Configuration tests before functional tests
- Cleanup tests at the end

### 3. Environment Files

Always specify or verify the environment file:

```bash
# Explicit environment file (recommended)
python run_transpiler.py -g grp.ips_nat.full -e env.fortistack.ips.conf

# Auto-detection (grp directory must contain env*.conf)
python run_transpiler.py -g grp.ips_nat.full
```

### 4. Version Control

Include in your repository:
- ✅ Group files (grp.*)
- ✅ DSL test scripts (.txt)
- ✅ Environment files (env*.conf)
- ❌ Generated pytest files (.pytest-order.txt, testcases/)
- ❌ Test reports (reports/)

### 5. Continuous Integration

For CI/CD pipelines:

```bash
#!/bin/bash
# ci-test.sh

# Convert tests from master group file
python run_transpiler.py -g testcase/ips/grp.ips_nat.full -o pytest_output

# Run tests in order
cd pytest_output
pytest -v testcases/

# Generate reports
# (already generated by pytest.ini configuration)
```

## Appendix: File Locations

```
autolibv3/autolib_v3/
├── prototype/
│   ├── run_transpiler.py          # Main transpiler script
│   ├── tools/
│   │   ├── grp_parser.py          # Group file parser
│   │   ├── dsl_transpiler.py      # DSL to pytest converter
│   │   └── ...
│   └── output/                    # Generated pytest files
│       ├── conftest.py            # Fixtures and test ordering hook
│       ├── pytest.ini             # Pytest configuration
│       ├── Makefile               # Test automation
│       ├── .pytest-order.txt      # Test execution order (generated)
│       ├── testcases/             # Generated test files
│       └── reports/               # Test reports
└── testcase/
    └── ips/
        ├── grp.ips_nat.full       # Group file
        ├── grp.ips_nat.crit       # Critical tests group
        ├── env.fortistack.ips.conf # Environment config
        └── topology1/             # DSL test scripts
            ├── 205812.txt
            ├── 205813.txt
            └── ...
```

## Summary

Group file support provides a powerful way to maintain test execution order while batch-converting DSL tests to pytest. Key benefits:

✅ **Preserves test sequence** from legacy DSL system  
✅ **Batch conversion** of multiple tests  
✅ **Automatic ordering** via pytest hooks  
✅ **Clear documentation** of test dependencies  
✅ **Makefile integration** for easy execution  
✅ **Compatible** with all existing test features  

Use group files when you need to maintain specific test execution sequences, especially for integration tests or test suites with setup/teardown dependencies.
