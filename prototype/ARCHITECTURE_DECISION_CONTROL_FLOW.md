# Architecture Decision: Control Flow in DSL-to-Pytest Conversion

## Decision Summary

**STATUS**: ✅ **APPROVED** - Use Native Python Control Flow

**DATE**: December 2024

**CONTEXT**: How to handle DSL control flow (if/while/for) when converting to pytest

---

## Background

### AutoLib v3 Traditional Architecture

```
┌─────────────┐
│  DSL Script │
│  (with      │
│  if/while)  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│    Compiler     │  Parses DSL, generates VM_CODE
│  (vm_code.py)   │  Control flow → line jumps
└──────┬──────────┘
       │
       ▼
┌──────────────────────────────┐
│         VM_CODE              │
│  [                           │
│    VMCode("command", ...),   │
│    VMCode("expect", ...),    │
│    VMCode("jump_if", ...),   │  ← Control flow as jumps
│    VMCode("jump", ...),      │
│  ]                           │
└──────┬───────────────────────┘
       │
       ▼
┌────────────────────────┐
│  Executor              │
│  .execute_vm_code()    │  Interprets VM_CODE
│  .program_counter      │  Handles jumps
│  .jump logic           │
└────────────────────────┘
```

**Key Points:**
- Compiler converts control flow to line number jumps
- VM_CODE is a list of instructions with jump targets
- Executor maintains program_counter and interprets jumps
- This works well for AutoLib v3's DSL execution model

### DSL-to-Pytest Current Architecture (Phase 2)

```
┌─────────────┐
│  DSL Script │
│  (linear,   │
│  no control │
│  flow yet)  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   Transpiler    │  Direct DSL → Python conversion
│  (dsl_parser)   │  No VM_CODE generation
└──────┬──────────┘
       │
       ▼
┌──────────────────────────────┐
│     pytest Test              │
│  def test_205812():          │
│    fgt.execute("cmd")        │
│    fgt.expect("pattern")     │
│    # No control flow yet     │
└──────┬───────────────────────┘
       │
       ▼
┌────────────────────────┐
│  FluentAPI             │
│  TestBed, FluentDevice │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│  PytestExecutor        │  Wraps Executor
│  .execute_api()        │  Routes to executor methods
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│  Executor              │
│  ._command()           │  ← Called directly (no VM_CODE)
│  .expect via API       │  
│  .report via API       │
│  (NO vm_code exec)     │
└────────────────────────┘
```

**Key Points:**
- PytestScript has empty vm_codes list
- Executor methods called directly (bypass VM_CODE interpreter)
- Works for linear tests (Phase 2 validated)
- **Question**: How to handle control flow?

---

## Problem Statement

DSL scripts contain control flow constructs:

```dsl
# DSL Example
command "show version"
expect -e "FortiGate" -for 12345

if %BUILD% >= 1000
    command "show full-configuration"
    expect -e "config" -for 12345
endif

while %counter% < 5
    command "ping FGT_B:IP_ETH1"
    varincrement counter
endwhile

for %device% in FGT_A FGT_B FGT_C
    device %device%
    command "get system status"
endfor
```

**Challenge**: How to convert this to pytest while leveraging Executor?

---

## Options Considered

### Option 1: Compile to VM_CODE, Execute in Pytest ❌

**Architecture:**
```
DSL → Compiler → VM_CODE → Pytest wraps VM_CODE → Executor.execute_vm_code()
```

**Implementation:**
```python
def test_205812():
    # Generate VM_CODE from DSL
    vm_codes = compiler.compile(dsl_script)
    
    # Execute VM_CODE in pytest
    executor.vm_codes = vm_codes
    executor.execute_vm_code()  # Interprets jumps, control flow
```

**Pros:**
- ✅ Reuses existing compiler
- ✅ Control flow handled by VM_CODE interpreter
- ✅ No need to parse if/while/for in transpiler

