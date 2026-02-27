# Python-Based Testing Framework - Architecture & Design

**Project Type**: Pure Python Testing Framework (pytest-based)  
**Base Framework**: AutoLib v3 (Device & Services Layer)  
**Target Users**: Developers/QA with Python knowledge  
**Last Updated**: 2026-02-18

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Reusable Components](#reusable-components)
4. [New Architecture Design](#new-architecture-design)
5. [Project Structure](#project-structure)
6. [Implementation Guide](#implementation-guide)
7. [Example Test Cases](#example-test-cases)
8. [Migration from DSL](#migration-from-dsl)
9. [Best Practices](#best-practices)
10. [Comparison: DSL vs Python](#comparison-dsl-vs-python)

---

## Executive Summary

### Project Vision

**Goal**: Create a Python-based testing framework leveraging AutoLib v3's robust device abstraction and services, replacing DSL scripting with pytest test cases.

**Key Benefits**:
- ✅ **Full Python power**: Use any Python library (pytest, requests, pandas, etc.)
- ✅ **IDE support**: PyCharm, VS Code autocomplete, type hints, debugging
- ✅ **Industry standard**: pytest is widely adopted, well-documented
- ✅ **Proven infrastructure**: Reuse battle-tested device/services layer
- ✅ **Type safety**: Static type checking with mypy/pylance
- ✅ **No custom compiler**: Leverage Python's compiler and runtime

**Trade-offs**:
- ❌ **Steeper learning curve**: Requires Python programming knowledge
- ❌ **More verbose**: `device.execute('cmd')` vs just `cmd` in DSL
- ❌ **Less abstraction**: Testing logic more explicit (pro or con depending on user)

### What We Keep vs Replace

| Component | Keep/Replace | Rationale |
|-----------|-------------|-----------|
| **Device Layer** | ✅ **KEEP** | Robust SSH/Telnet abstraction, multi-device support |
| **Services** | ✅ **KEEP** | Environment, logging, result management |
| **DSL Compiler** | ❌ **REMOVE** | Not needed for Python tests |
| **DSL Executor** | ❌ **REMOVE** | pytest handles execution |
| **Test Scripts** | ❌ **REPLACE** | DSL → Python pytest |

---

## Architecture Overview

### Current AutoLib v3 Architecture (DSL-Based)

```
┌─────────────────────────────────────────────────────────────┐
│              AUTOLIB V3 (DSL-BASED) ARCHITECTURE            │
└─────────────────────────────────────────────────────────────┘

Test Script (.txt DSL)
    │
    ▼
┌────────────────┐
│  DSL COMPILER  │  ← REMOVE THIS
│  (Lexer/Parser)│
└────────┬───────┘
         │
         ▼
    VM Codes
         │
         ▼
┌────────────────┐
│  DSL EXECUTOR  │  ← REMOVE THIS
└────────┬───────┘
         │
         ▼
┌────────────────────────────────────────┐
│  DEVICE LAYER (SSH/Telnet/Connection) │  ← KEEP THIS
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  SERVICES (Environment, Results, Log) │  ← KEEP THIS
└────────────────────────────────────────┘
```

### New Python-Based Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           NEW: PYTHON-BASED TESTING ARCHITECTURE            │
└─────────────────────────────────────────────────────────────┘

Test Script (.py pytest)
    │
    │  Written in pure Python
    │  Uses pytest framework
    │
    ▼
┌────────────────┐
│  PYTEST        │  ← Test discovery, execution, reporting
│  (Test Runner) │     Fixtures, parametrization, plugins
└────────┬───────┘
         │
         ▼
┌────────────────────────────────────────┐
│  TEST WRAPPER API (NEW - Thin Layer)  │  ← Convenience methods
│  • TestContext (fixture)               │     Device setup/teardown
│  • DeviceAPI wrapper                   │     Result collection
│  • Assertion helpers                   │     Common patterns
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  DEVICE LAYER (Reused from AutoLib v3)│  ← FortiGate, PC, etc.
│  • FortiGate, PC, FortiSwitch, etc.   │     SSH/Telnet/Serial
│  • Session management                  │     Command execution
│  • Connection handling                 │     Expect patterns
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  SERVICES (Reused from AutoLib v3)    │  ← Environment config
│  • Environment                         │     Result management
│  • ResultManager                       │     Logging
│  • Logger                              │     Oriole integration
└────────────────────────────────────────┘
```

**Key Architectural Change**: Replace **DSL Compiler + Executor** with **pytest + Thin Wrapper**

---

## Reusable Components

### ✅ Device Layer (100% Reusable)

**Location**: `lib/core/device/`

| Module | Purpose | Reuse Status | Notes |
|--------|---------|--------------|-------|
| **device.py** | Base device class | ✅ **Direct reuse** | Core abstraction |
| **fortigate.py** | FortiGate device | ✅ **Direct reuse** | SSH/Telnet to FortiGate |
| **pc.py** | PC/Linux device | ✅ **Direct reuse** | SSH to Linux machines |
| **fortiswitch.py** | FortiSwitch device | ✅ **Direct reuse** | Switch management |
| **computer.py** | Generic computer | ✅ **Direct reuse** | Windows/Linux |
| **kvm.py** | KVM hypervisor | ✅ **Direct reuse** | VM management |
| **faz_fmg.py** | FortiAnalyzer/Manager | ✅ **Direct reuse** | Central management |
| **fortiap.py** | FortiAP | ✅ **Direct reuse** | Wireless AP |
| **vm_manager.py** | VM lifecycle | ✅ **Direct reuse** | VM creation/deletion |
| **vm_builder.py** | VM provisioning | ✅ **Direct reuse** | VM image building |

**Key Classes to Use**:

```python
from lib.core.device.fortigate import FortiGate
from lib.core.device.pc import PC
from lib.core.device.fortiswitch import FortiSwitch
from lib.core.device.kvm import KVM

# Direct instantiation
fgt = FortiGate(host='192.168.1.99', username='admin', password='')
fgt.connect()
fgt.execute('show system status')
fgt.expect('FortiGate')
fgt.disconnect()
```

**Device Capabilities**:
- ✅ SSH/Telnet/Serial connection management
- ✅ Command execution with timeout
- ✅ Pattern matching (expect)
- ✅ File transfer (SCP/TFTP)
- ✅ Configuration backup/restore
- ✅ Reboot and wait for ready
- ✅ Multi-console support (primary/secondary)

---

### ✅ Services Layer (90% Reusable)

**Location**: `lib/services/`

| Module | Purpose | Reuse Status | Adaptation Needed |
|--------|---------|--------------|-------------------|
| **environment.py** | Environment config | ✅ **Direct reuse** | Load from .conf files |
| **result_manager.py** | Test result collection | ⚠️ **Minor adaptation** | Remove DSL-specific parts |
| **log.py** | Logging utilities | ✅ **Direct reuse** | Standard Python logging |
| **path_utils.py** | Path resolution | ✅ **Direct reuse** | File/directory helpers |
| **template_env.py** | Template rendering | ✅ **Optional** | Jinja2 templates if needed |
| **oriole/client.py** | Oriole integration | ✅ **Direct reuse** | Test management system |
| **fos/fos_platform.py** | FortiOS platform info | ✅ **Direct reuse** | Platform detection |
| **image_server.py** | Image server client | ✅ **Direct reuse** | Download FortiOS images |

**Environment Configuration** (Reuse as-is):

```python
from lib.services.environment import Environment

# Load environment from .conf file
env = Environment('envs/my_testbed.conf')

# Access devices
fgt_a_conf = env.get_device_conf('FGT_A')
# {'ip': '192.168.1.99', 'username': 'admin', 'password': '', ...}

# Access variables
build_number = env.get_var('build_number')
topology = env.get_var('topology')
```

**Result Manager** (Minor adaptation needed):

```python
from lib.services.result_manager import ResultManager

# Remove DSL-specific methods
# Keep: add_qaid_result, add_expect_result, get_summary, upload_to_oriole
result_mgr = ResultManager(env)
result_mgr.add_qaid_result('Q001', is_passed=True, output='Test passed')
result_mgr.get_summary()  # Pass/Fail count
result_mgr.upload_to_oriole()  # Send to test management
```

---

### ✅ Session Management (100% Reusable)

**Location**: `lib/core/device/session/`

| Module | Purpose | Reuse Status |
|--------|---------|--------------|
| **dev_conn.py** | Generic device connection | ✅ **Direct reuse** |
| **fos_conn.py** | FortiOS-specific connection | ✅ **Direct reuse** |
| **computer_conn.py** | Computer connection | ✅ **Direct reuse** |
| **pexpect_wrapper/** | Expect pattern matching | ✅ **Direct reuse** |

**No changes needed** - these are pure device communication abstractions.

---

### ❌ Components to Remove

**Location**: `lib/core/compiler/`, `lib/core/executor/`

| Module | Purpose | Remove | Reason |
|--------|---------|--------|--------|
| **compiler/lexer.py** | DSL tokenization | ❌ **REMOVE** | Python has its own parser |
| **compiler/parser.py** | DSL parsing | ❌ **REMOVE** | Not needed for Python tests |
| **compiler/syntax.py** | DSL schema | ❌ **REMOVE** | No DSL syntax |
| **executor/executor.py** | DSL execution | ❌ **REMOVE** | pytest handles execution |
| **executor/if_stack.py** | Control flow stack | ❌ **REMOVE** | Python's native control flow |
| **executor/vm_code.py** | VM code structure | ❌ **REMOVE** | No VM codes |

**Replacement**: pytest framework handles test discovery, execution, reporting

---

## New Architecture Design

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  PROJECT: fortios-pytest                    │
└─────────────────────────────────────────────────────────────┘

tests/
├── test_ha_failover.py          ← pytest test files
├── test_routing_ospf.py
├── test_firewall_policy.py
└── conftest.py                  ← pytest fixtures

fortios_test/                    ← NEW: Test wrapper library
├── __init__.py
├── context.py                   ← TestContext (device setup)
├── fixtures.py                  ← pytest fixtures
├── assertions.py                ← Custom assertions
└── helpers.py                   ← Common test utilities

lib/                             ← REUSED: AutoLib v3 components
├── core/
│   └── device/                  ← ✅ Reused 100%
│       ├── fortigate.py
│       ├── pc.py
│       ├── fortiswitch.py
│       └── session/
└── services/                    ← ✅ Reused 90%
    ├── environment.py
    ├── result_manager.py
    ├── log.py
    └── oriole/

envs/                            ← Environment configs (.conf)
├── testbed_01.conf
└── testbed_02.conf

pytest.ini                       ← pytest configuration
requirements.txt                 ← Python dependencies
```

---

### New Components to Create

#### 1. TestContext (Device Lifecycle Manager)

**File**: `fortios_test/context.py`

```python
"""Test context manager for device setup/teardown"""

from typing import Dict, Optional
from lib.core.device.fortigate import FortiGate
from lib.core.device.pc import PC
from lib.services.environment import Environment
from lib.services.result_manager import ResultManager


class TestContext:
    """
    Manages test environment, device connections, and results.
    
    Usage:
        ctx = TestContext('envs/testbed_01.conf')
        ctx.setup()
        fgt_a = ctx.get_device('FGT_A')
        fgt_a.execute('show system status')
        ctx.teardown()
    """
    
    def __init__(self, env_file: str):
        self.env = Environment(env_file)
        self.result_mgr = ResultManager(self.env)
        self.devices: Dict[str, any] = {}
        
    def setup(self):
        """Setup test environment and connect devices"""
        # Initialize devices from environment config
        for dev_name, dev_conf in self.env.devices.items():
            device = self._create_device(dev_name, dev_conf)
            if device:
                device.connect()
                self.devices[dev_name] = device
    
    def teardown(self):
        """Disconnect devices and cleanup"""
        for device in self.devices.values():
            try:
                device.disconnect()
            except Exception as e:
                print(f"Error disconnecting: {e}")
        
        # Upload results to Oriole
        self.result_mgr.upload_to_oriole()
    
    def get_device(self, name: str):
        """Get connected device by name"""
        return self.devices.get(name)
    
    def _create_device(self, name: str, conf: dict):
        """Factory method to create device based on type"""
        dev_type = conf.get('type', 'FortiGate')
        
        if dev_type == 'FortiGate':
            return FortiGate(**conf)
        elif dev_type == 'PC':
            return PC(**conf)
        # Add more device types as needed
        
        return None
```

---

#### 2. pytest Fixtures

**File**: `tests/conftest.py`

```python
"""pytest fixtures for FortiOS testing"""

import pytest
from fortios_test.context import TestContext


@pytest.fixture(scope='session')
def testbed():
    """
    Session-scope fixture for test environment.
    Setup once for all tests, teardown at end.
    """
    ctx = TestContext('envs/testbed_01.conf')
    ctx.setup()
    yield ctx
    ctx.teardown()


@pytest.fixture(scope='function')
def testbed_function():
    """
    Function-scope fixture for test environment.
    Setup/teardown for each test function.
    """
    ctx = TestContext('envs/testbed_01.conf')
    ctx.setup()
    yield ctx
    ctx.teardown()


@pytest.fixture
def fgt_a(testbed):
    """FortiGate A device fixture"""
    return testbed.get_device('FGT_A')


@pytest.fixture
def fgt_b(testbed):
    """FortiGate B device fixture"""
    return testbed.get_device('FGT_B')


@pytest.fixture
def pc1(testbed):
    """PC1 device fixture"""
    return testbed.get_device('PC1')


@pytest.fixture
def results(testbed):
    """Result manager fixture"""
    return testbed.result_mgr
```

---

#### 3. Custom Assertions

**File**: `fortios_test/assertions.py`

```python
"""Custom assertions for FortiOS testing"""

import re
from typing import Optional


class FortiOSAssertions:
    """Helper class for FortiOS-specific assertions"""
    
    @staticmethod
    def assert_output_contains(output: str, pattern: str, 
                              qaid: Optional[str] = None,
                              result_mgr=None):
        """
        Assert output contains pattern.
        
        Args:
            output: Command output
            pattern: Expected pattern (regex)
            qaid: Optional QAID for result tracking
            result_mgr: Optional result manager for recording
        """
        if re.search(pattern, output, re.MULTILINE):
            if result_mgr and qaid:
                result_mgr.add_qaid_result(qaid, True, f"Pattern found: {pattern}")
            return True
        else:
            if result_mgr and qaid:
                result_mgr.add_qaid_result(qaid, False, f"Pattern not found: {pattern}")
            raise AssertionError(f"Pattern '{pattern}' not found in output:\n{output}")
    
    @staticmethod
    def assert_ha_status(device, expected_status: str):
        """Assert HA status matches expected"""
        output = device.execute('get system ha status')
        assert expected_status in output, \
            f"Expected HA status '{expected_status}' not found in:\n{output}"
    
    @staticmethod
    def assert_interface_up(device, interface: str):
        """Assert interface is up"""
        output = device.execute(f'diagnose ip address list | grep -A 1 {interface}')
        assert 'up' in output.lower(), \
            f"Interface {interface} is not up:\n{output}"
```

---

## Project Structure

### Complete Directory Layout

```
fortios-pytest/                        ← New project root
│
├── README.md                          ← Project documentation
├── requirements.txt                   ← Python dependencies
├── pytest.ini                         ← pytest configuration
├── setup.py                           ← Package setup (optional)
├── .gitignore                         ← Git ignore file
│
├── fortios_test/                      ← NEW: Test wrapper library
│   ├── __init__.py
│   ├── context.py                     ← TestContext class
│   ├── fixtures.py                    ← Shared fixtures
│   ├── assertions.py                  ← Custom assertions
│   ├── helpers.py                     ← Utility functions
│   └── decorators.py                  ← Test decorators
│
├── lib/                               ← REUSED: From AutoLib v3
│   ├── __init__.py
│   ├── core/
│   │   └── device/                    ← ✅ Copy from AutoLib v3
│   │       ├── __init__.py
│   │       ├── device.py
│   │       ├── fortigate.py
│   │       ├── pc.py
│   │       ├── fortiswitch.py
│   │       ├── kvm.py
│   │       └── session/
│   │           ├── dev_conn.py
│   │           ├── fos_conn.py
│   │           └── pexpect_wrapper/
│   └── services/                      ← ✅ Copy from AutoLib v3
│       ├── __init__.py
│       ├── environment.py
│       ├── result_manager.py
│       ├── log.py
│       ├── path_utils.py
│       ├── fos/
│       └── oriole/
│
├── tests/                             ← NEW: pytest test files
│   ├── conftest.py                    ← pytest fixtures
│   ├── test_ha/                       ← Test suites by feature
│   │   ├── test_ha_failover.py
│   │   └── test_ha_sync.py
│   ├── test_routing/
│   │   ├── test_ospf.py
│   │   └── test_bgp.py
│   └── test_firewall/
│       ├── test_policy.py
│       └── test_nat.py
│
├── envs/                              ← Environment configs
│   ├── testbed_01.conf                ← Device/topology configs
│   ├── testbed_02.conf
│   └── README.md                      ← Env documentation
│
├── data/                              ← Test data
│   ├── configs/                       ← FortiGate configs
│   ├── expected_outputs/              ← Golden outputs
│   └── test_parameters.csv            ← Parameterized test data
│
└── reports/                           ← Test reports
    └── .gitkeep
```

---

## Implementation Guide

### Step 1: Project Setup

```bash
# Create new project directory
mkdir fortios-pytest
cd fortios-pytest

# Create directory structure
mkdir -p fortios_test lib/core lib/services tests envs data reports

# Copy reusable components from AutoLib v3
cp -r /path/to/autolibv3/lib/core/device lib/core/
cp -r /path/to/autolibv3/lib/services/* lib/services/

# Create Python package files
touch fortios_test/__init__.py
touch lib/__init__.py
touch lib/core/__init__.py
touch tests/conftest.py
```

---

### Step 2: Dependencies

**File**: `requirements.txt`

```txt
# Core dependencies
pytest>=7.4.0
pytest-html>=3.2.0
pytest-xdist>=3.3.0          # Parallel test execution
pytest-timeout>=2.1.0

# Device communication (from AutoLib v3)
pexpect>=4.8.0
paramiko>=3.3.0              # SSH
pyserial>=3.5                # Serial connection

# Utilities
pyyaml>=6.0
jinja2>=3.1.2
requests>=2.31.0

# Type checking (optional)
mypy>=1.5.0
types-requests
types-PyYAML

# Code quality (optional)
pylint>=2.17.0
black>=23.7.0
```

Install:
```bash
pip install -r requirements.txt
```

---

### Step 3: pytest Configuration

**File**: `pytest.ini`

```ini
[pytest]
# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Command line options
addopts = 
    -v                          # Verbose output
    --tb=short                  # Short traceback format
    --strict-markers            # Raise error on unknown markers
    --html=reports/report.html  # HTML report
    --self-contained-html       # Embed assets in HTML

# Markers
markers =
    smoke: Quick smoke tests
    regression: Full regression suite
    ha: HA-related tests
    routing: Routing protocol tests
    firewall: Firewall policy tests
    slow: Tests that take > 5 minutes
    requires_hardware: Tests requiring physical devices

# Logging
log_cli = true
log_cli_level = INFO
log_file = reports/pytest.log
log_file_level = DEBUG

# Timeout
timeout = 300  # 5 minutes per test
```

---

### Step 4: Environment Configuration

**File**: `envs/testbed_01.conf`

```ini
# Testbed Configuration (Same format as AutoLib v3)

[global]
topology = ha_active_passive
build_number = 7.4.1-b2396
test_suite = regression

[FGT_A]
type = FortiGate
host = 192.168.1.99
port = 22
username = admin
password = 
protocol = ssh
role = primary

[FGT_B]
type = FortiGate
host = 192.168.1.100
port = 22
username = admin
password =
protocol = ssh
role = secondary

[PC1]
type = PC
host = 192.168.2.10
username = root
password = fortinet
protocol = ssh
```

---

## Example Test Cases

### Example 1: Basic System Test

**File**: `tests/test_system/test_system_status.py`

```python
"""Test system status and platform detection"""

import pytest
from fortios_test.assertions import FortiOSAssertions


class TestSystemStatus:
    """System status tests"""
    
    def test_show_system_status(self, fgt_a, results):
        """
        Test QAID: Q001
        Verify FortiGate system status command works
        """
        # Execute command
        output = fgt_a.execute('show system status')
        
        # Assertions
        FortiOSAssertions.assert_output_contains(
            output, 
            r'Version:\s+FortiGate',
            qaid='Q001',
            result_mgr=results
        )
        
        assert 'Hostname' in output
        assert 'Serial-Number' in output
    
    def test_platform_detection(self, fgt_a):
        """Verify platform type is correctly detected"""
        output = fgt_a.execute('get system status | grep Platform')
        
        # Platform should be one of the known types
        assert any(platform in output for platform in [
            'FortiGate-VM64',
            'FortiGate-VM64-KVM',
            'FortiGate-60F',
            'FortiGate-100F'
        ])
    
    @pytest.mark.slow
    def test_system_performance(self, fgt_a):
        """Check system performance metrics"""
        output = fgt_a.execute('get system performance status')
        
        # Parse CPU usage
        import re
        cpu_match = re.search(r'CPU\s+states:\s+(\d+)%', output)
        if cpu_match:
            cpu_usage = int(cpu_match.group(1))
            assert cpu_usage < 90, f"CPU usage too high: {cpu_usage}%"
```

---

### Example 2: HA Failover Test

**File**: `tests/test_ha/test_ha_failover.py`

```python
"""HA failover testing"""

import pytest
import time
from fortios_test.assertions import FortiOSAssertions


class TestHAFailover:
    """HA failover test suite"""
    
    @pytest.fixture(autouse=True)
    def setup_ha_cluster(self, fgt_a, fgt_b):
        """Setup: Ensure HA cluster is healthy"""
        # Verify both devices are in sync
        FortiOSAssertions.assert_ha_status(fgt_a, 'primary')
        FortiOSAssertions.assert_ha_status(fgt_b, 'secondary')
        
        yield
        
        # Teardown: Restore to primary
        # (if needed)
    
    def test_manual_failover(self, fgt_a, fgt_b, results):
        """
        Test QAID: Q101
        Verify manual HA failover works correctly
        
        Steps:
        1. Verify FGT_A is primary
        2. Trigger failover on FGT_A
        3. Verify FGT_B becomes primary
        4. Verify FGT_A becomes secondary
        """
        # Step 1: Initial state
        output = fgt_a.execute('get system ha status')
        assert 'Mode: HA A-P' in output
        assert 'State: Primary' in output
        
        results.add_qaid_result('Q101-1', True, 'FGT_A is primary')
        
        # Step 2: Trigger failover
        fgt_a.execute('execute ha failover set 1')
        time.sleep(10)  # Wait for failover
        
        # Step 3: Verify FGT_B is now primary
        output_b = fgt_b.execute('get system ha status')
        assert 'State: Primary' in output_b
        
        results.add_qaid_result('Q101-2', True, 'FGT_B became primary')
        
        # Step 4: Verify FGT_A is now secondary
        output_a = fgt_a.execute('get system ha status')
        assert 'State: Secondary' in output_a
        
        results.add_qaid_result('Q101-3', True, 'FGT_A became secondary')
    
    @pytest.mark.parametrize('failure_type', ['power', 'heartbeat', 'port'])
    def test_automatic_failover(self, fgt_a, fgt_b, failure_type):
        """
        Test automatic failover on different failure types
        
        QAID: Q102-Q104
        """
        pytest.skip(f"Manual simulation needed for {failure_type} failure")
        # Implement failure simulation based on type
```

---

### Example 3: Parameterized Routing Test

**File**: `tests/test_routing/test_ospf.py`

```python
"""OSPF routing tests"""

import pytest


class TestOSPF:
    """OSPF protocol tests"""
    
    @pytest.mark.parametrize('interface,network,area', [
        ('port1', '192.168.1.0/24', '0.0.0.0'),
        ('port2', '192.168.2.0/24', '0.0.0.0'),
        ('port3', '10.0.0.0/16', '0.0.0.1'),
    ])
    def test_ospf_neighbor_formation(self, fgt_a, interface, network, area):
        """
        Test OSPF neighbor adjacency on different interfaces
        QAID: Q201-Q203
        """
        # Configure OSPF
        config = f'''
        config router ospf
            config network
                edit 1
                    set prefix {network}
                    set area {area}
                next
            end
        end
        '''
        fgt_a.execute(config)
        
        # Wait for neighbor formation
        import time
        time.sleep(30)
        
        # Verify neighbor
        output = fgt_a.execute('get router info ospf neighbor')
        assert 'Full' in output or 'ExStart' in output
    
    def test_ospf_route_redistribution(self, fgt_a):
        """Test OSPF route redistribution from connected routes"""
        # Configure redistribution
        config = '''
        config router ospf
            set redistribute "connected"
        end
        '''
        fgt_a.execute(config)
        
        # Verify routes are redistributed
        output = fgt_a.execute('get router info ospf database external')
        assert 'AS External Link States' in output
```

---

### Example 4: Data-Driven Test

**File**: `tests/test_firewall/test_policy.py`

```python
"""Firewall policy tests with CSV data"""

import pytest
import csv
from pathlib import Path


def load_policy_test_data():
    """Load policy test cases from CSV"""
    csv_file = Path('data/test_parameters.csv')
    if not csv_file.exists():
        return []
    
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        return list(reader)


class TestFirewallPolicy:
    """Firewall policy tests"""
    
    @pytest.mark.parametrize('test_case', load_policy_test_data())
    def test_policy_creation(self, fgt_a, test_case, results):
        """
        Data-driven policy creation test
        CSV columns: qaid, src_int, dst_int, src_addr, dst_addr, service, action
        """
        qaid = test_case['qaid']
        
        # Create policy
        config = f'''
        config firewall policy
            edit 0
                set name "Test-Policy-{qaid}"
                set srcintf {test_case['src_int']}
                set dstintf {test_case['dst_int']}
                set srcaddr {test_case['src_addr']}
                set dstaddr {test_case['dst_addr']}
                set service {test_case['service']}
                set action {test_case['action']}
            next
        end
        '''
        
        output = fgt_a.execute(config)
        
        # Verify policy was created
        verify = fgt_a.execute('show firewall policy | grep Test-Policy')
        assert f"Test-Policy-{qaid}" in verify
        
        results.add_qaid_result(qaid, True, f"Policy created: {test_case['qaid']}")
```

**Data file**: `data/test_parameters.csv`

```csv
qaid,src_int,dst_int,src_addr,dst_addr,service,action
Q301,port1,port2,all,all,HTTP,accept
Q302,port1,port2,all,all,HTTPS,accept
Q303,port2,port1,Internal_Net,all,ALL,deny
```

---

### Example 5: Fixture-Based Test

**File**: `tests/test_vpn/test_ipsec.py`

```python
"""IPsec VPN tests"""

import pytest


@pytest.fixture
def ipsec_tunnel(fgt_a):
    """Setup IPsec tunnel configuration"""
    # Setup
    config = '''
    config vpn ipsec phase1-interface
        edit "test-tunnel"
            set interface "port1"
            set peertype any
            set net-device disable
            set proposal aes256-sha256
            set remote-gw 10.1.1.1
            set psksecret fortinet123
        next
    end
    '''
    fgt_a.execute(config)
    
    yield 'test-tunnel'
    
    # Teardown
    fgt_a.execute('config vpn ipsec phase1-interface')
    fgt_a.execute('delete test-tunnel')
    fgt_a.execute('end')


class TestIPsec:
    """IPsec VPN tests"""
    
    def test_tunnel_status(self, fgt_a, ipsec_tunnel):
        """Verify IPsec tunnel status"""
        output = fgt_a.execute(f'diagnose vpn ike gateway list name {ipsec_tunnel}')
        assert ipsec_tunnel in output
    
    def test_tunnel_bring_up(self, fgt_a, ipsec_tunnel, pc1):
        """Test tunnel establishment by sending traffic"""
        # Send ping from PC through tunnel
        pc1.execute('ping -c 5 172.16.1.1')
        
        # Check tunnel is up
        output = fgt_a.execute('diagnose vpn tunnel list')
        assert 'up' in output.lower()
```

---

## Migration from DSL

### Migration Strategy

#### Option 1: One-to-One Translation

**DSL Script** (`test.txt`):
```plaintext
[FGT_A]
    show system status
    expect "FortiGate" -for Q001
    
    <if {$platform} eq FortiGate-VM64>
        diag debug enable
    <else>
        comment Not VM, skip debug
    <fi>
```

**Python Test** (`test_platform.py`):
```python
def test_system_status(fgt_a, results):
    """Q001: Verify system status"""
    output = fgt_a.execute('show system status')
    
    if 'FortiGate' in output:
        results.add_qaid_result('Q001', True, 'FortiGate detected')
    else:
        results.add_qaid_result('Q001', False, 'FortiGate not detected')
    
    # Get platform
    platform = fgt_a.get_platform()  # Or parse from output
    
    if platform == 'FortiGate-VM64':
        fgt_a.execute('diag debug enable')
    else:
        print("Not VM, skip debug")
```

---

#### Option 2: Refactor to pytest Patterns

**DSL approach** (procedural):
```plaintext
<intset retry 0>
<while {$retry} < 3>
    show system status
    expect "Ready" -t 5
    <if {$?} eq 0>
        comment System ready
        break
    <else>
        <intadd retry 1>
        <sleep 10>
    <fi>
<endwhile>
```

**Python approach** (pytest with retry):
```python
import pytest
from time import sleep

@pytest.mark.parametrize('attempt', range(3))
def test_system_ready_with_retry(fgt_a, attempt):
    """Wait for system to be ready (with retry)"""
    output = fgt_a.execute('show system status', timeout=5)
    
    if 'Ready' in output:
        pytest.skip("System ready, no more retries needed")
        return
    
    if attempt < 2:  # Not last attempt
        sleep(10)
        pytest.fail("System not ready, will retry")
    else:  # Last attempt
        pytest.fail("System not ready after 3 attempts")
```

Or use pytest-retry plugin:
```python
@pytest.mark.flaky(reruns=3, reruns_delay=10)
def test_system_ready(fgt_a):
    """Wait for system to be ready"""
    output = fgt_a.execute('show system status')
    assert 'Ready' in output
```

---

### Migration Checklist

- [ ] **Extract device configs** from DSL env to `.conf` files (already compatible!)
- [ ] **Map DSL commands** to Python device methods
  - `show X` → `device.execute('show X')`
  - `expect "pattern" -for QAID` → `assert_output_contains(..., qaid=QAID)`
  - `<if>` → `if`
  - `<while>` → `while` or `@pytest.mark.flaky`
- [ ] **Convert QAIDs** to pytest test IDs or markers
- [ ] **Reuse environment** files (same format)
- [ ] **Preserve test logic** but leverage Python constructs

---

## Best Practices

### 1. Test Structure

✅ **DO**: One test file per feature area
```python
tests/
├── test_ha/
│   ├── test_failover.py
│   └── test_sync.py
├── test_routing/
│   └── test_ospf.py
```

❌ **DON'T**: Monolithic test files
```python
tests/
└── test_everything.py  # 5000 lines
```

---

### 2. Fixture Usage

✅ **DO**: Use fixtures for setup/teardown
```python
@pytest.fixture
def configured_interface(fgt_a):
    # Setup
    fgt_a.execute('config system interface')
    fgt_a.execute('edit port1')
    fgt_a.execute('set ip 192.168.1.1/24')
    fgt_a.execute('end')
    
    yield 'port1'
    
    # Teardown
    fgt_a.execute('config system interface')
    fgt_a.execute('delete port1')
    fgt_a.execute('end')
```

❌ **DON'T**: Manual setup/teardown in every test
```python
def test_something(fgt_a):
    # Manual setup
    fgt_a.execute('config...')
    
    # Test logic
    ...
    
    # Manual teardown (often forgotten!)
    fgt_a.execute('delete...')
```

---

### 3. Assertions

✅ **DO**: Clear, specific assertions
```python
output = fgt_a.execute('get system ha status')
assert 'Mode: HA A-P' in output, "HA mode should be Active-Passive"
assert 'State: Primary' in output, "Device should be primary"
```

❌ **DON'T**: Vague assertions
```python
assert output  # What are we checking?
assert 'HA' in output  # Too broad
```

---

### 4. Parametrization

✅ **DO**: Use parametrization for similar tests
```python
@pytest.mark.parametrize('protocol,port', [
    ('HTTP', 80),
    ('HTTPS', 443),
    ('SSH', 22),
])
def test_service_filtering(fgt_a, protocol, port):
    # Test logic
    pass
```

❌ **DON'T**: Copy-paste test  functions
```python
def test_http_filtering(fgt_a):
    # Test HTTP
    pass

def test_https_filtering(fgt_a):
    # Test HTTPS (duplicate logic)
    pass
```

---

### 5. Documentation

✅ **DO**: Docstrings with QAID references
```python
def test_ha_failover(fgt_a, fgt_b):
    """
    Test HA failover functionality
    
    QAID: Q101
    Priority: P0
    Automation: Full
    
    Steps:
    1. Verify FGT_A is primary
    2. Trigger failover
    3. Verify FGT_B becomes primary
    """
    pass
```

---

### 6. Error Handling

✅ **DO**: Graceful error handling with context
```python
try:
    output = fgt_a.execute('show system status', timeout=10)
except TimeoutError as e:
    pytest.fail(f"Command timed out: {e}")
except Exception as e:
    pytest.fail(f"Unexpected error: {e}")
```

---

## Comparison: DSL vs Python

### Side-by-Side Feature Comparison

| Feature | DSL (AutoLib v3) | Python (pytest) | Winner |
|---------|-----------------|-----------------|--------|
| **Syntax simplicity** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐⭐ Moderate | DSL |
| **Learning curve** | ⭐⭐⭐⭐⭐ 1 day | ⭐⭐⭐ 1 week | DSL |
| **IDE support** | ⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full | Python |
| **Debugging** | ⭐⭐⭐ Custom | ⭐⭐⭐⭐⭐ pdb, IDE | Python |
| **Type safety** | ⭐ None | ⭐⭐⭐⭐⭐ mypy | Python |
| **Code reuse** | ⭐⭐⭐ Include | ⭐⭐⭐⭐⭐ Modules | Python |
| **Flexibility** | ⭐⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full | Python |
| **Libraries** | ⭐⭐ Built-in only | ⭐⭐⭐⭐⭐ PyPI | Python |
| **Parallel execution** | ⭐⭐ Custom | ⭐⭐⭐⭐⭐ pytest-xdist | Python |
| **Reporting** | ⭐⭐⭐ Custom | ⭐⭐⭐⭐⭐ HTML, JUnit | Python |

---

### When to Use Each

**Use DSL (AutoLib v3)** when:
- ✅ Users are QA engineers (not developers)
- ✅ Simple test scenarios (execute, expect, if/else)
- ✅ Need minimal training time
- ✅ Existing DSL test library to maintain

**Use Python (pytest)** when:
- ✅ Users know Python
- ✅ Complex test logic needed
- ✅ Want to use Python ecosystem (pandas, requests, etc.)
- ✅ Need strong IDE support
- ✅ Type safety is important
- ✅ Building new test suite from scratch

---

## Summary

### Reusable Components (High Value)

| Component | Status | Value |
|-----------|--------|-------|
| **Device Layer** | ✅ 100% reusable | ⭐⭐⭐⭐⭐ Critical |
| **Services** | ✅ 90% reusable | ⭐⭐⭐⭐ High |
| **Environment** | ✅ 100% reusable | ⭐⭐⭐⭐⭐ Critical |
| **Session** | ✅ 100% reusable | ⭐⭐⭐⭐⭐ Critical |

### New Components to Build

| Component | Effort | Priority |
|-----------|--------|----------|
| **TestContext** | 2 days | High |
| **pytest fixtures** | 1 day | High |
| **Assertions** | 1 day | Medium |
| **Documentation** | 2 days | Medium |

### Estimated Effort

- **Initial setup**: 1 week
- **Test migration** (per 100 DSL tests): 2-3 weeks
- **Training**: 1 week (for Python basics)

### Benefits

✅ **Full Python power** - Use any library  
✅ **Better tooling** - IDE, debugger, linters  
✅ **Industry standard** - pytest knowledge is transferable  
✅ **Type safety** - Catch errors before runtime  
✅ **Proven infrastructure** - Leverage AutoLib v3's device layer

---

## Next Steps

1. **Prototype** - Build 5-10 test examples to validate approach
2. **Training** - Python basics for QA team
3. **Migration** - Start with simple tests, build confidence
4. **CI/CD** - Integrate with Jenkins/GitHub Actions
5. **Documentation** - Internal wiki, examples, best practices

---

**Document Version**: 1.0  
**Author**: Software Architecture Team  
**Base Framework**: AutoLib v3 V3R10B0007  
**Created**: 2026-02-18
