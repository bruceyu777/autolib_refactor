# AutoLib v3 Component Reusability Guide

**Purpose**: Quick reference for reusing AutoLib v3 components in Python-based projects  
**Target**: Developers building pytest-based test frameworks  
**Last Updated**: 2026-02-18

---

## Overview

This guide helps you identify which AutoLib v3 components can be reused when building a **Python/pytest-based testing framework** without the DSL layer.

**TL;DR**: You can reuse ~70% of AutoLib v3 code by keeping the device and services layers and removing the compiler/executor.

---

## Component Reusability Matrix

| Component Path | Reusability | Effort | Notes |
|----------------|-------------|--------|-------|
| **lib/core/device/** | ✅ 100% | Zero | Copy as-is |
| **lib/core/device/session/** | ✅ 100% | Zero | Copy as-is |
| **lib/services/environment.py** | ✅ 100% | Zero | Copy as-is |
| **lib/services/log.py** | ✅ 100% | Zero | Copy as-is |
| **lib/services/path_utils.py** | ✅ 100% | Zero | Copy as-is |
| **lib/services/oriole/** | ✅ 100% | Zero | Copy as-is |
| **lib/services/fos/** | ✅ 100% | Zero | Copy as-is |
| **lib/services/result_manager.py** | ⚠️ 90% | 1 hour | Remove DSL-specific methods |
| **lib/services/template_env.py** | ⚠️ 80% | 30 min | Optional - for Jinja2 templates |
| **lib/core/compiler/** | ❌ 0% | N/A | Not needed - remove completely |
| **lib/core/executor/** | ❌ 0% | N/A | Not needed - pytest replaces this |
| **lib/core/scheduler/** | ⚠️ 50% | 2 hours | If you need parallel device control |

**Legend**:
- ✅ = Direct reuse (copy and use)
- ⚠️ = Minor adaptation needed
- ❌ = Not applicable for Python-based testing

---

## Device Layer (100% Reusable)

### What to Copy

```bash
# Copy entire device directory
cp -r autolibv3/lib/core/device/ your-project/lib/core/device/
```

### Available Device Classes

```python
from lib.core.device.fortigate import FortiGate
from lib.core.device.pc import PC
from lib.core.device.fortiswitch import FortiSwitch
from lib.core.device.kvm import KVM
from lib.core.device.fos_dev import FosDev
from lib.core.device.fortiap import FortiAP
from lib.core.device.faz_fmg import FAZ, FMG
from lib.core.device.computer import Computer
from lib.core.device.terminal_server import TerminalServer
from lib.core.device.pdu import PDU
from lib.core.device.vm_manager import VMManager
from lib.core.device.vm_builder import VMBuilder
```

### Usage Examples

#### FortiGate Device

```python
from lib.core.device.fortigate import FortiGate

# Create device instance
fgt = FortiGate(
    hostname='FGT-A',
    host='192.168.1.99',
    username='admin',
    password='',
    port=22,
    protocol='ssh'
)

# Connect
fgt.connect()

# Basic operations
output = fgt.execute('show system status')
fgt.expect('FortiGate-VM64', timeout=5)

# Configuration
config = '''
config system admin
    edit "apiuser"
        set password "fortinet"
    next
end
'''
fgt.execute(config)

# File operations
fgt.scp_upload('local_file.txt', 'remote_file.txt')
fgt.scp_download('remote.log', 'local.log')

# Reboot and wait
fgt.reboot()
fgt.wait_for_ready(timeout=300)

# Disconnect
fgt.disconnect()
```

#### PC/Linux Device

```python
from lib.core.device.pc import PC

pc = PC(
    hostname='PC1',
    host='192.168.2.10',
    username='root',
    password='fortinet'
)

pc.connect()
pc.execute('ping -c 5 192.168.1.99')
pc.execute('iperf3 -c 192.168.1.99 -t 60')
pc.disconnect()
```

#### KVM Hypervisor

```python
from lib.core.device.kvm import KVM

kvm = KVM(
    hostname='KVM-Host',
    host='192.168.100.1',
    username='root',
    password='fortinet'
)

kvm.connect()

# VM management
kvm.vm_start('FGT-VM-01')
kvm.vm_stop('FGT-VM-01')
kvm.vm_list()

kvm.disconnect()
```

### Device Capabilities Reference

| Method | FortiGate | PC | FortiSwitch | KVM | Description |
|--------|-----------|----|-----------|----|-------------|
| `connect()` | ✅ | ✅ | ✅ | ✅ | Establish connection |
| `disconnect()` | ✅ | ✅ | ✅ | ✅ | Close connection |
| `execute(cmd)` | ✅ | ✅ | ✅ | ✅ | Execute command |
| `expect(pattern)` | ✅ | ✅ | ✅ | ✅ | Wait for pattern |
| `send(text)` | ✅ | ✅ | ✅ | ✅ | Send text (no newline) |
| `send_line(text)` | ✅ | ✅ | ✅ | ✅ | Send text with newline |
| `scp_upload(local, remote)` | ✅ | ✅ | ✅ | ✅ | Upload file via SCP |
| `scp_download(remote, local)` | ✅ | ✅ | ✅ | ✅ | Download file via SCP |
| `reboot()` | ✅ | ✅ | ✅ | ✅ | Reboot device |
| `wait_for_ready()` | ✅ | ⚠️ | ✅ | ⚠️ | Wait until ready |
| `get_platform()` | ✅ | ❌ | ❌ | ❌ | Get FortiOS platform |
| `get_version()` | ✅ | ❌ | ✅ | ❌ | Get OS version |
| `backup_config()` | ✅ | ❌ | ✅ | ❌ | Backup configuration |
| `restore_config()` | ✅ | ❌ | ✅ | ❌ | Restore configuration |

---

## Services Layer (90% Reusable)

### Environment Service

**Reusability**: ✅ 100% - No changes needed

```python
from lib.services.environment import Environment

# Load environment from .conf file (same format as AutoLib v3)
env = Environment('envs/testbed_01.conf')

# Access device configurations
fgt_a_conf = env.get_device_conf('FGT_A')
# Returns: {'hostname': 'FGT_A', 'host': '192.168.1.99', 'username': 'admin', ...}

# Access global variables
build = env.get_var('build_number')
topology = env.get_var('topology')

# Get all devices
all_devices = env.get_all_devices()

# Environment file format (unchanged)
"""
[global]
build_number = 7.4.1-b2396
topology = ha_active_passive

[FGT_A]
type = FortiGate
host = 192.168.1.99
username = admin
password = 
"""
```

---

### Result Manager

**Reusability**: ⚠️ 90% - Remove `_parse_vm_code()` method

**Adaptation needed**:

```python
# In lib/services/result_manager.py

class ResultManager:
    # REMOVE this method (DSL-specific)
    # def _parse_vm_code(self, vm_code):
    #     ...
    
    # KEEP these methods (generic)
    def add_qaid_result(self, qaid, is_passed, output='', comment=''):
        """Record test result for a QAID"""
        pass
    
    def add_expect_result(self, pattern, output, is_found):
        """Record expect pattern result"""
        pass
    
    def get_summary(self):
        """Get pass/fail summary"""
        pass
    
    def upload_to_oriole(self):
        """Upload results to Oriole system"""
        pass
```

**Usage in pytest**:

```python
from lib.services.result_manager import ResultManager

def test_example(fgt_a):
    result_mgr = ResultManager(env)
    
    output = fgt_a.execute('show system status')
    
    if 'FortiGate' in output:
        result_mgr.add_qaid_result('Q001', True, output)
    else:
        result_mgr.add_qaid_result('Q001', False, output)
    
    # At end of test session
    result_mgr.upload_to_oriole()
```

---

### Logging Service

**Reusability**: ✅ 100% - No changes needed

```python
from lib.services.log import Logger

# Create logger
logger = Logger('test_ha_failover', log_dir='logs/')

# Use standard Python logging
logger.info('Starting HA failover test')
logger.debug('FGT_A IP: 192.168.1.99')
logger.warning('Timeout increased to 60s')
logger.error('Failed to connect to FGT_B')

# Or use directly
import logging
logging.info('Test started')
```

---

### Oriole Integration

**Reusability**: ✅ 100% - No changes needed

```python
from lib.services.oriole.client import OrioleClient

# Upload test results to Oriole system
oriole = OrioleClient(
    base_url='https://oriole.fortinet.com',
    api_key='your-api-key'
)

oriole.upload_results({
    'test_id': 'HA_FAILOVER_001',
    'status': 'PASSED',
    'duration': 120,
    'qaids': [
        {'qaid': 'Q001', 'status': 'PASSED'},
        {'qaid': 'Q002', 'status': 'PASSED'},
    ]
})
```

---

### FortiOS Platform Service

**Reusability**: ✅ 100% - No changes needed

```python
from lib.services.fos.fos_platform import FosPlatform

# Get platform information
platform = FosPlatform()

# Parse platform from output
output = "Platform: FortiGate-VM64-KVM"
plat_type = platform.parse_platform(output)
# Returns: 'FortiGate-VM64-KVM'

# Check if platform is VM
is_vm = platform.is_vm_platform('FortiGate-VM64')  # True
is_hw = platform.is_hw_platform('FortiGate-100F')  # True
```

---

## Removed Components (Not Needed)

### Compiler (lib/core/compiler/)

**Status**: ❌ Remove completely

**Reason**: Python/pytest handles parsing and execution. No DSL to compile.

| File | Purpose | Replacement |
|------|---------|-------------|
| `lexer.py` | DSL tokenization | Python's own parser |
| `parser.py` | DSL to VM code | Not needed |
| `syntax.py` | DSL schema | Not needed |
| `vm_code.py` | VM code structure | Not needed |

---

### Executor (lib/core/executor/)

**Status**: ❌ Remove completely

**Reason**: pytest runs tests, device methods execute commands directly.

| File | Purpose | Replacement |
|------|---------|-------------|
| `executor.py` | VM code execution | pytest test runner |
| `if_stack.py` | Control flow stack | Python's native if/while |
| `api_*.py` | DSL API implementations | Direct device method calls |

**Example comparison**:

```python
# DSL (AutoLib v3)
"""
[FGT_A]
show system status
expect "FortiGate" -for Q001
"""

# Executor processes VM codes:
# VMCode(1, "switch_device", ("FGT_A",))
# VMCode(2, "execute", ("show system status",))
# VMCode(3, "expect", ("FortiGate", "Q001"))

# Python/pytest (Direct)
def test_system_status(fgt_a, results):
    output = fgt_a.execute('show system status')
    assert 'FortiGate' in output
    results.add_qaid_result('Q001', True, output)
```

---

## Migration Checklist

### Phase 1: Copy Reusable Components

- [ ] Copy `lib/core/device/` directory (100% reusable)
- [ ] Copy `lib/services/environment.py` (100% reusable)
- [ ] Copy `lib/services/log.py` (100% reusable)
- [ ] Copy `lib/services/path_utils.py` (100% reusable)
- [ ] Copy `lib/services/oriole/` directory (100% reusable)
- [ ] Copy `lib/services/fos/` directory (100% reusable)
- [ ] Copy `lib/services/result_manager.py` (adapt: remove DSL methods)

### Phase 2: Skip Compiler/Executor

- [ ] **Do NOT copy** `lib/core/compiler/` (not needed)
- [ ] **Do NOT copy** `lib/core/executor/` (not needed)

### Phase 3: Create Wrapper Layer

- [ ] Create `fortios_test/context.py` (TestContext class)
- [ ] Create `tests/conftest.py` (pytest fixtures)
- [ ] Create `fortios_test/assertions.py` (custom assertions)
- [ ] Create `fortios_test/helpers.py` (utility functions)

### Phase 4: Configuration

- [ ] Copy environment `.conf` files from `autolibv3/envs/`
- [ ] Create `pytest.ini` for pytest configuration
- [ ] Create `requirements.txt` with dependencies

### Phase 5: Test Migration

- [ ] Convert DSL tests to Python/pytest
- [ ] Use device methods directly (no VM codes)
- [ ] Use pytest fixtures for setup/teardown
- [ ] Use pytest parametrize for data-driven tests

---

## Quick Start Example

### Minimal Working Setup

**Directory structure**:
```
my-pytest-framework/
├── lib/
│   ├── core/device/          ← Copied from AutoLib v3
│   └── services/             ← Copied from AutoLib v3
├── tests/
│   └── test_basic.py
├── envs/
│   └── testbed.conf
└── requirements.txt
```

**Test file** (`tests/test_basic.py`):
```python
import pytest
from lib.core.device.fortigate import FortiGate
from lib.services.environment import Environment

@pytest.fixture(scope='session')
def env():
    return Environment('envs/testbed.conf')

@pytest.fixture
def fgt_a(env):
    conf = env.get_device_conf('FGT_A')
    fgt = FortiGate(**conf)
    fgt.connect()
    yield fgt
    fgt.disconnect()

def test_system_status(fgt_a):
    """Basic test - verify system status"""
    output = fgt_a.execute('show system status')
    assert 'FortiGate' in output
    assert 'Version' in output
```

**Run test**:
```bash
pytest tests/test_basic.py -v
```

---

## Dependencies

### Required Python Packages

```txt
# From AutoLib v3 (device communication)
pexpect>=4.8.0
paramiko>=3.3.0
pyserial>=3.5

# pytest ecosystem
pytest>=7.4.0
pytest-html>=3.2.0

# Utilities
pyyaml>=6.0
```

### Optional Packages

```txt
# Parallel execution
pytest-xdist>=3.3.0

# Type checking
mypy>=1.5.0

# Code quality
black>=23.7.0
pylint>=2.17.0
```

---

## Common Patterns

### Pattern 1: Device Setup/Teardown

```python
@pytest.fixture
def fgt_with_config(fgt_a):
    """Setup device with specific config, restore after test"""
    # Backup current config
    fgt_a.execute('execute backup config flash backup.conf')
    
    # Apply test config
    fgt_a.execute('config system global')
    fgt_a.execute('set hostname "TEST-FGT"')
    fgt_a.execute('end')
    
    yield fgt_a
    
    # Restore config
    fgt_a.execute('execute restore config flash backup.conf')
```

### Pattern 2: Multi-Device Test

```python
@pytest.fixture
def ha_cluster(env):
    """Setup HA cluster (FGT_A + FGT_B)"""
    conf_a = env.get_device_conf('FGT_A')
    conf_b = env.get_device_conf('FGT_B')
    
    fgt_a = FortiGate(**conf_a)
    fgt_b = FortiGate(**conf_b)
    
    fgt_a.connect()
    fgt_b.connect()
    
    yield {'primary': fgt_a, 'secondary': fgt_b}
    
    fgt_a.disconnect()
    fgt_b.disconnect()

def test_ha_sync(ha_cluster):
    """Test HA configuration sync"""
    fgt_a = ha_cluster['primary']
    fgt_b = ha_cluster['secondary']
    
    # Make change on primary
    fgt_a.execute('config system global')
    fgt_a.execute('set admin-scp enable')
    fgt_a.execute('end')
    
    # Wait for sync
    import time
    time.sleep(5)
    
    # Verify on secondary
    output = fgt_b.execute('show system global | grep admin-scp')
    assert 'enable' in output
```

### Pattern 3: Result Tracking

```python
@pytest.fixture(scope='session')
def result_manager(env):
    from lib.services.result_manager import ResultManager
    mgr = ResultManager(env)
    yield mgr
    # Upload results at end of session
    mgr.upload_to_oriole()

def test_with_results(fgt_a, result_manager):
    """Test with QAID tracking"""
    output = fgt_a.execute('show system status')
    
    if 'FortiGate' in output:
        result_manager.add_qaid_result('Q001', True, output)
    else:
        result_manager.add_qaid_result('Q001', False, output)
        pytest.fail('FortiGate not found in output')
```

---

## Troubleshooting

### Issue: Import errors from lib.core.device

**Problem**:
```python
ImportError: No module named 'lib.core.device'
```

**Solution**:
```bash
# Option 1: Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/your/project"

# Option 2: Install as editable package
pip install -e .

# Option 3: Use sys.path in conftest.py
import sys
sys.path.insert(0, '/path/to/your/project')
```

---

### Issue: Environment file not found

**Problem**:
```python
FileNotFoundError: [Errno 2] No such file or directory: 'envs/testbed.conf'
```

**Solution**:
```python
# Use absolute path or path relative to project root
from pathlib import Path

project_root = Path(__file__).parent.parent
env_file = project_root / 'envs' / 'testbed.conf'
env = Environment(str(env_file))
```

---

### Issue: Device connection timeout

**Problem**:
```
TimeoutError: Timeout waiting for prompt
```

**Solution**:
```python
# Increase timeout in device config
fgt = FortiGate(
    host='192.168.1.99',
    username='admin',
    password='',
    timeout=60  # Increase from default 30s
)
```

---

## Summary

### Reuse Ratio

| Layer | Reusability | LOC | Effort |
|-------|-------------|-----|--------|
| Device | 100% | ~5,000 | Zero |
| Services | 90% | ~2,000 | 1-2 hours |
| Compiler | 0% | ~3,000 | N/A (remove) |
| Executor | 0% | ~2,000 | N/A (remove) |
| **Total** | **~70%** | **~12,000** | **1-2 hours** |

### Key Takeaways

✅ **Device layer is gold** - Copy and use as-is  
✅ **Services mostly reusable** - Minor cleanup needed  
✅ **Environment format unchanged** - Use same .conf files  
❌ **Skip compiler/executor** - pytest replaces them  
⚠️ **ResultManager needs cleanup** - Remove DSL methods  

### Next Steps

1. Read [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md) for complete architecture
2. Copy device and services layers
3. Create pytest fixtures
4. Start with simple tests
5. Gradually migrate complex tests

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Related**: [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md)
