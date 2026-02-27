# FluentAPI Integration with AutoLib v3 Executor

## Executive Summary

**Current State**: FluentAPI is a **prototype** that reimplements command execution, expect logic, result tracking, etc.

**Target State**: FluentAPI should be a **thin adapter layer** that delegates to AutoLib v3's existing executor infrastructure.

**Benefit**: Reuse 100% of AutoLib v3's battle-tested code for device handling, command execution, assertions, reporting, and utilities.

---

## Architecture Comparison

### Current (Prototype) Architecture ❌

```
┌─────────────────────────────────────────────────────────────┐
│                    pytest Test                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FluentAPI (Prototype)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ TestBed                                              │  │
│  │  - Creates mock devices                             │  │
│  │  - Implements own execute() logic                   │  │
│  │  - Implements own expect() logic                    │  │
│  │  - Implements own ResultManager                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ FluentDevice                                         │  │
│  │  - Reimplements execute()                           │  │
│  │  - Reimplements config()                            │  │
│  │  - Calls device.execute() directly                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ OutputAssertion                                      │  │
│  │  - Reimplements expect() logic                      │  │
│  │  - Does string matching                             │  │
│  │  - Tracks results manually                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Mock Device (In-Memory Simulation)                  │
│          OR                                                  │
│          Direct Device Calls (No Executor)                   │
└─────────────────────────────────────────────────────────────┘

❌ Issues:
- Duplicates functionality in executor/api/ modules
- Doesn't use ScriptResultManager
- Doesn't use ApiHandler registry
- Loses AutoLib v3's device management
- No access to utilities, services, etc.
- Not production-ready
```

### Target (Production) Architecture ✅

```
┌─────────────────────────────────────────────────────────────┐
│                    pytest Test                               │
│                                                              │
│  def test_205812(testbed):                                   │
│      with testbed.device('FGT_A') as fgt_a:                  │
│          fgt_a.execute("show ips custom")                    │
│               .expect("match small", qaid="205812")          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         FluentAPI (Thin Adapter Layer)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ TestBed                                              │  │
│  │  - Creates Executor instance                        │  │
│  │  - Wraps Executor.devices                           │  │
│  │  - Delegates to Executor APIs                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ FluentDevice                                         │  │
│  │  - Wraps Executor.cur_device                        │  │
│  │  - execute() → calls Executor.api_handler           │  │
│  │  - Returns OutputAssertion for chaining             │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ OutputAssertion                                      │  │
│  │  - expect() → calls executor.api_handler.expect()   │  │
│  │  - Returns FluentDevice for chaining                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              AutoLib v3 Executor                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Executor                                             │  │
│  │  - cur_device: Current device context               │  │
│  │  - devices: Device registry                         │  │
│  │  - result_manager: ScriptResultManager              │  │
│  │  - api_handler: ApiHandler instance                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ApiHandler (ApiMixin)                                │  │
│  │  - execute_api(name, params)                        │  │
│  │  - Looks up API in registry                         │  │
│  │  - Calls registered function                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              API Registry (Auto-Discovered)                  │
│                                                              │
│  lib/core/executor/api/                                      │
│    ├── command.py    → send_literal()                       │
│    ├── expect.py     → expect(), expect_ctrl_c()            │
│    ├── report.py     → report(), collect_dev_info()         │
│    ├── device.py     → forcelogin(), keep_running()         │
│    ├── buffer.py     → clear_buffer()                       │
│    ├── utility.py    → sleep(), comment()                   │
│    ├── variable.py   → setenv(), getenv()                   │
│    └── network.py    → ping(), traceroute()                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Supporting Infrastructure                       │
│                                                              │
│  ├── Device Layer (lib/core/device/)                        │
│  │    ├── FortiGate, Pc, Computer classes                   │
│  │    ├── send_command(), reset_config(), etc.              │
│  │                                                           │
│  ├── Services (lib/services/)                               │
│  │    ├── ScriptResultManager - Result tracking             │
│  │    ├── env - Environment variables                       │
│  │    ├── logger - Logging infrastructure                   │
│  │    ├── output - Output management                        │
│  │    ├── summary - Test summary                            │
│  │                                                           │
│  └── Utilities (lib/utilities/)                             │
│       ├── sleep_with_progress()                             │
│       ├── retry_decorator()                                 │
│       └── Various helper functions                          │
└─────────────────────────────────────────────────────────────┘

✅ Benefits:
- 100% code reuse from AutoLib v3
- Battle-tested device handling
- Production-ready result management
- Access to all utilities and services
- Minimal maintenance burden
- FluentAPI is just a thin wrapper
```

