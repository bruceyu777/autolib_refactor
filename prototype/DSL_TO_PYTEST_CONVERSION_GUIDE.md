# DSL to pytest Conversion Guide

## Overview

This document comprehensively explains the **direct DSL-to-pytest transpilation** approach implemented for AutoLib v3, including the conversion logic, implementation architecture, and design decisions.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Philosophy: Why Direct Transpilation?](#design-philosophy)
3. [Conversion Pipeline](#conversion-pipeline)
4. [DSL Parsing Logic](#dsl-parsing-logic)
5. [Conversion Rules](#conversion-rules)
6. [FluentAPI Architecture](#fluentapi-architecture)
7. [Environment Integration](#environment-integration)
8. [Example Walkthrough](#example-walkthrough)
9. [Current Limitations](#current-limitations)
10. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   DSL to pytest Transpiler                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Input: DSL Test File (e.g., 205812.txt)                        │
│  - Device sections: [FGT_A], [PC_05]                            │
│  - Commands: config, show, execute, etc.                        │
│  - Variables: FGT_A:CUSTOMSIG1, PC_05:IP_ETH1                   │
│  - Assertions: expect -e "pattern" -for QAID                    │
│  - Includes: include testcase/path/to/file.txt                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Transpilation Components                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. DSLTranspiler (tools/dsl_transpiler.py)               │  │
│  │    - parse_test_file(): Extract structure from DSL       │  │
│  │    - extract_includes(): Find include dependencies       │  │
│  │    - convert_section(): Convert device blocks            │  │
│  │    - generate_test_function(): Create pytest function    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2. IncludeConverter (tools/include_converter.py)         │  │
│  │    - convert_include(): Process include files            │  │
│  │    - to_pytest_fixture(): Generate pytest fixtures       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3. EnvParser (tools/env_parser.py)                       │  │
│  │    - parse_env_file(): Load environment configuration    │  │
│  │    - resolve_variable(): Runtime DEVICE:VAR resolution   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Output: pytest Test Script (e.g., test_205812.py)              │
│  - Test function: test_205812(testbed, fixtures)                │
│  - FluentAPI calls: testbed.device('FGT_A').execute(...)        │
│  - Variable placeholders: FGT_A:CUSTOMSIG1 (resolved at runtime)│
│  - Chained assertions: .execute(...).expect(...)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Runtime Execution (pytest)                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ FluentAPI (fluent_api/fluent.py)                         │  │
│  │  - TestBed: Central coordinator for devices              │  │
│  │  - FluentDevice: Wrapper for device operations           │  │
│  │  - @resolve_command_vars: Decorator for variable         │  │
│  │    resolution in ALL methods                             │  │
│  │  - ResultManager: Track QAID assertions                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Environment Loading (conftest.py)                        │  │
│  │  - Load env.fortistack.ips.conf                          │  │
│  │  - Parse device configurations                           │  │
│  │  - Create TestBed instance                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Variable Resolution (@resolve_command_vars)              │  │
│  │  - Intercept all method calls                            │  │
│  │  - Resolve DEVICE:VARIABLE patterns                      │  │
│  │  - FGT_A:CUSTOMSIG1 → custom1on1801F                     │  │
│  │  - PC_05:IP_ETH1 → 172.16.200.55                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Device Execution (Mock or Real)                                │
│  - Mock: In-memory simulation for testing                       │
│  - Real: AutoLib v3 device connections                          │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principle

**Direct Transpilation**: Convert DSL syntax directly to pytest + FluentAPI **without** using AutoLib v3's compiler or VM bytecode.

---

## Design Philosophy

### Why Direct Transpilation (Not VM-based)?

The AutoLib v3 framework has a compiler (`autotest.py compile`) that generates VM bytecode. However, we chose **direct transpilation** for the following strategic reasons:

> **⚠️ IMPORTANT NOTE**: The current FluentAPI is a **prototype implementation** that demonstrates the transpilation approach. For production use, FluentAPI must be refactored to leverage AutoLib v3's existing executor infrastructure (see [FLUENT_API_EXECUTOR_INTEGRATION.md](FLUENT_API_EXECUTOR_INTEGRATION.md)).

#### 1. **pytest Native Integration**
- **Goal**: Run tests with `pytest` command directly
- **Benefit**: Leverage pytest's extensive ecosystem (fixtures, plugins, reporting, CI/CD integration)
- **VM Issue**: VM bytecode execution would bypass pytest's test discovery and execution model

#### 2. **Readability & Maintainability**
- **Generated Code**: Human-readable Python with clear FluentAPI calls
- **Debugging**: Standard Python debugging tools, stack traces, and IDE support
- **VM Issue**: Bytecode is opaque, requires VM debugger, limited tooling

#### 3. **Type Safety & IDE Support**
- **FluentAPI**: Type hints enable autocomplete, type checking (mypy)
- **Modern Python**: Leverage Python 3.x features (context managers, decorators)
- **VM Issue**: Bytecode execution loses type information

#### 4. **Extensibility**
- **Easy Enhancement**: Add new FluentAPI methods, decorators, or patterns
- **Plugin Architecture**: pytest plugins can extend functionality
- **VM Issue**: VM instruction set is fixed, modifications require VM changes

#### 5. **Incremental Migration**
- **Coexistence**: DSL tests and pytest tests can run side-by-side
- **Gradual Adoption**: Teams can migrate incrementally
- **VM Issue**: All-or-nothing approach, harder to adopt gradually

#### 6. **Environment Configuration**
- **Runtime Resolution**: Variable resolution happens at runtime via decorator
- **Flexibility**: Same test runs in different environments
- **VM Issue**: VM would need custom variable resolution instructions

---

## Conversion Pipeline

### Step-by-Step Process

```
┌────────────────────────────────────────────────────────────────┐
│ Step 1: Command Line Invocation                                │
└────────────────────────────────────────────────────────────────┘

$ python run_transpiler.py \
    -i testcase/ips/topology1/205812.txt \
    -o output/ \
    -e testcase/ips/topology1/env.fortistack.ips.conf

                              │
                              ▼

┌────────────────────────────────────────────────────────────────┐
│ Step 2: Parse DSL File (DSLTranspiler.parse_test_file)         │
│                                                                 │
│  Input: 205812.txt                                             │
│                                                                 │
│  Output: Parsed structure                                      │
│  {                                                             │
│    'qaid': '205812',                                           │
│    'title': 'IPS Regression Test Case 2.1',                   │
│    'sections': [                                               │
│      {                                                         │
│        'device': 'FGT_A',                                      │
│        'commands': [                                           │
│          'comment REGR_IPS_02_01:Busy: ...',                   │
│          'config ips custom',                                  │
│          '  edit "match small"',                               │
│          '  ...',                                              │
│          'end',                                                │
│          'show ips custom',                                    │
│          'expect -e "match small" -for 205812 -t 5'            │
│        ]                                                       │
│      },                                                        │
│      { 'device': 'PC_05', 'commands': [...] }                  │
│    ],                                                          │
│    'includes': [                                               │
│      {                                                         │
│        'path': 'testcase/.../govdom1.txt',                     │
│        'resolved_path': Path('sample_includes/govdom1.txt')    │
│      }                                                         │
│    ]                                                           │
│  }                                                             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼

┌────────────────────────────────────────────────────────────────┐
│ Step 3: Convert Includes (IncludeConverter.convert_include)    │
│                                                                 │
│  For each include:                                             │
│    - Read include file content                                 │
│    - Determine type (setup/cleanup/config)                     │
│    - Generate pytest fixture                                   │
│    - Write to conftest.py                                      │
│                                                                 │
│  Output: List of fixture names                                 │
│  ['setup_govdom1', 'cleanup_outvdom']                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼

┌────────────────────────────────────────────────────────────────┐
│ Step 4: Convert Device Sections (DSLTranspiler.convert_section)│
│                                                                 │
│  For each [DEVICE] section:                                    │
│    a) Group commands into logical blocks                       │
│    b) Detect command types:                                    │
│       - config_block: multi-line config                        │
│       - command: single-line command                           │
│       - expect: assertion on output                            │
│    c) Chain expect assertions with preceding commands          │
│    d) Generate pytest code with FluentAPI calls                │
│                                                                 │
│  Output: pytest code string                                    │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼

┌────────────────────────────────────────────────────────────────┐
│ Step 5: Generate Test Function (generate_test_function)        │
│                                                                 │
│  Combine:                                                      │
│    - Imports (pytest, sys, FluentAPI)                          │
│    - Test function signature with fixtures                     │
│    - All converted sections                                    │
│    - Final result reporting                                    │
│                                                                 │
│  Output: Complete test_205812.py file                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼

┌────────────────────────────────────────────────────────────────┐
│ Step 6: Generate conftest.py                                   │
│                                                                 │
│  - Import FluentAPI and env_parser                             │
│  - Create testbed fixture with env loading                     │
│  - Add all include-based fixtures                              │
│                                                                 │
│  Output: conftest.py for pytest                                │
└────────────────────────────────────────────────────────────────┘
```

---

## DSL Parsing Logic

### Input DSL Structure

```dsl
#  IPS Regression Test Case 2.1
#  Verify create custom signature in cli, change and reboot
#  NAT mode

[FGT_A]
    comment REGR_IPS_02_01:Busy: create custom signatures
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    config ips custom
        edit "match small"
            set signature "F-SBID( --name \"match small\"; ...)"
        next
    end
    show ips custom
    expect -e "match small" -for 205812 -t 5
    exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD
    sleep 5

[PC_05]
    cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2
    expect -e "differ" -fail match -for 205812
    rm -f /root/FGT_A:CUSTOMSIG1
    report 205812
```

### Parsing Elements

#### 1. **QAID Extraction**
```python
# From filename
qaid = test_file.stem  # "205812"
```

#### 2. **Title Extraction**
```python
# From first comment line
title_match = re.search(r'#\s*(.+)', content)
title = title_match.group(1)  # "IPS Regression Test Case 2.1"
```

#### 3. **Device Section Parsing**
```python
# Pattern: [DEVICE_NAME]
device_match = re.match(r'\[(\w+)\]', line)

# Collects all commands under each device section until next [DEVICE] or EOF
```

#### 4. **Include Extraction**
```python
# Pattern: include testcase/path/to/file.txt
for match in re.finditer(r'^\s*include\s+(.+\.txt)', content, re.MULTILINE):
    include_path = match.group(1)
    # Resolve GLOBAL:VERSION and map to sample_includes/
```

#### 5. **Command Grouping**

Commands are grouped into logical blocks for better code generation:

```python
def _group_commands(self, commands: List[str]) -> List[dict]:
    """
    Groups commands into:
    - config_block: Multi-line config ... end blocks
    - command: Single-line commands
    - expect: Assertions on output
    
    Tracks config depth for nested config blocks
    """
```

**Example Grouping**:
```
Input DSL:
    config ips custom
        edit "test"
            set signature "..."
        next
    end
    show ips custom
    expect -e "match small" -for 205812

Output Blocks:
    [
      {'type': 'config_block', 'lines': ['config ips custom', 'edit "test"', ..., 'end']},
      {'type': 'command', 'command': 'show ips custom'},
      {'type': 'expect', 'pattern': 'match small', 'should_fail': False}
    ]
```

---

## Conversion Rules

### Rule 1: Device Section → Context Manager

**DSL**:
```dsl
[FGT_A]
    show system status
    expect -e "FortiGate" -for 205812
```

**pytest**:
```python
with testbed.device('FGT_A') as fgt_a:
    fgt_a.execute("show system status").expect("FortiGate", qaid="205812")
```

**Logic**:
- Device name becomes context manager: `testbed.device('FGT_A')`
- Variable name is lowercase: `as fgt_a`
- All commands in section use this variable

---

### Rule 2: Single Command → execute()

**DSL**:
```dsl
show ips custom
```

**pytest**:
```python
fgt_a.execute("show ips custom")
```

**Quote Handling**:
```python
def _quote_command(self, command: str) -> str:
    # If contains double quotes, use single quotes
    if '"' in command and "'" not in command:
        return f"'{command}'"
    # If contains single quotes, use double quotes
    elif "'" in command and '"' not in command:
        return f'"{command}"'
    # If contains both, escape double quotes
    else:
        escaped = command.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
```

---

### Rule 3: Config Block → Triple-Quoted String

**DSL**:
```dsl
config ips custom
    edit "match small"
        set signature "F-SBID(...)"
    next
end
```

**pytest**:
```python
fgt_a.execute("""
config ips custom
    edit "match small"
        set signature "F-SBID(...)"
    next
end
""")
```

**Logic**:
- Multi-line blocks use triple-quoted strings
- Preserves indentation and formatting
- Nested config blocks tracked by depth counter

---

### Rule 4: expect → Chained Assertion

**DSL**:
```dsl
show ips custom
expect -e "match small" -for 205812 -t 5
```

**pytest**:
```python
fgt_a.execute("show ips custom").expect("match small", qaid="205812")
```

**Chaining Logic**:
```python
# If next block is expect, chain them
if i + 1 < len(blocks) and blocks[i + 1]['type'] == 'expect':
    next_block = blocks[i + 1]
    pattern = next_block['pattern']
    
    pytest_code += f'{device_var}.execute({quoted_cmd})'
    pytest_code += f'.expect("{pattern}", qaid="{qaid}")\n'
    
    # Mark next block as processed to avoid double-processing
    blocks[i + 1] = {'type': 'processed'}
```

**Negative Assertion** (`-fail match`):
```dsl
expect -e "differ" -fail match -for 205812
```

**pytest**:
```python
.expect("differ", qaid="205812", should_fail=True)
```

---

### Rule 5: include → pytest Fixture

**DSL**:
```dsl
[FGT_A]
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    show system status
```

**pytest Test Function**:
```python
def test_205812(testbed, setup_govdom1, cleanup_outvdom):
    # setup_govdom1 runs before test
    # cleanup_outvdom runs after test
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("show system status")
```

**Generated Fixture** (in conftest.py):
```python
@pytest.fixture
def setup_govdom1(testbed):
    """
    Setup fixture from govdom1.txt
    Executes: Go to vdom1
    """
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("config global")
        fgt_a.execute("config vdom")
        fgt_a.execute("edit vdom1")
        fgt_a.execute("end")
    
    yield  # Test runs here
```

**Include Type Detection**:
```python
def _detect_type(self, filename: str, content: str) -> str:
    # Check filename patterns
    if 'gov' in filename.lower() or 'setup' in filename.lower():
        return 'setup'
    elif 'out' in filename.lower() or 'cleanup' in filename.lower():
        return 'cleanup'
    else:
        return 'config'
```

---

### Rule 6: Variables → Runtime Resolution

**DSL**:
```dsl
exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD
```

**pytest** (transpiler output, UNCHANGED):
```python
fgt_a.execute("exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")
```

**Runtime Resolution** (via @resolve_command_vars decorator):
```python
# Before execution, decorator resolves:
# FGT_A:CUSTOMSIG1 → custom1on1801F
# PC_05:IP_ETH1 → 172.16.200.55
# PC_05:PASSWORD → Qa123456!

# Actual command executed:
"exe backup ipsuserdefsig ftp custom1on1801F 172.16.200.55 root Qa123456!"
```

**Key Point**: Variables are **NOT** resolved during transpilation. They remain as `DEVICE:VARIABLE` patterns in the generated pytest code and are resolved **at runtime** when the test executes.

---

### Rule 7: Special Commands

**sleep**:
```dsl
sleep 5
```
```python
fgt_a.execute("sleep 5")
```

**keep_running**:
```dsl
keep_running 0
```
```python
fgt_a.execute("keep_running 0")
```

**comment**:
```dsl
comment REGR_IPS_02_01:Busy: create custom signatures
```
```python
fgt_a.execute("comment REGR_IPS_02_01:Busy: create custom signatures")
```

**report**:
```dsl
report 205812
```
```python
pc_05.execute("report 205812")

# Plus at end of test function:
testbed.results.report("205812")
```

---

## FluentAPI Architecture

### Core Classes

#### 1. **TestBed** (Central Coordinator)

```python
class TestBed:
    def __init__(self, devices: dict, use_mock: bool = False):
        self.devices = devices           # Device configurations
        self.results = ResultManager()   # Track QAID assertions
        self.use_mock = use_mock         # Mock vs real devices
        self._env_config = {}            # Environment configuration
    
    @contextmanager
    def device(self, name: str):
        """Get device with fluent API wrapper"""
        device_obj = self.get_device(name)
        fluent_device = FluentDevice(device_obj, self.results, testbed=self)
        yield fluent_device
    
    def resolve_variables(self, text: str) -> str:
        """
        Resolve DEVICE:VARIABLE patterns at runtime.
        
        Example:
          FGT_A:CUSTOMSIG1 → custom1on1801F
          PC_05:IP_ETH1 → 172.16.200.55
        
        Resolution order:
          1. Exact match (PASSWORD)
          2. Lowercase match (password)
          3. Uppercase match (PASSWORD)
          4. Keep original if not found
        """
        pattern = r'([A-Z][A-Z0-9_]*):([A-Za-z][A-Za-z0-9_]*)'
        
        def replace_match(match):
            device = match.group(1)
            var = match.group(2)
            
            if device in self._env_config:
                device_config = self._env_config[device]
                # Three-tier case-insensitive lookup
                if var in device_config:
                    return device_config[var]
                elif var.lower() in device_config:
                    return device_config[var.lower()]
                elif var.upper() in device_config:
                    return device_config[var.upper()]
            
            return f"{device}:{var}"  # Keep original
        
        return re.sub(pattern, replace_match, text)
```

#### 2. **FluentDevice** (Device Operations Wrapper)

```python
class FluentDevice:
    def __init__(self, device, result_manager, testbed=None):
        self.device = device
        self.results = result_manager
        self.testbed = testbed
        self._last_output = ""
    
    @resolve_command_vars  # ← Decorator resolves variables automatically
    def execute(self, command: str):
        """Execute command (variables already resolved by decorator)"""
        self._last_output = self.device.execute(command)
        return OutputAssertion(self._last_output, self.results, self)
    
    @resolve_command_vars
    def config(self, config_block: str):
        """Execute configuration block (variables already resolved)"""
        self.device.execute(config_block)
        return self
    
    @resolve_command_vars
    def raw_execute(self, command: str) -> str:
        """Direct execution (variables already resolved)"""
        return self.device.execute(command)
```

#### 3. **@resolve_command_vars Decorator** (Universal Variable Resolution)

```python
def resolve_command_vars(func):
    """
    Decorator to automatically resolve DEVICE:VARIABLE patterns
    in ALL string parameters before method execution.
    
    Applied to: execute(), config(), raw_execute()
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'testbed') and self.testbed:
            # Resolve variables in positional string arguments
            resolved_args = [
                self.testbed.resolve_variables(arg) if isinstance(arg, str) else arg
                for arg in args
            ]
            
            # Resolve variables in keyword string arguments
            resolved_kwargs = {
                key: self.testbed.resolve_variables(value) if isinstance(value, str) else value
                for key, value in kwargs.items()
            }
            
            return func(self, *resolved_args, **resolved_kwargs)
        else:
            return func(self, *args, **kwargs)
    
    return wrapper
```

**Why Decorator?**
- **Universal**: Works across ALL methods without repetition
- **Automatic**: No manual resolution calls needed
- **Maintainable**: Single location for variable resolution logic
- **Extensible**: Easy to add new methods with automatic resolution

#### 4. **OutputAssertion** (Fluent Assertions)

```python
class OutputAssertion:
    def __init__(self, output: str, result_manager, device):
        self.output = output
        self.results = result_manager
        self.device = device
    
    def expect(self, pattern: str, qaid: Optional[str] = None,
               timeout: int = 5, should_fail: bool = False):
        """
        Assert pattern in output.
        
        Args:
            pattern: String to search for in output
            qaid: Test QAID for result tracking
            should_fail: If True, pattern should NOT be in output
        
        Returns: device for chaining
        """
        found = pattern in self.output
        
        if should_fail:
            success = not found
            msg = f"Pattern '{pattern}' should NOT be in output"
        else:
            success = found
            msg = f"Pattern '{pattern}' should be in output"
        
        if qaid:
            self.results.add_qaid(qaid, success, self.output, msg)
        
        if not success:
            raise AssertionError(f"{msg}\nOutput:\n{self.output}")
        
        return self.device  # Enable chaining
```

**Method Chaining Example**:
```python
fgt_a.execute("show ips custom").expect("match small", qaid="205812")
#      └─ Returns OutputAssertion
#                               └─ Returns FluentDevice for further chaining
```

#### 5. **ResultManager** (QAID Tracking)

```python
class ResultManager:
    def __init__(self):
        self.results = {}  # {qaid: [assertions]}
        self.qaids = []
    
    def add_qaid(self, qaid: str, success: bool, output: str, message: str):
        """Record assertion result"""
        if qaid not in self.results:
            self.results[qaid] = []
        
        self.results[qaid].append({
            'success': success,
            'output': output,
            'message': message
        })
    
    def report(self, qaid: str):
        """Finalize and report QAID results"""
        all_passed = all(r['success'] for r in self.results[qaid])
        
        print(f"\n{'='*60}")
        print(f"QAID {qaid}: {'PASS' if all_passed else 'FAIL'}")
        print(f"{'='*60}")
        
        for i, result in enumerate(self.results[qaid], 1):
            print(f"  Step {i}: {'✓' if result['success'] else '✗'} {result['message']}")
        
        if not all_passed:
            raise AssertionError(f"QAID {qaid} failed")
```

---

## Environment Integration

### Environment File Format

**env.fortistack.ips.conf**:
```ini
[GLOBAL]
VERSION: 7.0

[PC_05]
CONNECTION: ssh -t fosqa@10.6.30.55 sudo -s
USERNAME: fosqa
PASSWORD: Qa123456!
IP_ETH1: 172.16.200.55
SCRIPT: /home/tester/attack_scripts

[FGT_A]
CONNECTION: telnet 0.0.0.0 11023
Model: FGVM
USERNAME: admin
PASSWORD: admin
CUSTOMSIG1: custom1on1801F
CUSTOMSIG2: custom2on1801F
```

### Environment Loading (conftest.py)

```python
from env_parser import parse_env_file

ENV_FILE = r'/path/to/env.fortistack.ips.conf'

@pytest.fixture
def testbed():
    """TestBed fixture with environment configuration"""
    # Load environment from file
    env_config = parse_env_file(ENV_FILE)
    
    # Create TestBed with configuration
    tb = TestBed(devices=env_config, use_mock=True)
    
    yield tb
    
    # Cleanup (if needed)
```

### Variable Resolution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Test Execution                                            │
│    fgt_a.execute("exe backup ... FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 ...") │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Decorator Intercepts                                      │
│    @resolve_command_vars triggers before execute()          │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Resolve Variables                                         │
│    self.testbed.resolve_variables(command)                   │
│                                                              │
│    Pattern: ([A-Z][A-Z0-9_]*):([A-Za-z][A-Za-z0-9_]*)       │
│                                                              │
│    Matches:                                                  │
│      - FGT_A:CUSTOMSIG1 → lookup in self._env_config['FGT_A']['CUSTOMSIG1'] │
│        → "custom1on1801F"                                    │
│                                                              │
│      - PC_05:IP_ETH1 → lookup in self._env_config['PC_05']['IP_ETH1'] │
│        → "172.16.200.55"                                     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Execute with Resolved Command                             │
│    device.execute("exe backup ... custom1on1801F 172.16.200.55 ...") │
└─────────────────────────────────────────────────────────────┘
```

---

## Example Walkthrough

Let's trace the complete conversion of QAID 205812.

### Input DSL (Excerpt)

```dsl
[FGT_A]
    comment REGR_IPS_02_01:Busy: create custom signatures
    config ips custom
        edit "match small"
            set signature "F-SBID( --name \"match small\"; ...)"
        next
    end
    show ips custom
    expect -e "match small" -for 205812 -t 5
    exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD

[PC_05]
    cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2
    expect -e "differ" -fail match -for 205812
    report 205812
```

### Step 1: Parse Test File

```python
parsed = {
    'qaid': '205812',
    'title': 'IPS Regression Test Case 2.1',
    'sections': [
        {
            'device': 'FGT_A',
            'commands': [
                'comment REGR_IPS_02_01:Busy: ...',
                'config ips custom',
                '    edit "match small"',
                '        set signature "..."',
                '    next',
                'end',
                'show ips custom',
                'expect -e "match small" -for 205812 -t 5',
                'exe backup ... FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 ...'
            ]
        },
        {
            'device': 'PC_05',
            'commands': [
                'cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2',
                'expect -e "differ" -fail match -for 205812',
                'report 205812'
            ]
        }
    ]
}
```

### Step 2: Group Commands

**FGT_A Section**:
```python
blocks = [
    {'type': 'command', 'command': 'comment REGR_IPS_02_01:Busy: ...'},
    {'type': 'config_block', 'lines': ['config ips custom', 'edit "match small"', ..., 'end']},
    {'type': 'command', 'command': 'show ips custom'},
    {'type': 'expect', 'pattern': 'match small', 'should_fail': False},
    {'type': 'command', 'command': 'exe backup ... FGT_A:CUSTOMSIG1 ...'}
]
```

**PC_05 Section**:
```python
blocks = [
    {'type': 'command', 'command': 'cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2'},
    {'type': 'expect', 'pattern': 'differ', 'should_fail': True},
    {'type': 'command', 'command': 'report 205812'}
]
```

### Step 3: Convert Sections

**FGT_A → pytest**:
```python
with testbed.device('FGT_A') as fgt_a:
    fgt_a.execute("comment REGR_IPS_02_01:Busy: create custom signatures")
    fgt_a.execute("""
config ips custom
    edit "match small"
        set signature "F-SBID( --name \"match small\"; ...)"
    next
end
    """)
    fgt_a.execute("show ips custom").expect("match small", qaid="205812")
    fgt_a.execute("exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")
```

**PC_05 → pytest**:
```python
with testbed.device('PC_05') as pc_05:
    pc_05.execute("cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2").expect("differ", qaid="205812", should_fail=True)
    pc_05.execute("report 205812")
```

### Step 4: Generate Test Function

```python
def test_205812(testbed, setup_govdom1, cleanup_outvdom):
    """
    IPS Regression Test Case 2.1
    
    QAID: 205812
    """
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("comment REGR_IPS_02_01:Busy: create custom signatures")
        fgt_a.execute("""
    config ips custom
        edit "match small"
            set signature "F-SBID( --name \"match small\"; --attack_id 5835; ...)"
        next
    end
        """)
        fgt_a.execute("show ips custom").expect("match small", qaid="205812")
        fgt_a.execute("exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")
    
    with testbed.device('PC_05') as pc_05:
        pc_05.execute("cmp /root/FGT_A:CUSTOMSIG1 /root/FGT_A:CUSTOMSIG2").expect("differ", qaid="205812", should_fail=True)
        pc_05.execute("report 205812")

    # All assertions tracked under QAID 205812
    testbed.results.report("205812")
```

### Step 5: Runtime Execution

When pytest runs:

1. **conftest.py** loads env file:
   ```python
   env_config = parse_env_file('/path/to/env.fortistack.ips.conf')
   # Returns: {'FGT_A': {'CUSTOMSIG1': 'custom1on1801F', ...}, 'PC_05': {'IP_ETH1': '172.16.200.55', ...}}
   ```

2. **testbed fixture** creates TestBed:
   ```python
   tb = TestBed(devices=env_config, use_mock=True)
   tb._env_config = env_config
   ```

3. **execute() call** triggers decorator:
   ```python
   # Original call:
   fgt_a.execute("exe backup ipsuserdefsig ftp FGT_A:CUSTOMSIG1 PC_05:IP_ETH1 root PC_05:PASSWORD")
   
   # Decorator resolves to:
   fgt_a.execute("exe backup ipsuserdefsig ftp custom1on1801F 172.16.200.55 root Qa123456!")
   ```

4. **Assertion tracking**:
   ```python
   .expect("match small", qaid="205812")
   # → ResultManager.add_qaid("205812", True, output, msg)
   ```

5. **Final report**:
   ```python
   testbed.results.report("205812")
   # → Prints summary and raises AssertionError if any assertion failed
   ```

---

## Current Limitations

### 1. **FluentAPI is Prototype Implementation** ⚠️

**Current State**:
- FluentAPI reimplements execute(), expect(), report() logic
- Does not leverage AutoLib v3's executor infrastructure
- Mock devices only, limited production readiness

**Required**: Full integration with AutoLib v3 Executor
- See [FLUENT_API_EXECUTOR_INTEGRATION.md](FLUENT_API_EXECUTOR_INTEGRATION.md) for architecture
- FluentAPI should be thin wrapper → Executor → API Registry
- Reuse 100% of battle-tested AutoLib v3 code

**Impact**: Current prototype works for testing transpiler logic, but production deployment requires executor integration.

---

### 2. **Complex Control Flow**

**Not Supported**:
```dsl
if [ "$status" == "up" ]; then
    show system status
fi
```

**Workaround**: Use Python control flow in pytest (though DSL rarely uses this)

---

### 3. **Nested Includes**

**Partial Support**:
- First-level includes → converted to fixtures
- Nested includes (include within include) → not yet handled

**Future Enhancement**: Recursive include resolution

---

### 4. **Variable Expressions**

**Not Supported**:
```dsl
set address ${PC_05:IP_ETH1}/24
```

**Current Support**: Only `DEVICE:VARIABLE` replacement
**Future Enhancement**: Expression evaluation, string concatenation

---

### 5. **Dynamic Device Discovery**

**Current**: All devices declared in env file
**Not Supported**: Runtime device discovery or creation

---

### 6. **Parallel Execution**

**Current**: Sequential device operations
**Future Enhancement**: Parallel command execution across devices using threading/async

---

## Future Enhancements

### 1. **Executor Integration** 🔴 HIGH PRIORITY

**Objective**: Replace prototype FluentAPI with production-ready implementation leveraging AutoLib v3 executor

**Architecture**:
```
pytest → FluentAPI (thin wrapper) → Executor → API Registry → API Functions
                                                            → Device Layer
                                                            → Services/Utilities
```

**Benefits**:
- ✅ 100% code reuse from AutoLib v3
- ✅ Battle-tested device handling
- ✅ Production-ready result management (ScriptResultManager)
- ✅ Access to all executor APIs (50+ functions)
- ✅ Minimal FluentAPI code (~200 lines vs 1000+)

**See**: [FLUENT_API_EXECUTOR_INTEGRATION.md](FLUENT_API_EXECUTOR_INTEGRATION.md) for complete architecture and implementation plan

**Implementation Steps**:
1. Create `executor_adapter.py` - Executor wrapper for pytest
2. Update `TestBed` to use Executor instance
3. Update `FluentDevice` to delegate to executor APIs
4. Update `OutputAssertion` to use executor's expect API
5. Test with real devices
6. Remove prototype code

---

### 2. **Advanced Variable Resolution**

- **Expressions**: `${PC_05:IP_ETH1}/24`, `${FGT_A:PORT + 1}`
- **Defaults**: `${DEVICE:VAR:-default_value}`
- **Environment Variables**: `${ENV:HOME}`, `${ENV:USER}`

---

### 2. **Enhanced Assertion Types**

```python
# Regular expression matching
.expect_regex(r'Status:\s+up', qaid="205812")

# JSON validation
.expect_json('$.status', 'up', qaid="205812")

# Numeric comparisons
.expect_value_gt('cpu_usage', 50, qaid="205812")
```

---

### 3. **Parallel Execution**

```python
# Parallel device operations
async def test_205812_parallel(testbed):
    async with testbed.parallel() as p:
        p.device('FGT_A').execute("show ips custom")
        p.device('FGT_B').execute("show ips custom")
        p.device('FGT_C').execute("show ips custom")
    
    # All complete before proceeding
```

---

### 4. **Better Include Handling**

- **Nested Includes**: Recursive resolution
- **Parameterized Includes**: Pass variables to included files
- **Include Libraries**: Shared fixture repository

---

### 5. **IDE Integration**

- **Type Stubs**: `.pyi` files for better autocomplete
- **FluentAPI Plugin**: VSCode extension for DSL → pytest conversion hints
- **Live Preview**: Show generated pytest while editing DSL

---

### 6. **Test Data Management**

```python
# Load test data from YAML/JSON
@pytest.fixture
def test_data():
    return yaml.safe_load(Path('test_data_205812.yaml').read_text())

def test_205812(testbed, test_data):
    for signature in test_data['custom_signatures']:
        fgt_a.execute(f'config ips custom')
        fgt_a.execute(f'  edit "{signature["name"]}"')
        # ...
```

---

### 7. **Better Error Messages**

```python
# Current:
AssertionError: Pattern 'match small' should be in output

# Future:
AssertionError: Pattern 'match small' should be in output
Expected: 'match small'
Actual output (first 200 chars):
  Total query time is 0 wallclock secs
  IPS custom signatures:
    [ No custom signatures found ]
  
Diff (expected vs actual):
  - match small
  + No custom signatures found
```

---

### 8. **Real Device Support**

```python
# Integration with AutoLib v3
class AutoLibDevice:
    def __init__(self, connection_string):
        from lib.device import Device
        self.device = Device(connection_string)
    
    def execute(self, command: str) -> str:
        return self.device.send_line_get_output(command)

# Testbed factory
def create_testbed(env_file, use_mock=False):
    env_config = parse_env_file(env_file)
    
    if use_mock:
        return TestBed(devices=env_config, use_mock=True)
    else:
        # Real devices
        devices = {
            name: AutoLibDevice(config.get('CONNECTION'))
            for name, config in env_config.items()
        }
        return TestBed(devices=devices, use_mock=False)
```

---

## Summary

### What We Built

✅ **Direct DSL-to-pytest Transpiler**
- No VM, no bytecode
- Pure Python + pytest
- FluentAPI for readability

✅ **Comprehensive Conversion Rules**
- Device sections → context managers
- Commands → execute() calls
- Config blocks → triple-quoted strings
- Assertions → chained .expect()
- Includes → pytest fixtures

✅ **Runtime Variable Resolution**
- Decorator-based (@resolve_command_vars)
- DEVICE:VARIABLE pattern
- Case-insensitive lookup
- Environment file integration

✅ **pytest Integration**
- Standard pytest test functions
- Fixtures for setup/cleanup
- Result tracking (ResultManager)
- Human-readable output

✅ **Mock Device Support**
- Prototype testing without real devices
- Same FluentAPI interface
- Easy switch to real devices

---

### What We Did NOT Use

❌ **AutoLib v3 Compiler**
- `autotest.py compile` not used
- No VM bytecode generation
- No instruction set execution

❌ **Generated VM Code**
- DSL directly transpiled to pytest
- No intermediate bytecode representation

---

### Architecture Benefits

| Aspect | Direct Transpilation | VM-based Approach |
|--------|---------------------|-------------------|
| **Readability** | ✅ Human-readable Python | ❌ Opaque bytecode |
| **Debugging** | ✅ Standard Python tools | ❌ VM debugger needed |
| **pytest Integration** | ✅ Native | ⚠️ Custom integration |
| **Type Safety** | ✅ Type hints, mypy | ❌ Lost in bytecode |
| **IDE Support** | ✅ Autocomplete, navigation | ❌ Limited |
| **Extensibility** | ✅ Add methods easily | ⚠️ VM changes needed |
| **Learning Curve** | ✅ Standard Python | ⚠️ Learn VM model |

---

### Current Status

**Production Ready For**:
- Mock device testing (prototype validation)
- DSL syntax verification
- Test structure validation
- FluentAPI development and testing

**Needs Work For**:
- Real device execution (AutoLib v3 integration)
- Complex control flow (if/else, loops)
- Nested includes
- Advanced variable expressions

---

### Next Steps

1. **Review Generated Code**: Verify pytest scripts match DSL intent
2. **Identify Gaps**: Test cases that don't convert correctly
3. **Real Device Integration**: Connect FluentAPI to AutoLib v3 devices
4. **Extended Testing**: Run transpiled tests against real FortiGate devices
5. **Documentation**: User guide for test migration
6. **CI/CD Integration**: Automated transpilation in build pipeline

---

## References

**Implementation Files**:
- [tools/dsl_transpiler.py](tools/dsl_transpiler.py) - Main transpiler
- [tools/include_converter.py](tools/include_converter.py) - Include handling
- [tools/env_parser.py](tools/env_parser.py) - Environment parsing
- [fluent_api/fluent.py](fluent_api/fluent.py) - FluentAPI implementation
- [run_transpiler.py](run_transpiler.py) - CLI interface

**Documentation**:
- [TRANSPILER_USAGE.md](TRANSPILER_USAGE.md) - Usage guide
- [ENVIRONMENT_INTEGRATION.md](ENVIRONMENT_INTEGRATION.md) - Environment setup
- [DECORATOR_VARIABLE_RESOLUTION.md](DECORATOR_VARIABLE_RESOLUTION.md) - Variable resolution
- [DECORATOR_IMPLEMENTATION_SUMMARY.md](DECORATOR_IMPLEMENTATION_SUMMARY.md) - Decorator details

**Test Files**:
- [test_variable_resolution.py](test_variable_resolution.py) - Variable resolution tests
- [test_decorator_resolution.py](test_decorator_resolution.py) - Decorator tests
- [test_full_integration.sh](test_full_integration.sh) - Integration tests
- [output/test_205812.py](output_baseline/test_205812.py) - Generated pytest example

---

**Generated**: February 24, 2026
**Version**: 1.0 (Initial Documentation)
