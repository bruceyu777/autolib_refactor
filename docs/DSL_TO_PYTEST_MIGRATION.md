# DSL-to-pytest Migration Strategy & Fluent API Design

**Project**: Automated DSL Test Conversion with Readable Python API  
**Purpose**: Convert 200+ DSL test scripts to pytest while maintaining readability  
**Last Updated**: 2026-02-18

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [API Reusability Analysis](#api-reusability-analysis)
3. [Automated Conversion Strategy](#automated-conversion-strategy)
4. [Fluent API Design](#fluent-api-design)
5. [DSL Transpiler Architecture](#dsl-transpiler-architecture)
6. [Implementation Plan](#implementation-plan)
7. [Readability Comparison](#readability-comparison)
8. [Migration Tools](#migration-tools)

---

## Executive Summary

### Current Challenge

You have **200+ DSL test scripts** that are:
- ✅ **Very readable** (almost plain English)
- ✅ **Test-focused** (minimal boilerplate)
- ✅ **Battle-tested** (proven in production)
- ❌ **Hard to maintain** (custom DSL requires custom compiler)
- ❌ **Limited flexibility** (can't use Python libraries)

### Migration Goals

1. **Preserve readability** - Python tests should be as clear as DSL
2. **Automate conversion** - Don't manually rewrite 200+ tests
3. **Reuse APIs** - Leverage existing API implementations
4. **Progressive migration** - Convert incrementally, not all-at-once

### Proposed Solution: 3-Tier Approach

```
┌─────────────────────────────────────────────────────────────┐
│                  MIGRATION STRATEGY                         │
└─────────────────────────────────────────────────────────────┘

Tier 1: API Registry Reuse
├─ Keep AutoLib v3 API implementations
├─ Wrap in fluent Python interface
└─ 100% compatibility, zero rewrite

Tier 2: Automated Transpiler
├─ Parse DSL → Generate pytest
├─ VM codes as intermediate representation
├─ 80% automated conversion
└─ Manual touch-up for complex cases

Tier 3: Fluent API Layer
├─ Method chaining for readability
├─ Context managers for device switching
├─ Custom assertions for expect patterns
└─ DSL-like Python syntax
```

---

## API Reusability Analysis

### Question: Can AutoLib v3 APIs be Reused in Pure Python?

**Answer**: ✅ **YES** - with minimal adaptation

### How AutoLib v3 APIs Work

**Current Architecture** (DSL-based):

```
DSL Script (.txt)
    │
    ▼
Compiler → VM Codes
    │
    ▼
Executor → API Registry → API Function
    │                         │
    ▼                         ▼
Device Layer             [Python Function]
```

**API Registration**:
```python
# In lib/core/executor/executor.py
class Executor:
    def __init__(self):
        self.api_registry = {}
        self._discover_apis()
    
    def _discover_apis(self):
        """Auto-discover APIs from plugins/apis/"""
        # Scan plugins/apis/ directory
        # Import all .py files
        # Register functions with @api decorator
```

**Example API** (`plugins/apis/api_expect.py`):
```python
def expect(executor, params):
    """
    Wait for pattern in device output
    
    DSL: expect -e "pattern" -for Q001 -t 5
    """
    pattern = params.pattern
    qaid = params.qaid
    timeout = params.timeout
    
    # Execute expect on current device
    result = executor.cur_device.expect(pattern, timeout=timeout)
    
    # Record result
    executor.result_manager.add_qaid_result(qaid, result, ...)
```

### Reusability in Python/pytest

**Option 1: Direct API Reuse** (Minimal Change)

```python
# Keep API implementations as-is
# Create lightweight executor wrapper

class PyTestExecutor:
    """Lightweight executor for pytest (no DSL compilation)"""
    
    def __init__(self, env):
        self.env = env
        self.api_registry = {}
        self.cur_device = None
        self.result_manager = ResultManager(env)
        self._discover_apis()  # Same as AutoLib v3
    
    def call_api(self, api_name, **kwargs):
        """Call API by name"""
        if api_name in self.api_registry:
            # Convert kwargs to ApiParams object
            params = ApiParams(**kwargs)
            return self.api_registry[api_name](self, params)

# Usage in pytest
def test_ips_sensor(fgt_a):
    executor = PyTestExecutor(env)
    executor.cur_device = fgt_a
    
    # Call API directly
    executor.call_api('expect', 
                     pattern='os Windows',
                     qaid='205817',
                     timeout=5)
```

**Option 2: Fluent API Wrapper** (Recommended)

```python
# Wrap APIs in fluent interface
class FluentDevice:
    """Fluent API wrapper around device + executor"""
    
    def __init__(self, device, executor):
        self.device = device
        self.executor = executor
        self.executor.cur_device = device
    
    def execute(self, command):
        """Execute command on device"""
        self.device.execute(command)
        return self  # Enable chaining
    
    def expect(self, pattern, qaid=None, timeout=5, fail_on_match=False):
        """Call expect API"""
        self.executor.call_api('expect',
                              pattern=pattern,
                              qaid=qaid,
                              timeout=timeout,
                              fail_on_match=fail_on_match)
        return self  # Enable chaining
    
    def config(self, config_text):
        """Execute configuration block"""
        self.device.execute(config_text)
        return self

# Usage (fluent style)
def test_ips_sensor(fgt_a_fluent):
    (fgt_a_fluent
        .execute('show ips sensor sensor-temp')
        .expect('os Windows', qaid='205817', timeout=5)
        .execute('config ips sensor')
        .execute('delete "sensor-temp"')
        .execute('end')
        .expect('sensor-temp', qaid='205817', fail_on_match=True))
```

**Verdict**: ✅ **APIs are 100% reusable** with thin wrapper layer

---

## Automated Conversion Strategy

### Strategy 1: Direct DSL → Python (Naive)

**Problem**: Loses structure, hard to maintain

```python
# Generated code (ugly)
def test_205817(fgt_a):
    fgt_a.execute("config ips sensor")
    fgt_a.execute('edit "sensor-temp"')
    fgt_a.execute('set comment "temp sensor for testing"')
    # ... 50 more lines
```

---

### Strategy 2: VM Codes → Python (Recommended)

**Advantage**: Reuse proven compilation logic

```
DSL Script (.txt)
    │
    ▼
[Existing Compiler]  ← Reuse!
    │
    ▼
VM Codes (structured)
    │
    ▼
[NEW: Transpiler]
    │
    ▼
pytest Test (.py)
```

**Why VM Codes?**

✅ **Already parsed** - Control flow resolved  
✅ **Validated** - Syntax checked  
✅ **Structured** - Clear operations + parameters  
✅ **Line numbers** - Preserve source context  
✅ **Proven** - Same compilation as production  

**VM Code Structure**:
```python
VMCode(
    line_number=25,
    operation='expect',
    parameters=('os Windows', 'Q205817', 5),
    comment='# Verify sensor created'
)
```

**Translation**:
```python
# VM Code → pytest
output = fgt_a.execute('show ips sensor sensor-temp')  # Previous execute
assert 'os Windows' in output  # expect → assertion
results.add_qaid('Q205817', 'os Windows' in output)
```

---

### Strategy 3: Hybrid Approach (Best)

**Combine**: VM codes for logic + Fluent API for readability

```
DSL → VM Codes → [Analyzer] → Python AST → Formatted pytest
                    │
                    ├─ Detect patterns
                    ├─ Group config blocks
                    └─ Generate fluent API calls
```

---

## Fluent API Design

### Goal: Make Python as Readable as DSL

**DSL Version** (Original):
```plaintext
[FGT_A]
    show ips sensor sensor-temp
    expect -e "os Windows" -for 205817 -t 5
    config ips sensor
        delete "sensor-temp"
    end
    expect -e "sensor-temp" -fail match -for 205817
    report 205817
```

**Python Version 1** (Naive - Not Readable):
```python
def test_205817(fgt_a, results):
    output = fgt_a.execute('show ips sensor sensor-temp')
    if 'os Windows' not in output:
        results.add_qaid('205817', False, output)
        pytest.fail('Pattern not found')
    else:
        results.add_qaid('205817', True, output)
    
    fgt_a.execute('config ips sensor')
    fgt_a.execute('delete "sensor-temp"')
    fgt_a.execute('end')
    
    output2 = fgt_a.execute('show ips sensor')
    if 'sensor-temp' in output2:
        results.add_qaid('205817', False, output2)
        pytest.fail('Sensor not deleted')
```

**Python Version 2** (Fluent API - Readable):
```python
def test_205817(fgt: FluentFortiGate):
    """
    IPS Regression Test Case 2.6
    Verify delete ips sensor in CLI
    QAID: 205817
    """
    with fgt.device('FGT_A'):
        # Create and verify IPS sensor
        (fgt
            .comment('REGR_IPS_02_04:Busy: create custom signatures')
            .include('testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt')
            .config('''
                config ips sensor
                    edit "sensor-temp"
                        set comment "temp sensor for testing"
                        config entries
                            edit "1"
                                set severity critical
                                set protocol TCP
                                set os Windows
                                set status enable
                            next
                        end
                    next
                end
            ''')
            .show('ips sensor sensor-temp')
            .expect('os Windows', qaid='205817', timeout=5)
        )
        
        # Delete sensor and verify
        (fgt
            .config('config ips sensor; delete "sensor-temp"; end')
            .clear_buffer()
            .show('ips sensor')
            .expect('sensor-temp', qaid='205817', should_fail=True)
            .include('testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt')
            .report('205817')
        )
```

**Python Version 3** (Context Manager - Ultra Readable):
```python
def test_205817(testbed):
    """IPS Regression Test Case 2.6 - Verify delete ips sensor in CLI"""
    
    with testbed.device('FGT_A') as fgt:
        # Setup: Create IPS sensor
        fgt.config.ips.sensor.create('sensor-temp', {
            'comment': 'temp sensor for testing',
            'entries': [{
                'id': 1,
                'severity': 'critical',
                'protocol': 'TCP',
                'os': 'Windows',
                'status': 'enable'
            }]
        })
        
        # Verify: Sensor created with correct OS
        fgt.show('ips sensor sensor-temp').should_contain('os Windows', qaid='205817')
        
        # Action: Delete sensor
        fgt.config.ips.sensor.delete('sensor-temp')
        
        # Verify: Sensor removed
        fgt.show('ips sensor').should_not_contain('sensor-temp', qaid='205817')
        
        # Report
        fgt.report('205817')
```

---

### Fluent API Design Patterns

#### Pattern 1: Method Chaining (Builder Pattern)

```python
class FluentFortiGate:
    """Fluent API for FortiGate testing"""
    
    def __init__(self, device, result_manager):
        self.device = device
        self.results = result_manager
        self._last_output = ""
    
    def execute(self, command):
        """Execute command and store output"""
        self._last_output = self.device.execute(command)
        return self  # Enable chaining
    
    def show(self, command):
        """Alias for execute with 'show' prefix"""
        return self.execute(f'show {command}')
    
    def config(self, config_block):
        """Execute configuration"""
        return self.execute(config_block)
    
    def expect(self, pattern, qaid=None, timeout=5, should_fail=False):
        """Assert pattern in last output"""
        found = pattern in self._last_output
        
        if should_fail:
            success = not found
        else:
            success = found
        
        if qaid:
            self.results.add_qaid(qaid, success, self._last_output)
        
        if not success:
            raise AssertionError(f"Pattern '{pattern}' {'found' if should_fail else 'not found'}")
        
        return self
    
    def clear_buffer(self):
        """Clear output buffer"""
        self._last_output = ""
        return self
    
    def comment(self, text):
        """Add comment (no-op for logging)"""
        import logging
        logging.info(f"# {text}")
        return self
    
    def report(self, qaid):
        """Report test completion"""
        self.results.report(qaid)
        return self
```

---

#### Pattern 2: Context Manager (Device Switching)

```python
class TestBed:
    """Test environment with device context management"""
    
    def __init__(self, env):
        self.env = env
        self.devices = {}
        self.result_manager = ResultManager(env)
    
    @contextmanager
    def device(self, name):
        """Context manager for device operations"""
        if name not in self.devices:
            # Create device from environment config
            conf = self.env.get_device_conf(name)
            dev = FortiGate(**conf)
            dev.connect()
            self.devices[name] = dev
        
        device = self.devices[name]
        fluent = FluentFortiGate(device, self.result_manager)
        
        yield fluent
        
        # Cleanup if needed

# Usage
def test_multi_device(testbed):
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.show('system status')
    
    with testbed.device('FGT_B') as fgt_b:
        fgt_b.show('system status')
```

---

#### Pattern 3: Assertion Helpers (should_* methods)

```python
class OutputAssertion:
    """Fluent assertions for command output"""
    
    def __init__(self, output, result_manager):
        self.output = output
        self.results = result_manager
    
    def should_contain(self, pattern, qaid=None):
        """Assert output contains pattern"""
        if pattern not in self.output:
            if qaid:
                self.results.add_qaid(qaid, False, self.output)
            raise AssertionError(f"'{pattern}' not in output:\n{self.output}")
        
        if qaid:
            self.results.add_qaid(qaid, True, self.output)
        return self
    
    def should_not_contain(self, pattern, qaid=None):
        """Assert output does not contain pattern"""
        if pattern in self.output:
            if qaid:
                self.results.add_qaid(qaid, False, self.output)
            raise AssertionError(f"'{pattern}' found in output:\n{self.output}")
        
        if qaid:
            self.results.add_qaid(qaid, True, self.output)
        return self
    
    def should_match(self, regex, qaid=None):
        """Assert output matches regex"""
        import re
        if not re.search(regex, self.output):
            if qaid:
                self.results.add_qaid(qaid, False, self.output)
            raise AssertionError(f"Pattern '{regex}' not matched")
        
        if qaid:
            self.results.add_qaid(qaid, True, self.output)
        return self

# Enhanced FluentFortiGate
class FluentFortiGate:
    def show(self, command):
        self._last_output = self.device.execute(f'show {command}')
        return OutputAssertion(self._last_output, self.results)

# Usage
fgt.show('system status').should_contain('FortiGate', qaid='Q001')
```

---

#### Pattern 4: Configuration DSL (Nested Builder)

```python
class ConfigBuilder:
    """Fluent configuration builder"""
    
    def __init__(self, device):
        self.device = device
        self.config = self
    
    @property
    def ips(self):
        return IPSConfig(self.device)
    
    @property
    def firewall(self):
        return FirewallConfig(self.device)

class IPSConfig:
    def __init__(self, device):
        self.device = device
        self.sensor = IPSSensorConfig(device)

class IPSSensorConfig:
    def __init__(self, device):
        self.device = device
    
    def create(self, name, settings):
        """Create IPS sensor"""
        config = f'''
        config ips sensor
            edit "{name}"
                set comment "{settings.get('comment', '')}"
        '''
        # Build configuration from nested dict
        # ...
        self.device.execute(config)
        return self
    
    def delete(self, name):
        """Delete IPS sensor"""
        config = f'''
        config ips sensor
            delete "{name}"
        end
        '''
        self.device.execute(config)
        return self

# Usage (DSL-like)
fgt.config.ips.sensor.create('sensor-temp', {
    'comment': 'temp sensor',
    'entries': [...]
})
```

---

## DSL Transpiler Architecture

### Component Design

```
┌─────────────────────────────────────────────────────────────┐
│              DSL-TO-PYTEST TRANSPILER                       │
└─────────────────────────────────────────────────────────────┘

Input: DSL Script (.txt)
    │
    ▼
┌────────────────┐
│ Phase 1:       │
│ Compile to VM  │  ← Reuse AutoLib v3 compiler
└────────┬───────┘
         │
         ▼
    VM Codes List
    [VMCode(1, 'switch_device', ('FGT_A',)),
     VMCode(2, 'execute', ('show system status',)),
     VMCode(3, 'expect', ('FortiGate', 'Q001', 5))]
         │
         ▼
┌────────────────┐
│ Phase 2:       │
│ Analyze & Group│  ← NEW: Pattern recognition
└────────┬───────┘
         │         • Group consecutive execute → config block
         │         • Detect expect patterns
         │         • Identify device switches
         │         • Recognize control flow
         ▼
    Structured Blocks
    [DeviceContext('FGT_A', [
        ConfigBlock([...]),
        ExpectAssertion(...),
        ...
     ])]
         │
         ▼
┌────────────────┐
│ Phase 3:       │
│ Generate Python│  ← NEW: Python code generator
└────────┬───────┘
         │         • Import statements
         │         • Test function
         │         • Fluent API calls
         │         • Assertions
         ▼
    Python AST
         │
         ▼
┌────────────────┐
│ Phase 4:       │
│ Format & Emit  │  ← Use black for formatting
└────────┬───────┘
         │
         ▼
Output: pytest Test (.py)
```

---

### Transpiler Implementation

**File**: `tools/dsl_transpiler.py`

```python
"""
DSL to pytest transpiler

Usage:
    python tools/dsl_transpiler.py testcase/ips/topology1/205817.txt
    
Output:
    tests/test_ips/test_205817.py
"""

import ast
from pathlib import Path
from typing import List
from lib.core.compiler.compiler import Compiler
from lib.core.vm_code import VMCode


class VMCodeAnalyzer:
    """Analyze VM codes and group into logical blocks"""
    
    def analyze(self, vm_codes: List[VMCode]):
        """Convert VM codes to structured blocks"""
        blocks = []
        i = 0
        
        while i < len(vm_codes):
            code = vm_codes[i]
            
            if code.operation == 'switch_device':
                # Device context block
                device_name = code.parameters[0]
                device_blocks = []
                i += 1
                
                # Collect all operations until next device switch
                while i < len(vm_codes) and vm_codes[i].operation != 'switch_device':
                    sub_block = self._analyze_block(vm_codes, i)
                    device_blocks.append(sub_block)
                    i = sub_block.end_index + 1
                
                blocks.append(DeviceContext(device_name, device_blocks))
            else:
                i += 1
        
        return blocks
    
    def _analyze_block(self, vm_codes, start_idx):
        """Analyze a single logical block"""
        code = vm_codes[start_idx]
        
        # Configuration block (multi-line config)
        if code.operation == 'execute' and 'config ' in code.parameters[0]:
            return self._group_config_block(vm_codes, start_idx)
        
        # Expect pattern
        if code.operation == 'expect':
            return ExpectBlock(code)
        
        # Single execution
        if code.operation == 'execute':
            return ExecuteBlock(code)
        
        # Include directive
        if code.operation == 'include':
            return IncludeBlock(code)
        
        return GenericBlock(code)
    
    def _group_config_block(self, vm_codes, start_idx):
        """Group consecutive config commands into one block"""
        config_lines = []
        i = start_idx
        
        # Collect until 'end' command
        while i < len(vm_codes):
            code = vm_codes[i]
            if code.operation == 'execute':
                cmd = code.parameters[0]
                config_lines.append(cmd)
                if cmd.strip() == 'end':
                    break
            i += 1
        
        return ConfigBlock(config_lines, end_index=i)


class PythonGenerator:
    """Generate pytest code from structured blocks"""
    
    def generate(self, blocks, test_name, description):
        """Generate Python AST and format as string"""
        # Build Python AST
        imports = self._generate_imports()
        test_func = self._generate_test_function(blocks, test_name, description)
        
        # Convert AST to source code
        module = ast.Module(body=[*imports, test_func], type_ignores=[])
        code = ast.unparse(module)
        
        # Format with black
        import black
        formatted = black.format_str(code, mode=black.FileMode())
        
        return formatted
    
    def _generate_imports(self):
        """Generate import statements"""
        return [
            ast.Import(names=[ast.alias(name='pytest', asname=None)]),
            ast.ImportFrom(
                module='fortios_test.fluent',
                names=[ast.alias(name='FluentFortiGate', asname=None)],
                level=0
            )
        ]
    
    def _generate_test_function(self, blocks, name, desc):
        """Generate test function AST"""
        # def test_205817(testbed):
        #     """Description"""
        #     ...
        
        body = [ast.Expr(value=ast.Constant(value=desc))]
        
        for block in blocks:
            if isinstance(block, DeviceContext):
                # with testbed.device('FGT_A') as fgt:
                context_body = []
                for sub_block in block.blocks:
                    context_body.extend(self._generate_block_code(sub_block))
                
                with_stmt = ast.With(
                    items=[
                        ast.withitem(
                            context_expr=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id='testbed', ctx=ast.Load()),
                                    attr='device',
                                    ctx=ast.Load()
                                ),
                                args=[ast.Constant(value=block.device_name)],
                                keywords=[]
                            ),
                            optional_vars=ast.Name(id='fgt', ctx=ast.Store())
                        )
                    ],
                    body=context_body
                )
                body.append(with_stmt)
        
        return ast.FunctionDef(
            name=f'test_{name}',
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg='testbed', annotation=None)],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            ),
            body=body,
            decorator_list=[],
            returns=None
        )
    
    def _generate_block_code(self, block):
        """Generate code for a block"""
        if isinstance(block, ConfigBlock):
            # fgt.config('''...''')
            config_text = '\n'.join(block.config_lines)
            return [
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='fgt', ctx=ast.Load()),
                            attr='config',
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value=config_text)],
                        keywords=[]
                    )
                )
            ]
        
        elif isinstance(block, ExpectBlock):
            # fgt.show('...').should_contain('pattern', qaid='Q001')
            # (Generated from previous execute + expect)
            pattern = block.vm_code.parameters[0]
            qaid = block.vm_code.parameters[1] if len(block.vm_code.parameters) > 1 else None
            
            return [
                ast.Expr(
                    value=ast.Call(
                        func=ast.Attribute(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id='fgt', ctx=ast.Load()),
                                    attr='show',
                                    ctx=ast.Load()
                                ),
                                args=[],
                                keywords=[]
                            ),
                            attr='should_contain',
                            ctx=ast.Load()
                        ),
                        args=[ast.Constant(value=pattern)],
                        keywords=[
                            ast.keyword(arg='qaid', value=ast.Constant(value=qaid))
                        ] if qaid else []
                    )
                )
            ]
        
        # ... more block types
        
        return []


class DSLTranspiler:
    """Main transpiler class"""
    
    def __init__(self):
        self.compiler = Compiler()
        self.analyzer = VMCodeAnalyzer()
        self.generator = PythonGenerator()
    
    def transpile_file(self, dsl_file: Path, output_file: Path = None):
        """Transpile a DSL file to pytest"""
        # Step 1: Compile DSL to VM codes (reuse existing compiler!)
        vm_codes = self.compiler.compile_file(str(dsl_file))
        
        # Step 2: Analyze VM codes
        blocks = self.analyzer.analyze(vm_codes)
        
        # Step 3: Extract test metadata
        test_name = dsl_file.stem  # 205817
        description = self._extract_description(dsl_file)
        
        # Step 4: Generate Python code
        python_code = self.generator.generate(blocks, test_name, description)
        
        # Step 5: Write output
        if output_file is None:
            output_file = Path(f'tests/test_{test_name}.py')
        
        output_file.write_text(python_code)
        print(f"Generated: {output_file}")
        
        return output_file
    
    def _extract_description(self, dsl_file):
        """Extract test description from comments"""
        with open(dsl_file) as f:
            lines = f.readlines()
        
        # Collect comment lines at top
        description = []
        for line in lines:
            if line.strip().startswith('#'):
                description.append(line.strip('# \n'))
            elif line.strip():
                break
        
        return '\n'.join(description)
    
    def batch_transpile(self, input_dir: Path, output_dir: Path):
        """Transpile all DSL files in a directory"""
        dsl_files = list(input_dir.glob('*.txt'))
        
        print(f"Found {len(dsl_files)} DSL files")
        
        for dsl_file in dsl_files:
            try:
                output_file = output_dir / f'test_{dsl_file.stem}.py'
                self.transpile_file(dsl_file, output_file)
            except Exception as e:
                print(f"Error transpiling {dsl_file}: {e}")


# Data structures
class DeviceContext:
    def __init__(self, device_name, blocks):
        self.device_name = device_name
        self.blocks = blocks

class ConfigBlock:
    def __init__(self, config_lines, end_index):
        self.config_lines = config_lines
        self.end_index = end_index

class ExpectBlock:
    def __init__(self, vm_code):
        self.vm_code = vm_code

class ExecuteBlock:
    def __init__(self, vm_code):
        self.vm_code = vm_code

class IncludeBlock:
    def __init__(self, vm_code):
        self.vm_code = vm_code

class GenericBlock:
    def __init__(self, vm_code):
        self.vm_code = vm_code


# CLI entrypoint
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python dsl_transpiler.py <dsl_file.txt>")
        sys.exit(1)
    
    transpiler = DSLTranspiler()
    
    input_path = Path(sys.argv[1])
    
    if input_path.is_file():
        transpiler.transpile_file(input_path)
    elif input_path.is_dir():
        output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('tests')
        transpiler.batch_transpile(input_path, output_dir)
```

---

## Include Directive Handling & Dependency Tracking

### Critical Requirement: Convert Includes First

**Problem**: DSL tests use `include` directives to reuse common code:

```plaintext
[FGT_A]
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    # ... test code ...
    include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
```

**Challenge**:
- ❌ Can't convert main test until includes are converted
- ❌ Same include used by 50+ tests - need to reuse fixture
- ❌ Includes may have nested includes (dependencies)
- ❌ Need to track what's already converted

---

### Solution: Dependency-First Conversion with Registry

```
┌─────────────────────────────────────────────────────────────┐
│         INCLUDE HANDLING STRATEGY                           │
└─────────────────────────────────────────────────────────────┘

Step 1: Scan for Dependencies
──────────────────────────────
Input: 205817.txt
Scan: Find all include directives
  - include testcase/.../govdom1.txt
  - include testcase/.../outvdom.txt

Build dependency tree:
  205817.txt
    ├── govdom1.txt
    │   └── (no nested includes)
    └── outvdom.txt
        └── (no nested includes)


Step 2: Convert Dependencies First (Bottom-Up)
────────────────────────────────────────────────
1. Check conversion registry
   - govdom1.txt already converted? 
     → YES: reuse fixture
     → NO: convert now

2. Convert govdom1.txt → conftest.py fixture
   ```python
   @pytest.fixture
   def setup_vdom_gov(fgt):
       """Enter government VDOM"""
       fgt.execute('config vdom')
       fgt.execute('edit vd1')
       return fgt
   ```

3. Record in registry:
   govdom1.txt → setup_vdom_gov (conftest.py:15)

4. Repeat for outvdom.txt


Step 3: Convert Main Test with Fixture Calls
──────────────────────────────────────────────
```python
def test_205817(testbed, setup_vdom_gov, cleanup_vdom):
    """IPS sensor deletion test"""
    with testbed.device('FGT_A') as fgt:
        # Original: include testcase/.../govdom1.txt
        # Converted: use setup_vdom_gov fixture
        
        # ... test code ...
        
        # Original: include testcase/.../outvdom.txt
        # Converted: use cleanup_vdom fixture
```
```

---

### Conversion Registry Design

**File**: `tools/.conversion_registry.json`

```json
{
  "version": "1.0",
  "conversions": {
    "testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt": {
      "type": "fixture",
      "fixture_name": "setup_vdom_gov",
      "fixture_file": "tests/conftest.py",
      "fixture_line": 15,
      "scope": "function",
      "converted_date": "2026-02-18T10:30:00",
      "hash": "a5f8c2e9d1b4...",
      "dependencies": [],
      "used_by": [
        "testcase/ips/topology1/205817.txt",
        "testcase/ips/topology1/205818.txt",
        "testcase/ips/topology1/300045.txt"
      ]
    },
    "testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt": {
      "type": "fixture",
      "fixture_name": "cleanup_vdom",
      "fixture_file": "tests/conftest.py",
      "fixture_line": 28,
      "scope": "function",
      "converted_date": "2026-02-18T10:31:00",
      "hash": "b7d9e3f1a2c6...",
      "dependencies": [],
      "used_by": [
        "testcase/ips/topology1/205817.txt",
        "testcase/ips/topology1/205818.txt"
      ]
    },
    "testcase/GLOBAL:VERSION/firewall/lib/create_address.txt": {
      "type": "helper",
      "helper_name": "create_firewall_address",
      "helper_file": "tests/helpers/firewall_helpers.py",
      "helper_line": 45,
      "converted_date": "2026-02-18T11:00:00",
      "hash": "c8e1f4g2b3d7...",
      "dependencies": [],
      "used_by": [
        "testcase/firewall/policy/100234.txt",
        "testcase/firewall/policy/100235.txt"
      ]
    }
  }
}
```

---

### Include Classification

**Type 1: Setup/Teardown Includes** → pytest fixtures

```plaintext
# DSL
[FGT_A]
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    # ... test code ...
    include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
```

**Convert to**:
```python
# tests/conftest.py
@pytest.fixture
def setup_vdom_gov(fgt):
    """Enter government VDOM - converted from govdom1.txt"""
    fgt.execute('config vdom')
    fgt.execute('edit vd1')
    yield fgt
    # No teardown in original include

@pytest.fixture
def cleanup_vdom(fgt):
    """Exit VDOM - converted from outvdom.txt"""
    yield fgt  # Teardown after test
    fgt.execute('end')  # Exit vdom context
```

**Usage**:
```python
def test_205817(testbed, setup_vdom_gov, cleanup_vdom):
    with testbed.device('FGT_A') as fgt:
        # include testcase/.../govdom1.txt → automatic via fixture
        
        # ... test code ...
        
        # include testcase/.../outvdom.txt → automatic via fixture
```

---

**Type 2: Reusable Actions** → helper functions

```plaintext
# DSL: testcase/GLOBAL:VERSION/firewall/lib/create_address.txt
config firewall address
    edit "$ADDR_NAME"
        set subnet $SUBNET
        set comment "$COMMENT"
    next
end
```

**Convert to**:
```python
# tests/helpers/firewall_helpers.py
def create_firewall_address(fgt, name, subnet, comment=""):
    """
    Create firewall address object
    Converted from: testcase/.../create_address.txt
    """
    config = f'''
    config firewall address
        edit "{name}"
            set subnet {subnet}
            set comment "{comment}"
        next
    end
    '''
    fgt.config(config)
    return name
```

**Usage**:
```python
from tests.helpers.firewall_helpers import create_firewall_address

def test_firewall_policy(testbed):
    with testbed.device('FGT_A') as fgt:
        # Original: include testcase/.../create_address.txt
        # Variables: strset $ADDR_NAME "TEST_ADDR"
        # Converted:
        addr = create_firewall_address(
            fgt, 
            name="TEST_ADDR",
            subnet="192.168.1.0/24",
            comment="Test address"
        )
```

---

**Type 3: Configuration Blocks** → fixtures with parameters

```plaintext
# DSL: testcase/lib/setup_ha.txt
# Setup HA between FGT_A and FGT_B
[FGT_A]
    config system ha
        set group-name "HA-CLUSTER"
        set priority 200
        set mode a-p
    end

[FGT_B]
    config system ha
        set group-name "HA-CLUSTER"
        set priority 100
        set mode a-p
    end
```

**Convert to**:
```python
# tests/conftest.py
@pytest.fixture
def ha_cluster(testbed):
    """
    Setup HA cluster with FGT_A (primary) and FGT_B (secondary)
    Converted from: testcase/lib/setup_ha.txt
    """
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.config('''
            config system ha
                set group-name "HA-CLUSTER"
                set priority 200
                set mode a-p
            end
        ''')
    
    with testbed.device('FGT_B') as fgt_b:
        fgt_b.config('''
            config system ha
                set group-name "HA-CLUSTER"
                set priority 100
                set mode a-p
            end
        ''')
    
    yield testbed
    
    # Teardown: disable HA
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.config('config system ha; set mode standalone; end')
    with testbed.device('FGT_B') as fgt_b:
        fgt_b.config('config system ha; set mode standalone; end')
```

---

### Enhanced Transpiler with Include Handling

**File**: `tools/dsl_transpiler.py` (updated)

```python
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set


class ConversionRegistry:
    """Track converted include files to enable reuse"""
    
    def __init__(self, registry_file='tools/.conversion_registry.json'):
        self.registry_file = Path(registry_file)
        self.registry = self._load_registry()
    
    def _load_registry(self) -> dict:
        """Load existing conversion registry"""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {"version": "1.0", "conversions": {}}
    
    def save(self):
        """Save registry to disk"""
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def get_conversion(self, include_path: str) -> dict:
        """Get existing conversion info for include file"""
        return self.registry['conversions'].get(include_path)
    
    def add_conversion(self, include_path: str, conversion_info: dict):
        """Record a new conversion"""
        self.registry['conversions'][include_path] = conversion_info
        self.save()
    
    def is_converted(self, include_path: str) -> bool:
        """Check if include file already converted"""
        return include_path in self.registry['conversions']
    
    def mark_usage(self, include_path: str, used_by: str):
        """Track which test uses this include"""
        if include_path in self.registry['conversions']:
            used_by_list = self.registry['conversions'][include_path].get('used_by', [])
            if used_by not in used_by_list:
                used_by_list.append(used_by)
                self.registry['conversions'][include_path]['used_by'] = used_by_list
                self.save()


class IncludeAnalyzer:
    """Analyze include dependencies in DSL files"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
    
    def find_includes(self, dsl_file: Path) -> List[str]:
        """Extract all include directives from DSL file"""
        includes = []
        with open(dsl_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith('include '):
                    include_path = line.replace('include ', '').strip()
                    includes.append(include_path)
        return includes
    
    def build_dependency_tree(self, dsl_file: Path) -> Dict[str, List[str]]:
        """Build dependency tree (recursive)"""
        dependencies = {}
        
        def collect_deps(file_path: Path, visited: Set[str] = None):
            if visited is None:
                visited = set()
            
            file_key = str(file_path)
            if file_key in visited:
                return  # Circular dependency
            
            visited.add(file_key)
            includes = self.find_includes(file_path)
            dependencies[file_key] = includes
            
            # Recursively collect nested includes
            for include in includes:
                include_full = self.workspace_root / include
                if include_full.exists():
                    collect_deps(include_full, visited)
        
        collect_deps(dsl_file)
        return dependencies
    
    def topological_sort(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """Sort files by dependency order (leaves first)"""
        from collections import deque
        
        # Build in-degree map
        in_degree = {file: 0 for file in dependencies}
        for deps in dependencies.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Start with files that have no dependencies
        queue = deque([f for f, deg in in_degree.items() if deg == 0])
        sorted_files = []
        
        while queue:
            file = queue.popleft()
            sorted_files.append(file)
            
            # Reduce in-degree for dependents
            for dep in dependencies.get(file, []):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
        
        return sorted_files


class IncludeConverter:
    """Convert include files to pytest fixtures/helpers"""
    
    def __init__(self, registry: ConversionRegistry, analyzer: IncludeAnalyzer):
        self.registry = registry
        self.analyzer = analyzer
        self.compiler = Compiler()
    
    def classify_include(self, include_file: Path) -> str:
        """Determine include type: fixture, helper, or config"""
        content = include_file.read_text()
        
        # Heuristics:
        # - If only one device and simple commands → fixture
        # - If uses variables extensively → helper function
        # - If sets up multiple devices → fixture with teardown
        
        if 'config vdom' in content and 'edit' in content:
            return 'fixture'  # VDOM setup
        elif content.count('[$') > 1:  # Multiple variable references
            return 'helper'
        else:
            return 'fixture'
    
    def convert_to_fixture(self, include_file: Path, fixture_name: str) -> str:
        """Convert include file to pytest fixture"""
        vm_codes = self.compiler.compile_file(str(include_file))
        
        # Generate fixture code
        fixture_code = f'''
@pytest.fixture
def {fixture_name}(fgt):
    """
    Auto-generated from: {include_file}
    """
'''
        
        # Convert VM codes to fixture body
        for vm_code in vm_codes:
            if vm_code.operation == 'execute':
                cmd = vm_code.parameters[0]
                fixture_code += f'    fgt.execute("{cmd}")\n'
        
        fixture_code += '    return fgt\n'
        
        return fixture_code
    
    def convert_to_helper(self, include_file: Path, helper_name: str) -> str:
        """Convert include file to helper function"""
        vm_codes = self.compiler.compile_file(str(include_file))
        
        # Extract parameters from variable usage
        variables = set()
        for vm_code in vm_codes:
            if vm_code.operation == 'execute':
                cmd = vm_code.parameters[0]
                # Simple regex to find $VAR patterns
                import re
                vars_found = re.findall(r'\$\w+', cmd)
                variables.update(vars_found)
        
        # Generate helper function
        params = ', '.join([v.strip('$').lower() for v in sorted(variables)])
        
        helper_code = f'''
def {helper_name}(fgt, {params}):
    """
    Auto-generated from: {include_file}
    Parameters: {', '.join(sorted(variables))}
    """
'''
        
        # Convert VM codes with variable substitution
        for vm_code in vm_codes:
            if vm_code.operation == 'execute':
                cmd = vm_code.parameters[0]
                # Replace $VAR with {var}
                for var in variables:
                    cmd = cmd.replace(var, '{' + var.strip('$').lower() + '}')
                helper_code += f'    fgt.execute(f"{cmd}")\n'
        
        return helper_code
    
    def convert_include(self, include_path: str, output_dir: Path) -> dict:
        """Convert include file and return conversion info"""
        include_file = self.analyzer.workspace_root / include_path
        
        if not include_file.exists():
            raise FileNotFoundError(f"Include file not found: {include_path}")
        
        # Check if already converted
        if self.registry.is_converted(include_path):
            print(f"  ✓ Already converted: {include_path}")
            return self.registry.get_conversion(include_path)
        
        # Classify include type
        include_type = self.classify_include(include_file)
        
        # Generate name
        fixture_name = self._generate_name(include_path, include_type)
        
        # Convert based on type
        if include_type == 'fixture':
            code = self.convert_to_fixture(include_file, fixture_name)
            target_file = output_dir / 'conftest.py'
            
            # Append to conftest.py
            with open(target_file, 'a') as f:
                f.write(f'\n{code}\n')
            
            conversion_info = {
                'type': 'fixture',
                'fixture_name': fixture_name,
                'fixture_file': str(target_file),
                'scope': 'function',
                'converted_date': self._get_timestamp(),
                'hash': self._calculate_hash(include_file),
                'dependencies': [],
                'used_by': []
            }
        
        elif include_type == 'helper':
            code = self.convert_to_helper(include_file, fixture_name)
            target_file = output_dir / 'helpers' / 'common_helpers.py'
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_file, 'a') as f:
                f.write(f'\n{code}\n')
            
            conversion_info = {
                'type': 'helper',
                'helper_name': fixture_name,
                'helper_file': str(target_file),
                'converted_date': self._get_timestamp(),
                'hash': self._calculate_hash(include_file),
                'dependencies': [],
                'used_by': []
            }
        
        # Record conversion
        self.registry.add_conversion(include_path, conversion_info)
        
        print(f"  ✓ Converted {include_type}: {include_path} → {fixture_name}")
        
        return conversion_info
    
    def _generate_name(self, include_path: str, include_type: str) -> str:
        """Generate fixture/helper name from include path"""
        # testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
        # → setup_govdom1 or govdom1_helper
        
        path_parts = Path(include_path).stem  # govdom1
        
        if include_type == 'fixture':
            if 'in' in path_parts or 'setup' in path_parts or 'enter' in path_parts:
                return f'setup_{path_parts}'
            elif 'out' in path_parts or 'cleanup' in path_parts or 'exit' in path_parts:
                return f'cleanup_{path_parts}'
            else:
                return f'fixture_{path_parts}'
        else:
            return f'{path_parts}_helper'
    
    def _get_timestamp(self) -> str:
        """Get ISO timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection"""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]


class DSLTranspiler:
    """Main transpiler with include handling"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.compiler = Compiler()
        self.analyzer = VMCodeAnalyzer()
        self.generator = PythonGenerator()
        
        # Include handling
        self.registry = ConversionRegistry()
        self.include_analyzer = IncludeAnalyzer(workspace_root)
        self.include_converter = IncludeConverter(self.registry, self.include_analyzer)
    
    def transpile_file(self, dsl_file: Path, output_file: Path = None):
        """Transpile DSL file with dependency resolution"""
        
        # Step 0: Convert includes first
        print(f"\nAnalyzing dependencies for {dsl_file.name}...")
        includes = self.include_analyzer.find_includes(dsl_file)
        
        if includes:
            print(f"  Found {len(includes)} include(s)")
            output_dir = output_file.parent if output_file else Path('tests')
            
            for include_path in includes:
                try:
                    self.include_converter.convert_include(include_path, output_dir)
                    self.registry.mark_usage(include_path, str(dsl_file))
                except Exception as e:
                    print(f"  ✗ Error converting include {include_path}: {e}")
        
        # Step 1-5: Normal transpilation (as before)
        vm_codes = self.compiler.compile_file(str(dsl_file))
        blocks = self.analyzer.analyze(vm_codes)
        test_name = dsl_file.stem
        description = self._extract_description(dsl_file)
        
        # Enhanced: inject fixture parameters
        fixture_params = self._get_fixture_params(includes)
        
        python_code = self.generator.generate(
            blocks, 
            test_name, 
            description,
            fixture_params=fixture_params
        )
        
        if output_file is None:
            output_file = Path(f'tests/test_{test_name}.py')
        
        output_file.write_text(python_code)
        print(f"✓ Generated: {output_file}")
        
        return output_file
    
    def _get_fixture_params(self, includes: List[str]) -> List[str]:
        """Get fixture parameter names for test function"""
        fixture_params = ['testbed']  # Always include testbed
        
        for include_path in includes:
            conversion = self.registry.get_conversion(include_path)
            if conversion and conversion['type'] == 'fixture':
                fixture_params.append(conversion['fixture_name'])
        
        return fixture_params
    
    def _extract_description(self, dsl_file):
        """Extract test description from comments"""
        with open(dsl_file) as f:
            lines = f.readlines()
        
        description = []
        for line in lines:
            if line.strip().startswith('#'):
                description.append(line.strip('# \n'))
            elif line.strip():
                break
        
        return '\n'.join(description)
    
    def batch_transpile(self, input_dir: Path, output_dir: Path):
        """Transpile all files with dependency resolution"""
        dsl_files = list(input_dir.glob('*.txt'))
        
        print(f"Found {len(dsl_files)} DSL files")
        print("Building dependency graph...")
        
        # Build complete dependency graph
        all_includes = set()
        for dsl_file in dsl_files:
            includes = self.include_analyzer.find_includes(dsl_file)
            all_includes.update(includes)
        
        print(f"Found {len(all_includes)} unique include file(s)")
        
        # Convert all includes first
        print("\nConverting include files...")
        for include_path in sorted(all_includes):
            try:
                self.include_converter.convert_include(include_path, output_dir)
            except Exception as e:
                print(f"  ✗ Error: {include_path}: {e}")
        
        # Now convert main test files
        print(f"\nConverting {len(dsl_files)} test files...")
        for dsl_file in dsl_files:
            try:
                output_file = output_dir / f'test_{dsl_file.stem}.py'
                self.transpile_file(dsl_file, output_file)
            except Exception as e:
                print(f"✗ Error transpiling {dsl_file}: {e}")
        
        print("\n" + "="*60)
        print("CONVERSION SUMMARY")
        print("="*60)
        print(f"Include files converted: {len(all_includes)}")
        print(f"Test files converted: {len(dsl_files)}")
        print(f"Registry saved to: {self.registry.registry_file}")
```

---

### Example: Test with Includes

**Original DSL**: `testcase/ips/topology1/205817.txt`

```plaintext
# IPS Regression Test Case 2.6
[FGT_A]
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    
    config ips sensor
        edit "sensor-temp"
            set os Windows
        next
    end
    
    show ips sensor sensor-temp
    expect -e "os Windows" -for 205817
    
    include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
    report 205817
```

**Include file**: `testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt`

```plaintext
# Enter government VDOM
config vdom
    edit vd1
```

**Include file**: `testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt`

```plaintext
# Exit VDOM
end
```

---

**Converted pytest**: `tests/test_ips/test_205817.py`

```python
"""
IPS Regression Test Case 2.6
Auto-generated from: testcase/ips/topology1/205817.txt
"""

import pytest
from fortios_test.fluent import FluentFortiGate, TestBed


def test_205817_delete_ips_sensor(testbed, setup_govdom1, cleanup_outvdom):
    """
    Test Steps:
    1. Enter government VDOM (via setup_govdom1 fixture)
    2. Create IPS sensor with Windows signature
    3. Verify sensor created
    4. Delete sensor
    5. Exit VDOM (via cleanup_outvdom fixture)
    
    Include dependencies:
    - testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt → setup_govdom1
    - testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt → cleanup_outvdom
    """
    
    with testbed.device('FGT_A') as fgt:
        # Original DSL: include testcase/.../govdom1.txt
        # Converted: Automatic via setup_govdom1 fixture
        
        # Create IPS sensor
        (fgt.config("""
            config ips sensor
                edit "sensor-temp"
                    set os Windows
                next
            end
        """))
        
        # Verify sensor created
        (fgt
            .execute("show ips sensor sensor-temp")
            .expect("os Windows", qaid="205817")
        )
        
        # Original DSL: include testcase/.../outvdom.txt
        # Converted: Automatic via cleanup_outvdom fixture (teardown)
        
        # Report
        fgt.report("205817")
```

**Generated fixtures**: `tests/conftest.py`

```python
import pytest
from fortios_test.fluent import TestBed


@pytest.fixture
def setup_govdom1(testbed):
    """
    Enter government VDOM
    Auto-generated from: testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    """
    fgt = testbed.get_device('FGT_A')
    fgt.execute("config vdom")
    fgt.execute("edit vd1")
    return fgt


@pytest.fixture
def cleanup_outvdom(testbed):
    """
    Exit VDOM context
    Auto-generated from: testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
    """
    yield testbed  # Run test first
    
    # Teardown after test
    fgt = testbed.get_device('FGT_A')
    fgt.execute("end")
```

---

### Conversion Registry Output

After converting test 205817:

```json
{
  "version": "1.0",
  "conversions": {
    "testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt": {
      "type": "fixture",
      "fixture_name": "setup_govdom1",
      "fixture_file": "tests/conftest.py",
      "fixture_line": 15,
      "scope": "function",
      "converted_date": "2026-02-23T14:30:00",
      "hash": "a5f8c2e9d1b4f7a3",
      "dependencies": [],
      "used_by": [
        "testcase/ips/topology1/205817.txt"
      ]
    },
    "testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt": {
      "type": "fixture",
      "fixture_name": "cleanup_outvdom",
      "fixture_file": "tests/conftest.py",
      "fixture_line": 28,
      "scope": "function",
      "converted_date": "2026-02-23T14:30:01",
      "hash": "b7d9e3f1a2c6d8e5",
      "dependencies": [],
      "used_by": [
        "testcase/ips/topology1/205817.txt"
      ]
    }
  }
}
```

**Next conversion** (test 205818.txt using same includes):

```
Analyzing dependencies for 205818.txt...
  Found 2 include(s)
  ✓ Already converted: testcase/.../govdom1.txt (reusing setup_govdom1)
  ✓ Already converted: testcase/.../outvdom.txt (reusing cleanup_outvdom)
✓ Generated: tests/test_ips/test_205818.py
```

Registry updated:
```json
{
  "testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt": {
    ...
    "used_by": [
      "testcase/ips/topology1/205817.txt",
      "testcase/ips/topology1/205818.txt"  // ← Added
    ]
  }
}
```

---

### Benefits of Include Tracking

✅ **Reusability**: Convert common includes once, reuse 50+ times  
✅ **Consistency**: Same include → same fixture across all tests  
✅ **Traceability**: Know which tests depend on which fixtures  
✅ **Change detection**: Hash tracking detects when includes change  
✅ **Dependency resolution**: Automatic bottom-up conversion order  
✅ **Avoid duplication**: Registry prevents re-converting same file  

---

## Implementation Plan

### Phase 1: Fluent API Layer (2 weeks)

**Week 1: Core Fluent API**
- [ ] Create `fortios_test/fluent.py`
- [ ] Implement `FluentFortiGate` class
  - [ ] Method chaining (execute, show, config)
  - [ ] Expect assertions (should_contain, should_not_contain)
  - [ ] Buffer management (clear_buffer)
- [ ] Implement `TestBed` class
  - [ ] Device context managers
  - [ ] Result management integration
- [ ] Write unit tests for fluent API

**Week 2: Enhanced Features**
- [ ] Configuration builders (config.ips.sensor, config.firewall.policy)
- [ ] Assertion helpers (OutputAssertion class)
- [ ] Include directive support (placeholder/comment generation)
- [ ] Comment/logging integration
- [ ] Documentation and examples

**Deliverables**:
- `fortios_test/fluent.py` - Fluent API implementation
- `tests/test_fluent_api.py` - Unit tests
- `docs/FLUENT_API_GUIDE.md` - Usage documentation

---

### Phase 2: Include Handling & Registry (2 weeks)

**Week 1: Conversion Registry**
- [ ] Create `tools/conversion_registry.py`
- [ ] Implement ConversionRegistry class
  - [ ] Load/save JSON registry
  - [ ] Track converted fixtures/helpers
  - [ ] Mark usage (which tests use which includes)
  - [ ] Hash-based change detection
- [ ] Implement IncludeAnalyzer
  - [ ] Extract include directives from DSL
  - [ ] Build dependency tree (recursive)
  - [ ] Topological sort (dependency order)
  - [ ] Detect circular dependencies
- [ ] Write unit tests

**Week 2: Include Conversion**
- [ ] Implement IncludeConverter
  - [ ] Classify includes (fixture vs helper vs config)
  - [ ] Convert to pytest fixture (setup/teardown)
  - [ ] Convert to helper function (parameterized)
  - [ ] Extract variables from includes
  - [ ] Generate conftest.py fixtures
  - [ ] Generate helper modules
- [ ] Integration with main transpiler
- [ ] Write tests for include conversion

**Deliverables**:
- `tools/conversion_registry.py` - Registry implementation
- `tools/include_converter.py` - Include conversion logic
- `tools/.conversion_registry.json` - Tracking database
- `tests/test_include_conversion.py` - Include conversion tests

---

### Phase 3: DSL Transpiler (3 weeks)

**Week 1: VM Code Analysis**
- [ ] Create `tools/dsl_transpiler/analyzer.py`
- [ ] Implement VMCodeAnalyzer
  - [ ] Device context detection
  - [ ] Config block grouping
  - [ ] Expect pattern recognition
  - [ ] Control flow detection (if/while)
  - [ ] Include block identification
- [ ] Write tests for analyzer

**Week 2: Python Code Generation**
- [ ] Create `tools/dsl_transpiler/generator.py`
- [ ] Implement PythonGenerator
  - [ ] AST generation for test functions
  - [ ] Import statement generation
  - [ ] Fluent API call generation
  - [ ] Assertion generation
  - [ ] **Fixture parameter injection** (from include conversion)
  - [ ] **Include comment preservation**
- [ ] Integrate black formatter
- [ ] Write tests for generator

**Week 3: Integration & Testing**
- [ ] Create `tools/dsl_transpiler.py` (main entry point)
- [ ] **Integrate include handling** (dependency resolution)
- [ ] Implement batch conversion with include tracking
- [ ] Manual review of 10 generated tests (including fixtures)
- [ ] Refinement based on review
- [ ] CLI tool creation

**Deliverables**:
- `tools/dsl_transpiler.py` - Complete transpiler with include handling
- `tests/test_transpiler.py` - Transpiler tests
- `docs/DSL_TRANSPILER_GUIDE.md` - Usage guide
- `tools/.conversion_registry.json` - Include conversion tracking

---

### Phase 4: Migration & Validation (2 weeks)

**Week 1: Include Files Conversion**
- [ ] Scan all DSL tests for unique includes
- [ ] Build complete dependency graph
- [ ] Convert all include files to fixtures/helpers
  ```bash
  python tools/convert_includes.py testcase/ tests/
  ```
- [ ] Verify fixture correctness (sample 10 includes)
- [ ] Update registry with all conversions

**Week 2: Batch Test Conversion**
- [ ] Convert all 200+ DSL tests to pytest
  ```bash
  python tools/dsl_transpiler.py testcase/ips/topology1/ tests/test_ips/
  ```
- [ ] Verify fixture reuse (check registry usage counts)
- [ ] Manual review of generated tests (sample 20 tests)
- [ ] Fix common conversion issues
- [ ] Update transpiler based on findings

**Deliverables**:
- All include files converted to fixtures/helpers
- 200+ pytest test files in `tests/test_ips/`
- Populated conversion registry
- conftest.py with all fixtures

---

### Phase 5: Validation & Refinement (2 weeks)

**Week 1: Execution Validation**
- [ ] Run converted pytest tests against testbed
- [ ] Compare results: DSL execution vs pytest execution
- [ ] Fix discrepancies
- [ ] Document migration issues and solutions

**Week 2: Optimization & Cleanup**
- [ ] Review fixture scopes (function vs module vs session)
- [ ] Consolidate duplicate fixtures
- [ ] Optimize fixture dependencies
- [ ] Performance comparison

**Deliverables**:
- Migration report (success rate, issues found)
- Validation results (DSL vs pytest comparison)
- Updated documentation

---

### Phase 6: Documentation & Training (1 week)

- [ ] Write comprehensive documentation
  - [ ] Fluent API guide
  - [ ] Transpiler usage guide
  - [ ] Migration best practices
- [ ] Create example tests showing both approaches
- [ ] Team training session
- [ ] Create quick reference guide

---

## Readability Comparison

### Example: Test 205817 (IPS Sensor Delete)

#### Original DSL (Baseline - 100% Readability)

```plaintext
[FGT_A]
    comment REGR_IPS_02_04:Busy: create custom signatures
    include testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
    config ips sensor
        edit "sensor-temp"
            set comment "temp sensor for testing"
            config entries
                edit "1"
                    set severity critical
                    set protocol TCP
                    set os Windows
                next
            end
        next
    end
    show ips sensor sensor-temp
    expect -e "os Windows" -for 205817 -t 5
    config ips sensor
        delete "sensor-temp"
    end
    show ips sensor
    expect -e "sensor-temp" -fail match -for 205817
    report 205817
```

**Readability Score**: ⭐⭐⭐⭐⭐ (5/5)
- Almost plain English
- Minimal syntax noise
- Test logic is clear

---

#### Naive Python (40% Readability)

```python
def test_205817(fgt_a, results):
    fgt_a.execute('config ips sensor')
    fgt_a.execute('edit "sensor-temp"')
    fgt_a.execute('set comment "temp sensor for testing"')
    fgt_a.execute('config entries')
    fgt_a.execute('edit "1"')
    fgt_a.execute('set severity critical')
    fgt_a.execute('set protocol TCP')
    fgt_a.execute('set os Windows')
    fgt_a.execute('next')
    fgt_a.execute('end')
    fgt_a.execute('next')
    fgt_a.execute('end')
    
    output1 = fgt_a.execute('show ips sensor sensor-temp')
    assert 'os Windows' in output1
    results.add_qaid('205817', True, output1)
    
    fgt_a.execute('config ips sensor')
    fgt_a.execute('delete "sensor-temp"')
    fgt_a.execute('end')
    
    output2 = fgt_a.execute('show ips sensor')
    assert 'sensor-temp' not in output2
    results.add_qaid('205817', True, output2)
```

**Readability Score**: ⭐⭐ (2/5)
- Very verbose
- Repetitive execute() calls
- Test logic obscured by syntax

---

#### Fluent API (85% Readability)

```python
def test_205817_delete_ips_sensor(testbed):
    """
    IPS Regression Test Case 2.6
    Verify delete ips sensor in CLI
    """
    with testbed.device('FGT_A') as fgt:
        # Create IPS sensor with Windows signature
        (fgt
            .comment('REGR_IPS_02_04:Busy: create custom signatures')
            .include('testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt')
            .config('''
                config ips sensor
                    edit "sensor-temp"
                        set comment "temp sensor for testing"
                        config entries
                            edit "1"
                                set severity critical
                                set protocol TCP
                                set os Windows
                            next
                        end
                    next
                end
            ''')
        )
        
        # Verify sensor created
        (fgt
            .show('ips sensor sensor-temp')
            .should_contain('os Windows', qaid='205817', timeout=5)
        )
        
        # Delete sensor
        (fgt
            .config('config ips sensor; delete "sensor-temp"; end')
        )
        
        # Verify sensor deleted
        (fgt
            .show('ips sensor')
            .should_not_contain('sensor-temp', qaid='205817')
        )
        
        # Report
        fgt.report('205817')
```

**Readability Score**: ⭐⭐⭐⭐ (4/5)
- Clear structure
- Method chaining reduces noise
- Test logic is visible
- Close to DSL readability

---

#### Structured Builder (90% Readability)

```python
def test_205817_delete_ips_sensor(testbed):
    """IPS Regression Test Case 2.6 - Verify delete ips sensor in CLI"""
    
    with testbed.device('FGT_A') as fgt:
        # Create sensor
        sensor = fgt.config.ips.sensor('sensor-temp')
        sensor.set('comment', 'temp sensor for testing')
        sensor.entry(1).set({
            'severity': 'critical',
            'protocol': 'TCP',
            'os': 'Windows'
        })
        sensor.apply()
        
        # Verify created
        fgt.show.ips.sensor('sensor-temp').expect('os Windows', qaid='205817')
        
        # Delete sensor
        fgt.config.ips.sensor('sensor-temp').delete()
        
        # Verify deleted
        fgt.show.ips.sensors().expect_not('sensor-temp', qaid='205817')
        
        # Report
        testbed.report('205817')
```

**Readability Score**: ⭐⭐⭐⭐⭐ (5/5)
- Most readable Python version
- Domain-specific language feel
- Natural object hierarchy
- Requires most development effort

---

### Readability Analysis

| Approach | Readability | Development Effort | Flexibility |
|----------|-------------|-------------------|-------------|
| **DSL (Original)** | ⭐⭐⭐⭐⭐ | N/A (existing) | ⭐⭐ |
| **Naive Python** | ⭐⭐ | ⭐ (low) | ⭐⭐⭐⭐⭐ |
| **Fluent API** | ⭐⭐⭐⭐ | ⭐⭐⭐ (medium) | ⭐⭐⭐⭐ |
| **Structured Builder** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (high) | ⭐⭐⭐ |

**Recommendation**: Use **Fluent API** approach
- Good balance of readability and effort
- Automated transpiler can generate this style
- Extensible for future enhancements

---

## Migration Tools

### Tool 1: DSL Transpiler CLI

```bash
# Single file conversion
python tools/dsl_transpiler.py testcase/ips/topology1/205817.txt

# Batch conversion (directory)
python tools/dsl_transpiler.py testcase/ips/topology1/ tests/test_ips/

# With options
python tools/dsl_transpiler.py \
    --input testcase/ips/topology1/ \
    --output tests/test_ips/ \
    --style fluent \
    --format black \
    --validate
```

---

### Tool 2: Validation Tool

**Compare DSL vs pytest execution**:

```bash
# Run same test in both modes
python tools/validate_migration.py 205817

# Output:
# Running DSL version...  PASSED (3 QAIDs)
# Running pytest version... PASSED (3 QAIDs)
# ✓ Results match
```

**Implementation**:
```python
def validate_migration(test_id):
    # Run DSL version
    dsl_results = run_dsl_test(f'testcase/ips/topology1/{test_id}.txt')
    
    # Run pytest version
    pytest_results = run_pytest(f'tests/test_ips/test_{test_id}.py')
    
    # Compare
    if dsl_results == pytest_results:
        print("✓ Results match")
    else:
        print("✗ Results differ:")
        print(f"  DSL: {dsl_results}")
        print(f"  pytest: {pytest_results}")
```

---

### Tool 3: Include Registry Inspector

**View converted includes and their usage**:

```bash
python tools/inspect_registry.py

# Output:
# Conversion Registry Report
# ===========================
# Total conversions: 23
#
# Most-used includes:
#   1. govdom1.txt → setup_govdom1 (used by 87 tests)
#   2. outvdom.txt → cleanup_outvdom (used by 87 tests)
#   3. create_address.txt → create_firewall_address (used by 45 tests)
#
# Fixture summary:
#   - 18 fixtures in conftest.py
#   - 5 helper functions in helpers/
#
# Coverage:
#   - Converted: 23/25 unique includes (92%)
#   - Pending: 2 includes (complex control flow)
```

**Show which tests use a specific include**:
```bash
python tools/inspect_registry.py --include govdom1.txt

# Output:
# Include: testcase/GLOBAL:VERSION/ips/topology1/govdom1.txt
# Converted to: setup_govdom1 (fixture)
# Location: tests/conftest.py:15
# Hash: a5f8c2e9d1b4f7a3
# Converted: 2026-02-23T14:30:00
#
# Used by 87 tests:
#   - testcase/ips/topology1/205817.txt
#   - testcase/ips/topology1/205818.txt
#   - testcase/ips/topology1/300045.txt
#   ...
```

---

### Tool 4: Coverage Analyzer

**Identify which DSL features are used**:

```bash
python tools/analyze_dsl_usage.py testcase/ips/topology1/

# Output:
# DSL Feature Usage Analysis
# ==========================
# Total files: 234
#
# Features used:
#   config blocks:       234 (100%)
#   expect:              198 (84%)
#   include:             156 (67%)  ← Key metric
#   if/else:              45 (19%)
#   while loops:          12 (5%)
#   strset/intset:        89 (38%)
#
# Unique includes: 25
#   - Setup/teardown: 18 (72%)
#   - Helper functions: 5 (20%)
#   - Complex logic: 2 (8%)
#
# Transpiler coverage: 95%
# Manual review needed: 5% (12 files with while loops)
```

---

## Summary & Recommendations

### Key Decisions

| Question | Answer |
|----------|--------|
| Can we reuse AutoLib v3 APIs? | ✅ **YES** - with thin wrapper |
| Can we automate DSL → pytest conversion? | ✅ **YES** - via VM code transpiler |
| How to handle include directives? | ✅ **Convert includes to fixtures first** - with registry tracking |
| Can Python be as readable as DSL? | ⚠️ **MOSTLY** - with Fluent API (85-90%) |
| Should we migrate all tests? | ⚠️ **PROGRESSIVELY** - start with new tests |

---

### Recommended Approach

**Hybrid Strategy**: Run DSL and pytest side-by-side with dependency-aware conversion

1. **Keep DSL infrastructure** (for existing 200+ tests)
2. **Build Fluent API layer** (for new pytest tests)
3. **Create conversion registry** (track include → fixture mappings)
4. **Convert includes first** (bottom-up dependency resolution)
5. **Create automated transpiler** (for gradual test migration with fixture reuse)
6. **Validate both approaches** (ensure parity)
7. **Retire DSL eventually** (after full migration + validation)

---

### Include Handling Strategy Summary

**Critical Principle**: **Dependencies before dependents**

```
Conversion Order:
1. Scan all DSL tests → identify unique includes (e.g., 25 unique)
2. Convert all includes to fixtures/helpers → record in registry
3. Convert main tests → inject fixture parameters from registry
4. Reuse fixtures across multiple tests → no duplication
```

**Example Workflow**:
```
Step 1: Batch scan
  ├─ Found 234 test files
  ├─ Found 25 unique includes
  └─ 156 include references total

Step 2: Convert includes (bottom-up)
  ├─ govdom1.txt → setup_govdom1 (fixture)
  ├─ outvdom.txt → cleanup_outvdom (fixture)
  ├─ create_address.txt → create_firewall_address (helper)
  └─ ... 22 more

Step 3: Convert tests
  ├─ 205817.txt → test_205817.py (uses setup_govdom1, cleanup_outvdom)
  ├─ 205818.txt → test_205818.py (reuses same fixtures)
  └─ ... 232 more

Step 4: Registry tracks usage
  └─ govdom1.txt used by: [205817, 205818, 300045, ...]
```

**Benefits**:
- ✅ Convert once, reuse many times (govdom1.txt → 87 tests)
- ✅ Consistency across all tests using same include
- ✅ Easy updates (change fixture → all tests updated)
- ✅ Traceability (know impact of changing an include)

---

### Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Fluent API | 2 weeks | Working fluent interface |
| Phase 2: Include Handling | 2 weeks | Registry + Include converter |
| Phase 3: Transpiler | 3 weeks | Automated DSL → pytest tool |
| Phase 4: Include Migration | 2 weeks | All includes → fixtures/helpers |
| Phase 5: Test Migration | 2 weeks | 200+ converted tests |
| Phase 6: Validation | 2 weeks | Verified equivalent results |
| **Total** | **13 weeks** | Production-ready pytest framework |

**Note**: Timeline increased from 9 to 13 weeks to properly handle include directive conversion and dependency tracking.

---

### Success Criteria

✅ **Automated transpiler** converts 95%+ of DSL tests  
✅ **Include registry** tracks all include → fixture conversions  
✅ **Fixture reuse** - common includes converted once, used many times  
✅ **Fluent API** achieves 85%+ readability vs DSL  
✅ **pytest tests** produce identical results to DSL  
✅ **Dependency resolution** - automatic bottom-up conversion  
✅ **Team adoption** - developers prefer Python/pytest  
✅ **Maintenance reduction** - less custom compiler code  

---

## Next Steps

1. **Review this document** with team (focus on include handling strategy)
2. **Approve approach** (Fluent API + Registry + Transpiler)
3. **Prototype include conversion** (convert 5 common includes manually)
4. **Validate fixture reuse** (ensure multiple tests can share fixtures)
5. **Implement registry** (2 week spike)
6. **Full implementation** (13 week plan)

---

**Document Version**: 2.0  
**Author**: Software Architecture Team  
**Related Documents**:
- [Transpiler Example](TRANSPILER_EXAMPLE.md) - Real test conversion walkthrough
- [Python-Based Testing Framework](PYTHON_BASED_TESTING_FRAMEWORK.md)
- [Component Reusability Guide](COMPONENT_REUSABILITY_GUIDE.md)
- [Software Architecture & Design Patterns](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md)

**Created**: 2026-02-18  
**Updated**: 2026-02-23 - Added include directive handling strategy