---

## Key Components Deep Dive

### 1. Executor

**Location**: `lib/core/executor/executor.py`

**Responsibilities**:
- Device context management (`cur_device`)
- Device registry (`devices`)
- Result tracking (`result_manager: ScriptResultManager`)
- API execution (`api_handler: ApiHandler`)
- Variable interpolation
- Internal operations (switch_device, etc.)

**Key Methods**:
```python
class Executor:
    def __init__(self, script, devices, need_report=True):
        self.script = script
        self.devices = devices
        self.cur_device = None
        self.result_manager = ScriptResultManager(self.script)
        self.api_handler = ApiHandler(self)
    
    def _switch_device(self, parameters):
        """Switch to a different device"""
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]
        self.cur_device.switch()
    
    def _command(self, parameters):
        """Send command to current device"""
        cmd = parameters[0]
        cli_output = self.cur_device.send_command(cmd)
        self.result_manager.check_cli_error(self.last_line_number, cmd, cli_output)
```

**Integration Point**:
FluentAPI should create an Executor instance and delegate operations to it.

---

### 2. ApiHandler (via ApiMixin)

**Location**: `lib/core/executor/api_manager.py`

**Responsibilities**:
- API registry management
- Auto-discovery of API modules
- Parameter validation (via ApiParams)
- API execution

**Key Methods**:
```python
class ApiMixin:
    def execute_api(self, api_endpoint: str, parameters: Tuple):
        """Execute an API by name"""
        # Get schema and validate parameters
        schema = get_schema(api_endpoint)
        if schema:
            params = ApiParams(parameters, schema)
            params.validate()
        
        # Execute registered API function
        if api_endpoint in _API_REGISTRY:
            func = _API_REGISTRY[api_endpoint]
            return func(self.executor, params)
        
        raise AttributeError(f"API '{api_endpoint}' not found")
```

**Auto-Discovery**:
- Scans `lib/core/executor/api/*.py`
- Registers all public functions (not starting with `_`)
- Module name becomes category
- Function name becomes API endpoint

**Example Registration**:
```python
# lib/core/executor/api/expect.py
def expect(executor, params):
    """Expect pattern in output"""
    rule = params.rule
    qaid = params.qaid
    # ... implementation ...

# Auto-registered as:
_API_REGISTRY['expect'] = expect
```

---

### 3. API Functions

**Location**: `lib/core/executor/api/`

#### a) command.py
```python
def send_literal(executor, params):
    """Send literal string with escape sequences"""
    literal = params.literal
    cmd = literal[1:-1].encode().decode("unicode_escape")
    executor.cur_device.send(cmd)
```

#### b) expect.py
```python
def expect(executor, params):
    """
    Expect pattern in output with retry logic.
    
    Parameters:
        params.rule (str): Pattern to match [-e]
        params.qaid (str): Test case ID [-for]
        params.wait_seconds (int): Timeout [-t]
        params.fail_match (str): "match"/"unmatch" [-fail]
        params.clear (str): Clear buffer [-clear]
        params.retry_command (str): Command to retry [-retry_command]
        params.retry_cnt (int): Retry count [-retry_cnt]
    """
    rule = params.rule
    qaid = params.qaid
    timeout = params.get('wait_seconds', 5)
    fail_match = params.get('fail_match', 'unmatch') == 'match'
    
    # Use device's expect functionality
    is_matched = executor.cur_device.expect_string(
        rule, 
        timeout=timeout,
        fail_match=fail_match
    )
    
    # Report result
    executor.result_manager.add_expect_result(
        qaid, 
        is_matched, 
        rule, 
        executor.cur_device.get_buffer()
    )
```

#### c) report.py
```python
def report(executor, params):
    """Mark QAID for reporting"""
    qaid = params.qaid
    dut = executor.cur_device.dev_name
    executor.result_manager.add_report_qaid_and_dev_map(qaid, dut)
```

