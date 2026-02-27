# Variable Usage and Troubleshooting Guide

This guide covers variable management, common issues, and troubleshooting workflows in AutoLib v3, based on real debugging sessions.

## Table of Contents
1. [Variable Syntax Overview](#variable-syntax-overview)
2. [Common Issues and Solutions](#common-issues-and-solutions)
3. [Variable Replacement Workflow](#variable-replacement-workflow)
4. [Understanding DSL Syntax](#understanding-dsl-syntax)
5. [Troubleshooting Workflow](#troubleshooting-workflow)
6. [API Reference](#api-reference)

---

## Variable Syntax Overview

AutoLib v3 uses **two different syntaxes** for variables:

### 1. Environment Config Variables: `$varname`

**Source:** Defined in environment `.conf` files  
**Syntax:** `$VARNAME` (no curly braces)  
**Use Case:** Device configuration, network settings, credentials

**Example:**
```ini
# In env.fortistack.ips_nm.conf
[FGT_B]
Platform: FGVM
CONNECTION: ssh admin@10.96.234.41 -p 62022
USERNAME: admin
IP_PORT1: 172.16.200.1 255.255.255.0

[GLOBAL]
DUT: FGT_B
```

**Usage in DSL:**
```python
# Direct usage - no special syntax needed
[FGT_B]
    get system status
    
# In comments or commands
comment Connecting to $USERNAME at $IP_PORT1
```

### 2. User-Defined Variables: `{$varname}`

**Source:** Created at runtime via `setvar`, `intset`, `strset`  
**Syntax:** `{$varname}` (requires curly braces)  
**Use Case:** Extracting values from device output, counters, dynamic data

**Example:**
```python
# Extract serial number from output
get system status | grep 'Serial-Number'
setvar -e "Serial-Number: (FGVM\w+)" -to sn

# Use the variable - MUST use {$sn}
comment Device serial: {$sn}         # ✅ CORRECT
comment Device serial: $sn           # ❌ WRONG - will not expand
```

### Quick Reference Table

| Variable Type | Syntax | Source | Example |
|---------------|--------|--------|---------|
| **Environment Config** | `$VAR` | `.conf` file | `$USERNAME`, `$IP_PORT1`, `$DUT` |
| **User-Defined** | `{$VAR}` | `setvar`, `intset`, `strset` | `{$sn}`, `{$count}`, `{$result}` |
| **Device-Scoped Config** | `DEVICE:VAR` | `.conf` section | `FGT_A:PORT1`, `FGT_B:CONNECTION` |

---

## Common Issues and Solutions

### Issue 1: `setvar` Not Extracting Values

**Symptom:**
```log
2026-02-17 15:14:57,877 - root - DEBUG - Pattern - Serial-Number: (FGno.*), time used: 10.1 s
2026-02-17 15:14:57,878 - root - ERROR - Failed to execute setvar.
2026-02-17 15:14:57,878 - root - INFO - Device serial: $sn
```

**Root Cause:** Pattern was transformed from `(FGVM.*)` to `(FGno.*)` due to `VM: no` in environment config.

**The Bug:**
```ini
# In env.fortistack.ips_nm.conf
VM: no    # ❌ Causes variable interpolation: FGVM → FGno
```

**Solution:**
```ini
# In env.fortistack.ips_nm.conf
; VM: no  # ✅ Comment out unused variables
```

**Why:** AutoLib's variable interpolation scans environment config and replaces text. When `VM: no` exists, the string `FGVM` gets transformed to `FGno` during parameter replacement (VM → no).

**How expect() Works:**
```python
# In lib/core/device/session/dev_conn.py
def expect(pattern, timeout=1, need_clear=True):
    m, output = self.search(pattern, timeout)  # 1. Search pattern in buffer
    
    if m is not None:                          # 2. If matched
        if need_clear:                         # 3. THEN clear buffer (after match)
            self.clear_buffer(pos=m.end())
    
    return m, output  # Returns match object and output
```

**Important:** Buffer is cleared **AFTER** pattern matching, so `need_clear=True` (default) is safe for setvar. The buffer clearing happens after extraction, not before.

**Best Practice:**
```python
# Always run a command BEFORE setvar to populate the buffer
get system status | grep 'Serial-Number'
setvar -e "Serial-Number: (FGVM\w+)" -to sn  # Uses default need_clear=True

# Don't do this - buffer is empty!
# setvar -e "Serial-Number: (FGVM\w+)" -to sn
```

### Issue 2: Variable Not Expanding in Comments

**Symptom:**
```log
2026-02-17 15:29:31,794 - root - INFO - Device serial: $sn  # Shows literal $sn
```

**Root Cause:** Used `$sn` instead of `{$sn}` for user-defined variable.

**Solution:**
```python
# ❌ WRONG - config variable syntax for user-defined variable
comment Device serial: $sn

# ✅ CORRECT - curly braces for user-defined variables
comment Device serial: {$sn}
```

**Output After Fix:**
```log
2026-02-1debug logs: Pattern shows as `(FGno.*)` - different!
3. Check environment config: Found `VM: no` line (not commented)

### Issue 3: Pattern Mysteriously Changes (FGVM → FGno)

**Symptom:**
```log
# Test file has: setvar -e "Serial-Number: (FGVM.*)" -to sn
# But log shows: Pattern - Serial-Number: (FGno.*), time used: 10.1 s
```

**Root Cause:** Environment config file had `VM: no` which triggered pattern replacement.

**Investigation Steps:**
1. Check test file: Pattern is `(FGVM.*)`
2. Check compiled cache: Clear `__pycache__` directories
3. Check environment config: Found `;VM: no` line

**Solution:**
```ini
# In env.fortistack.ips_nm.conf

# ❌ WRONG - causes FGVM → FGno transformation
VM: no

# ✅ CORRECT - comment it out if not needed
; VM: no
```

**Why This Happens:**  
AutoLib's variable interpolation scans for `VM:` in the environment config and performs text replacement. When `VM: no` exists, `FGVM` gets transformed to `FGno` during variable interpolation.

**Prevention:** Only define necessary variables in config files. Comment out unused variables with `;`.

### Issue 4: Greedy Regex Capturing Extra Text

**Symptom:**
```python
setvar -e "Serial-Number: (FGVM.*)" -to sn
# Captures: "FGVMULTM25002684\n\nFGTB (Interim)# "
```

**Root Cause:** `.*` is greedy and matches everything including newlines and prompt.

**Solution:**
```python
# ✅ Better - use word characters only
setvar -e "Serial-Number: (FGVM\w+)" -to sn
# Captures: "FGVMULTM25002684"

# ✅ Alternative - non-greedy match with word boundary
setvar -e "Serial-Number: (FGVM.*?)\s" -to sn

# ✅ Alternative - explicit character class
setvar -e "Serial-Number: (FG[A-Z0-9]+)" -to sn
```

---

## Variable Replacement Workflow

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. TEST SCRIPT (DSL)                                            │
│     setvar -e "Serial-Number: (FGVM\w+)" -to sn                 │
│     comment Device serial: {$sn}                                 │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. COMPILATION (parser.py + cli_syntax.json)                   │
│     • Tokenize DSL text                                          │
│     • Create VMCode: ("setvar", ("Serial-Number: (FGVM\w+)", "sn")) │
│     • Create VMCode: ("comment", ("Device serial: {$sn}",))     │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. EXECUTION (executor.py)                                      │
│     FOR each VMCode:                                             │
│       • Extract: operation="setvar", parameters=("...", "sn")   │
│       • Call: variable_replacement(parameters)                   │
│       • Execute: api_handler.execute_api("setvar", params)      │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. VARIABLE REPLACEMENT (executor.py)                           │
│                                                                  │
│     def variable_replacement(parameters):                        │
│         for parameter in parameters:                             │
│             # STEP 1: Replace environment config vars ($VAR)    │
│             parameter = env.variable_interpolation(parameter)    │
│                                                                  │
│             # STEP 2: Replace user-defined vars ({$VAR})        │
│             parameter = _user_defined_variable_interpolation()   │
│         return parameters                                        │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. API EXECUTION (api_manager.py + variable.py)                │
│     • Wrap parameters in ApiParams object                        │
│     • Call: setvar(executor, params)                             │
│     • Extract: match = expect(rule, need_clear=False)           │
│     • Store: env.add_var("sn", "FGVMULTM25002684")              │
└─────────────────────────────────────────────────────────────────┘
```

### Two-Pass Variable Interpolation

**File:** `lib/core/executor/executor.py`

```python
def _variable_interpolation(self, original_parameter):
    """Two-pass variable replacement."""
    
    # PASS 1: Environment config variables ($USERNAME, $IP_PORT1, etc.)
    parameter = env.variable_interpolation(
        original_parameter, 
        current_device=self.cur_device.dev_name
    )
    
    # PASS 2: User-defined variables ({$sn}, {$count}, etc.)
    parameter = self._user_defined_variable_interpolation(parameter)
    
    logger.debug("Variable interpolation: '%s' -> '%s'", 
                 original_parameter, parameter)
    return parameter

@staticmethod
def _user_defined_variable_interpolation(_string):
    """Replace {$varname} with values from env.get_var()."""
    matched = re.findall(r"{\$.*?}", _string)
    for m in matched:
        var_name = m[2:-1]  # Strip {$ and }
        value = env.get_var(var_name)
        if value is not None:
            _string = _string.replace(m, str(value))
        else:
            logger.error("Failed to find the value for %s", var_name)
    return _string
```

### When Variable Replacement Happens

**File:** `lib/core/executor/executor.py` (line 249)

```python
def execute(self):
    """Main execution loop."""
    while self.program_counter < len(self.vm_codes):
        code = self.vm_codes[self.program_counter]
        parameters = code.parameters
        
        # Variable replacement happens BEFORE API execution
        # Exception: switch_device and setenv handle variables internally
        if code.operation not in ["switch_device", "setenv"]:
            parameters = self.variable_replacement(parameters)
        
        # Execute the API with replaced parameters
        self.api_handler.execute_api(code.operation, parameters)
```

**Key Point:** Variables are replaced **just before** the API is called, not during compilation.

---

## Understanding DSL Syntax

### Where to Find Syntax Definitions

#### 1. CLI Syntax Schema

**File:** `lib/core/compiler/static/cli_syntax.json`

This JSON file defines **all DSL commands** and their parameters:

```json
{
  "setvar": {
    "description": "Extract value from pattern match and set variable",
    "category": "variable",
    "parse_mode": "options",
    "parameters": {
      "-e": {
        "alias": "rule",           // -e maps to params.rule
        "type": "string",
        "position": 0,
        "required": true,
        "description": "Regex pattern with capture group"
      },
      "-to": {
        "alias": "name",           // -to maps to params.name
        "type": "string",
        "position": 1,
        "required": true,
        "description": "Variable name to set"
      }
    }
  },
  
  "expect": {
    "description": "Wait for pattern match in device output",
    "category": "expect",
    "parse_mode": "options",
    "parameters": {
      "-e": {
        "alias": "pattern",
        "type": "string",
        "position": 0,
        "required": true
      },
      "-for": {
        "alias": "qaid",
        "type": "string",
        "position": 1,
        "required": false
      },
      "-t": {
        "alias": "timeout",
        "type": "int",
        "position": 2,
        "required": false,
        "default": 10
      }
    }
  }
}
```

**How to Use:**
1. Find the command name (e.g., `"setvar"`)
2. Check `parse_mode`: `"options"` (uses `-flag value`) or `"positional"` (uses arguments)
3. Look at `parameters`: Each option's `alias` becomes the Python parameter name
4. Check `required` and `default` values

#### 2. API Implementation

**Files:** `lib/core/executor/api/*.py`

Each API category has its own module:
- `variable.py` - Variable operations (setvar, intset, strset, etc.)
- `expect.py` - Pattern matching (expect, expect_not, etc.)
- `utility.py` - Helpers (comment, sleep, breakpoint)
- `control.py` - Flow control (if, while, for, etc.)

**Example - Reading setvar Implementation:**

```python
# File: lib/core/executor/api/variable.py

def setvar(executor, params):
    """
    Set variable from pattern match in device output.
    
    DSL Syntax:
        setvar -e "pattern" -to varname
    
    Parameters (from cli_syntax.json):
        params.rule (str): Regex pattern with capture group [-e]
        params.name (str): Variable name to set [-to]
    """
    rule = _normalize_regexp(params.rule)  # Access -e via params.rule
    name = params.name                     # Access -to via params.name
    
    # Search previous command output
    # Uses default need_clear=True - buffer cleared AFTER extraction
    match, _ = executor.cur_device.expect(rule)
    
    if match:
        value = match.group(1)  # Extract first capture group
        env.add_var(name, value)  # Store as {$name}
        logger.info("Succeeded to set variable %s to '%s'", name, value)
    else:
        logger.error("Failed to execute setvar.")
```

**How Parameters Work:**

```
DSL Command:     setvar -e "Serial-Number: (FGVM\w+)" -to sn
                         ↓                              ↓
Schema Mapping:  "-e" → alias: "rule"          "-to" → alias: "name"
                         ↓                              ↓
Python Access:   params.rule                    params.name
```

See [DSL_COMPILATION_FLOW.md](DSL_COMPILATION_FLOW.md) for detailed explanation of how DSL text becomes API calls.

#### 3. Example Test Scripts

**Location:** `testcase/` and `examples/`

Look at existing test scripts to see DSL usage:

```bash
# Find examples of setvar usage
grep -r "setvar" testcase/ examples/

# Find examples of expect usage
grep -r "expect -e" testcase/ examples/

# Find variable usage
grep -r "{\$" testcase/ examples/
```

---

## Troubleshooting Workflow

### Step 1: Enable Debug Logging

Always run with `-d` flag to see detailed logs:

```bash
cd /home/fosqa/autolibv3/autolib_v3
python3 autotest.py \
    -c testcase/path/to/test.txt \
    -e testcase/path/to/env.conf \
    -d  # Enable debug logging
```

**What to Look For:**
```log
# Variable interpolation
2026-02-17 15:29:31,794 - root - DEBUG - replaced content: 'Device serial: {$sn}'

# Pattern matching
2026-02-17 15:14:57,877 - root - DEBUG - Pattern - <None> was matched?  Serial-Number: (FGVM.*), time used: 10.1 s

# Buffer content
2026-02-17 15:14:57,877 - root - DEBUG - Buffer content is :
--------------------------------------------------------------------------------
Serial-Number: FGVMULTM25002684
FGTB (Interim)#  
--------------------------------------------------------------------------------

# Variable set result
2026-02-17 15:29:31,793 - root - INFO - Succeeded to set variable sn to 'FGVMULTM25002684'
```

### Step 2: Check Output Directory

Test results are stored in `outputs/YYYY-MM-DD/HH-MM-SS--script--testname/`:

```bash
# Find latest test output
ls -lt outputs/$(date +%Y-%m-%d)/ | head -5

# View summary log
cat outputs/2026-02-17/15-29-29--script--first_case/summary/autotest.log

# Check failed QA IDs
cat outputs/2026-02-17/15-29-29--script--first_case/summary/failed.txt
```

### Step 3: Common Debug Techniques

#### Check Variable Values

```python
# In your test script, add debug output
setvar -e "Serial-Number: (FGVM\w+)" -to sn
comment DEBUG: Serial number is {$sn}  # Check if variable is set
```

#### Check Buffer Content

```python
# Before setvar, verify the output is in the buffer
get system status | grep 'Serial-Number'
expect -e "Serial-Number:" -t 5  # Verify output appeared
setvar -e "Serial-Number: (FGVM\w+)" -to sn  # Now extract it
```

#### Test Pattern Matching

```python
# Use expect to test your pattern first
get system status
expect -e "Serial-Number: (FGVM\w+)" -for TEST_001 -t 5

# If expect works, setvar will work with same pattern
setvar -e "Serial-Number: (FGVM\w+)" -to sn
```

#### Clear Python Cache

If code changes aren't taking effect:

```bash
# Remove compiled Python cache
find lib/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Or clear specific module cache
rm -rf lib/core/executor/api/__pycache__
```

### Step 4: Check Configuration Issues

#### Environment Config Problems

```bash
# Check for problematic variables
grep -E "^[^;#].*:.*no$" testcase/path/to/env.conf

# Example output showing issue:
# VM: no    # ← This causes FGVM → FGno transformation!

# Fix: Comment it out
# ; VM: no
```

#### Device Connection Issues

```bash
# Verify CONNECTION string is correct
grep "^CONNECTION:" testcase/path/to/env.conf

# Should be:
# CONNECTION: ssh admin@10.96.234.41 -p 62022

# Not:
# CONNECTION: ssh admin@10.96.234.41  # Missing port!
```

### Step 5: Verify API Understanding

Check the implementation if behavior is unexpected:

```bash
# Find where setvar is defined
grep -rn "def setvar" lib/core/executor/api/

# View the implementation
cat lib/core/executor/api/variable.py

# Check the schema
cat lib/core/compiler/static/cli_syntax.json | jq '.variable.setvar'
```

---

## API Reference

### Variable Management APIs

#### `setvar` - Extract Value from Pattern

**Syntax:**
```python
setvar -e "regex_pattern" -to variable_name
```

**Parameters:**
- `-e` (required): Regex pattern with **one capture group** `()`
- `-to` (required): Variable name (without `$` or `{$}`)

**Example:**
```python
# Extract serial number
get system status
setvar -e "Serial-Number: (FG[\w]+)" -to serial

# Use it later
comment Serial: {$serial}
```

**Important:**
- Pattern must have exactly one capture group `(...)`
- Searches the **previous command's output** (buffer)
- Only captures `match.group(1)` - the first capture group
- Variable is accessed as `{$varname}` in DSL

#### `intset` - Set Integer Variable

**Syntax:**
```python
intset variable_name number
```

**Example:**
```python
intset retry_count 5
intset timeout 300

# Use in commands
comment Retry count: {$retry_count}
```

#### `strset` - Set String Variable

**Syntax:**
```python
strset variable_name value
```

**Example:**
```python
strset platform FortiGate-100E
strset status active

comment Platform: {$platform}, Status: {$status}
```

#### `intchange` - Modify Integer Variable

**Syntax:**
```python
intchange {$variable} operator value
```

**Operators:** `+`, `-`, `*`, `/`

**Example:**
```python
intset counter 0
intchange {$counter} + 1
intchange {$counter} * 2
comment Counter value: {$counter}  # Shows: 2
```

### Pattern Matching APIs

#### `expect` - Wait for Pattern

**Syntax:**
```python
expect -e "pattern" [-for qaid] [-t timeout] [-fail match|unmatch]
```

**Parameters:**
- `-e` (required): Regex pattern to match
- `-for` (optional): QA ID to report result
- `-t` (optional): Timeout in seconds (default: 10)
- `-fail` (optional): `match` (fail if found) or `unmatch` (fail if not found)

**Example:**
```python
get system status
expect -e "Version: FortiGate" -for 205817 -t 5
```

### Usage Pattern: expect + setvar

**Common Workflow:**
```python
# 1. Run command
get system status

# 2. Verify output appeared (optional but recommended)
expect -e "Serial-Number:" -t 5

# 3. Extract value
setvar -e "Serial-Number: (FG[\w]+)" -to sn

# 4. Use extracted value
comment Device SN: {$sn}
```

---

## Best Practices

### 1. Always Verify Buffer Before setvar

```python
# ✅ GOOD - Verify output exists first
get system status | grep 'Serial-Number'
expect -e "Serial-Number:" -t 5  # Confirm it appeared
setvar -e "Serial-Number: (FGVM\w+)" -to sn

# ❌ BAD - Blindly call setvar
setvar -e "Serial-Number: (FGVM\w+)" -to sn  # May fail silently
```

### 2. Use Specific Patterns

```python
# ❌ BAD - Too greedy, captures everything
setvar -e "Serial-Number: (.*)" -to sn

# ✅ BETTER - Character class
setvar -e "Serial-Number: (FG[A-Z0-9]+)" -to sn

# ✅ BEST - Specific pattern
setvar -e "Serial-Number: (FGVM\w+)" -to sn
```

### 3. Debug Variable Expansion

```python
# Add debug comments
setvar -e "Serial-Number: (FGVM\w+)" -to sn
comment DEBUG: SN = {$sn}  # Check if variable was set correctly
```

### 4. Comment Unused Config Variables

```ini
# In .conf file - comment out unused variables
; VM: no           # ✅ GOOD - won't interfere
; UNUSED_VAR: foo  # ✅ GOOD

# VM: no           # ❌ BAD - may cause issues
```

### 5. Use Meaningful Variable Names

```python
# ✅ GOOD - Clear purpose
setvar -e "Serial-Number: (FGVM\w+)" -to device_serial
setvar -e "Build ([0-9]+)" -to build_number

# ❌ BAD - Unclear names
setvar -e "Serial-Number: (FGVM\w+)" -to sn
setvar -e "Build ([0-9]+)" -to bn
```

---

## Quick Troubleshooting Checklist

When variables don't work:

- [ ] **Syntax:** Using `{$varname}` for user-defined variables?
- [ ] **Buffer:** Did you run a command BEFORE setvar?
- [ ] **Pattern:** Does the pattern have exactly one capture group `(...)`?
- [ ] **Pattern:** Is the pattern too greedy? (Use `\w+` instead of `.*`)
- [ ] **Config:** Any conflicting variables in `.conf` file? (Check for `VM:`, etc.)
- [ ] **Cache:** Cleared `__pycache__` after code changes?
- [ ] **Logging:** Running with `-d` flag to see debug output?
- [ ] **Timing:** Did the output appear before timeout?

When pattern doesn't match:

- [ ] Check buffer content in debug log
- [ ] Test pattern with `expect` first
- [ ] Verify escape sequences (`\` vs `\\`)
- [ ] Check if environment config is modifying the pattern

---

## Related Documentation

- **[DSL_COMPILATION_FLOW.md](DSL_COMPILATION_FLOW.md)** - How DSL text becomes API calls
- **[DSL_USAGE_GUIDE.md](DSL_USAGE_GUIDE.md)** - Complete DSL API reference
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Basic usage tutorial
- **[DEVICE_CONFIGURATION.md](DEVICE_CONFIGURATION.md)** - Device setup and DUT management
- **[TROUBLESHOOTING_ORIOLE.md](TROUBLESHOOTING_ORIOLE.md)** - Oriole reporting issues

---

## Summary

**Key Takeaways:**

1. **Two Variable Syntaxes:**
   - `$VAR` - Environment config from `.conf` file
   - `{$VAR}` - User-defined from `setvar`, `intset`, `strset`

2. **setvar Requirements:**
   - Run command BEFORE setvar to populate buffer
   - Pattern must have exactly ONE capture group `(...)`
   - Uses `need_clear=False` to preserve buffer

3. **Troubleshooting:**
   - Always use `-d` flag for debug logs
   - Check buffer content in logs
   - Test patterns with `expect` first
   - Clear `__pycache__` after code changes

4. **Resources:**
   - Syntax: `lib/core/compiler/static/cli_syntax.json`
   - Implementation: `lib/core/executor/api/*.py`
   - Examples: `testcase/` and `examples/`

For detailed compilation flow and parameter mapping, see [DSL_COMPILATION_FLOW.md](DSL_COMPILATION_FLOW.md).
