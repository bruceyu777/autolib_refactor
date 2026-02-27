# Environment Configuration Integration Guide

## Overview

The DSL to pytest transpiler now integrates with AutoLib v3's environment configuration files to provide real device and network settings to generated tests. This ensures that transpiled pytest tests use the same configuration as the original DSL tests.

## Architecture

### Environment File Format

AutoLib v3 uses INI-style configuration files with sections and key-value pairs:

```ini
[GLOBAL]
Platform: FGVM
VERSION: trunk
Build: build3615
DUT: FGT_A

[PC_01]
CONNECTION: ssh -t fosqa@10.6.30.11 sudo -s
USERNAME: fosqa
PASSWORD: Qa123456!
IP_ETH1: 10.1.100.11
SCRIPT: /home/tester/ips/attack_scripts

[FGT_A]
Platform: FGVM
CONNECTION: telnet 0.0.0.0 11023
USERNAME: admin
PASSWORD: admin
Model: FGVM
CUSTOMSIG1: custom1on1801F
CUSTOMSIG2: custom2on1801F
IP_PORT1: 172.16.200.1 255.255.255.0
```

### Key Features

1. **Section-based organization**: Each device has its own section
2. **Colon separator**: Uses `KEY: VALUE` format (not `KEY=VALUE`)
3. **Variable references**: DSL tests use `DEVICE:VARIABLE` format
4. **Global settings**: Common settings in `[GLOBAL]` section

## Components

### 1. Environment Parser (`env_parser.py`)

Located: `/home/fosqa/tools/env_parser.py` and `/home/fosqa/autolibv3/autolib_v3/prototype/tools/env_parser.py`

**Purpose**: Parse AutoLib v3 environment configuration files

**Key Classes**:
- `EnvParser`: Main parser class
- `parse_env_file()`: Convenience function

**Example Usage**:

```python
from env_parser import parse_env_file

# Parse environment file
env_config = parse_env_file('env.fortistack.ips.conf')

# Access device configuration
print(env_config['FGT_A']['password'])  # 'admin'
print(env_config['PC_05']['IP_ETH1'])   # '172.16.200.55'

# Use with TestBed
testbed = TestBed(env_config, use_mock=True)
```

**Methods**:

```python
# Create parser instance
parser = EnvParser()

# Parse file
config = parser.parse_file('env.fortistack.ips.conf')

# Get specific device config
fgt_config = parser.get_device_config('FGT_A')

# Get global config
global_config = parser.get_global_config()

# Resolve variable (DEVICE:VAR format)
ip = parser.resolve_variable('PC_05:IP_ETH1')

# Get TestBed-compatible config
testbed_config = parser.to_testbed_config()
```

### 2. Transpiler CLI Updates (`run_transpiler.py`)

**New Parameter**: `-e/--env`

```bash
# Specify environment file explicitly
python run_transpiler.py -f test.txt -e env.fortistack.ips.conf

# Auto-detection (searches for env*.conf near test files)
python run_transpiler.py -f test.txt

# Batch conversion with env file
python run_transpiler.py -d testcase/ips/topology1/ -e env.fortistack.ips.conf
```

**Auto-Detection Logic**:
1. If `-e/--env` not specified, searches for `env*.conf` files
2. First checks in same directory as test file
3. Then checks parent directory
4. Uses first match found
5. Falls back to minimal default config if none found

### 3. Generated Conftest Integration

**With Environment File**:

```python
"""Auto-generated conftest.py"""

import pytest
from pathlib import Path
import sys

# Add fluent API to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'fluent_api'))
from fluent import TestBed

# Add tools to path for env parser
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from env_parser import parse_env_file

# Environment configuration file
ENV_FILE = r'/path/to/env.fortistack.ips.conf'

@pytest.fixture
def testbed():
    """
    TestBed fixture with device connections
    Loads environment from env.fortistack.ips.conf
    """
    # Load environment configuration from file
    env_config = parse_env_file(ENV_FILE)
    
    # For prototype: use mock devices
    # For production: use_mock=False for real devices
    testbed = TestBed(env_config, use_mock=True)
    return testbed
```

**Without Environment File** (fallback):

```python
@pytest.fixture
def testbed():
    """
    Warning: No environment file specified!
    Using minimal defaults.
    """
    # Minimal env config
    env_config = {
        'FGT_A': {'hostname': 'FGT_A', 'type': 'fortigate'},
        'PC_01': {'hostname': 'PC_01', 'type': 'linux'},
        # ...
    }
    
    testbed = TestBed(env_config, use_mock=True)
    return testbed
```

