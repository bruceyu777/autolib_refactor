# Environment Configuration Integration - Summary

## Quick Overview

The DSL to pytest transpiler now **automatically integrates** with AutoLib v3 environment configuration files, ensuring generated pytest tests use the same device configurations as original DSL tests.

## What Changed

### Before
- **Hardcoded minimal config** in generated `conftest.py`
- Only basic device names (FGT_A, PC_01, etc.)
- No real IPs, passwords, paths, or device-specific settings
- Manual updates needed for each test environment

### After ✅
- **Real configuration from env files** (e.g., `env.fortistack.ips.conf`)
- Full device configs: IPs, credentials, connection strings, paths
- **Auto-detection** of env files (no manual parameter needed)
- Same configuration as DSL tests use

## New Components

### 1. Environment Parser (`env_parser.py`)

```python
from env_parser import parse_env_file

# Parse AutoLib v3 env file
config = parse_env_file('env.fortistack.ips.conf')

# Access device settings
print(config['FGT_A']['password'])     # 'admin'
print(config['PC_05']['IP_ETH1'])      # '172.16.200.55'
print(config['FGT_A']['CUSTOMSIG1'])   # 'custom1on1801F'
```

**Location**: 
- `/home/fosqa/tools/env_parser.py` (main)
- `/home/fosqa/autolibv3/autolib_v3/prototype/tools/env_parser.py` (copy for transpiler)

### 2. CLI Parameter (`-e/--env`)

```bash
# Explicit env file
python3 run_transpiler.py -f test.txt -e env.fortistack.ips.conf

# Auto-detect (searches for env*.conf)
python3 run_transpiler.py -f test.txt
```

### 3. Updated Conftest Generation

**Generated conftest.py now includes**:
```python
from env_parser import parse_env_file

ENV_FILE = r'/path/to/env.fortistack.ips.conf'

@pytest.fixture
def testbed():
    # Load real environment configuration
    env_config = parse_env_file(ENV_FILE)
    testbed = TestBed(env_config, use_mock=True)
    return testbed
```

## Usage

### Basic (Auto-Detection)

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Auto-detects env*.conf in testcase directory
python3 run_transpiler.py -f testcase/ips/topology1/205812.txt
```

**Output**:
```
ℹ️  Auto-detected environment file: env.fortistack.ips.conf
📄 Converting: 205812.txt
   Env:    .../env.fortistack.ips.conf
```

### With Explicit Env File

```bash
python3 run_transpiler.py \
  -f testcase/ips/topology1/205812.txt \
  -e testcase/ips/env.fortistack.ips.conf
```

### Batch Conversion

```bash
python3 run_transpiler.py \
  -d testcase/ips/topology1/ \
  -e testcase/ips/env.fortistack.ips.conf \
  -o output/batch_tests/
```

## Verification

### Check Generated Conftest

```bash
# View env integration in conftest.py
cat output/conftest.py | grep -A10 "ENV_FILE"
```

**Expected**:
```python
ENV_FILE = r'/home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf'

@pytest.fixture
def testbed():
    # Load environment configuration from file
    env_config = parse_env_file(ENV_FILE)
    testbed = TestBed(env_config, use_mock=True)
    return testbed
```

### Run Tests

```bash
cd output
pytest test__205812.py -v
```

**Expected**:
```
test__205812.py::test__205812 PASSED [100%]
========================= 1 passed in 0.02s =========================
```

## Files Created/Modified

### New Files
1. `/home/fosqa/tools/env_parser.py` - Environment file parser (313 lines)
2. `/home/fosqa/autolibv3/autolib_v3/prototype/tools/env_parser.py` - Copy for transpiler
3. `/home/fosqa/autolibv3/autolib_v3/prototype/ENV_INTEGRATION_GUIDE.md` - Complete documentation

### Modified Files
1. `run_transpiler.py` - Added `-e/--env` parameter and auto-detection logic
2. `tools/dsl_transpiler.py` - Updated `transpile()` and `generate_conftest_header()` methods
3. `TRANSPILER_USAGE.md` - Added env file usage examples

## Environment File Format

**Structure**: INI-style configuration
**Location**: `testcase/ips/env.*.conf`
**Example**: `env.fortistack.ips.conf`

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
CONNECTION: telnet 0.0.0.0 11023
USERNAME: admin
PASSWORD: admin
CUSTOMSIG1: custom1on1801F
CUSTOMSIG2: custom2on1801F
```

