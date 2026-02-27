# Environment Configuration Integration

**Status**: ✅ Implemented and Tested  
**Date**: 2026-02-24  
**Version**: 1.0

## Overview

The DSL to pytest transpiler now fully integrates with AutoLib v3 environment configuration files. This enables generated pytest tests to use the same device configurations, credentials, and runtime variables as the original DSL tests.

## Components

### 1. Environment File Parser (`tools/env_parser.py`)

**Purpose**: Parse INI-style environment configuration files used by AutoLib v3.

**Key Features**:
- Parses sections like `[GLOBAL]`, `[PC_01]`, `[FGT_A]`, etc.
- Handles `KEY: VALUE` format (colon separator)
- Converts to TestBed-compatible dictionary structure
- Provides variable resolution helper methods

**Example Usage**:
```python
from env_parser import parse_env_file

# Parse environment file
env_config = parse_env_file('env.fortistack.ips.conf')

# Access device configuration
fgt_config = env_config['FGT_A']
print(fgt_config['password'])  # 'admin'
print(fgt_config['CUSTOMSIG1'])  # 'custom1on1801F'
```

### 2. Environment File Format

**Sample Structure**:
```ini
[GLOBAL]
Platform: FGVM
VERSION: trunk
Build: build3615

[PC_05]
CONNECTION: ssh -t fosqa@10.6.30.55 sudo -s
USERNAME: fosqa
PASSWORD: Qa123456!
IP_ETH1: 172.16.200.55
SCRIPT: /home/tester/attack_scripts

[FGT_A]
Platform: FGVM
CONNECTION: telnet 0.0.0.0 11023
Model: FGVM
USERNAME: admin
PASSWORD: admin
CUSTOMSIG1: custom1on1801F
CUSTOMSIG2: custom2on1801F
```

**Key Normalization**:
- Common keys (`USERNAME`, `PASSWORD`, `MODEL`) → normalized to lowercase
- Custom keys (`CUSTOMSIG1`, `IP_ETH1`) → kept as-is
- Supports both cases via case-insensitive lookup

### 3. CLI Updates (`run_transpiler.py`)

**New Parameter**:
```bash
-e, --env <env_file>     # Specify environment configuration file
```

**Usage Examples**:
```bash
# Explicit env file
python run_transpiler.py -f test.txt -e env.fortistack.ips.conf

# Auto-detect env file (searches testcase directory)
python run_transpiler.py -f testcase/ips/205812.txt

# Batch conversion with env file
python run_transpiler.py -d testcase/ips/topology1/ -e env.fortistack.ips.conf
```

**Auto-Detection Logic**:
1. Checks testcase directory for `env*.conf` files
2. Checks parent directory if not found in testcase dir
3. Falls back to minimal default config if no env file found

### 4. Generated conftest.py

**With Environment File**:
```python
import pytest
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'fluent_api'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))

from fluent import TestBed
from env_parser import parse_env_file

# Environment configuration file
ENV_FILE = r'/path/to/env.fortistack.ips.conf'

@pytest.fixture
def testbed():
    """TestBed fixture with device connections from env file"""
    # Load environment configuration from file
    env_config = parse_env_file(ENV_FILE)
    
    # Create testbed (use_mock=True for prototype, False for real devices)
    testbed = TestBed(env_config, use_mock=True)
    return testbed
```

**Without Environment File** (Fallback):
```python
@pytest.fixture
def testbed():
    """TestBed with minimal default configuration"""
    env_config = {
        'FGT_A': {'hostname': 'FGT_A', 'type': 'fortigate'},
        'PC_01': {'hostname': 'PC_01', 'type': 'linux'},
        # ... minimal config
    }
    testbed = TestBed(env_config, use_mock=True)
    return testbed
```

### 5. Runtime Variable Resolution

**Automatic Resolution with Decorator Pattern**:

All methods in `FluentDevice` that accept string parameters use the `@resolve_command_vars` decorator, which automatically resolves `DEVICE:VARIABLE` patterns before method execution.

**Decorated Methods**:
- `execute(command)` - Command execution
- `config(config_block)` - Configuration blocks
- `raw_execute(command)` - Raw device commands

**Example**:

DSL Test Command:
```
FGT_A
exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD
```

Generated pytest:
```python
with testbed.device('FGT_A') as fgt_a:
    fgt_a.execute("exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")
```

Runtime Resolution (automatic via decorator):
```
Original:  exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD
Resolved:  exe backup ipsuserdefsig ftp custom1on1801F 172.16.200.55 root Qa123456!
```

**Variable Pattern**: `DEVICE_NAME:VARIABLE_NAME`
- `DEVICE_NAME`: Uppercase letters/numbers/underscores (e.g., `FGT_A`, `PC_05`)
- `VARIABLE_NAME`: Alphanumeric with underscores (e.g., `CUSTOMSIG1`, `IP_ETH1`, `PASSWORD`)

**Resolution Logic**:
1. Try exact case match first
2. Try lowercase (for normalized keys: `password`, `username`, `model`)
3. Try uppercase (for env vars: `IP_ETH1`, `CUSTOMSIG1`)
4. Keep original if not found (with warning)