#### d) device.py
```python
def keep_running(executor, params):
    """Set keep_running flag"""
    value = bool(params.enabled)
    executor.cur_device.set_keep_running(value)

def forcelogin(executor, params):
    """Force login to current device"""
    executor.cur_device.force_login()
```

---

### 4. ScriptResultManager

**Location**: `lib/services/result_manager.py`

**Responsibilities**:
- Track QAID assertions
- Collect device info
- Generate test reports
- Integrate with Oriole (test management system)

**Key Methods**:
```python
class ScriptResultManager:
    def add_expect_result(self, qaid, is_matched, rule, output):
        """Record expect assertion result"""
    
    def add_report_qaid_and_dev_map(self, qaid, device):
        """Mark QAID for final reporting"""
    
    def check_cli_error(self, line_number, cmd, output):
        """Check for CLI errors in output"""
    
    def report_script_result(self, devices_info):
        """Generate final test report"""
```

---

## Integration Plan

### Phase 1: Minimal Viable Integration

**Objective**: Get FluentAPI calling Executor APIs without breaking existing transpiled tests

**Steps**:

1. **Create Executor Container**
   ```python
   # fluent_api/executor_adapter.py
   
   from lib.core.executor import Executor
   from lib.core.compiler import Script
   
   class PytestExecutor:
       """Executor adapter for pytest tests (no VM, direct API calls)"""
       
       def __init__(self, devices, test_name="pytest_test"):
           # Create minimal Script object (no VM codes)
           self.script = Script(test_name, vm_codes=[], source_lines=[])
           
           # Create executor
           self.executor = Executor(
               script=self.script,
               devices=devices,
               need_report=True
           )
       
       def switch_device(self, device_name: str):
           """Switch to device and return fluent wrapper"""
           self.executor._switch_device([device_name])
           return self.executor.cur_device
       
       def execute_api(self, api_name: str, *params):
           """Execute API through handler"""
           return self.executor.api_handler.execute_api(api_name, params)
       
       def get_result_manager(self):
           """Get result manager for assertions"""
           return self.executor.result_manager
   ```

2. **Update TestBed to Use Executor**
   ```python
   # fluent_api/fluent.py
   
   from .executor_adapter import PytestExecutor
   
   class TestBed:
       def __init__(self, env_config: dict = None, use_mock: bool = False):
           # Create devices using AutoLib v3 device factory
           self.devices = self._create_devices(env_config, use_mock)
           
           # Create executor adapter
           self.executor_adapter = PytestExecutor(self.devices)
           
           # Alias for compatibility
           self.results = self.executor_adapter.get_result_manager()
       
       def _create_devices(self, env_config, use_mock):
           """Create AutoLib v3 device instances"""
           if use_mock:
               # For prototype testing
               from mock_device import create_mock_device
               return {
                   name: create_mock_device(name, config)
                   for name, config in env_config.items()
               }
           else:
               # Real AutoLib v3 devices
               from lib.core.device import create_device_from_config
               return {
                   name: create_device_from_config(name, config)
                   for name, config in env_config.items()
               }
       
       @contextmanager
       def device(self, name: str):
           """Context manager for device operations"""
           # Switch device via executor
           device_obj = self.executor_adapter.switch_device(name)
           
           # Wrap in FluentDevice
           fluent = FluentDevice(
               device_obj, 
               self.executor_adapter,
               testbed=self
           )
           
           yield fluent
   ```

3. **Update FluentDevice to Delegate to Executor**
   ```python
   class FluentDevice:
       def __init__(self, device, executor_adapter, testbed=None):
           self.device = device
           self.executor = executor_adapter
           self.testbed = testbed
       
       @resolve_command_vars
       def execute(self, command: str):
           """Execute command via Executor API"""
           # Call executor's command API
           self.executor.execute_api('_command', command)
           
           # Get output from device buffer
           output = self.device.get_buffer()
           
           return OutputAssertion(output, self.executor, self)
       
       @resolve_command_vars
       def config(self, config_block: str):
           """Execute config block"""
           self.executor.execute_api('_command', config_block)
           return self
       
       def sleep(self, seconds: int):
           """Sleep via utility API"""
           self.executor.execute_api('sleep', seconds)
           return self
       
       def keep_running(self, state: int):
           """Keep running via device API"""
           self.executor.execute_api('keep_running', state)
           return self
   ```

