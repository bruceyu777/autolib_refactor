# Flexible Device Architecture - Mock vs Real Devices

## Overview

The fluent API now supports **both mock devices (for prototyping/testing) and real AutoLib v3 devices (for production testing)**. You can easily switch between modes without changing test code.

## Quick Start

### Using Mock Devices (Default for Prototype)

```python
from fluent import TestBed

# Explicit mock mode
testbed = TestBed(use_mock=True)

with testbed.device('FGT_A') as fgt:
    fgt.execute("show system status")
```

### Using Real Devices (Default for Production)

```python
from fluent import TestBed

# Explicit real device mode
testbed = TestBed(use_mock=False)

# Or simply (defaults to real):
testbed = TestBed()

with testbed.device('FGT_A') as fgt:
    fgt.execute("get system status")
```

### Using Environment Variable

```bash
# Set environment variable
export USE_MOCK_DEVICES=true  # or false

# Python code auto-detects
testbed = TestBed()  # Reads USE_MOCK_DEVICES
```

## Architecture

### Device Factory Pattern

```python
def create_device(name: str, config: dict = None, use_mock: bool = False):
    """
    Factory creates appropriate device based on mode:
    - use_mock=True  → MockFortiGate or MockPC
    - use_mock=False → FortiGate or Pc (from AutoLib v3)
    """
```

### Class Hierarchy

**Mock Devices** (for prototyping):
```
MockDevice (base)
├── MockFortiGate
└── MockPC
```

**Real Devices** (from AutoLib v3):
```
Device (base from lib/core/device/device.py)
├── FortiGate (lib/core/device/fortigate.py)
├── Pc (lib/core/device/pc.py)
├── Computer
├── FortiSwitch
├── FortiAP
└── ...
```

### Unified Interface

Both mock and real devices work through the same FluentDevice API:

```python
class FluentDevice:
    def execute(self, command: str):
        # Handles both mock and real:
        if hasattr(self.device, 'execute'):
            # Mock device interface
            return self.device.execute(command)
        elif hasattr(self.device, 'send_line_get_output'):
            # Real AutoLib v3 device interface
            return self.device.send_line_get_output(command)
```

## Configuration

### In conftest.py (Generated)

**For Prototype Testing** (default generated):
```python
@pytest.fixture
def testbed():
    env_config = {...}
    return TestBed(env_config, use_mock=True)  # Mock devices
```

**For Real Device Testing**:
```python
@pytest.fixture
def testbed():
    env_config = {...}
    return TestBed(env_config, use_mock=False)  # Real devices
    # Or simply:
    # return TestBed(env_config)  # Defaults to real
```

### TestBed.__init__() Parameters

```python
def __init__(self, env_config: dict = None, use_mock: bool = None):
    """
    Args:
        env_config: Environment configuration dict
        use_mock: 
            - True: Use mock devices
            - False: Use real AutoLib v3 devices
            - None (default): Check USE_MOCK_DEVICES env var, defaults to False
    """
```

## Migration Guide

### From Mock-Only to Flexible Architecture

**Before** (old code):
```python
from mock_device import create_mock_device

dev = create_mock_device("FGT_A")
```

**After** (new code):
```python
from fluent import create_device

# Mock
dev = create_device("FGT_A", use_mock=True)

# Real
dev = create_device("FGT_A", use_mock=False)
```

### Backward Compatibility

```python
# FluentFortiGate is now an alias
from fluent import FluentFortiGate, FluentDevice

assert FluentFortiGate is FluentDevice  # True

# Old code still works
fluent = FluentFortiGate(device, results)
```

## Usage Examples

### Prototype Testing (Mock Devices)

```python
#!/usr/bin/env python3
import pytest
from fluent import TestBed

@pytest.fixture
def testbed():
    return TestBed(use_mock=True)  # Mock devices

def test_ips_signatures(testbed):
    with testbed.device('FGT_A') as fgt:
        fgt.execute('''
        config ips custom
        edit "my_sig"
        set signature "F-SBID(...)"
        next
        end
        ''')
        
        fgt.execute("show ips custom").expect("my_sig")
```

### Production Testing (Real Devices)

```python
#!/usr/bin/env python3
import pytest
from fluent import TestBed

@pytest.fixture
def testbed():
    # Environment must have real devices configured
    return TestBed(use_mock=False)  # Real AutoLib v3 devices

def test_system_status(testbed):
    with testbed.device('FGT_A') as fgt:
        output = fgt.execute("get system status")
        output.expect("FortiGate")
```

### Environment-Based Switching

```bash
#!/bin/bash
# test_runner.sh

# Prototype mode
export USE_MOCK_DEVICES=true
pytest test_ips.py

# Real device mode
export USE_MOCK_DEVICES=false
pytest test_ips.py
```

```python
# test_ips.py
from fluent import TestBed

@pytest.fixture
def testbed():
    # Auto-detects from environment
    return TestBed()
```

## Device Type Detection

### Factory Logic