**Supported Variables**:

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `PC_05:IP_ETH1` | `172.16.200.55` | IP address of PC_05 eth1 interface |
| `PC_05:PASSWORD` | `Qa123456!` | Password for PC_05 |
| `PC_05:SCRIPT` | `/home/tester/attack_scripts` | Script directory path |
| `FGT_A:CUSTOMSIG1` | `custom1on1801F` | Custom signature filename |
| `FGT_A:CUSTOMSIG2` | `custom2on1801F` | Custom signature filename |
| `FGT_A:Model` | `FGVM` | FortiGate model |
| `FGT_A:PASSWORD` | `admin` | FortiGate admin password |

## Implementation Details

### Decorator Pattern for Automatic Resolution

**Location**: `fluent_api/fluent.py`

**Decorator**:
```python
@resolve_command_vars
def execute(self, command: str):
    """Execute command (variables auto-resolved by decorator)"""
    # command already has variables resolved
    self.logger.info(f"Executing: {command}")
    ...
```

**How it Works**:
1. Decorator intercepts method call before execution
2. Identifies all string parameters (positional and keyword)
3. Calls `testbed.resolve_variables()` on each string
4. Passes resolved strings to the actual method
5. Method executes with all variables already replaced

**Benefits**:
- **Universal**: Works on all string parameters automatically
- **DRY**: No need to manually call resolve in each method
- **Bug-resistant**: Can't forget to add resolution
- **Maintainable**: Single place to update resolution logic

See [DECORATOR_VARIABLE_RESOLUTION.md](DECORATOR_VARIABLE_RESOLUTION.md) for detailed decorator documentation.

### TestBed.resolve_variables()

**Location**: `fluent_api/fluent.py`

**Method Signature**:
```python
def resolve_variables(self, command: str) -> str:
    """Resolve DEVICE:VARIABLE patterns in command string"""
```

**Algorithm**:
1. Use regex to find all `DEVICE:VARIABLE` patterns
2. For each match, lookup device in env_config
3. Search for variable key (case-insensitive)
4. Replace with actual value or keep original

**Regex Pattern**:
```python
pattern = r'([A-Z][A-Z0-9_]*):([A-Za-z][A-Za-z0-9_]*)'
```

### FluentDevice Methods with Auto-Resolution

**Location**: `fluent_api/fluent.py`

**All methods with string parameters use the decorator**:
```python
class FluentDevice:
    @resolve_command_vars
    def execute(self, command: str):
        """Execute command (variables auto-resolved)"""
        # command already has variables resolved by decorator
        self.logger.info(f"Executing: {command}")
        # ... execute with resolved variables
    
    @resolve_command_vars
    def config(self, config_block: str):
        """Execute configuration block (variables auto-resolved)"""
        # config_block already has variables resolved by decorator
        self.device.execute(config_block)
        return self
    
    @resolve_command_vars
    def raw_execute(self, command: str) -> str:
        """Execute raw command (variables auto-resolved)"""
        # command already has variables resolved by decorator
        return self.device.execute(command)
```

**Key Point**: Variables are resolved **before** the method body executes, so all logging and execution already use the resolved values.

## Testing

### Unit Test: Variable Resolution

**File**: `prototype/test_variable_resolution.py`

**Coverage**:
- Environment file parsing
- TestBed configuration loading
- Variable resolution with different patterns
- Case-insensitive lookups
- Integration with mock device execution

**Results**:
```
✅ FGT_A:CUSTOMSIG1     → custom1on1801F
✅ FGT_A:CUSTOMSIG2     → custom2on1801F
✅ PC_05:IP_ETH1        → 172.16.200.55
✅ PC_05:PASSWORD       → Qa123456!
✅ FGT_A:Model          → FGVM
✅ PC_05:SCRIPT         → /home/tester/attack_scripts

✅ All variable resolutions PASSED
```

### Integration Test: pytest Execution

**File**: `output/test__205812.py`

**Command**:
```bash
cd prototype/output && pytest test__205812.py -vs
```

**Result**:
```
QAID 205812: PASS
  Step 1: ✓ Pattern 'match small' should be in output
  Step 2: ✓ Pattern '6312' should be in output
  Step 3: ✓ Pattern 'ABCDEFG' should be in output
  ... 7 steps total
  
========================= 1 passed, 1 warning in 0.02s ===================
```

## Benefits

1. **Consistency**: Generated pytest uses same configuration as DSL tests
2. **Flexibility**: Easy to switch environments by changing env file
3. **Maintainability**: Single source of truth for device configurations
4. **Portability**: Tests work across different test environments
5. **Security**: Credentials managed in env files, not hardcoded
6. **Automation**: Auto-detection of env files reduces manual configuration

## Workflow

### Standard Workflow with Environment Files

```bash
# 1. Convert DSL test with environment file
cd prototype/
python run_transpiler.py \
    -f /path/to/testcase/205812.txt \
    -e /path/to/env.fortistack.ips.conf \
    -o output/

# 2. Review generated files
cd output/
ls -lh
# conftest.py      - Loads env file, creates testbed
# test_205812.py   - Tests with variable references

# 3. Run pytest tests (with mock devices)
pytest test_205812.py -vs

# 4. For real device testing
# Edit conftest.py: change use_mock=True to use_mock=False
pytest test_205812.py -vs
```

