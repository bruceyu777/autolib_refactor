# Executor Deep Dive - VM Code Processing and Control Flow

**Module**: `lib/core/executor/`  
**Version**: AutoLib v3 V3R10B0007  
**Purpose**: Understand how VM codes are executed and control flow is managed

---

## Table of Contents

1. [Executor Architecture](#executor-architecture)
2. [Main Execution Loop](#main-execution-loop)
3. [VM Code Structure](#vm-code-structure)
4. [Control Flow with if_stack](#control-flow-with-if_stack)
5. [API Dispatch Mechanism](#api-dispatch-mechanism)
6. [Parameter Handling](#parameter-handling)
7. [Real Execution Examples](#real-execution-examples)
8. [Jump Mechanism](#jump-mechanism)
9. [Variable Interpolation](#variable-interpolation)

---

## Executor Architecture

### Class Structure

```python
class Executor:
    def __init__(self, script, devices, need_report=True):
        self.script = script              # Compiled Script object
        self.devices = devices             # Dict of device objects {'FGT_B': device}
        self.cur_device = None            # Currently active device
        self.result_manager = ScriptResultManager()
        self.program_counter = 0          # PC: Current VM code index
        self.last_line_number = None      # Last executed DSL line number
        self.api_handler = ApiHandler(self)  # API dispatcher
        self.need_stop = False            # Abort execution flag
```

### Key Components

| Component | Purpose | File |
|-----------|---------|------|
| **Executor** | Main execution loop, PC management | `executor.py` |
| **ApiHandler** | API discovery and dispatch | `api_manager.py` |
| **ApiParams** | Parameter adapter (tuple ↔ named access) | `api_params.py` |
| **if_stack** | Control flow stack (if/else/while) | `if_stack.py` |
| **VMCode** | Compiled instruction structure | `compiler/vm_code.py` |
| **Script** | Compiled script with VM codes | `compiler/script.py` |

---

## Main Execution Loop

### Execution Flow

```python
def execute(self):
    """Main VM code execution loop - the heart of AutoLib."""
    
    total_code_lines = self.script.get_program_counter_limit()
    
    while self.program_counter < total_code_lines:
        # 1. Fetch next VM code and update PC for debugging
        self.program_counter, code = self.script.update_code_to_execute(
            self.program_counter
        )
        
        # 2. Extract operation and parameters
        operation = code.operation      # e.g., "expect", "if_not_goto", "comment"
        parameters = code.parameters    # e.g., ("Version:", "QAID", "5")
        
        # 3. Log execution (skip noise from comment/with_device)
        if operation not in ["comment", "with_device"]:
            line_number = code.line_number
            if self.last_line_number != line_number:
                logger.debug("Line #%d - '%s'", 
                    line_number, 
                    self.script.get_script_line(line_number))
                self.last_line_number = line_number
        
        # 4. Variable interpolation (except for device switching)
        if operation not in ["switch_device", "setenv"]:
            parameters = self.variable_replacement(parameters)
        
        # 5. Check for internal commands (executor methods)
        internal_command = self.get_internal_command(operation)
        if internal_command:
            internal_command(parameters)
        else:
            # 6. Dispatch to API handler
            self.api_handler.execute_api(operation, parameters)
        
        # 7. Increment PC (unless control flow API modified it)
        if operation not in ["if_not_goto", "else", "elseif", "until"]:
            self.program_counter += 1
        
        # 8. Check for abort signal
        if self.need_stop:
            break
```

### Program Counter (PC) Management

The **program counter** is the core of execution flow:

```python
# Initial state
self.program_counter = 0

# Normal execution: PC increments
while PC < total_vm_codes:
    execute(vm_codes[PC])
    PC += 1

# Control flow: PC jumps based on conditions
# Example: if_not_goto jumps PC forward
# Example: until jumps PC backward (loops)
```

**Key Insight**: Control flow APIs (`if_not_goto`, `else`, `elseif`, `until`) modify the PC directly, so the main loop **doesn't increment** after these operations.

---

## VM Code Structure

### VMCode Data Class

```python
class VMCode:
    def __init__(self, line_number, operation, parameters):
        self.line_number = line_number    # Original DSL line (for debugging)
        self.operation = operation        # API name or control flow marker
        self.parameters = parameters      # Tuple of parameters
```

### Real VM Code Examples

**Example 1: Device Switching**
```python
VMCode(
    line_number=2,
    operation="switch_device",
    parameters=("FGT_B",)
)
```

**Example 2: Variable Definition**
```python
VMCode(
    line_number=11,
    operation="strset",
    parameters=("QAID_MAIN", "205817")
)
```

**Example 3: API Call (expect)**
```python
VMCode(
    line_number=50,
    operation="expect",
    parameters=(
        "Version: FortiGate",  # rule (pattern)
        "QAID_CONN_RETRY",     # qaid (variable name, interpolated later)
        "5",                   # timeout
        "unmatch",             # fail_match
        None,                  # invert_check
        None,                  # allow_ctrl_c
        "yes",                 # need_clear
        None,                  # msg
        "3"                    # retry_cnt
    )
)
```

**Example 4: Control Flow (if_not_goto)**
```python
VMCode(
    line_number=98,
    operation="if_not_goto",
    parameters=(
        "platform_type",       # variable to check
        "eq",                  # comparison operator
        "FortiGate-VM64",      # value to compare
        103                    # jump target line number
    )
)
```

**Example 5: Loop (until)**
```python
VMCode(
    line_number=59,
    operation="until",
    parameters=(
        44,                    # loop start line number
        "retry_count",         # variable to check
        "eq",                  # operator
        "max_retries"          # value to compare
    )
)
```

---

## Control Flow with if_stack

### if_stack Implementation

**File**: `lib/core/executor/if_stack.py`

```python
class IfStack:
    """
    Stack-based control flow manager.
    
    Tracks nested if/else conditions to determine whether 
    to execute or skip code blocks.
    """
    def __init__(self):
        self.stack = []    # Stack of boolean values
    
    def push(self, if_matched):
        """Push condition result onto stack."""
        self.stack.append(if_matched)
    
    def pop(self):
        """Pop condition result from stack."""
        return self.stack.pop()
    
    def top(self):
        """Peek at top of stack (current condition state)."""
        return self.stack[-1]

# Global singleton instance
if_stack = IfStack()
```

### How if_stack Works

**Stack States**:
- `True` on stack → Current branch is executing
- `False` on stack → Current branch is skipped
- Empty stack → Normal execution (no conditionals active)

**Example Scenario**:
```plaintext
DSL Source:
  <if {$platform_type} eq FortiGate-VM64>
      comment Branch A
  <elseif {$platform_type} eq FortiGate-VM64-KVM>
      comment Branch B
  <else>
      comment Branch C
  <fi>

VM Codes:
  98  if_not_goto platform_type eq FortiGate-VM64 103
  99  comment Branch A
  100 ...
  103 elseif platform_type eq FortiGate-VM64-KVM 107
  104 comment Branch B
  105 ...
  107 else 110
  108 comment Branch C
  109 ...
  110 endif
```

**Execution Trace** (when `platform_type = "FortiGate-VM64-KVM"`):

| PC | Operation | Action | Stack State | PC After |
|----|-----------|--------|-------------|----------|
| 98 | `if_not_goto platform_type eq FortiGate-VM64 103` | Evaluate: "VM64-KVM" == "VM64" → **FALSE** | [] |  |
|  | | Push FALSE to stack | [FALSE] |  |
|  | | Jump to line 103 | [FALSE] | 103 |
| 103 | `elseif platform_type eq FortiGate-VM64-KVM 107` | Stack top is FALSE → Check condition |  |  |
|  | | Evaluate: "VM64-KVM" == "VM64-KVM" → **TRUE** |  |  |
|  | | Pop FALSE, push TRUE | [TRUE] |  |
|  | | Continue execution | [TRUE] | 104 |
| 104 | `comment Branch B` | Stack top is TRUE → Execute | [TRUE] | 105 |
| 107 | `else 110` | Stack top is TRUE → Skip else | [TRUE] |  |
|  | | Jump to line 110 | [TRUE] | 110 |
| 110 | `endif` | Pop stack | [] | 111 |

### Control Flow API Implementations

#### if_not_goto

**File**: `lib/core/executor/api/control_flow.py`

```python
def if_not_goto(executor, params):
    """
    Conditional jump if expression is FALSE.
    
    VM Code: if_not_goto <var> <op> <value> <line_number>
    Example: if_not_goto retry_count < max_retries 58
    
    Logic:
      1. Evaluate expression
      2. If TRUE → push TRUE, continue (PC+1)
      3. If FALSE → push FALSE, jump to line_number
    """
    # Extract parameters (variable length)
    parameters = params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    
    line_number = parameters[-1]    # Jump target
    expression = parameters[:-1]     # Expression tokens
    
    if executor.eval_expression(expression):
        # Condition TRUE → execute if block
        if_stack.push(True)
        executor.program_counter += 1
    else:
        # Condition FALSE → skip if block
        if_stack.push(False)
        executor.jump_forward(line_number)
```

**Real Example**:
```python
# VM Code: if_not_goto retry_count < max_retries 58
# Variables: retry_count=1, max_retries=3

# Evaluation:
expression = ["retry_count", "<", "max_retries"]
executor.eval_expression(expression)
# → "1 < 3" → TRUE

# Action:
if_stack.push(True)      # Will execute if block
executor.program_counter += 1  # PC = 57 (continue)
```

#### else_

```python
def else_(executor, params):
    """
    Else clause - flips execution state.
    
    VM Code: else <line_number>
    Example: else 110
    
    Logic:
      1. Check if_stack top
      2. If TRUE (if block executed) → jump to endif
      3. If FALSE (if block skipped) → continue (execute else)
    """
    parameters = params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    line_number = parameters[-1]
    
    if if_stack.top():
        # If block was executed → skip else block
        executor.jump_forward(line_number)
    else:
        # If block was skipped → execute else block
        executor.program_counter += 1
```

**Real Example**:
```python
# Stack state: [True] (if block executed)
# VM Code: else 110

if if_stack.top():  # True
    executor.jump_forward(110)  # Skip else, jump to endif
```

#### elseif

```python
def elseif(executor, params):
    """
    Else-if clause - check alternative condition.
    
    VM Code: elseif <var> <op> <value> <line_number>
    Example: elseif platform_type eq FortiGate-VM64-KVM 107
    
    Logic:
      1. If previous if/elseif was TRUE → skip (jump to next)
      2. If previous was FALSE → evaluate new condition
         - If TRUE → pop old FALSE, push TRUE, continue
         - If FALSE → jump to next elseif/else
    """
    parameters = params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    
    line_number = parameters[-1]
    expression = parameters[:-1]
    
    if if_stack.top():
        # Previous condition matched → skip this elseif
        executor.jump_forward(line_number)
    else:
        # Previous condition failed → check this condition
        if executor.eval_expression(expression):
            # This condition matches
            if_stack.pop()       # Remove old FALSE
            if_stack.push(True)  # Push new TRUE
            executor.program_counter += 1
        else:
            # This condition also fails → skip to next
            executor.jump_forward(line_number)
```

**Real Example**:
```python
# Stack state: [False] (previous if failed)
# VM Code: elseif platform_type eq FortiGate-VM64-KVM 107
# Variable: platform_type = "FortiGate-VM64-KVM"

if if_stack.top():  # False → check elseif condition
    pass
else:
    # Evaluate: "FortiGate-VM64-KVM" eq "FortiGate-VM64-KVM" → TRUE
    if executor.eval_expression(expression):
        if_stack.pop()      # Stack: []
        if_stack.push(True) # Stack: [True]
        executor.program_counter += 1  # Continue to line 104
```

#### endif

```python
def endif(executor, params):
    """
    End if block - pop condition from stack.
    
    VM Code: endif
    
    Logic:
      Simply pop the if condition from stack
    """
    if_stack.pop()
```

#### until (Loop End)

```python
def until(executor, params):
    """
    Loop end - check exit condition or jump back.
    
    VM Code: until <loop_start_line> <var> <op> <value>
    Example: until 44 retry_count eq max_retries
    
    Logic:
      1. Evaluate exit condition
      2. If TRUE → exit loop (PC+1)
      3. If FALSE → jump back to loop start
    """
    parameters = params._raw if hasattr(params, "_raw") else list(params.to_dict().values())
    
    line_number = parameters[0]  # Loop start line
    expression = parameters[1:]   # Exit condition
    
    # Interpolate variables in expression
    new_expression = []
    for token in expression:
        if token.startswith("$"):
            new_token = env.get_var(token[1:])
            new_expression.append(new_token if new_token else token)
        else:
            new_expression.append(token)
    
    if executor.eval_expression(new_expression):
        # Exit condition TRUE → exit loop
        executor.program_counter += 1
    else:
        # Exit condition FALSE → continue loop
        executor.jump_backward(line_number)
```

**Real Example**:
```python
# VM Code: until 44 retry_count eq max_retries
# Variables: retry_count=3, max_retries=3

# Build expression:
new_expression = []
for token in ["retry_count", "eq", "max_retries"]:
    if token.startswith("$"):
        new_expression.append(env.get_var(token[1:]))
    else:
        new_expression.append(token)

# Result: ["retry_count", "eq", "max_retries"]
# Evaluate: 3 == 3 → TRUE

# Action:
executor.program_counter += 1  # Exit loop, continue to line 60
```

### Nested If Example

**DSL**:
```plaintext
<if {$outer} eq yes>
    <if {$inner} eq yes>
        comment Nested true
    <else>
        comment Nested false
    <fi>
<else>
    comment Outer false
<fi>
```

**Stack Trace** (outer=yes, inner=no):

| Operation | Stack State | Action |
|-----------|-------------|--------|
| `if_not_goto outer eq yes` | [True] | Outer condition TRUE |
| `if_not_goto inner eq yes` | [True, False] | Inner condition FALSE, skip |
| `else` | [True, False] | Inner else, continue |
| `comment Nested false` | [True, False] | Execute |
| `endif` | [True] | Pop inner |
| `else` | [True] | Outer was TRUE, skip outer else |
| `endif` | [] | Pop outer |

---

## API Dispatch Mechanism

### ApiHandler Class

**File**: `lib/core/executor/api_manager.py`

```python
class ApiHandler:
    """Handles API discovery and execution."""
    
    def __init__(self, executor):
        self.executor = executor
        # Auto-discover all APIs on first use
        discover_apis()
    
    def execute_api(self, api_name, raw_params):
        """
        Execute an API by name with parameters.
        
        Args:
            api_name: API function name (e.g., "expect", "setvar")
            raw_params: Tuple of parameters
        
        Flow:
            1. Lookup API function in registry
            2. Load schema for parameter mapping
            3. Create ApiParams wrapper
            4. Inject context for user-defined APIs
            5. Execute API function
        """
        # 1. Get API function from registry
        api_func = _API_REGISTRY.get(api_name)
        if not api_func:
            raise ValueError(f"Unknown API: {api_name}")
        
        # 2. Load schema for parameter validation
        schema = get_schema(api_name)
        
        # 3. Create parameter wrapper
        params = ApiParams(raw_params, schema)
        
        # 4. Inject context for user-defined APIs
        if not is_builtin_category(api_func):
            # User APIs need context (devices, variables, config)
            context = _build_context(self.executor)
            params = ApiParams({"context": context, **params.to_dict()}, schema)
        
        # 5. Execute API
        try:
            result = api_func(self.executor, params)
            return result
        except Exception as e:
            logger.error("API %s failed: %s", api_name, e)
            raise
```

### API Discovery

**Auto-discovery Process**:

1. **Scan Built-in APIs** (`lib/core/executor/api/*.py`):
   ```python
   api_package = lib.core.executor.api
   for module_file in api_package_dir.glob("*.py"):
       module = importlib.import_module(f"lib.core.executor.api.{module_name}")
       _register_module_functions(module, "Built-In - Expect")
   ```

2. **Scan User APIs** (`plugins/apis/*.py`):
   ```python
   plugins_dir = base_path / "plugins" / "apis"
   for py_file in plugins_dir.rglob("*.py"):
       module = importlib.util.module_from_spec(spec)
       _register_module_functions(module, "User-Defined - Custom")
   ```

3. **Register Public Functions**:
   ```python
   def _register_module_functions(module, category):
       for name, obj in inspect.getmembers(module, inspect.isfunction):
           if not name.startswith("_"):
               api_endpoint = name.rstrip("_")  # else_ → else
               _API_REGISTRY[api_endpoint] = obj
               _CATEGORY_REGISTRY[category].append(api_endpoint)
   ```

**Result**: Global registry mapping API names to functions
```python
_API_REGISTRY = {
    "expect": <function expect at 0x...>,
    "setvar": <function setvar at 0x...>,
    "if_not_goto": <function if_not_goto at 0x...>,
    "else": <function else_ at 0x...>,
    ...
}
```

---

## Parameter Handling

### ApiParams Adapter

**File**: `lib/core/executor/api_params.py`

**Purpose**: Bridge between tuple-based VM codes and named parameter access

```python
class ApiParams:
    """
    Dual-access parameter adapter.
    
    Enables:
      - Named access: params.rule
      - Dict access: params["rule"]
      - Tuple unpacking: (rule, qaid) = params
      - Schema validation
    """
    
    def __init__(self, data, schema=None):
        self._raw = data          # Original tuple/dict
        self._schema = schema     # API schema for mapping
        self._data = self._normalize(data, schema)
    
    def _normalize(self, data, schema):
        """
        Convert tuple to dict using schema.
        
        Example:
          data = ("Version:", "QAID", "5")
          schema.param_order = ["rule", "qaid", "wait_seconds"]
          
          Result: {
              "rule": "Version:",
              "qaid": "QAID",
              "wait_seconds": "5"
          }
        """
        if isinstance(data, (tuple, list)) and schema:
            result = {}
            param_order = schema.get_param_order()
            
            for i, param_name in enumerate(param_order):
                if i < len(data):
                    result[param_name] = data[i]
                else:
                    # Use default from schema
                    param_schema = schema.get_param(param_name)
                    if param_schema and param_schema.default:
                        result[param_name] = param_schema.default
            
            return result
        return data
```

### Schema-Driven Mapping

**Schema Definition** (cli_syntax.json):
```json
{
  "expect": {
    "parameters": [
      {"-e": {"alias": "rule", "position": 0, "required": true}},
      {"-for": {"alias": "qaid", "position": 1, "required": false, "default": "NO_QAID"}},
      {"-t": {"alias": "wait_seconds", "position": 2, "type": "int", "default": 5}}
    ]
  }
}
```

**Mapping Process**:
```python
# VM Code parameters (tuple):
raw_params = ("Version: FortiGate", "QAID_CONN_RETRY", "5")

# Schema loads and maps:
schema = get_schema("expect")
params = ApiParams(raw_params, schema)

# Normalized dict (named access):
params._data = {
    "rule": "Version: FortiGate",
    "qaid": "QAID_CONN_RETRY",
    "wait_seconds": 5  # Auto-cast to int
}

# API uses named access:
def expect(executor, params):
    rule = params.rule              # "Version: FortiGate"
    qaid = params.qaid              # "QAID_CONN_RETRY"
    timeout = params.wait_seconds   # 5 (int)
```

### Backward Compatibility

**Old Style** (tuple unpacking):
```python
def old_api(executor, params):
    # Still works via __iter__
    (rule, qaid, timeout) = params
```

**New Style** (named access):
```python
def new_api(executor, params):
    rule = params.rule
    qaid = params.qaid
    timeout = params.get("timeout", 10)  # With default
```

---

## Real Execution Examples

### Example 1: Simple Command Execution

**DSL**:
```plaintext
[FGT_B]
    get system status
```

**VM Codes**:
```plaintext
2  switch_device FGT_B
49 command get system status
```

**Execution Trace**:

| PC | VM Code | Executor Action | Device I/O |
|----|---------|-----------------|------------|
| 0 | `switch_device FGT_B` | `executor.cur_device = devices['FGT_B']` | - |
| 1 | `command get system status` | `executor._command(("get system status",))` | → `get system status` |
|  |  | `cur_device.send_command("get system status")` | ← `Version: FortiGate...` |

**Code Flow**:
```python
# PC=0
code = VMCode(2, "switch_device", ("FGT_B",))
internal_cmd = executor.get_internal_command("switch_device")
# → executor._switch_device
internal_cmd(("FGT_B",))
# executor.cur_device = devices['FGT_B']
PC = 1

# PC=1
code = VMCode(49, "command", ("get system status",))
internal_cmd = executor.get_internal_command("command")
# → executor._command
internal_cmd(("get system status",))
# device.send_command("get system status")
# → Device output received
PC = 2
```

---

### Example 2: If/Else Branch

**DSL**:
```plaintext
<if {$platform_type} eq FortiGate-VM64-KVM>
    comment Detected KVM platform
<else>
    comment Other platform
<fi>
```

**VM Codes**:
```plaintext
103 elseif platform_type eq FortiGate-VM64-KVM 107
104 comment Detected KVM platform
105 expect Virtual QAID_VM64_KVM_CHECK 5 ...
107 else 110
108 comment Other platform
110 endif
```

**Execution Trace** (platform_type = "FortiGate-VM64-KVM"):

| PC | VM Code | Stack | Eval | Action | Next PC |
|----|---------|-------|------|--------|---------|
| 103 | `elseif platform_type eq FortiGate-VM64-KVM 107` | [False] | | Stack top FALSE, check condition | |
|  |  |  | "VM64-KVM" == "VM64-KVM" → TRUE | Pop FALSE, push TRUE | |
|  |  | [True] | | Continue execution | 104 |
| 104 | `comment Detected KVM platform` | [True] | | Execute comment | 105 |
| 105 | `expect Virtual ...` | [True] | | Execute expect API | 106 |
| 107 | `else 110` | [True] | | Stack top TRUE → Jump | 110 |
| 110 | `endif` | [True] | | Pop stack | 111 |
|  |  | [] | | Continue | 111 |

**Detailed Code Execution**:

```python
# PC=103: elseif
code = VMCode(103, "elseif", ("platform_type", "eq", "FortiGate-VM64-KVM", 107))

# Control flow API
api_func = _API_REGISTRY["elseif"]
params = ApiParams(("platform_type", "eq", "FortiGate-VM64-KVM", 107), schema)
api_func(executor, params)

# Inside elseif():
if if_stack.top():  # False (previous if failed)
    pass
else:
    expression = ["platform_type", "eq", "FortiGate-VM64-KVM"]
    if executor.eval_expression(expression):  # TRUE
        if_stack.pop()       # Stack: [False] → []
        if_stack.push(True)  # Stack: [] → [True]
        executor.program_counter += 1  # PC = 104

# PC=104: comment
code = VMCode(104, "comment", ("Detected KVM platform",))
api_func = _API_REGISTRY["comment"]
api_func(executor, params)
# Prints: "Detected KVM platform"
PC = 105

# PC=105: expect
code = VMCode(105, "expect", ("Virtual", "QAID_VM64_KVM_CHECK", "5", ...))
# Variable interpolation:
parameters = executor.variable_replacement(("Virtual", "QAID_VM64_KVM_CHECK", ...))
# QAID_VM64_KVM_CHECK → "205819"
parameters = ("Virtual", "205819", "5", ...)

api_func = _API_REGISTRY["expect"]
params = ApiParams(parameters, schema)
api_func(executor, params)
# device.expect("Virtual", timeout=5)
# → Match found, QAID 205819 PASS
PC = 106

# PC=107: else
code = VMCode(107, "else", (110,))
api_func = _API_REGISTRY["else"]
api_func(executor, params)

# Inside else_():
if if_stack.top():  # True (if block executed)
    executor.jump_forward(110)  # Skip else block
    # PC = 110

# PC=110: endif
code = VMCode(110, "endif", ())
api_func = _API_REGISTRY["endif"]
api_func(executor, params)

# Inside endif():
if_stack.pop()  # Stack: [True] → []
PC = 111
```

---

### Example 3: While Loop with Retry

**DSL**:
```plaintext
<intset retry_count 0>
<intset max_retries 3>

<while {$retry_count} < {$max_retries}>
    <intchange {$retry_count} + 1>
    comment Attempt {$retry_count}
    get system status
    expect -e "Version:" -for {$QAID} -t 5
<endwhile {$retry_count} eq {$max_retries}>
```

**VM Codes**:
```plaintext
37 intset retry_count 0
38 intset max_retries 3
44 loop {$retry_count} < {$max_retries}
45 intchange retry_count + 1
46 comment Attempt {$retry_count} of {$max_retries}...
49 command get system status
50 expect Version: FortiGate QAID_CONN_RETRY 5 ...
59 until 44 retry_count eq max_retries
```

**Execution Trace** (Full Loop - 3 Iterations):

**Iteration 1**:
| PC | VM Code | Variables | Stack | Action |
|----|---------|-----------|-------|--------|
| 37 | `intset retry_count 0` | retry_count=0 | [] | Set variable |
| 38 | `intset max_retries 3` | max_retries=3 | [] | Set variable |
| 44 | `loop {$retry_count} < {$max_retries}` | retry_count=0, max_retries=3 | [] | Check: 0<3 → TRUE |
| 45 | `intchange retry_count + 1` | retry_count=1 | [] | Increment |
| 46 | `comment Attempt 1 of 3...` | - | [] | Display (interpolated) |
| 49 | `command get system status` | - | [] | Send command to device |
| 50 | `expect Version: FortiGate ...` | - | [] | Pattern match → PASS |
| 59 | `until 44 retry_count eq max_retries` | retry_count=1, max_retries=3 | [] | Check: 1==3 → FALSE |
|  |  |  |  | Jump back to PC=44 |

**Iteration 2**:
| PC | VM Code | Variables | Action |
|----|---------|-----------|--------|
| 44 | `loop {$retry_count} < {$max_retries}` | retry_count=1 | Check: 1<3 → TRUE |
| 45 | `intchange retry_count + 1` | retry_count=2 | Increment |
| 46 | `comment Attempt 2 of 3...` | - | Display |
| 49 | `command get system status` | - | Send command |
| 50 | `expect Version: FortiGate ...` | - | Pattern match → PASS |
| 59 | `until 44 retry_count eq max_retries` | retry_count=2 | Check: 2==3 → FALSE, Jump to 44 |

**Iteration 3**:
| PC | VM Code | Variables | Action |
|----|---------|-----------|--------|
| 44 | `loop {$retry_count} < {$max_retries}` | retry_count=2 | Check: 2<3 → TRUE |
| 45 | `intchange retry_count + 1` | retry_count=3 | Increment |
| 46 | `comment Attempt 3 of 3...` | - | Display |
| 49 | `command get system status` | - | Send command |
| 50 | `expect Version: FortiGate ...` | - | Pattern match → PASS |
| 59 | `until 44 retry_count eq max_retries` | retry_count=3 | Check: 3==3 → TRUE, Exit loop |
| 61 | `comment Connection attempts completed...` | - | Continue execution |

**Detailed Code Flow**:

```python
# First iteration - PC=44
code = VMCode(44, "loop", ("{$retry_count} < {$max_retries}",))
# Note: loop API does nothing, just a marker

# PC=45
code = VMCode(45, "intchange", ("retry_count", "+", "1"))
api_func = _API_REGISTRY["intchange"]
api_func(executor, params)
# env.set_var("retry_count", 0 + 1)  # retry_count = 1

# PC=59
code = VMCode(59, "until", (44, "retry_count", "eq", "max_retries"))
api_func = _API_REGISTRY["until"]
params = ApiParams((44, "retry_count", "eq", "max_retries"), schema)
api_func(executor, params)

# Inside until():
line_number = 44  # Loop start
expression = ["retry_count", "eq", "max_retries"]

# Interpolate variables:
new_expression = []
for token in expression:
    if token.startswith("$"):
        new_token = env.get_var(token[1:])
        new_expression.append(new_token if new_token else token)
    else:
        new_expression.append(token)

# Result: ["retry_count", "eq", "max_retries"]
# Eval: 1 == 3 → FALSE

if executor.eval_expression(new_expression):  # FALSE
    pass
else:
    executor.jump_backward(44)  # Jump back to loop start
    # PC = 44
```

---

## Jump Mechanism

### Forward Jump (if/else skip)

```python
def jump_forward(self, line_number):
    """
    Jump forward to a specific DSL line number.
    
    Args:
        line_number: Target line number in DSL source
    
    Process:
        Increment PC until vm_code.line_number == target
    """
    self.__jump(line_number, forward=True)

def __jump(self, target_line_number, forward=True):
    step = 1 if forward else -1
    
    while True:
        code = self.script.get_compiled_code_line(self.program_counter)
        if code.line_number == target_line_number:
            break
        self.program_counter += step
```

**Example**:
```python
# Current PC: 98, line_number: 98
# Target: line 103
# VM codes:
#   PC=98: VMCode(line=98, op="if_not_goto", ...)
#   PC=99: VMCode(line=99, op="comment", ...)
#   PC=100: VMCode(line=100, op="command", ...)
#   PC=101: VMCode(line=101, op="expect", ...)
#   PC=102: VMCode(line=103, op="elseif", ...)  # line_number=103!

jump_forward(103):
    PC=98: line_number=98 ≠ 103 → PC=99
    PC=99: line_number=99 ≠ 103 → PC=100
    PC=100: line_number=100 ≠ 103 → PC=101
    PC=101: line_number=101 ≠ 103 → PC=102
    PC=102: line_number=103 == 103 → STOP
    
Final PC: 102
```

### Backward Jump (loop)

```python
def jump_backward(self, line_number):
    """
    Jump backward to loop start.
    
    Args:
        line_number: Target line number (loop start)
    
    Process:
        Decrement PC until vm_code.line_number == target
    """
    self.__jump(line_number, forward=False)
```

**Example**:
```python
# Current PC: 59, line_number: 59 (until)
# Target: line 44 (loop start)
# VM codes:
#   PC=44: VMCode(line=44, op="loop", ...)
#   PC=45: VMCode(line=45, op="intchange", ...)
#   ...
#   PC=59: VMCode(line=59, op="until", ...)

jump_backward(44):
    PC=59: line_number=59 ≠ 44 → PC=58
    PC=58: line_number=58 ≠ 44 → PC=57
    ...continued decrement...
    PC=45: line_number=45 ≠ 44 → PC=44
    PC=44: line_number=44 == 44 → STOP
    
Final PC: 44
```

---

## Variable Interpolation

### Two-Pass System

**Pass 1: Environment Variables** (Compile-time)
```python
# In compiler during VM code generation
parameter = env.variable_interpolation(parameter, current_device)

# Example:
"testcase/GLOBAL:VERSION/test.txt" 
→ "testcase/trunk/test.txt"
```

**Pass 2: User-Defined Variables** (Runtime)
```python
# In executor during execution
def variable_replacement(self, parameters):
    replaced = []
    for parameter in parameters:
        if isinstance(parameter, str):
            parameter = self._variable_interpolation(parameter)
        replaced.append(parameter)
    return tuple(replaced)

def _user_defined_variable_interpolation(self, _string):
    # Find all {$VAR} patterns
    matched = re.findall(r"{\$.*?}", _string)
    for m in matched:
        var_name = m[2:-1]  # Strip {$ and }
        value = env.get_var(var_name)
        if value is not None:
            _string = _string.replace(m, str(value))
    return _string
```

**Example**:
```python
# Before execution:
parameters = ("Version:", "{$QAID_CONN_RETRY}", "5")

# Variable interpolation:
env.vars = {"QAID_CONN_RETRY": "205801"}

# After interpolation:
parameters = ("Version:", "205801", "5")
```

**Full Example from first_case.txt**:
```python
# VM Code:
VMCode(50, "expect", ("Version: FortiGate", "QAID_CONN_RETRY", "5", ...))

# Runtime variables:
env.vars = {
    "QAID_CONN_RETRY": "205801",
    "QAID_VERSION_CHECK": "205817",
    "retry_count": 3,
    ...
}

# Executor processes:
parameters = ("Version: FortiGate", "QAID_CONN_RETRY", "5", ...)

# Variable replacement:
replaced = executor.variable_replacement(parameters)

# For each parameter:
#   "Version: FortiGate" → No {$, unchanged
#   "QAID_CONN_RETRY" → Check if variable, yes: "205801"
#   "5" → Unchanged

# Result:
replaced = ("Version: FortiGate", "205801", "5", ...)
```

---

## Summary

### Execution Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   EXECUTOR MAIN LOOP                        │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │  PC < total_vm_codes?   │
          └─────────┬───────────────┘
                    │ YES
                    ▼
          ┌─────────────────────────┐
          │ Fetch VMCode at PC      │
          │ code = vm_codes[PC]     │
          └─────────┬───────────────┘
                    │
                    ▼
          ┌─────────────────────────┐
          │ Extract operation +     │
          │ parameters              │
          └─────────┬───────────────┘
                    │
                    ▼
          ┌─────────────────────────┐
          │ Variable interpolation  │
          │ {$VAR} → value          │
          └─────────┬───────────────┘
                    │
         ┌──────────┴──────────────┐
         │                         │
         ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│ Internal Command?│    │   API Dispatch   │
│ (switch_device,  │    │  (expect, setvar,│
│  command, etc)   │    │   if_not_goto)   │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         │   ┌───────────────────┘
         │   │
         ▼   ▼
┌─────────────────────────────────┐
│        Execute Action           │
│  - Device I/O                   │
│  - Variable manipulation        │
│  - Control flow (if_stack)      │
│  - Results recording            │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  Update Program Counter         │
│  - Normal: PC + 1               │
│  - Control flow: Modified by API│
│    (jump_forward, jump_backward)│
└─────────┬───────────────────────┘
          │
          └─────► (Loop back to PC check)
```

### Key Components Summary

| Component | Responsibility | File |
|-----------|---------------|------|
| **Executor** | Main loop, PC management, variable interpolation | `executor.py` |
| **if_stack** | Track nested if/else conditions | `if_stack.py` |
| **ApiHandler** | Auto-discover and dispatch APIs | `api_manager.py` |
| **ApiParams** | Convert tuple → named access | `api_params.py` |
| **VMCode** | Compiled instruction structure | `compiler/vm_code.py` |
| **Control Flow APIs** | if_not_goto, else, elseif, until | `api/control_flow.py` |

### Control Flow Mechanism

1. **if_stack** maintains execution state (execute vs skip)
2. **Control flow APIs** modify PC via jumps
3. **Normal APIs** always increment PC
4. **Jump methods** scan VM codes to find target line number

### Variable System

- **Environment vars**: `$VAR` (compile-time from .conf)
- **User vars**: `{$VAR}` (runtime from setvar/intset/strset)
- **Interpolation**: Happens before API execution

### API Execution

1. **Fetch** VM code at PC
2. **Interpolate** variables in parameters
3. **Dispatch** to internal command or API
4. **Execute** with ApiParams wrapper
5. **Update** PC (normal +1 or control flow jump)

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-18  
**Framework Version**: AutoLib v3 V3R10B0007