## Usage Examples

### Example 1: Single File with Environment

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

python3 run_transpiler.py \
  -f /home/fosqa/autolibv3/autolib_v3/testcase/ips/topology1/205812.txt \
  -e /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf
```

**Output**:
```
📄 Converting: 205812.txt
   Source: .../testcase/ips/topology1/205812.txt
   Env:    .../testcase/ips/env.fortistack.ips.conf

[2/5] Initializing conftest.py...
  ✓ Created: .../output/conftest.py
    Using env config: .../env.fortistack.ips.conf
```

### Example 2: Auto-Detection

```bash
python3 run_transpiler.py -f testcase/ips/topology1/205812.txt
```

**Output**:
```
ℹ️  Auto-detected environment file: env.fortistack.ips.conf
```

### Example 3: Batch Conversion

```bash
python3 run_transpiler.py \
  -d testcase/ips/topology1/ \
  -e testcase/ips/env.fortistack.ips.conf \
  -o output/batch_tests/
```

### Example 4: Running Tests

```bash
cd output
pytest test__205812.py -v

# Output:
# test__205812.py::test__205812 PASSED [100%]
```

## Environment Configuration Structure

### Parsed Config Format

The `parse_env_file()` function returns a dictionary suitable for `TestBed`:

```python
{
    'GLOBAL': {
        'Platform': 'FGVM',
        'VERSION': 'trunk',
        'Build': 'build3615',
        'DUT': 'FGT_A'
    },
    'FGT_A': {
        'type': 'fortigate',
        'hostname': 'FGT_A',
        'connection': 'telnet 0.0.0.0 11023',
        'username': 'admin',
        'password': 'admin',
        'model': 'FGVM',
        'CUSTOMSIG1': 'custom1on1801F',
        'CUSTOMSIG2': 'custom2on1801F',
        # ... all other variables from [FGT_A] section
    },
    'PC_05': {
        'type': 'pc',
        'hostname': 'PC_05',
        'connection': 'ssh -t fosqa@10.6.30.55 sudo -s',
        'username': 'fosqa',
        'password': 'Qa123456!',
        'IP_ETH1': '172.16.200.55',
        'SCRIPT': '/home/tester/attack_scripts',
        # ... all other variables from [PC_05] section
    }
}
```

### Device Type Detection

The parser automatically determines device types:
- Sections starting with `PC_` → `type: 'pc'`
- Other sections (except GLOBAL, ORIOLE) → `type: 'fortigate'`

### Variable Resolution

DSL tests use `DEVICE:VARIABLE` format for variables:

**In DSL**:
```
backup PC_05:IP_ETH1 /var/log/messages
backup FTP PC_05 /var/log/messages ftp://PC_05:PC_05:PASSWORD@FGT_A:CUSTOMSIG1
```

**Resolved Values** (from env file):
- `PC_05:IP_ETH1` → `172.16.200.55`
- `PC_05:PASSWORD` → `Qa123456!`
- `FGT_A:CUSTOMSIG1` → `custom1on1801F`

**In pytest** (via env_config):
```python
testbed = TestBed(env_config, use_mock=True)
pc05_config = testbed.env_config['PC_05']
print(pc05_config['IP_ETH1'])  # '172.16.200.55'
```

## Testing the Integration

### Test Parser Directly

```bash
python3 /home/fosqa/tools/env_parser.py \
  /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf
```

**Expected Output**:
```
Parsing environment file: env.fortistack.ips.conf
==============================================================================

Found 15 sections:
  - ORIOLE
  - GLOBAL
  - PC_01
  - PC_05
  - FGT_A
  - FGT_B
  - FGT_C
  ...

Variable Resolution Examples:
  PC_05:IP_ETH1 = 172.16.200.55
  PC_05:PASSWORD = Qa123456!
  FGT_A:CUSTOMSIG1 = custom1on1801F
  FGT_A:CUSTOMSIG2 = custom2on1801F
```

### Test Transpiler with Env File

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Clean output directory
rm -rf output/

# Run transpiler
python3 run_transpiler.py \
  -e /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf

# Verify conftest.py has env integration
grep -A5 "parse_env_file" output/conftest.py

# Run generated tests
cd output
pytest test__205812.py -v
```

## Configuration Scenarios

### Scenario 1: Mock Device Testing

**Use Case**: Prototype development without real hardware