### Auto-Detection Workflow

```bash
# If env file is in testcase directory, it's auto-detected
python run_transpiler.py -f testcase/ips/205812.txt

# Output shows:
# ℹ️  Auto-detected environment file: env.fortistack.ips.conf
```

## Migration Guide

### From Hardcoded Config to Environment Files

**Before** (Minimal hardcoded config):
```python
env_config = {
    'FGT_A': {'hostname': 'FGT_A', 'type': 'fortigate'},
    'PC_05': {'hostname': 'PC_05', 'type': 'linux'},
}
```

**After** (Environment file loaded):
```python
env_config = parse_env_file(ENV_FILE)
# Full configuration with:
# - Credentials (username, password)
# - Network config (IP addresses, gateways)
# - Paths (script directories, TFTP paths)
# - Custom variables (CUSTOMSIG1, etc.)
```

### Variable References in Tests

**DSL Test**:
```
FGT_A
exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD
```

**Generated pytest** (unchanged):
```python
fgt_a.execute("exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")
```

**Runtime** (automatic resolution):
```python
# Actual command executed:
# "exe backup ipsuserdefsig ftp custom1on1801F 172.16.200.55 root Qa123456!"
```

## Configuration Reference

### Environment File Sections

| Section | Purpose | Example Keys |
|---------|---------|--------------|
| `[GLOBAL]` | Global test settings | `Platform`, `VERSION`, `Build`, `DUT` |
| `[PC_##]` | PC device configuration | `CONNECTION`, `IP_ETH1`, `PASSWORD` |
| `[FGT_#]` | FortiGate configuration | `connection`, `USERNAME`, `PASSWORD`, `Model` |
| `[ORIOLE]` | Credentials (optional) | `USER`, `ENCODE_PASSWORD` |

### Common Variable Types

| Type | Pattern | Example |
|------|---------|---------|
| IP Address | `DEVICE:IP_interface` | `PC_05:IP_ETH1` |
| IPv6 Address | `DEVICE:IP6_interface` | `PC_05:IP6_ETH1` |
| Password | `DEVICE:PASSWORD` | `PC_05:PASSWORD` |
| Path | `DEVICE:SCRIPT` | `PC_05:SCRIPT` |
| Custom | `DEVICE:CUSTOM*` | `FGT_A:CUSTOMSIG1` |
| Model | `DEVICE:Model` | `FGT_A:Model` |

## Troubleshooting

### Variable Not Found

**Symptom**:
```
WARNING: Variable not found: PC_05:UNKNOWN_VAR
```

**Solution**:
1. Check env file has `[PC_05]` section
2. Verify variable name exists in section
3. Check case sensitivity (try uppercase/lowercase)

### Environment File Not Found

**Symptom**:
```
⚠️  Warning: Environment file not found: env.conf
          Will use minimal default configuration
```

**Solution**:
1. Use `-e` parameter with correct path
2. Place env file in testcase directory for auto-detection
3. Check file exists: `ls -l env*.conf`

### Import Error

**Symptom**:
```
ImportError: No module named 'env_parser'
```

**Solution**:
1. Ensure `tools/env_parser.py` exists
2. Check path in conftest.py is correct
3. Verify relative path to tools directory

## Future Enhancements

- [ ] Support for environment variable templates
- [ ] Validation of required variables before test execution
- [ ] Multiple environment file support (overlay configs)
- [ ] Environment-specific test filtering
- [ ] Encrypted credential support
- [ ] Environment file schema validation

## Related Documentation

- [DSL_TO_PYTEST_MIGRATION.md](DSL_TO_PYTEST_MIGRATION.md) - Overall migration strategy
- [TRANSPILER_USAGE.md](TRANSPILER_USAGE.md) - Transpiler CLI reference
- [FLEXIBLE_DEVICE_ARCHITECTURE.md](FLEXIBLE_DEVICE_ARCHITECTURE.md) - Mock vs Real devices
- [DECORATOR_VARIABLE_RESOLUTION.md](DECORATOR_VARIABLE_RESOLUTION.md) - Decorator pattern details

## Summary

Environment configuration integration is **fully implemented and tested**:

✅ **Environment file parser** - Parses INI-style config files  
✅ **CLI integration** - `-e/--env` parameter with auto-detection  
✅ **conftest.py generation** - Loads env file or falls back to defaults  
✅ **Runtime variable resolution** - Automatic `DEVICE:VAR` → value replacement via decorator  
✅ **Decorator pattern** - Universal resolution across all string parameters  
✅ **Case-insensitive lookup** - Handles normalized and custom keys  
✅ **Testing** - Unit tests and integration tests pass  

Generated pytest tests now use the same environment configurations as the original DSL tests, ensuring consistency and enabling real device testing with proper credentials and network settings.

The decorator pattern ensures that **all** methods with string parameters automatically resolve variables, making it impossible to forget variable resolution and ensuring consistent behavior across the entire fluent API.