4. **Update OutputAssertion to Use Executor's Expect API**
   ```python
   class OutputAssertion:
       def __init__(self, output: str, executor_adapter, device):
           self.output = output
           self.executor = executor_adapter
           self.device = device
       
       def expect(self, pattern: str, qaid: Optional[str] = None, 
                  timeout: int = 5, should_fail: bool = False):
           """Assert pattern using Executor's expect API"""
           
           # Map to AutoLib v3 expect parameters
           fail_match = 'match' if should_fail else 'unmatch'
           
           # Call executor's expect API
           self.executor.execute_api(
               'expect',
               '-e', pattern,
               '-for', qaid,
               '-t', str(timeout),
               '-fail', fail_match
           )
           
           return self.device  # For chaining
   ```

---

### Phase 2: Full Integration

**Objective**: Use 100% of AutoLib v3 infrastructure

**Additional Steps**:

5. **Report Integration**
   ```python
   class FluentDevice:
       def report(self, qaid: str):
           """Report via executor API"""
           self.executor.execute_api('report', qaid)
           return self
   ```

6. **Buffer Management**
   ```python
   class FluentDevice:
       def clear_buffer(self):
           """Clear buffer via executor API"""
           self.executor.execute_api('clear_buffer')
           return self
   ```

7. **Variable Integration**
   ```python
   class TestBed:
       def resolve_variables(self, command: str) -> str:
           """Use executor's variable interpolation"""
           # Delegate to executor's variable_replacement
           replaced = self.executor_adapter.executor.variable_replacement((command,))
           return replaced[0]
   ```

8. **Network Operations**
   ```python
   class FluentDevice:
       def ping(self, target: str, count: int = 4):
           """Ping via network API"""
           self.executor.execute_api('ping', target, str(count))
           return self
   ```

---

### Phase 3: Advanced Features

9. **Script Management Integration**
   ```python
   class FluentDevice:
       def run_script(self, script_path: str):
           """Execute external script"""
           self.executor.execute_api('run_script', script_path)
           return self
   ```

10. **Control Flow Support**
    ```python
    class FluentDevice:
        def if_condition(self, condition: str):
            """Conditional execution"""
            # Use executor's if_stack for control flow
            self.executor.execute_api('if', condition)
            return self
    ```

---

## API Mapping Reference

### DSL → FluentAPI → Executor API

| DSL Command | FluentAPI Method | Executor API | Implementation |
|-------------|------------------|--------------|----------------|
| `show system status` | `execute(cmd)` | `_command` | `executor.py::_command()` |
| `expect -e "pattern" -for QAID` | `expect(pattern, qaid)` | `expect` | `api/expect.py::expect()` |
| `report QAID` | `report(qaid)` | `report` | `api/report.py::report()` |
| `sleep 5` | `sleep(5)` | `sleep` | `api/utility.py::sleep()` |
| `keep_running 0` | `keep_running(0)` | `keep_running` | `api/device.py::keep_running()` |
| `comment "text"` | `comment("text")` | `comment` | `api/utility.py::comment()` |
| `clear_buffer` | `clear_buffer()` | `clear_buffer` | `api/buffer.py::clear_buffer()` |
| `forcelogin` | `forcelogin()` | `forcelogin` | `api/device.py::forcelogin()` |
| `setenv VAR=val` | `setenv(var, val)` | `setenv` | `api/variable.py::setenv()` |

---

## Benefits of Executor Integration

### 1. Code Reuse ✅
- **0 lines** of duplicated command execution logic
- **0 lines** of duplicated expect logic
- **0 lines** of duplicated device management
- **100%** reuse of production code

### 2. Battle-Tested ✅
- Executor has run **thousands** of test cases
- All edge cases handled
- Retry logic built-in
- Error handling robust

### 3. Feature Completeness ✅
- Access to **all** AutoLib v3 APIs
- Network operations (ping, traceroute, etc.)
- Advanced expect (regex, retry, timeout)
- Device info collection
- License management
- Script execution
- Control flow

### 4. Maintenance ✅
- Bug fixes in executor → automatically available
- New APIs in executor → automatically available
- FluentAPI is **thin wrapper** (~200 lines instead of 1000+)
- Single source of truth

