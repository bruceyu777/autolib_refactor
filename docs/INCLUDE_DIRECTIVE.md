# Include Directive - Script Reuse and Modularization

## Overview

The `include` directive enables **compile-time script inclusion** with **variable interpolation**, allowing you to:
- Reuse common test sequences across multiple test files
- Create modular, maintainable test suites
- Adapt script paths dynamically based on environment configuration
- Share device context between parent and included scripts

## Table of Contents

1. [Basic Syntax](#basic-syntax)
2. [How It Works](#how-it-works)
3. [Variable Interpolation](#variable-interpolation)
4. [Compilation Process](#compilation-process)
5. [Execution Model](#execution-model)
6. [Common Patterns](#common-patterns)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Basic Syntax

```plaintext
include <script_path>
```

**Parameters**:
- `script_path` (required): Relative or absolute path to script file to include

**Example**:
```plaintext
[FGT_A]
    # Simple include
    include testcase/common/login.txt
    
    # Include with variable interpolation
    include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
    
    # Include device-specific config
    include testcase/device_configs/FGT_A:PROFILE.txt
```

---

## How It Works

### 1. Parse Time - Recognition

When the parser encounters `include`, it:
- Stores the path **with variable placeholders** (e.g., `GLOBAL:VERSION`)
- Records the current **device section** context (e.g., `FGT_A`)
- Generates VM code for runtime execution

```python
# Parser behavior (parser.py)
def _include(self):
    token = self._cur_token
    self._add_vm_code(token.line_number, "include", (token.str,))
    self.called_files.add((token.str, self.cur_section))
```

### 2. Compile Time - Variable Resolution

After parsing, the compiler:
- **Interpolates variables** from environment config
- **Recursively compiles** the resolved file path
- **Caches** compiled VM codes to avoid re-compilation

```python
# Compiler behavior (compiler.py)
for f, current_device in called_files:
    f = env.variable_interpolation(f, current_device=current_device)
    self._compile_file(f)  # Recursive compilation
```

### 3. Runtime - Execution

When the `include` VM code executes:
- Creates a **sub-executor** with same device pool
- **Preserves device context** (current device remains active)
- Executes included script's VM codes
- Returns control to parent script

```python
# Execution behavior (script.py)
def include(executor, params):
    include_script = IncludeScript(script_path, executor.cur_device.dev_name)
    with Executor(include_script, executor.devices, False) as sub_executor:
        sub_executor.cur_device = executor.cur_device
        sub_executor.execute()
```

---

## Variable Interpolation

### Syntax Patterns

Include paths support **environment variable substitution** using the pattern `SECTION:VARIABLE`:

| Pattern | Description | Example |
|---------|-------------|---------|
| `GLOBAL:VERSION` | Global configuration variable | `testcase/GLOBAL:VERSION/common/` |
| `SECTION:VAR` | Any section variable | `scripts/TOPOLOGY:TYPE/setup.txt` |
| `DEVICE:VAR` | Device-local variable (no prefix needed) | `configs/PROFILE.txt` → `configs/default.txt` |

### Resolution Order

1. **Section-prefixed variables** (e.g., `GLOBAL:VERSION`, `TOPOLOGY:TYPE`)
   - Sorted by length (longest first) to avoid partial matches
   - Replaces `SECTION:VARIABLE` with configured value

2. **Device-local variables** (only when current_device is set)
   - Replaces `VARIABLE` (no prefix) with device-specific value
   - Uses current device section context

### Example Transformation

**Test Script** (`testcase/ips/topology1/206335.txt`):
```plaintext
[FGT_A]
    include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
```

**Environment Config** (`env.fortistack.ips_nm.conf`):
```ini
[GLOBAL]
VERSION: trunk
Platform: FGVM
```

**Resolution Process**:
```
Original:  testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
          ↓ (variable_interpolation with section=GLOBAL)
Resolved:  testcase/trunk/ips/topology1/goglobal.txt
          ↓ (file loaded and compiled)
Executed:  VM codes from goglobal.txt run on device FGT_A
```

### Multiple Variables Example

**Environment Config**:
```ini
[GLOBAL]
VERSION: 7.6
TOPOLOGY: simple

[FGT_A]
PROFILE: ha_master
```

**Include Statements**:
```plaintext
[FGT_A]
    # Resolves to: testcase/7.6/simple/setup.txt
    include testcase/GLOBAL:VERSION/GLOBAL:TOPOLOGY/setup.txt
    
    # Resolves to: configs/ha_master.txt
    # (PROFILE is device-local, no prefix needed)
    include configs/PROFILE.txt
```

---

## Compilation Process

### Recursive Compilation

The compiler processes includes **recursively** at compile-time:

```
main_test.txt
  ├─ include common/setup.txt
  │    └─ (compiled once, cached)
  │
  ├─ include GLOBAL:VERSION/device_init.txt
  │    ├─ Variable interpolation: VERSION=trunk
  │    ├─ Resolved path: trunk/device_init.txt
  │    └─ (compiled once, cached)
  │
  └─ include common/setup.txt
       └─ (cache hit, reused without re-compilation)
```

### Caching Strategy

**Benefits**:
- Each unique file path compiled **only once**
- Multiple includes of same file → single compilation + cache reuse
- Thread-safe compilation for parallel execution
- Faster overall compilation time for large test suites

**Cache Key**: Resolved absolute file path after variable interpolation

**Example**:
```plaintext
# These three includes result in only ONE compilation:
[FGT_A]
    include common/login.txt
    
[FGT_B]
    include common/login.txt
    
[PC_01]
    include common/login.txt
```

### Validation

All included files are validated during compilation:
- **File existence**: Missing files cause immediate compilation error
- **Syntax errors**: Detected before any execution begins
- **Schema validation**: All DSL commands validated against schema
- **Nested includes**: Recursive includes validated (no circular dependency check currently)

---

## Execution Model

### Device Context Preservation

When executing an included script:

```plaintext
[FGT_A]
    # Current device: FGT_A
    command These commands run on FGT_A
    
    include common/vdom_commands.txt
    # ↑ Included script ALSO executes on FGT_A
    #   Device context is preserved
    
    command Back to main script, still on FGT_A
```

### Variable Scope

**Important**: Included scripts run in an **isolated executor** with:
- ✅ **Shared**: Device pool, connection sessions
- ❌ **Isolated**: User-defined variables (setvar, intset, strset)
- ❌ **Isolated**: Program counter, control flow state

**Example**:
```plaintext
# main_test.txt
[FGT_A]
    <strset myvar "Hello">
    include subscripts/inner.txt
    comment Value: {$myvar}  # ✅ Still "Hello"

# subscripts/inner.txt
[FGT_A]
    <strset myvar "Changed">  # ❌ Does NOT affect parent
    comment Inner: {$myvar}   # Shows "Changed" here only
```

**Workaround**: Use environment config variables for cross-script communication:
```ini
[GLOBAL]
SHARED_VALUE: test123
```

Both parent and included scripts can access `$SHARED_VALUE`.

### Execution Flow Diagram

```
Main Script Executor
    │
    ├─ [FGT_A]
    │   ├─ command Device setup commands
    │   │
    │   ├─ include common/login.txt  ← VM Code execution
    │   │       │
    │   │       └─→ Sub-Executor Created
    │   │           ├─ Preserves: cur_device=FGT_A
    │   │           ├─ Shares: device pool, SSH sessions
    │   │           ├─ Isolated: variables, program counter
    │   │           ├─ Execute: login.txt VM codes
    │   │           └─ Complete → Return to parent
    │   │
    │   └─ command Continues with FGT_A context
    │
    └─ [PC_01]
        └─ command Switches to PC_01, includes work here too
```

---

## Common Patterns

### 1. Version-Specific Test Flows

**Use Case**: Different FortiOS versions have different CLI syntax

```plaintext
# Environment config
[GLOBAL]
VERSION: 7.6

# Test script
[FGT_A]
    # Automatically uses 7.6-specific commands
    include testcase/GLOBAL:VERSION/config_system.txt
```

**Directory Structure**:
```
testcase/
  ├─ 7.4/
  │   └─ config_system.txt  (FortiOS 7.4 syntax)
  ├─ 7.6/
  │   └─ config_system.txt  (FortiOS 7.6 syntax)
  └─ trunk/
      └─ config_system.txt  (Latest trunk syntax)
```

### 2. VDOM Navigation (goglobal/outvdom)

**Use Case**: Enter and exit global VDOM context

```plaintext
[FGT_A]
    comment Configure global settings
    include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
    
    # Now in global VDOM, configure system-level settings
    config system interface
        edit port1
            set ip 192.168.1.1/24
        next
    end
    
    # Return to root or previous VDOM
    include testcase/GLOBAL:VERSION/ips/topology1/outvdom.txt
```

**goglobal.txt** (example):
```plaintext
config global
```

**outvdom.txt** (example):
```plaintext
end
```

### 3. Topology-Specific Device Initialization

**Use Case**: Different topologies need different device configs

```plaintext
# Environment config
[GLOBAL]
TOPOLOGY: star

# Test script
[FGT_A]
    include topologies/GLOBAL:TOPOLOGY/fgt_a_init.txt
[FGT_B]
    include topologies/GLOBAL:TOPOLOGY/fgt_b_init.txt
```

**Directory Structure**:
```
topologies/
  ├─ star/
  │   ├─ fgt_a_init.txt  (Hub configuration)
  │   └─ fgt_b_init.txt  (Spoke configuration)
  └─ mesh/
      ├─ fgt_a_init.txt  (Peer A configuration)
      └─ fgt_b_init.txt  (Peer B configuration)
```

### 4. Reusable Test Sequences

**Use Case**: Common validation checks across multiple tests

```plaintext
# Multiple test files can include same validations
[FGT_A]
    # Test-specific setup
    config firewall policy
        edit 1
            set srcintf port1
        next
    end
    
    # Standard validation sequence
    include common/validate_policy.txt
    include common/check_system_resources.txt
    include common/verify_ha_sync.txt
```

### 5. Platform-Specific Commands

**Use Case**: Hardware vs VM have different capabilities

```plaintext
# Environment config
[GLOBAL]
Platform: FGVM

[FGT_A]
    # Automatically uses VM-specific commands
    include platforms/GLOBAL:Platform/network_setup.txt
```

---

## Best Practices

### ✅ DO

1. **Use descriptive file names**
   ```plaintext
   ✅ include common/vdom_enter_global.txt
   ❌ include common/g.txt
   ```

2. **Organize by functionality and version**
   ```
   testcase/
     ├─ common/           # Version-independent utilities
     ├─ 7.6/              # Version-specific flows
     ├─ platforms/        # Platform-specific (VM vs hardware)
     └─ topologies/       # Topology-specific configs
   ```

3. **Use variable interpolation for paths**
   ```plaintext
   ✅ include testcase/GLOBAL:VERSION/setup.txt
   ❌ include testcase/7.6/setup.txt  # Hardcoded version
   ```

4. **Document what included files do**
   ```plaintext
   [FGT_A]
       # Enter global VDOM to configure system interface
       include testcase/GLOBAL:VERSION/ips/topology1/goglobal.txt
   ```

5. **Keep included scripts focused and single-purpose**
   - One script = one logical task (login, configure interface, validate HA, etc.)
   - Easier to test, debug, and reuse

### ❌ DON'T

1. **Don't create circular includes**
   ```plaintext
   # a.txt
   include b.txt
   
   # b.txt
   include a.txt  # ❌ Infinite loop (not currently detected)
   ```

2. **Don't rely on user-defined variables crossing include boundaries**
   ```plaintext
   # main.txt
   <strset myvar "value">
   include sub.txt
   
   # sub.txt
   comment {$myvar}  # ❌ Won't work, variables are isolated
   ```

3. **Don't hardcode environment-specific paths**
   ```plaintext
   ❌ include /home/user/testcase/trunk/setup.txt
   ✅ include testcase/GLOBAL:VERSION/setup.txt
   ```

4. **Don't create deeply nested includes (>3 levels)**
   - Harder to debug and follow execution flow
   - Consider refactoring into flatter structure

5. **Don't put device-switching logic in included scripts**
   ```plaintext
   # ❌ Bad: included script switches devices
   # common/bad_example.txt
   [FGT_B]  # Switches device context unexpectedly
       command Something
   
   # ✅ Good: let parent control device context
   # common/good_example.txt
   command Something  # Runs on whatever device parent specified
   ```

---

## Troubleshooting

### Issue 1: File Not Found Error

**Symptom**:
```
FileNotExist: testcase/trunk/ips/topology1/goglobal.txt
```

**Diagnosis**:
1. Check variable interpolation: What is `GLOBAL:VERSION` in your config?
   ```bash
   grep "VERSION:" env.conf
   ```

2. Verify resolved path exists:
   ```bash
   # If VERSION=trunk, check:
   ls -la testcase/trunk/ips/topology1/goglobal.txt
   ```

3. Check for typos in section/variable names:
   ```plaintext
   ❌ include testcase/GLOBAL:VARSION/...  # Typo
   ✅ include testcase/GLOBAL:VERSION/...
   ```

**Solution**:
- Ensure environment config has the variable defined
- Verify file exists at resolved path
- Use absolute paths for debugging: `include $(pwd)/testcase/7.6/test.txt`

### Issue 2: Variable Not Interpolating

**Symptom**:
```
FileNotExist: testcase/GLOBAL:VERSION/setup.txt
```
(Path contains literal `GLOBAL:VERSION` instead of value)

**Diagnosis**:
1. Check if variable is defined in environment config:
   ```bash
   grep -A5 "\[GLOBAL\]" env.conf | grep VERSION
   ```

2. Verify section name matches exactly (case-sensitive):
   ```ini
   ❌ [global]     # Lowercase won't match
   ✅ [GLOBAL]
   ```

3. Check for whitespace issues:
   ```ini
   ❌ VERSION : trunk    # Extra spaces around colon
   ✅ VERSION: trunk
   ```

**Solution**:
- Add missing variable to environment config
- Fix section name casing
- Remove extra whitespace in config file

### Issue 3: Commands Execute on Wrong Device

**Symptom**: Included script runs on different device than expected

**Diagnosis**:
Check if included script has its own device section headers:
```plaintext
# main.txt
[FGT_A]
    include common/setup.txt  # Expects to run on FGT_A

# common/setup.txt - WRONG
[FGT_B]  # ❌ Switches device context!
    command Something
```

**Solution**:
- Remove device section headers from included scripts
- Let parent script control device context:
```plaintext
# common/setup.txt - CORRECT
command Something  # ✅ Runs on current device (FGT_A)
```

### Issue 4: Slow Compilation

**Symptom**: Compilation takes long time with many includes

**Diagnosis**:
1. Check for redundant variable interpolation
2. Look for duplicate includes of same file
3. Enable debug mode to see compilation flow:
   ```bash
   python3 autotest.py -t test.txt -e env.conf -d
   ```

**Solution**:
- Compilation is cached, but variable interpolation happens per-include
- Consolidate multiple includes of same file if possible
- Use version control to track which files changed (compiler caches haven't changed)

### Issue 5: Variable Scope Confusion

**Symptom**: Variable set in included script not visible in parent

**Diagnosis**:
```plaintext
# parent.txt
include sub.txt
comment Value: {$myvar}  # Shows empty or old value

# sub.txt
<strset myvar "new_value">  # Sets in isolated scope
```

**Solution**:
- Use **environment config variables** for cross-script communication:
  ```ini
  [GLOBAL]
  SHARED_VAR: value
  ```
- Or use `setvar` with device output in parent script after include
- Document variable scope limitations for your team

---

## Advanced Topics

### Include Path Resolution Algorithm

```python
def variable_interpolation(content, current_device=None):
    # Step 1: Replace SECTION:VARIABLE patterns
    for section in env.sections():
        if f"{section}:" in content:
            for var, value in env.get_section(section):
                content = content.replace(f"{section}:{var}", value)
    
    # Step 2: Replace device-local variables (no prefix)
    if current_device:
        for var, value in env.get_section(current_device):
            content = content.replace(var, value)
    
    return content
```

**Key Notes**:
- Variables sorted by length (longest first) to prevent partial replacements
- Section-prefixed variables processed first
- Device-local variables processed second (only when device context exists)
- Case-sensitive matching

### Performance Characteristics

| Aspect | Performance | Notes |
|--------|-------------|-------|
| First compilation | ~100-500ms | Depends on file size and includes |
| Cached compilation | <1ms | Cache hit, no re-parsing |
| Variable interpolation | <1ms per include | String replacement |
| Include execution | <1ms overhead | Sub-executor creation |
| Memory usage | Minimal | VM codes shared via cache |

### Thread Safety

The compiler is **thread-safe** for:
- ✅ Reading cached compiled files
- ✅ Parallel compilation of different files
- ✅ Concurrent include execution

Uses **reentrant locks** (`threading.RLock`) to support:
- Recursive compilation (includes within includes)
- Parallel test execution
- Safe cache access

---

## Schema Reference

**Category**: `script`  
**Parse Mode**: `positional`

```json
{
  "include": {
    "description": "Include and execute another script",
    "category": "script",
    "parse_mode": "positional",
    "parameters": [
      {
        "name": "script_path",
        "type": "string",
        "position": 0,
        "required": true,
        "description": "Path to script to include"
      }
    ]
  }
}
```

**API Implementation**: `lib/core/executor/api/script.py::include()`

---

## Summary

The `include` directive provides powerful script modularization with:

| Feature | Benefit |
|---------|---------|
| **Variable Interpolation** | Adapt paths dynamically (VERSION, TOPOLOGY, etc.) |
| **Compile-time Resolution** | Errors detected before execution starts |
| **Caching** | Fast compilation, efficient memory usage |
| **Device Context Preservation** | Included scripts run on current device |
| **Recursive Support** | Includes can include other scripts |
| **Thread Safety** | Safe for parallel execution |

**When to Use**:
- ✅ Repeating command sequences across tests
- ✅ Version-specific test flows
- ✅ Platform-specific configurations
- ✅ Common validation routines
- ✅ VDOM navigation helpers

**When NOT to Use**:
- ❌ Single-use, one-off command sequences
- ❌ Sharing variables between scripts (use env config instead)
- ❌ Complex logic that requires runtime path decisions

---

## See Also

- [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) - Complete compilation pipeline
- [Variable Usage and Troubleshooting](VARIABLE_USAGE_AND_TROUBLESHOOTING.md) - Variable syntax details
- [cli_syntax.json](../lib/core/compiler/static/cli_syntax.json) - Schema definition
- [script.py](../lib/core/executor/api/script.py) - API implementation