```python
# In conftest.py (auto-generated)
testbed = TestBed(env_config, use_mock=True)
```

**Result**: Uses `MockFortiGate` and `MockPC` devices

### Scenario 2: Real Device Testing

**Use Case**: Integration testing with actual devices

```python
# In conftest.py (manual edit or future enhancement)
testbed = TestBed(env_config, use_mock=False)
```

**Result**: Uses `FortiGate` and `Pc` from `lib/core/device`

### Scenario 3: Environment Variable Control

```bash
# Set environment variable
export USE_MOCK_DEVICES=false

# Run tests
pytest test__205812.py -v
```

**Result**: TestBed reads env var and uses real devices

## Troubleshooting

### Issue: "No module named 'env_parser'"

**Cause**: env_parser.py not in correct location

**Solution**:
```bash
# Copy to prototype tools directory
cp /home/fosqa/tools/env_parser.py \
   /home/fosqa/autolibv3/autolib_v3/prototype/tools/
```

### Issue: "Environment file not found"

**Cause**: Invalid path or file doesn't exist

**Solution**:
```bash
# Use absolute path
python3 run_transpiler.py -e /absolute/path/to/env.fortistack.ips.conf

# Or use relative path from current directory
python3 run_transpiler.py -e ../testcase/ips/env.fortistack.ips.conf
```

### Issue: Missing Fixtures in conftest.py

**Cause**: Registry out of sync with actual files

**Solution**:
```bash
# Delete registry and regenerate
rm output/.conversion_registry.json output/conftest.py
python3 run_transpiler.py -e env.fortistack.ips.conf
```

### Issue: Variable Not Resolved

**Cause**: Variable doesn't exist in env file

**Solution**:
```python
# Debug: Print all available variables
from env_parser import EnvParser
parser = EnvParser()
parser.parse_file('env.fortistack.ips.conf')
print(parser.get_device_config('PC_05'))
```

## File Locations

```
/home/fosqa/
├── tools/
│   └── env_parser.py                    # Original parser
│
└── autolibv3/autolib_v3/
    ├── testcase/ips/
    │   └── env.fortistack.ips.conf      # Environment config
    │
    └── prototype/
        ├── run_transpiler.py             # CLI with -e option
        ├── tools/
        │   ├── env_parser.py             # Parser (copy)
        │   └── dsl_transpiler.py         # Updated transpiler
        │
        ├── fluent_api/
        │   └── fluent.py                 # TestBed integration
        │
        └── output/
            ├── conftest.py               # Generated with env
            └── test__205812.py           # Generated test
```

## Benefits

### ✅ Real Configuration
- Uses actual device IPs, credentials, paths from env files
- No hardcoded values in generated tests
- Same config as original DSL tests

### ✅ Consistency
- Single source of truth for test environment
- Changes to env file automatically propagate
- Easier to maintain multi-environment setups

### ✅ Flexibility
- Can use different env files for different test environments
- Auto-detection reduces CLI complexity
- Fallback to minimal config for quick prototyping

### ✅ Variable Resolution
- DSL variables like `PC_05:IP_ETH1` resolved from env
- Access to all env configuration at runtime
- TestBed provides env_config to all tests

## Future Enhancements

### Dynamic Variable Substitution
Auto-replace `DEVICE:VAR` in generated test code with actual values

### Multi-Environment Support
```bash
python3 run_transpiler.py -f test.txt --env-profile production
```

### Environment Validation
Check that all devices referenced in test exist in env file

### Encrypted Credentials
Support for encrypted passwords in env files

## Summary

The environment configuration integration provides:
1. **Parser** (`env_parser.py`) - Reads AutoLib v3 env files
2. **CLI** (`-e/--env`) - Specifies or auto-detects env file
3. **Conftest** (generated) - Loads env config into TestBed
4. **Runtime** (TestBed) - Provides config to all tests

This ensures transpiled pytest tests use the same configuration as original DSL tests, maintaining consistency and reducing maintenance overhead.

## Quick Reference

```bash
# With explicit env file
python3 run_transpiler.py -f test.txt -e env.fortistack.ips.conf

# Auto-detect env file
python3 run_transpiler.py -f test.txt

# Batch with env file
python3 run_transpiler.py -d testcase/ips/ -e env.fortistack.ips.conf

# Test parser
python3 tools/env_parser.py env.fortistack.ips.conf

# Run generated tests
cd output && pytest test__205812.py -v
```
