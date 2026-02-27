# AutoLib v3 - Complete Workflow Documentation

**Version**: V3R10B0007  
**Purpose**: Automated FortiOS Testing Framework  
**Language**: Python 3.8+

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Workflow Phases](#workflow-phases)
4. [Core Modules](#core-modules)
5. [Data Flow](#data-flow)
6. [Deep Dive Topics](#deep-dive-topics)
7. [Execution Models](#execution-models)
8. [Error Handling](#error-handling)

---

## Overview

AutoLib v3 is a **DSL-based test automation framework** for FortiOS devices. It enables engineers to write test scripts in a high-level scripting language that gets compiled to executable code and run against physical/virtual FortiGate devices.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **DSL Scripting** | 35+ built-in APIs with custom scripting language |
| **Multi-Device** | Parallel execution across multiple devices (FortiGate, PC, FortiSwitch, etc.) |
| **Compile-Time Validation** | Syntax and schema validation before execution |
| **Variable Interpolation** | Environment-based configuration and user-defined variables |
| **Result Reporting** | Integrated with Oriole test management system |
| **Debug Support** | Step-through debugging, breakpoints, detailed logging |
| **Plugin Architecture** | Custom API extensions via plugins/apis/ |

### End-to-End Flow (High Level)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Test Script    │────▶│   Compilation    │────▶│   Execution     │
│  (.txt file)    │     │   (Lexer/Parser) │     │   (Devices)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                         │
        │                       │                         │
        ▼                       ▼                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Environment    │     │    VM Codes      │     │   Results       │
│  Config (.conf) │     │    (Cache)       │     │   (Oriole/JSON) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Execution Time**: Small test ~5-10 seconds, Complex test ~minutes to hours

---

## Architecture

### Component Hierarchy

```
autolib_v3/
├─ autotest.py                 # Entry point
├─ lib/
│  ├─ core/                    # Core engine
│  │  ├─ compiler/             # DSL compilation
│  │  ├─ executor/             # Test execution
│  │  ├─ device/               # Device abstraction
│  │  └─ scheduler/            # Parallel execution
│  │
│  ├─ services/                # Supporting services
│  │  ├─ environment.py        # Config management
│  │  ├─ result_manager.py     # Result collection
│  │  ├─ log.py                # Logging
│  │  └─ oriole/               # Test management integration
│  │
│  └─ utilities/               # Helper functions
│
├─ testcase/                   # Test scripts
├─ plugins/                    # Custom APIs
└─ outputs/                    # Execution results
```

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Layer                              │
│  Test Scripts (.txt) + Environment Config (.conf)           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Compiler Layer                            │
│  Lexer → Parser → Schema Validator → VM Code Generator      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Executor Layer                            │
│  API Manager → Code Executor → Control Flow Handler         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Device Layer                              │
│  Device Abstraction → Session Manager → Protocol Handlers   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Services Layer                            │
│  Result Manager → Logger → Environment → Oriole Client      │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Phases

### Phase 1: Initialization

**Entry Point**: `autotest.py`

```python
# Command line execution
python3 autotest.py \
    -t testcase/ips/test.txt \           # Test script
    -e testcase/env/env.conf \           # Environment config
    -d                                    # Debug mode
```

**Steps**:

1. **Parse Command Line Arguments**
   - Test script path (`-t`)
   - Environment config path (`-e`)
   - Execution options (`-d`, `--non_strict`, etc.)

2. **Load Environment Configuration**
   - Parse `.conf` file (INI format)
   - Load device definitions
   - Load global variables
   - Module: `lib.services.environment.Environment`

3. **Initialize Services**
   - Logger (`lib.services.log`)
   - Result Manager (`lib.services.result_manager`)
   - Oriole Client (`lib.services.oriole`)
   - Image Server (if needed)

4. **Setup Output Directory**
   - Create timestamped folder: `outputs/YYYY-MM-DD_HH-MM-SS/`
   - Initialize log files
   - Copy environment config for reference

**Output**: Configured runtime environment ready for compilation

**Duration**: <1 second

---

### Phase 2: Compilation

**Module**: `lib.core.compiler`

**Purpose**: Transform human-readable DSL scripts into executable VM codes

#### Stage 2.1: Lexical Analysis (Lexer)

**File**: `lib/core/compiler/lexer.py`

**Input**: Test script text file

**Process**:
1. Read source file line by line
2. Apply regex patterns to identify tokens
3. Classify tokens: `api`, `section`, `keyword`, `comment`, `include`, `command`
4. Store token metadata (type, value, line number)

**Example**:
```plaintext
[FGT_A]                          → Token(type='section', str='FGT_A', line=1)
    expect -e "login:" -t 5      → Token(type='api', api='expect', params=..., line=2)
    command get system status    → Token(type='command', str='get system status', line=3)
```

**Output**: List of tokens with metadata

**See Also**: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md#stage-1-lexical-analysis)

#### Stage 2.2: Syntax Parsing (Parser)

**File**: `lib/core/compiler/parser.py`

**Input**: Token stream from lexer

**Process**:
1. Identify device sections (`[FGT_A]`, `[PC_01]`)
2. Parse API commands with parameters
3. Handle control flow (`if/else`, `while` loops)
4. Process `include` directives
5. Collect device names and included files

**Example**:
```plaintext
Token: expect -e "login:" -t 5
  ↓
Parsed:
  - API name: expect
  - Parameters: {'-e': 'login:', '-t': '5'}
  - Line number: 2
  - Device context: FGT_A
```

**Output**: 
- Parsed command structures
- Device registry
- Include file list
- Control flow markers

#### Stage 2.3: Schema Validation

**File**: `lib/core/compiler/schema_loader.py`

**Input**: Parsed API commands

**Process**:
1. Load API schema from `cli_syntax.json`
2. Validate required parameters present
3. Validate parameter types (string, int, boolean)
4. Map CLI options to Python parameter names via `alias` field
5. Apply default values for optional parameters

**Example**:
```json
// Schema definition
{
  "expect": {
    "parameters": [
      {"-e": {"alias": "rule", "required": true}},
      {"-t": {"alias": "timeout", "default": 10}},
      {"-for": {"alias": "qaid", "required": false, "default": "NO_QAID"}}
    ]
  }
}
```

**Validation**:
```plaintext
Command: expect -e "login:" -t 5
  ✓ Required -e present
  ✓ Type check: -e is string
  ✓ Type check: -t is int
  ✓ Optional -for missing → use default "NO_QAID"
```

**Output**: Validated parameters mapped to Python names

**See Also**: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md#stage-3-schema-validation)

#### Stage 2.4: VM Code Generation

**File**: `lib/core/compiler/vm_code.py`

**Input**: Validated commands

**Process**:
1. Convert parsed commands to VM code objects
2. Create `VMCode(line_number, api_name, params_tuple)`
3. Handle variable interpolation for environment vars
4. Generate control flow VM codes (if/else/while)

**Example**:
```plaintext
DSL: expect -e "login:" -t 5 -for 12345
  ↓
VMCode:
  - line_number: 2
  - api_name: "expect"
  - params: ("login:", 5, "12345")
```

**VM Code Types**:
| Type | Purpose | Example |
|------|---------|---------|
| API Call | Execute API function | `expect`, `command`, `config` |
| Control Flow | if/else/while markers | `if_start`, `else`, `fi`, `while_start` |
| Device Switch | Change active device | `with_device` |
| Script Include | Execute sub-script | `include` |

**Output**: List of VM codes ready for execution

**Caching**: Compiled VM codes cached in `compiler.files[filepath]`

**See Also**: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md#stage-4-vm-code-generation)

#### Stage 2.5: Include Resolution

**File**: `lib/core/compiler/compiler.py`

**Input**: List of included files from parser

**Process**:
1. Extract include paths with variable placeholders
2. Interpolate environment variables (`GLOBAL:VERSION` → `trunk`)
3. Recursively compile included files
4. Cache compiled codes to avoid re-compilation

**Example**:
```plaintext
Include: testcase/GLOBAL:VERSION/ips/goglobal.txt

Step 1: Variable interpolation
  GLOBAL:VERSION → trunk
  Result: testcase/trunk/ips/goglobal.txt

Step 2: Recursive compilation
  ├─ Lexer parses goglobal.txt
  ├─ Parser generates VM codes
  └─ Codes cached for reuse

Step 3: Cache management
  ├─ First include → full compilation
  └─ Second include → cache hit, reuse
```

**Output**: All included files compiled and cached

**See Also**: [Include Directive](INCLUDE_DIRECTIVE.md)

---

### Phase 3: Device Initialization

**Module**: `lib.core.device`

**Purpose**: Establish connections to all devices defined in environment config

#### Stage 3.1: Device Discovery

**Input**: Environment configuration `[DEVICE_NAME]` sections

**Process**:
1. Scan config for device sections
2. Identify device types (FortiGate, PC, FortiSwitch, etc.)
3. Extract connection parameters (IP, username, password, protocol)

**Example Config**:
```ini
[FGT_A]
CONNECTION: telnet admin@10.160.132.71
PASSWORD: password
PORT1: 172.16.200.1

[PC_01]
CONNECTION: ssh root@10.6.30.11
PASSWORD: Qa123456!
```

**Output**: Device registry with connection metadata

#### Stage 3.2: Connection Establishment

**Files**: 
- `lib/core/device/device.py` - Base device class
- `lib/core/device/fortigate.py` - FortiGate-specific
- `lib/core/device/pc.py` - PC/Linux-specific

**Process**:
1. Create device objects based on type
2. Establish protocol connections (Telnet/SSH/Serial)
3. Perform initial handshake
4. Set terminal settings (width, echo, paging)
5. Store connection in session pool

**Connection Types**:
| Protocol | Port | Use Case |
|----------|------|----------|
| Telnet | 23 | Legacy FortiGate access |
| SSH | 22 | Secure device access |
| Serial | COM/ttyUSB | Console access |
| HTTP/HTTPS | 80/443 | API access (future) |

**Connection Pooling**:
- Connections kept alive during test execution
- Reused across multiple commands
- Closed at end of test or on error

**Output**: Active device connections ready for command execution

**Duration**: 1-5 seconds per device

---

### Phase 4: Execution

**Module**: `lib.core.executor`

**Purpose**: Execute VM codes against connected devices

#### Stage 4.1: Executor Initialization

**File**: `lib/core/executor/executor.py`

**Input**: 
- Compiled VM codes
- Active device connections

**Process**:
1. Create `Executor` instance
2. Initialize program counter (PC = 0)
3. Setup control flow stack (for if/while)
4. Setup result manager
5. Initialize API manager

**Executor State**:
```python
{
    'program_counter': 0,              # Current VM code index
    'cur_device': None,                # Active device object
    'devices': {...},                  # All device objects
    'if_stack': [],                    # Control flow stack
    'result_manager': ResultManager(), # Collect results
    'continue_on_error': False         # Error handling mode
}
```

#### Stage 4.2: Program Counter Loop

**Main Loop**:
```python
while program_counter < len(vm_codes):
    # 1. Fetch next VM code
    vm_code = vm_codes[program_counter]
    
    # 2. Check control flow (skip if in false branch)
    if should_skip_execution(if_stack):
        program_counter += 1
        continue
    
    # 3. Execute VM code
    execute_vm_code(vm_code)
    
    # 4. Handle control flow modifications
    program_counter = update_program_counter(vm_code)
```

**Control Flow Handling**:
| VM Code | Action | PC Update |
|---------|--------|-----------|
| Normal API | Execute | PC + 1 |
| `if_start` | Evaluate condition, push stack | PC + 1 or jump to else |
| `else` | Flip stack state | PC + 1 |
| `fi` | Pop stack | PC + 1 |
| `while_start` | Evaluate, push stack | PC + 1 or jump to endwhile |
| `endwhile` | Loop back if condition true | PC → while_start or PC + 1 |

#### Stage 4.3: API Execution

**File**: `lib/core/executor/api_manager.py`

**Process**:
1. Unpack VM code: `(line_number, api_name, params_tuple)`
2. Convert params tuple to `ApiParams` object
3. Lookup API function from registry
4. Execute API with executor context and parameters
5. Capture return value and errors

**API Types**:

| Category | APIs | Purpose |
|----------|------|---------|
| **Device Commands** | `expect`, `command`, `config` | Send commands, match output |
| **Variables** | `setvar`, `intset`, `strset` | Define/modify variables |
| **Control Flow** | `if`, `else`, `while` | Conditional execution |
| **Script** | `include`, `comment`, `report` | Script control |
| **Device Control** | `reset`, `reboot`, `login` | Device lifecycle |
| **Custom** | Plugin APIs | User-defined extensions |

**Example Execution**:
```python
# VM Code: expect -e "login:" -t 5 -for 12345
vm_code = VMCode(line=10, api="expect", params=("login:", 5, "12345"))

# 1. Convert to ApiParams
params = ApiParams(("login:", 5, "12345"), schema)
# Access: params.rule="login:", params.timeout=5, params.qaid="12345"

# 2. Lookup API function
api_func = api_manager.get_api("expect")
# Returns: lib.core.executor.api.expect.expect()

# 3. Execute
api_func(executor, params)
# → Sends command to device
# → Waits for "login:" pattern
# → Records result with QAID 12345
```

**See Also**: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md#stage-5-api-execution)

#### Stage 4.4: Device Communication

**Files**: `lib/core/device/session/*.py`

**Process**:
1. Get active device from executor context
2. Send command via device session
3. Wait for output with timeout
4. Apply buffer management (clear/preserve)
5. Return output to API

**Communication Flow**:
```
API (expect)
   │
   ├─ executor.cur_device.expect(pattern, timeout)
   │     │
   │     ├─ session.send_command(pattern)
   │     │     │
   │     │     └─ Protocol Handler (Telnet/SSH)
   │     │           │
   │     │           └─ Socket I/O → Device
   │     │
   │     └─ session.read_until(pattern, timeout)
   │           │
   │           └─ Buffer accumulation + regex matching
   │
   └─ Return match result + output
```

**Buffer Management**:
- **Output Buffer**: Accumulates all device output
- **Clear Policy**: After successful match, clear buffer up to match.end()
- **Preservation**: Some APIs preserve buffer for subsequent matches

**Timeout Handling**:
- Default timeout: 10 seconds (configurable)
- Timeout exception raised if pattern not found
- Configurable per-command via `-t` parameter

#### Stage 4.5: Variable Interpolation

**Timing**: Two-pass interpolation

**Pass 1 - Environment Variables** (Compile-time):
```plaintext
Source: command get system status for $DUT
Config: [GLOBAL]
        DUT: FGT_A
Result: command get system status for FGT_A
```

**Pass 2 - User Variables** (Execution-time):
```plaintext
Before: comment Serial: {$sn}
Setvar: <setvar sn "Serial-Number: (.*)">  → sn = FGVM12345
After:  comment Serial: FGVM12345
```

**Variable Types**:
| Syntax | Source | When Replaced | Example |
|--------|--------|---------------|---------|
| `$VAR` | Environment config | Compile-time | `$DUT`, `$VERSION` |
| `{$VAR}` | setvar/intset/strset | Execution-time | `{$sn}`, `{$counter}` |
| `SECTION:VAR` | Environment section | Compile-time | `GLOBAL:VERSION` |

**See Also**: [Variable Usage and Troubleshooting](VARIABLE_USAGE_AND_TROUBLESHOOTING.md)

#### Stage 4.6: Result Collection

**File**: `lib/services/result_manager.py`

**Purpose**: Track test results for reporting

**Result Types**:
| Type | Method | Purpose |
|------|--------|---------|
| QAID Result | `add_qaid_expect_result()` | Track expect/validation results |
| Comment | `add_comment()` | Log informational messages |
| Error | `add_error()` | Record failures |
| Summary | `generate_summary()` | Aggregate final results |

**QAID Tracking**:
```python
# When expect succeeds:
result_manager.add_qaid_expect_result(
    qaid="12345",
    is_succeeded=True,
    output="login: _",
    command="expect -e 'login:'"
)

# Result stored:
{
    'qaid': '12345',
    'status': 'PASS',
    'timestamp': '2026-02-18 10:30:45',
    'output': 'login: _',
    'command': 'expect -e "login:"'
}
```

**Reporting**:
- Results aggregated at end of execution
- Uploaded to Oriole test management system
- Saved to local JSON file
- Displayed in console summary

---

### Phase 5: Reporting

**Module**: `lib.services.result_manager` + `lib.services.oriole`

**Purpose**: Aggregate results and upload to test management system

#### Stage 5.1: Result Aggregation

**Process**:
1. Collect all QAID results
2. Collect all errors and warnings
3. Calculate summary statistics
4. Generate HTML/JSON reports

**Summary Statistics**:
```json
{
    "total_qaids": 15,
    "passed": 13,
    "failed": 2,
    "skipped": 0,
    "duration_seconds": 45.3,
    "start_time": "2026-02-18 10:30:00",
    "end_time": "2026-02-18 10:30:45"
}
```

#### Stage 5.2: Oriole Integration

**File**: `lib/services/oriole/client.py`

**Purpose**: Upload results to Oriole test management system

**Process**:
1. Authenticate with Oriole API
2. Create test run record
3. Upload individual QAID results
4. Upload attachments (logs, screenshots)
5. Mark test run complete

**Oriole Metadata**:
```ini
[ORIOLE]
USER: yzhengfeng
ENCODE_PASSWORD: <encrypted>
RELEASE: 7.6.5
RES_FIELD_MARK: Fortistack_Autolib_v3
```

**Upload Format**:
```json
{
    "release": "7.6.5",
    "test_case_id": "12345",
    "result": "PASS",
    "log": "Device responded with expected output",
    "duration": 2.3,
    "platform": "FGVM",
    "build": "build3615"
}
```

#### Stage 5.3: Local Output

**Output Directory Structure**:
```
outputs/2026-02-18_10-30-00/
├─ test_summary.html          # Human-readable summary
├─ results.json               # Machine-readable results
├─ execution.log              # Detailed execution log
├─ environment.conf           # Copy of env config used
└─ devices/
   ├─ FGT_A_output.txt        # Device-specific output
   └─ PC_01_output.txt
```

**HTML Summary** (example):
```html
Test Execution Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test Script: testcase/ips/first_case.txt
Start Time:  2026-02-18 10:30:00
End Time:    2026-02-18 10:30:45
Duration:    45.3 seconds

Results:
  ✓ PASS: 13
  ✗ FAIL: 2
  ○ SKIP: 0

Failed QAIDs:
  - 205803: HA status check failed
  - 205806: Memory threshold exceeded
```

---

## Core Modules

### Module 1: Compiler (`lib/core/compiler/`)

**Responsibilities**:
- Parse DSL scripts into tokens
- Validate syntax and schema
- Generate executable VM codes
- Cache compiled code
- Handle include directives

**Key Files**:
| File | Purpose |
|------|---------|
| `lexer.py` | Tokenize DSL text |
| `parser.py` | Parse tokens into commands |
| `schema_loader.py` | Validate API parameters |
| `vm_code.py` | VM code data structure |
| `compiler.py` | Orchestrate compilation |
| `syntax.py` | API pattern definitions |
| `cli_syntax.json` | API schema definitions |

**Interfaces**:
```python
# Compile a test script
compiler.run(file_path)

# Retrieve compiled VM codes
vm_codes = compiler.retrieve_vm_codes(file_path)

# Get all device names
devices = compiler.retrieve_devices()
```

**Performance**:
- Compilation: ~100-500ms for typical test
- Caching: <1ms for cache hits
- Thread-safe for parallel compilation

**See Also**: [DSL Compilation Flow](DSL_COMPILATION_FLOW.md)

---

### Module 2: Executor (`lib/core/executor/`)

**Responsibilities**:
- Execute VM codes sequentially
- Manage program counter and control flow
- Dispatch API calls to handlers
- Handle errors and exceptions
- Collect execution results

**Key Files**:
| File | Purpose |
|------|---------|
| `executor.py` | Main execution loop |
| `code_executor.py` | VM code execution logic |
| `api_manager.py` | API registry and dispatch |
| `api_params.py` | Parameter wrapper |
| `if_stack.py` | Control flow stack |
| `api/` | API implementation modules |

**Interfaces**:
```python
# Create executor
executor = Executor(script, devices, continue_on_error)

# Execute test
with executor:
    executor.execute()

# Access results
results = executor.result_manager.get_results()
```

**API Categories**:
```
api/
├─ expect.py           # Pattern matching
├─ command.py          # Device commands
├─ config.py           # Configuration commands
├─ variable.py         # Variable operations
├─ control_flow.py     # if/else/while
├─ script.py           # include/comment/report
├─ device_control.py   # reset/reboot/login
└─ custom/             # Plugin APIs
```

---

### Module 3: Device (`lib/core/device/`)

**Responsibilities**:
- Abstract device types (FortiGate, PC, FortiSwitch)
- Manage device connections
- Handle protocol communication
- Provide device-specific operations

**Key Files**:
| File | Purpose |
|------|---------|
| `device.py` | Base device abstraction |
| `fortigate.py` | FortiGate-specific logic |
| `pc.py` | PC/Linux devices |
| `fortiswitch.py` | FortiSwitch devices |
| `session/` | Connection protocols |

**Device Types**:
```python
class Device:
    def connect()           # Establish connection
    def disconnect()        # Close connection
    def send_command()      # Send CLI command
    def expect()            # Wait for pattern
    def reset()             # Device reset
    def get_version()       # Version info
```

**Session Types**:
| Session | Protocol | File |
|---------|----------|------|
| TelnetSession | Telnet | `session/telnet_session.py` |
| SSHSession | SSH | `session/ssh_session.py` |
| SerialSession | Serial | `session/serial_session.py` |

---

### Module 4: Services (`lib/services/`)

**Responsibilities**:
- Environment configuration management
- Logging and debugging
- Result collection and reporting
- Oriole integration
- Template rendering

**Key Files**:
| File | Purpose |
|------|---------|
| `environment.py` | Config parsing and variable interpolation |
| `log.py` | Logging infrastructure |
| `result_manager.py` | Result aggregation |
| `oriole/client.py` | Test management API |
| `output.py` | Output formatting |

**Environment Service**:
```python
env = Environment()
env.load_config("env.conf")

# Get device config
device_ip = env.get("FGT_A", "IP")

# Variable interpolation
path = env.variable_interpolation("testcase/GLOBAL:VERSION/test.txt")
```

---

### Module 5: Scheduler (`lib/core/scheduler/`)

**Responsibilities**:
- Parallel test execution
- Task queue management
- Resource allocation
- Group test organization

**Key Files**:
| File | Purpose |
|------|---------|
| `task.py` | Individual test task |
| `group_task.py` | Group of related tests |
| `job.py` | Job scheduling logic |

**Parallel Execution**:
```python
# Create task group
group = GroupTask([test1, test2, test3])

# Execute in parallel (max 5 concurrent)
group.execute(max_workers=5)

# Collect results
results = group.get_results()
```

---

## Data Flow

### Complete Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         INPUT PHASE                              │
└──────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
        ▼                                             ▼
┌───────────────┐                             ┌──────────────┐
│  Test Script  │                             │ Environment  │
│  (.txt)       │                             │ Config (.conf)│
└───────┬───────┘                             └──────┬───────┘
        │                                            │
        │  "expect -e 'login:' -t 5"                │  "VERSION: trunk"
        │  "include GLOBAL:VERSION/test.txt"         │  "DUT: FGT_A"
        │                                            │
        └────────────────┬───────────────────────────┘
                         │
┌──────────────────────────────────────────────────────────────────┐
│                      COMPILATION PHASE                           │
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  Lexer        │  Tokenize: "expect" → Token(api='expect')
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  Parser       │  Structure: API calls, device sections
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  Schema       │  Validate: params match schema
                 │  Validator    │  Map: -e → rule, -t → timeout
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  VM Code      │  Generate: VMCode(10, "expect", ("login:", 5))
                 │  Generator    │
                 └───────┬───────┘
                         │
                         ▼
                 ┌───────────────┐
                 │  Compiler     │  Cache: compiled_codes[filepath] = vm_codes
                 │  Cache        │
                 └───────┬───────┘
                         │
┌──────────────────────────────────────────────────────────────────┐
│                     DEVICE INIT PHASE                            │
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
  ┌───────────────┐           ┌───────────────┐
  │  FGT_A        │           │  PC_01        │
  │  Telnet       │           │  SSH          │
  │  10.160.132.71│           │  10.6.30.11   │
  └───────┬───────┘           └───────┬───────┘
          │                           │
          └───────────┬───────────────┘
                      │
┌──────────────────────────────────────────────────────────────────┐
│                      EXECUTION PHASE                             │
└──────────────────────────────────────────────────────────────────┘
                      │
                      ▼
         ┌─────────────────────┐
         │  Executor           │
         │  PC = 0             │
         │  cur_device = None  │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │  Execution Loop     │
         │  while PC < len():  │
         │    execute_vm_code  │
         │    PC += 1          │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │  API Dispatch       │
         │  api_manager.call() │
         └──────────┬──────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌────────┐    ┌─────────┐    ┌──────────┐
│ expect │    │ command │    │  config  │
└───┬────┘    └────┬────┘    └─────┬────┘
    │              │               │
    └──────────────┼───────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │  Device Session  │
        │  send/receive    │
        └─────────┬────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  Result Manager  │
        │  Collect results │
        └─────────┬────────┘
                  │
┌──────────────────────────────────────────────────────────────────┐
│                      REPORTING PHASE                             │
└──────────────────────────────────────────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
┌──────────────┐      ┌──────────────┐
│ Local Output │      │ Oriole Upload│
│ - HTML       │      │ - API POST   │
│ - JSON       │      │ - Results    │
│ - Logs       │      │ - Metadata   │
└──────────────┘      └──────────────┘
```

---

## Deep Dive Topics

### Topic 0: Software Architecture & Design Patterns

**Deep Dive**: [Software Architecture & Design Patterns](SOFTWARE_ARCHITECTURE_DESIGN_PATTERNS.md)

**Key Concepts**:
- Current AutoLib v3 architecture (Direct Compilation + Custom VM)
- 6 alternative design patterns (Interpreter, AST Compiler, Embedded Python, Fluent API, Template Engine, Parser Generator)
- Comparative analysis (simplicity, performance, maintainability, debuggability)
- Design pattern implementation (Command, Strategy, Factory, Observer, Template Method)
- Trade-off matrix and decision tree
- Evolution paths and scalability considerations

**When to Read**:
- Understanding architectural decisions and trade-offs
- Evaluating alternative approaches for similar projects
- Learning why AutoLib doesn't use AST or embedded Python
- Making architecture decisions for DSLs
- Planning evolution and new features

---

### Topic 1: DSL Syntax and Compilation

**Deep Dive**: 
- [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) - High-level 5-stage pipeline
- [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) - Lexer/parser internals, control flow compilation, line number tracking

**Key Concepts**:
- How DSL syntax maps to Python API calls
- Schema-driven parameter validation
- VM code structure and execution model
- Control flow compilation (if/while/loop)
- Line number tracking for jump targets
- Recursive parsing with prev_vm_code linking
- ApiParams wrapper for backward compatibility

**When to Read**: 
- Adding new DSL commands
- Debugging compilation errors
- Understanding parameter mapping
- Understanding how control flow is compiled
- Investigating line number issues in VM codes

---

### Topic 2: Compiler Architecture Fundamentals

**Deep Dive**: [Compiler Architecture Comparison](COMPILER_ARCHITECTURE_COMPARISON.md)

**Key Concepts**:
- Universal compilation pipeline (Lexer → Parser → Code Gen → Execution)
- Python's compilation model (tokens → AST → bytecode → PVM)
- AutoLib v3's compilation model (tokens → VM codes → executor)
- AST-based vs direct VM code generation
- Stack-based vs hybrid execution models
- When to use each pattern (general-purpose vs DSL)

**When to Read**:
- Understanding compiler theory basics
- Comparing AutoLib with mainstream languages
- Learning why AutoLib doesn't build an AST
- Making architecture decisions for DSLs
- Educational context on compilation approaches

---

### Topic 3: Variable System

**Deep Dive**: [Variable Usage and Troubleshooting](VARIABLE_USAGE_AND_TROUBLESHOOTING.md)

**Key Concepts**:
- Two variable syntaxes: `$VAR` vs `{$VAR}`
- Compile-time vs runtime interpolation
- Environment config variables
- User-defined variables (setvar/intset/strset)

**When to Read**:
- Variable not expanding correctly
- Understanding variable scope
- Debugging pattern transformation issues

---

### Topic 4: Include Directive

**Deep Dive**: [Include Directive](INCLUDE_DIRECTIVE.md)

**Key Concepts**:
- Script modularization and reuse
- Variable interpolation in paths
- Recursive compilation
- Device context preservation

**When to Read**:
- Creating reusable test components
- Organizing large test suites
- Understanding include path resolution

---

### Topic 5: Executor and VM Code Execution

**Deep Dive**: [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md)

**Key Concepts**:
- Program counter (PC) mechanism
- VM code processing loop
- if_stack control flow management
- API dispatch and parameter handling
- Jump-based branching (forward/backward)
- Variable interpolation during execution

**When to Read**:
- Understanding how compiled VM codes execute
- Debugging control flow issues
- Learning how if/else/while work internally
- Understanding API parameter access patterns

---

### Topic 6: Control Flow

**Implementation**: `lib/core/executor/if_stack.py`

**Structures**:

**If/Else**:
```plaintext
if {$status} == "up"
    comment HA is active
elseif {$status} == "down"
    comment HA is inactive
else
    comment Unknown status
fi
```

**While Loop**:
```plaintext
<intset counter 0>
while {$counter} < 5
    command echo Iteration {$counter}
    <intadd counter 1>
endwhile
```

**VM Code Flow**:
```
Line  VM Code          Stack Action
1     if_start(cond)   Evaluate→ Push true/false
2     ...              Execute if true
3     else             Flip stack top
4     ...              Execute if was false
5     fi               Pop stack
```

---

### Topic 7: Error Handling

**Modes**:

1. **Strict Mode** (default):
   - Any error stops execution immediately
   - Suitable for validation tests
   - Exit code non-zero on failure

2. **Non-Strict Mode** (`--non_strict`):
   - Continue execution after errors
   - Suitable for exploration/debugging
   - All errors logged, final summary shows failures

**Error Types**:
| Type | Example | Handling |
|------|---------|----------|
| Compilation Error | Syntax error, unknown API | Stop immediately |
| Validation Error | Missing required param | Stop immediately |
| Connection Error | Device unreachable | Retry or fail |
| Timeout Error | Expect pattern not found | Skip or fail |
| Assertion Error | expect -fail match found match | Mark QAID failed |

**Error Recovery**:
```plaintext
# Retry on failure
<intset retry_count 0>
while {$retry_count} < 3
    expect -e "login:" -t 5
    if {$?} == 0
        comment Login successful
        break
    else
        comment Retry {$retry_count}
        <intadd retry_count 1>
    fi
endwhile
```

---

### Topic 8: Custom API Development

**Location**: `plugins/apis/`

**Structure**:
```python
# plugins/apis/my_custom.py

def my_api(executor, params):
    """
    Custom API implementation.
    
    Parameters:
        params.param1 (str): Description
        params.param2 (int): Description
    """
    # Access current device
    device = executor.cur_device
    
    # Execute device command
    output = device.send_command(params.command)
    
    # Record result
    executor.result_manager.add_qaid_expect_result(
        params.qaid,
        is_succeeded=True,
        output=output
    )
```

**Schema Definition** (`cli_syntax.json`):
```json
{
  "my_api": {
    "description": "My custom API",
    "category": "custom",
    "parse_mode": "positional",
    "parameters": [
      {"-c": {"alias": "command", "required": true}},
      {"-for": {"alias": "qaid", "required": true}}
    ]
  }
}
```

**Registration**: Auto-discovered from `plugins/apis/` on startup

---

## Execution Models

### Model 1: Sequential Execution

**Default behavior**: Execute one test at a time

```bash
python3 autotest.py -t test1.txt -e env.conf
python3 autotest.py -t test2.txt -e env.conf
```

**Pros**:
- Simple, predictable
- Easy to debug
- No resource conflicts

**Cons**:
- Slow for large test suites
- Underutilizes resources

---

### Model 2: Parallel Execution (Group)

**Use Case**: Run multiple independent tests simultaneously

```bash
python3 autotest.py -g test_group.txt -e env.conf
```

**test_group.txt**:
```plaintext
testcase/ips/test1.txt
testcase/ips/test2.txt
testcase/ips/test3.txt
```

**Execution**:
- Tests run in parallel (configurable workers)
- Each test gets own device pool
- Results aggregated at end

**Pros**:
- Fast execution for independent tests
- Good resource utilization

**Cons**:
- Requires isolated test environments
- More complex debugging

---

### Model 3: Multi-Device Coordination

**Use Case**: Test requires coordination between multiple devices

```plaintext
[FGT_A]
    config system ha
        set mode a-p
    end

[FGT_B]
    config system ha
        set mode a-p
    end

[FGT_A]
    expect -e "Primary" -t 30

[FGT_B]
    expect -e "Secondary" -t 30
```

**Execution**:
- Single test, multiple devices
- Sequential execution but coordinated
- Device context switches via `[DEVICE_NAME]`

---

## Error Handling

### Error Categories

1. **Pre-Execution Errors**
   - File not found
   - Invalid syntax
   - Schema validation failure
   - Connection failure

2. **Runtime Errors**
   - Timeout waiting for pattern
   - Command execution failure
   - Unexpected device output
   - Variable not defined

3. **Post-Execution Errors**
   - Result upload failure
   - Report generation failure

### Error Propagation

```
API Execution (expect.py)
    ↓ raises TimeoutError
Code Executor (code_executor.py)
    ↓ catches, logs, decides
Executor (executor.py)
    ↓ continue_on_error check
    ├─ True:  Log error, continue
    └─ False: Stop execution, cleanup
Main (autotest.py)
    ↓ final cleanup
Exit with code 0 (success) or 1 (failure)
```

### Debugging Tools

1. **Debug Mode** (`-d`):
   - Detailed token output
   - VM code dump
   - Step-by-step execution log

2. **Breakpoints**:
   ```plaintext
   breakpoint  # Pause execution, enter interactive mode
   ```

3. **Verbose Logging**:
   ```ini
   [GLOBAL]
   log_level: 7  # Maximum verbosity
   ```

4. **Output Preservation**:
   - All device output saved to `outputs/*/devices/`
   - Compilation artifacts in `lib/core/compiler/outputs/`

---

## Performance Considerations

### Compilation Performance

| Factor | Impact | Optimization |
|--------|--------|--------------|
| File size | ~1ms per 100 lines | Split large files |
| Include depth | Linear per level | Limit nesting to 3 levels |
| Variable count | Minimal | No practical limit |
| Cache hits | <1ms | Share includes across tests |

### Execution Performance

| Factor | Impact | Optimization |
|--------|--------|--------------|
| Device latency | ~100-500ms per command | Reduce command count |
| Timeout values | Directly proportional | Use realistic timeouts |
| Pattern complexity | Minimal (regex) | Simple patterns faster |
| Connection overhead | ~1-5s per device | Reuse connections |

### Memory Usage

| Component | Typical Usage | Peak Usage |
|-----------|---------------|------------|
| VM Codes | ~1KB per 100 lines | ~10MB for large suite |
| Device Buffers | ~10KB per device | ~100KB for verbose output |
| Result Data | ~1KB per QAID | ~1MB for 1000 QAIDs |
| Total | ~50MB | ~500MB for complex scenarios |

---

## Summary

AutoLib v3 provides a **complete test automation framework** with:

✅ **DSL-based scripting**: High-level language for test creation  
✅ **Multi-device support**: Coordinate tests across device topology  
✅ **Compile-time validation**: Catch errors before execution  
✅ **Flexible execution**: Sequential, parallel, distributed  
✅ **Comprehensive reporting**: Local and remote result tracking  
✅ **Extensible architecture**: Plugin system for custom APIs  

**Typical Workflow**:
1. Write test script in DSL (`.txt` file)
2. Configure environment (`.conf` file)
3. Run `autotest.py -t test.txt -e env.conf`
4. View results in `outputs/` or Oriole dashboard

**Next Steps**:
- Review [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) for compilation details
- Read [Variable Usage Guide](VARIABLE_USAGE_AND_TROUBLESHOOTING.md) for variable system
- Study [Include Directive](INCLUDE_DIRECTIVE.md) for script modularization
- Explore example tests in `testcase/` directory
- Check API implementations in `lib/core/executor/api/`

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Framework Version**: V3R10B0007
