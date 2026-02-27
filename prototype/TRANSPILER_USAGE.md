# DSL to pytest Transpiler - Usage Guide

## Overview

The `run_transpiler.py` script converts AutoLib DSL test scripts to pytest format. It supports both single-file and batch conversion modes.

## Command-Line Interface

### Basic Usage

```bash
# Default: Convert test 205812.txt
python3 run_transpiler.py

# Convert single file
python3 run_transpiler.py -f path/to/test.txt

# Convert all tests in a folder
python3 run_transpiler.py -d path/to/folder/

# Custom output directory
python3 run_transpiler.py -f test.txt -o /tmp/output/
```

### Options

| Option | Long Form | Description |
|--------|-----------|-------------|
| `-f` | `--file` | Single DSL test file to convert (.txt) |
| `-d` | `--dir` | Directory containing DSL test files for batch conversion |
| `-o` | `--output` | Output directory for generated pytest files (default: ./output) |
| `-e` | `--env` | Environment configuration file (e.g., env.fortistack.ips.conf). Auto-detected if not specified. |
| `-h` | `--help` | Show help message and exit |

## Examples

### Example 1: Convert Single Test

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Convert specific test file
python3 run_transpiler.py -f /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt

# Output:
# - output/test_205812.py
# - output/conftest.py
# - output/.conversion_registry.json
```

### Example 2: Batch Convert Folder

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Convert all tests in topology1 folder
python3 run_transpiler.py -d /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/

# Output:
# - output/test_205812.py
# - output/test_1008830.py
# - output/test_1008831.py
# - ... (all .txt files converted)
# - output/conftest.py
# - output/.conversion_registry.json
```

### Example 3: Custom Output Directory

```bash
# Convert to custom location
python3 run_transpiler.py \
    -f testcase/ips/205812.txt \
    -o /tmp/my_pytest_tests/
```

### Example 4: Specify Environment Configuration

```bash
# Use specific environment configuration file
python3 run_transpiler.py \
    -f testcase/ips/topology1/205812.txt \
    -e /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf

# Auto-detect environment file (searches for env*.conf)
python3 run_transpiler.py -f testcase/ips/topology1/205812.txt

# Batch conversion with environment file
python3 run_transpiler.py \
    -d testcase/ips/topology1/ \
    -e testcase/ips/env.fortistack.ips.conf \
    -o output/batch_tests/
```

**Environment File Integration**:
- Environment files contain device configurations, IPs, credentials, paths
- Format: INI-style with sections like `[GLOBAL]`, `[PC_01]`, `[FGT_A]`
- Auto-detected if not specified (searches for `env*.conf` near test files)
- See `ENV_INTEGRATION_GUIDE.md` for detailed documentation

## Output Structure

After conversion, the output directory contains:

```
output/
├── conftest.py                    # Pytest fixtures from includes
├── test_205812.py                 # Generated test file
├── test_1008830.py                # Another test (if batch mode)
└── .conversion_registry.json      # Conversion tracking registry
```

## Generated Test Files

Each DSL test file (`QAID.txt`) is converted to `test_QAID.py`:

- **Test function**: `def test_QAID(testbed, fixtures...)`
- **Docstring**: Original test title
- **QAID tracking**: Assertions include `qaid="QAID"` parameter
- **Fluent API**: Uses method chaining for device operations
- **Fixtures**: Include files converted to pytest fixtures in `conftest.py`

## Conversion Registry

The `.conversion_registry.json` file tracks:

- Which include files have been converted
- Mapping of include paths → fixture names
- Number of tests using each fixture
- Prevents duplicate conversions

## Mock Device Updates

**Important**: Some tests may require custom mock device behavior.

### When to Update `mock_device.py`

Update the mock device when tests:
- Use specialized FortiGate commands
- Expect specific output formats
- Require stateful simulations (config persistence, reboot, etc.)
- Need file operations (backup, comparison)
- Use complex multi-line config blocks

### Example: Adding Command Handler

```python
# In fluent_api/mock_device.py

def execute(self, command: str) -> str:
    # ... existing code ...
    
    # Add custom handler
    elif command.startswith("diagnose test"):
        return "Test output here"
    
    # Add pattern matching
    elif "sys ha" in command:
        return self._handle_ha_config(command)
```