### 5. Result Integration ✅
- Uses `ScriptResultManager`
- Integrates with Oriole
- Standard report format
- Device info collection
- Assertion tracking

---

## Implementation Checklist

### Prerequisites
- [ ] Understand Executor architecture
- [ ] Understand ApiHandler/ApiMixin
- [ ] Understand Script object structure
- [ ] Understand device layer

### Phase 1: Minimal Integration
- [ ] Create `executor_adapter.py`
- [ ] Create `PytestExecutor` class
- [ ] Update `TestBed.__init__` to create executor
- [ ] Update `FluentDevice.execute()` to call `_command` API
- [ ] Update `OutputAssertion.expect()` to call `expect` API
- [ ] Test with QAID 205812
- [ ] Verify all assertions pass

### Phase 2: Full Integration
- [ ] Integrate `report()` API
- [ ] Integrate `keep_running()` API
- [ ] Integrate `clear_buffer()` API
- [ ] Integrate `sleep()` API
- [ ] Update variable resolution to use executor
- [ ] Test with multiple test cases
- [ ] Verify result reporting

### Phase 3: Production Readiness
- [ ] Real device testing (not mock)
- [ ] Multi-device test cases
- [ ] Network operation tests
- [ ] Error handling verification
- [ ] Performance benchmarking
- [ ] Documentation updates

---

## Code Examples

### Before (Prototype)
```python
class FluentDevice:
    def execute(self, command: str):
        # ❌ Reimplements command execution
        self.logger.info(f"Executing: {command}")
        
        if hasattr(self.device, 'execute'):
            self._last_output = self.device.execute(command)
        elif hasattr(self.device, 'send_line_get_output'):
            self._last_output = self.device.send_line_get_output(command)
        else:
            self.logger.warning(f"Unknown device interface")
            self._last_output = ""
            
        return OutputAssertion(self._last_output, self.results, self)
```

### After (Executor Integration)
```python
class FluentDevice:
    def execute(self, command: str):
        # ✅ Delegates to executor's tested implementation
        self.executor.execute_api('_command', command)
        output = self.device.get_buffer()
        return OutputAssertion(output, self.executor, self)
```

---

## Migration Strategy

### Step 1: Parallel Implementation
- Keep prototype FluentAPI working
- Create new `fluent_v2.py` with executor integration
- Run tests with both versions
- Compare results

### Step 2: Gradual Migration
- Migrate one API at a time (execute → expect → report)
- Test after each migration
- Fix any discrepancies

### Step 3: Cutover
- Once all tests pass with executor version
- Replace old fluent.py with new version
- Archive prototype code

### Step 4: Cleanup
- Remove mock device code
- Remove prototype result manager
- Remove duplicated logic

---

## Questions & Answers

### Q: Won't this add complexity?
**A**: No, it **reduces** complexity. FluentAPI becomes a thin wrapper (~200 lines) instead of reimplementing everything (~1000+ lines).

### Q: What about pytest integration?
**A**: FluentAPI remains the pytest interface. Executor is internal implementation detail.

### Q: Will this slow down tests?
**A**: No. Same underlying code, just called through different interface.

### Q: Can we still use mock devices?
**A**: Yes. For development/CI, mock devices. For production, real devices. Executor handles both.

### Q: What about the variable resolution decorator?
**A**: Keep it! It's a FluentAPI feature for DEVICE:VARIABLE patterns. Executor has its own variable interpolation for $VARIABLES.

### Q: Do we need to modify the transpiler?
**A**: No. Transpiler generates pytest → FluentAPI calls. Implementation of FluentAPI is transparent.

---

## Conclusion

**Current FluentAPI**: Prototype that reimplements AutoLib v3 functionality

**Target FluentAPI**: Thin adapter that leverages AutoLib v3 executor infrastructure

**Result**: 
- ✅ Production-ready
- ✅ Battle-tested code
- ✅ Full feature access
- ✅ Minimal maintenance
- ✅ Clean architecture

**Next Steps**:
1. Review this document
2. Implement `executor_adapter.py`
3. Update `TestBed` to use executor
4. Update `FluentDevice` to delegate to APIs
5. Test with QAID 205812
6. Iterate and expand

---

**Document Version**: 1.0  
**Date**: February 24, 2026  
**Status**: Architecture Proposal