**Cons:**
- ❌ Pytest tests become opaque (just VM_CODE execution)
- ❌ No Python debugging (can't step through if/while)
- ❌ Can't use pytest features (fixtures, parametrize)
- ❌ Loses pytest benefits (readable tests, IDE support)
- ❌ Hard to maintain (VM_CODE is internal detail)
- ❌ Anti-pattern: pytest wrapping VM interpreter

**Verdict**: ❌ **REJECTED** - Defeats purpose of pytest conversion

---

### Option 2: Native Python Control Flow ✅

**Architecture:**
```
DSL → Transpiler (enhanced) → pytest (Python if/while/for) → Executor APIs
```

**Implementation:**
```python
def test_205812(testbed):
    with testbed.device('FGT_A') as fgt:
        fgt.execute("show version").expect("FortiGate", qaid="12345")
        
        # Native Python control flow
        if int(env.get_var('BUILD')) >= 1000:
            fgt.execute("show full-configuration").expect("config", qaid="12345")
        
        counter = 0
        while counter < 5:
            fgt.execute(f"ping {testbed.resolve_variables('FGT_B:IP_ETH1')}")
            counter += 1
        
        for device_name in ['FGT_A', 'FGT_B', 'FGT_C']:
            with testbed.device(device_name) as dev:
                dev.execute("get system status")
```

**Pros:**
- ✅ **Clean pytest tests** - readable, maintainable
- ✅ **Native debugging** - breakpoints, pdb, IDE stepping
- ✅ **Pytest features** - fixtures, parametrize, marks
- ✅ **Python ecosystem** - linters, type checkers, coverage
- ✅ **Already working** - Phase 2 validates this approach
- ✅ **Flexible** - Can use Python features (try/except, with)
- ✅ **Understandable** - Junior devs can read/modify tests

**Cons:**
- ⚠️ Transpiler needs to parse control flow (manageable)
- ⚠️ Don't reuse compiler (but compiler is for VM_CODE, not pytest)

**Verdict**: ✅ **APPROVED** - This is the right approach

---

## Decision: Native Python Control Flow

### Rationale

1. **pytest Philosophy**: pytest tests should be Python code, not VM interpreters
2. **Debuggability**: Python debuggers work, VM_CODE execution is opaque
3. **Maintainability**: Python control flow is standard, VM_CODE is custom
4. **Phase 2 Success**: We proved executor APIs work without VM_CODE
5. **Flexibility**: Can evolve tests beyond DSL capabilities

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DSL Script                               │
│  command "show version"                                     │
│  if %BUILD% >= 1000                                         │
│      command "show full-config"                             │
│  endif                                                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Enhanced Transpiler                            │
│  ┌───────────────────────────────────────┐                 │
│  │ 1. Parse DSL (DSLParser)               │                 │
│  │    - Commands, expects, etc.           │                 │
│  │    - Control flow (if/while/for)       │                 │
│  │    - Variables (%VAR%)                 │                 │
│  │                                        │                 │
│  │ 2. Generate Python AST                 │                 │
│  │    - if → if statement                 │                 │
│  │    - while → while loop                │                 │
│  │    - for → for loop                    │                 │
│  │    - command → fgt.execute()           │                 │
│  │                                        │                 │
│  │ 3. Emit pytest Code                    │                 │
│  │    - Native Python syntax              │                 │
│  │    - FluentAPI calls                   │                 │
│  └───────────────────────────────────────┘                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  pytest Test (Python)                       │
│  def test_example(testbed):                                 │
│      with testbed.device('FGT_A') as fgt:                   │
│          fgt.execute("show version")                        │
│          if int(env.get_var('BUILD')) >= 1000:              │
│              fgt.execute("show full-config")                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     FluentAPI                               │
│  TestBed, FluentDevice, OutputAssertion                     │
│  - Provides fluent interface                                │
│  - Delegates to PytestExecutor                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  PytestExecutor                             │
│  - Wraps AutoLib v3 Executor                                │
│  - Routes API calls                                         │
│  - NO VM_CODE execution                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              AutoLib v3 Executor (API Mode)                 │
│  ┌───────────────────────────────────────┐                 │
│  │ Used:                                 │                 │
│  │  ✅ ._command(params)                 │                 │
│  │  ✅ .expect via API handler           │                 │
│  │  ✅ .report via API handler           │                 │
│  │  ✅ ._switch_device(params)           │                 │
│  │  ✅ .result_manager                   │                 │
│  │  ✅ .devices                          │                 │
│  │                                       │                 │
│  │ NOT Used:                             │                 │
│  │  ❌ .execute_vm_code()                │                 │
│  │  ❌ .program_counter                  │                 │
│  │  ❌ .jump logic                       │                 │
│  │  ❌ .vm_codes list                    │                 │
│  └───────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Requirements

### 1. Transpiler Enhancements (Phase 3)

**Current State:**
- `dsl_parser.py` parses linear DSL (commands, expects)
- `pytest_generator.py` generates simple pytest functions
- No control flow support

**Required Enhancements:**

#### A. Parse Control Flow Constructs

```python
# In dsl_parser.py
class DSLParser:
    def parse_if_statement(self, tokens):
        """Parse: if %var% op value"""
        condition = self.parse_condition(tokens)
        body = self.parse_block_until('endif')
        return IfStatement(condition, body)
    
    def parse_while_loop(self, tokens):
        """Parse: while %var% op value"""
        condition = self.parse_condition(tokens)
        body = self.parse_block_until('endwhile')
        return WhileLoop(condition, body)
    
    def parse_for_loop(self, tokens):
        """Parse: for %var% in list"""
        var_name = tokens[1]
        items = tokens[3:]  # After 'in'
        body = self.parse_block_until('endfor')
        return ForLoop(var_name, items, body)
```

#### B. Generate Python Control Flow

```python
# In pytest_generator.py
class PytestGenerator:
    def generate_if_statement(self, if_stmt):
        """Generate Python if statement"""
        condition = self.translate_condition(if_stmt.condition)
        body = self.generate_statements(if_stmt.body, indent=8)
        return f"    if {condition}:\n{body}"
    
    def translate_condition(self, condition):
        """Convert DSL condition to Python"""
        # %BUILD% >= 1000 → int(env.get_var('BUILD')) >= 1000
        # %MODE% == "HA" → env.get_var('MODE') == "HA"
        var_name = condition.variable.strip('%')
        operator = condition.operator
        value = condition.value
        return f"int(env.get_var('{var_name}')) {operator} {value}"
```

#### C. Example Conversion

**Input DSL:**
```dsl
command "show version"
expect -e "FortiGate" -for 12345

if %BUILD% >= 1000
    command "show full-configuration"
    expect -e "config" -for 12345
else
    comment "Old build, skip full config"
endif

while %retry_count% < 3
    command "ping FGT_B:IP_ETH1"
    expect -e "bytes from" -for 12345
    varincrement retry_count
endwhile

for %device% in FGT_A FGT_B FGT_C
    device %device%
    command "get system status"
    expect -e "FortiGate" -for 12345
endfor
```

**Output pytest:**
```python
def test_example(testbed, env):
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("show version").expect("FortiGate", qaid="12345")
        
        # if statement
        if int(env.get_var('BUILD')) >= 1000:
            fgt_a.execute("show full-configuration").expect("config", qaid="12345")
        else:
            # Old build, skip full config
            pass
        
        # while loop
        retry_count = 0
        while retry_count < 3:
            fgt_a.execute(f"ping {testbed.resolve_variables('FGT_B:IP_ETH1')}")
            fgt_a.expect("bytes from", qaid="12345")
            retry_count += 1
        
        # for loop
        for device_name in ['FGT_A', 'FGT_B', 'FGT_C']:
            with testbed.device(device_name) as dev:
                dev.execute("get system status").expect("FortiGate", qaid="12345")
```

### 2. Variable Management

**DSL Variables:**
- `%BUILD%`, `%MODE%`, `%counter%`, etc.
- Set via `varset`, `varincrement`, `vardecrement`

**Python Implementation:**

```python
# Use AutoLib v3 env service
from lib.services import env

# In pytest
env.add_var('BUILD', '1234')
env.add_var('counter', '0')

# In transpiled code
if int(env.get_var('BUILD')) >= 1000:
    ...

# Variable operations
counter = int(env.get_var('counter'))
counter += 1
env.add_var('counter', str(counter))
```

### 3. Executor API Usage (BYPASS VM_CODE)

**What We Call:**
```python
# Direct executor methods (internal APIs starting with _)
executor._command(("show version",))
executor._switch_device(("FGT_A",))

# Public APIs via api_handler
executor.api_handler.execute_api('expect', params)
executor.api_handler.execute_api('report', params)
```

**What We DON'T Call:**
```python
# ❌ Don't call these
executor.execute_vm_code()       # VM_CODE interpreter
executor.program_counter = ...   # Line number tracking
executor.jump_to(line_number)    # Jump logic
```

---

## Benefits of This Approach

### 1. Clean, Readable Tests

**Before (if we used VM_CODE):**
```python
def test_example():
    vm_codes = [
        VMCode("command", ("show version",)),
        VMCode("expect", ("-e", "FortiGate", "-for", "12345")),
        VMCode("jump_if", (5, "%BUILD%", ">=", "1000")),
        VMCode("command", ("show full-config",)),
        VMCode("jump", (6,)),
        # ... complex jump logic
    ]
    executor.execute_vm_code(vm_codes)  # Opaque!
```

**After (native Python):**
```python
def test_example(testbed):
    with testbed.device('FGT_A') as fgt:
        fgt.execute("show version").expect("FortiGate", qaid="12345")
        if int(env.get_var('BUILD')) >= 1000:
            fgt.execute("show full-config")
```
**→ Immediately understandable!**

### 2. Native Debugging

**Python debugger works:**
```python
def test_example(testbed):
    with testbed.device('FGT_A') as fgt:
        fgt.execute("show version")
        
        import pdb; pdb.set_trace()  # ✅ Can set breakpoint
        
        if int(env.get_var('BUILD')) >= 1000:
            fgt.execute("show full-config")  # ✅ Can step through
```

**VS Code / PyCharm:**
- ✅ Breakpoints work
- ✅ Variable inspection works
- ✅ Step into/over/out works

### 3. pytest Features

```python
@pytest.mark.parametrize("build", [800, 1000, 1200])
def test_version_feature(testbed, build, env):
    env.add_var('BUILD', str(build))
    
    with testbed.device('FGT_A') as fgt:
        if build >= 1000:
            fgt.execute("show new-feature")  # ✅ Can parametrize
```

### 4. Error Handling

```python
def test_example(testbed):
    with testbed.device('FGT_A') as fgt:
        try:
            fgt.execute("show version").expect("FortiGate", qaid="12345")
        except AssertionError:
            # ✅ Can catch and handle errors
            fgt.execute("get system status")  # Fallback
            raise
```

### 5. Code Coverage

```bash
pytest --cov=prototype --cov-report=html test__205812.py
# ✅ Reports show which lines executed
# ✅ Can see if/else branches covered
```

---

## Migration Strategy

### Phase 1: ✅ COMPLETE - Linear Tests
- Transpile commands, expects, reports
- No control flow
- Test validation: QAID 205812 passed

### Phase 2: ✅ COMPLETE - Executor Integration
- PytestExecutor wraps Executor
- Call executor APIs directly (no VM_CODE)
- Mock devices implement AutoLib v3 interface
- Test validation: QAID 205812 passed

### Phase 3: 🔄 NEXT - Control Flow Support
- Parse if/while/for in DSL
- Generate Python control flow
- Variable management via env service
- Test validation: DSL with control flow

### Phase 4: Future - Advanced Features
- Error handling (try/except)
- Fixtures for common setups
- Parametrized tests
- Custom assertions

---

## Code Examples

### Example 1: If/Else

**DSL:**
```dsl
device FGT_A
command "show version"
expect -e "FortiGate" -for 12345

if %MODE% == "HA"
    command "get system ha status"
    expect -e "HA mode" -for 12345
else
    comment "Standalone mode"
endif
```

**Generated pytest:**
```python
def test_ha_check(testbed, env):
    with testbed.device('FGT_A') as fgt_a:
        fgt_a.execute("show version").expect("FortiGate", qaid="12345")
        
        if env.get_var('MODE') == "HA":
            fgt_a.execute("get system ha status").expect("HA mode", qaid="12345")
        else:
            # Standalone mode
            pass
```

### Example 2: While Loop

**DSL:**
```dsl
varset retry_count 0
while %retry_count% < 3
    command "ping FGT_B:IP_ETH1"
    expect -e "bytes from" -for 12345
    varincrement retry_count
endwhile
```

**Generated pytest:**
```python
def test_ping_retry(testbed, env):
    retry_count = 0
    with testbed.device('FGT_A') as fgt_a:
        while retry_count < 3:
            fgt_a.execute(f"ping {testbed.resolve_variables('FGT_B:IP_ETH1')}")
            fgt_a.expect("bytes from", qaid="12345")
            retry_count += 1
```

### Example 3: For Loop

**DSL:**
```dsl
for %device% in FGT_A FGT_B FGT_C
    device %device%
    command "get system status"
    expect -e "FortiGate" -for 12345
endfor
```

**Generated pytest:**
```python
def test_multi_device(testbed):
    for device_name in ['FGT_A', 'FGT_B', 'FGT_C']:
        with testbed.device(device_name) as dev:
            dev.execute("get system status").expect("FortiGate", qaid="12345")
```

---

## Documentation Requirements

### 1. Update DSL_TO_PYTEST_CONVERSION_GUIDE.md
- Document control flow conversion
- Add examples for if/while/for
- Explain variable management

### 2. Update IMPLEMENTATION_ROADMAP.md
- Mark Phase 2 complete
- Detail Phase 3 requirements
- Add control flow examples

### 3. Create TRANSPILER_CONTROL_FLOW_SPEC.md
- Formal specification for control flow parsing
- Grammar for if/while/for
- Validation rules

---

## Testing Strategy

### Unit Tests for Transpiler
```python
def test_parse_if_statement():
    dsl = """
    if %BUILD% >= 1000
        command "show full-config"
    endif
    """
    ast = parser.parse(dsl)
    assert isinstance(ast[0], IfStatement)
    assert ast[0].condition.variable == 'BUILD'
```

### Integration Tests
```python
def test_transpile_with_control_flow():
    dsl_file = "sample_with_if.txt"
    pytest_code = transpiler.transpile(dsl_file)
    # Verify generated pytest code
    assert "if int(env.get_var('BUILD'))" in pytest_code
```

### End-to-End Tests
```python
# Run transpiled test with control flow
def test_generated_pytest_executes():
    pytest.main(["test_generated_with_if.py", "-v"])
```

---

## Success Criteria

Phase 3 will be considered complete when:

1. ✅ Transpiler parses if/while/for statements
2. ✅ Generated pytest has native Python control flow
3. ✅ Tests execute without VM_CODE
4. ✅ Debugger works in control flow blocks
5. ✅ All DSL control flow patterns supported
6. ✅ Variable management via env service works
7. ✅ Documentation updated with examples

---

## Risks and Mitigations

### Risk 1: Complex DSL Control Flow
**Issue**: DSL may have nested if/while/for that's hard to parse
**Mitigation**: Start with simple cases, add complexity incrementally

### Risk 2: Variable Type Conversions
**Issue**: DSL variables are strings, Python needs types
**Mitigation**: Use explicit type conversions (int(), str(), bool())

### Risk 3: Performance
**Issue**: Python loops might be slower than VM_CODE
**Mitigation**: Not a concern - test execution time is dominated by device I/O

---

## Conclusion

**DECISION: Use Native Python Control Flow**

- ✅ Convert DSL if/while/for to Python if/while/for
- ✅ Call Executor APIs directly (no VM_CODE execution)
- ✅ Leverage Python's debugging and testing ecosystem
- ✅ Produce readable, maintainable pytest tests

**Next Steps:**
1. Enhance transpiler to parse control flow
2. Generate Python control flow in pytest
3. Add variable management via env service
4. Test with DSL scripts containing if/while/for

This approach aligns with pytest philosophy and maximizes the benefits of Python-based testing while still leveraging AutoLib v3's robust executor infrastructure.