## Variable Resolution

**DSL Format**: `DEVICE:VARIABLE`

**Example in DSL**:
```
backup PC_05:IP_ETH1 /var/log/messages
```

**Resolved from env file**:
- `PC_05:IP_ETH1` → `172.16.200.55`
- `PC_05:PASSWORD` → `Qa123456!`
- `FGT_A:CUSTOMSIG1` → `custom1on1801F`

**Access in pytest**:
```python
def test_example(testbed):
    pc05_config = testbed.env_config['PC_05']
    ip = pc05_config['IP_ETH1']  # '172.16.200.55'
```

## Benefits

### ✅ Consistency
- Same configuration as original DSL tests
- Single source of truth for test environments
- No manual config duplication

### ✅ Maintenance
- Update env file once, affects all generated tests
- Easy to switch between test environments
- No hardcoded values in generated code

### ✅ Accuracy
- Real device IPs, credentials, paths
- All variables from DSL available at runtime
- Device-specific settings preserved

### ✅ Flexibility
- Auto-detection reduces CLI complexity
- Explicit specification when needed
- Fallback to minimal config for quick prototyping

## Testing

### Test Parser

```bash
python3 /home/fosqa/tools/env_parser.py \
  /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf
```

### Test Transpiler

```bash
cd /home/fosqa/autolibv3/autolib_v3/prototype

# Clean start
rm -rf output/

# Run with env file
python3 run_transpiler.py \
  -e /home/fosqa/autolibv3/autolib_v3/testcase/ips/env.fortistack.ips.conf

# Run tests
cd output
pytest test__205812.py -v
```

### Expected Results

✅ **Parser**: Displays 15+ sections, variable resolutions
✅ **Transpiler**: Shows "Using env config: ..."
✅ **Conftest**: Contains `parse_env_file(ENV_FILE)`
✅ **Pytest**: Test passes (PASSED [100%])

## Troubleshooting

### ModuleNotFoundError: env_parser

**Fix**:
```bash
cp /home/fosqa/tools/env_parser.py \
   /home/fosqa/autolibv3/autolib_v3/prototype/tools/
```

### Environment file not found

**Fix**: Use absolute path or verify file exists
```bash
ls -la /home/fosqa/autolibv3/autolib_v3/testcase/ips/env*.conf
```

### Missing fixtures

**Fix**: Delete registry and regenerate
```bash
rm output/.conversion_registry.json output/conftest.py
python3 run_transpiler.py -e env.fortistack.ips.conf
```

## Documentation

- **Complete Guide**: `ENV_INTEGRATION_GUIDE.md`
- **Usage Examples**: `TRANSPILER_USAGE.md`
- **Parser Reference**: `tools/env_parser.py` (docstrings)
- **This Summary**: `ENV_INTEGRATION_SUMMARY.md`

## Next Steps

### For Users

1. **Convert existing tests**:
   ```bash
   python3 run_transpiler.py -d testcase/ips/topology1/
   ```

2. **Run generated tests**:
   ```bash
   cd output && pytest -v
   ```

3. **Switch to real devices** (edit conftest.py):
   ```python
   testbed = TestBed(env_config, use_mock=False)
   ```

### For Developers

**Future Enhancements**:
- Dynamic variable substitution in generated code
- Multi-environment profile support
- Environment validation (check devices exist)
- Encrypted credential support
- Variable usage analysis and reporting

## Summary

The environment configuration integration is **complete and tested**:

✅ **Parser**: Reads AutoLib v3 env files correctly
✅ **CLI**: `-e/--env` option with auto-detection
✅ **Conftest**: Generated with real env config
✅ **Tests**: Pass with environment integration
✅ **Documentation**: Comprehensive guides created

**Impact**: Generated pytest tests now use the same real-world configuration as original DSL tests, ensuring accuracy and reducing maintenance.