```python
def create_device(name, config, use_mock):
    if use_mock:
        # Mock device selection
        if 'FGT' in name.upper():
            return MockFortiGate(name, config)
        elif name.startswith('PC_'):
            return MockPC(name, config)
    else:
        # Real device selection
        if 'FGT' in name.upper():
            return FortiGate(name)  # AutoLib v3
        elif name.startswith('PC_'):
            return Pc(name)  # AutoLib v3
```

### Supported Patterns

| Device Name | Mock Type | Real Type |
|-------------|-----------|-----------|
| FGT_A | MockFortiGate | FortiGate |
| FGT_PRIMARY | MockFortiGate | FortiGate |
| FGTA_Node1 | MockFortiGate | FortiGate |
| PC_05 | MockPC | Pc |
| PC-Linux-01 | MockPC | Pc |

## Real Device Integration

### AutoLib v3 Device Path

```python
# Devices imported from:
from lib.core.device import FortiGate, Pc, Computer

# Located at:
/home/fosqa/autolibv3/autolib_v3/lib/core/device/
├── device.py         # Base Device class
├── fortigate.py      # FortiGate class
├── pc.py             # Pc class
├── computer.py       # Computer class
└── ...
```

### Device Interfaces

**Mock Device**:
```python
class MockFortiGate:
    def execute(self, command: str) -> str:
        # Returns output directly
```

**Real Device**:
```python
class FortiGate:
    def send_line_get_output(self, command: str) -> str:
        # Returns output from real connection
```

**FluentDevice** handles both:
```python
class FluentDevice:
    def execute(self, command: str):
        if hasattr(self.device, 'execute'):
            output = self.device.execute(command)  # Mock
        elif hasattr(self.device, 'send_line_get_output'):
            output = self.device.send_line_get_output(command)  # Real
```

## Benefits

### 1. **Rapid Prototyping**
- Use mock devices for fast iteration
- No hardware dependencies
- Instant test execution

### 2. **Production Readiness**
- Switch to real devices when ready
- Same test code works in both modes
- Gradual migration path

### 3. **Flexible Testing**
- Mock devices for CI/CD pipelines
- Real devices for final validation
- Environment-based switching

### 4. **Backward Compatible**
- Existing FluentFortiGate code still works
- Incremental migration
- No breaking changes

## Best Practices

### Development Workflow

```
1. Write tests with mock devices (fast iteration)
   testbed = TestBed(use_mock=True)

2. Validate logic with mocks
   pytest test_*.py  # Quick feedback

3. Test with real devices
   testbed = TestBed(use_mock=False)

4. Deploy to CI/CD
   USE_MOCK_DEVICES=true pytest  # CI pipeline
   USE_MOCK_DEVICES=false pytest # Nightly on real hardware
```

### File Organization

```
tests/
├── conftest.py              # TestBed fixture with mode selection
├── test_ips_signatures.py   # Test logic (mode-agnostic)
├── test_vdom_operations.py  # Test logic (mode-agnostic)
└── pytest.ini               # Configure default mode

fluent_api/
├── fluent.py                # Flexible TestBed + FluentDevice
├── mock_device.py           # Mock implementations
└── devices/                 # Real device wrappers (optional)
```

### Configuration File

```ini
# pytest.ini
[pytest]
env =
    USE_MOCK_DEVICES=true  # Default to mock for CI
```

## Troubleshooting

### Import Errors with Real Devices

**Problem**: Cannot import FortiGate from lib.core.device

**Solution**: The factory auto-adds AutoLib v3 lib to sys.path:
```python
autolib_lib = Path(__file__).parent.parent.parent / 'lib'
sys.path.insert(0, str(autolib_lib))
```

### Device Not Found

**Problem**: Real device name not in environment

**Solution**: Add to environment configuration or use mock:
```python
env_config = {
    'FGT_A': {'hostname': '10.1.1.1', 'user': 'admin', 'password': '...'},
}
testbed = TestBed(env_config, use_mock=False)
```

### Mock vs Real Behavior Differences

**Problem**: Test passes with mock but fails with real device

**Solution**: Update mock device to better match real behavior:
```python
# In mock_device.py MockFortiGate class
def execute(self, command: str) -> str:
    # Add more realistic output formatting
    # Match timing, prompts, error messages
```

## Future Enhancements

- [ ] Hybrid mode (some mock, some real)
- [ ] Device recording/playback
- [ ] Auto-generate mocks from real device interactions
- [ ] Performance comparison (mock vs real)
- [ ] Mock accuracy metrics

## Summary

The flexible architecture provides:
- ✅ **Default**: Real AutoLib v3 devices (production-ready)
- ✅ **Optional**: Mock devices (fast prototyping)
- ✅ **Configurable**: Via parameter, env var, or fixture
- ✅ **Transparent**: Same test code for both modes
- ✅ **Compatible**: FluentFortiGate alias maintained
- ✅ **Extensible**: Easy to add new device types

**One test suite, two execution modes!** 🚀