### Common Patterns Requiring Updates

1. **IPS Signatures** - Multi-line config parsing ✅ (Already implemented)
2. **VDOM Operations** - Context switching
3. **HA Configuration** - Cluster state simulation
4. **VPN Tunnels** - Connection state tracking
5. **Routing Tables** - Dynamic route updates
6. **Policy Rules** - Rule matching and evaluation
7. **Log Queries** - Log generation and filtering

## Workflow

### Single Test Development

```bash
# 1. Convert test
python3 run_transpiler.py -f testcase/ips/205812.txt

# 2. Run pytest to identify failures
cd output
pytest test_205812.py -v

# 3. Update mock_device.py if needed
vim ../fluent_api/mock_device.py

# 4. Re-run test
pytest test_205812.py -v

# 5. Iterate until passing
```

### Batch Conversion Workflow

```bash
# 1. Convert all tests
python3 run_transpiler.py -d testcase/ips/topology1/

# 2. Run all tests to see which pass/fail
cd output
pytest -v

# 3. Identify common patterns in failures
pytest --tb=short | grep "AssertionError"

# 4. Update mock_device.py for common patterns
vim ../fluent_api/mock_device.py

# 5. Re-run failed tests
pytest --lf -v

# 6. Iterate until all pass
```

## Limitations

- **Include Files**: Must exist in testcase directory structure
- **Device Types**: Currently supports FGT_* and PC_* devices
- **Commands**: Mock device has basic FortiGate command set
- **Expect Patterns**: Simple substring matching (no regex)
- **File Operations**: Basic file backup/comparison simulation

## Extending the Transpiler

### Adding New Command Patterns

1. Update `dsl_transpiler.py` → `_group_commands()` method
2. Add pattern detection logic
3. Update `convert_section()` to handle new pattern

### Adding New Fixture Types

1. Update `include_converter.py` → `convert_include_to_fixture()`
2. Add fixture template in `conftest_template`
3. Register in conversion registry

### Adding Device Types

1. Update `fluent.py` → Add device class (e.g., `FluentSwitch`)
2. Update `mock_device.py` → Add device simulation
3. Update DSL parser to recognize device format

## Troubleshooting

### Test Fails: "Pattern should be in output"

**Cause**: Mock device doesn't return expected output

**Solution**:
1. Check what command is being executed
2. Add handler in `mock_device.py` for that command
3. Return expected FortiGate-style output

### Import Errors

**Cause**: Missing `sys.path` for fluent_api

**Solution**:
```python
# In conftest.py, add:
sys.path.insert(0, str(Path(__file__).parent.parent / 'fluent_api'))
```

### Fixture Not Found

**Cause**: Include file wasn't converted

**Solution**:
1. Check if include file exists
2. Verify path in DSL test file
3. Re-run transpiler to regenerate conftest.py

### Empty Test Output

**Cause**: Expect chained to command without output

**Solution**: Transpiler should auto-chain expects to previous command with output. If not, file a bug.

## Best Practices

1. **Start Small**: Convert 1-2 tests first, validate approach
2. **Iterate on Mock**: Add handlers incrementally as needed
3. **Share Fixtures**: Common setup → shared fixtures in conftest.py
4. **Batch Convert**: Once mock is stable, convert entire test suites
5. **Version Control**: Track changes to mock_device.py carefully
6. **Document Patterns**: Note which commands need special handling

## Future Enhancements

- [ ] Parallel test execution
- [ ] Real device integration (SSH/Telnet)
- [ ] Regex pattern matching in expects
- [ ] Test coverage reporting
- [ ] Auto-generate mock handlers from real device output
- [ ] Support for nested includes
- [ ] Variable substitution from env_config
- [ ] Timeout configuration per test
- [ ] Retry logic for flaky patterns
- [ ] HTML test reports with QAID tracking

## Support

For issues or questions:
1. Check `TRANSPILER_EXAMPLE.md` for conversion examples
2. Review `DSL_TO_PYTEST_MIGRATION.md` for architecture
3. See `PROTOTYPE_SUMMARY.md` for implementation details
4. File issues with test name, error message, and DSL snippet
