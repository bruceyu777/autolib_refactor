# DSL to Execution - Complete Walkthrough with Real Example

**Test Case**: `first_case.txt` - Advanced Health Check Test  
**Device**: FGT_B (FortiGate-VM64-KVM)  
**Execution Date**: 2026-02-17 17:10:44  
**Framework**: AutoLib v3 V3R10B0007

---

## Table of Contents

1. [Overview](#overview)
2. [Stage 1: DSL Source Code](#stage-1-dsl-source-code)
3. [Stage 2: Lexical Analysis (Tokens)](#stage-2-lexical-analysis-tokens)
4. [Stage 3: VM Code Generation](#stage-3-vm-code-generation)
5. [Stage 4: Execution](#stage-4-execution)
6. [Stage 5: Results](#stage-5-results)
7. [Complete Flow Diagram](#complete-flow-diagram)
8. [Key Insights](#key-insights)

---

## Overview

This document provides a **concrete, end-to-end walkthrough** of how AutoLib v3 transforms DSL test scripts into executable code and executes them against real devices. We'll trace an actual test execution showing:

- **Input**: DSL test script with variables, control flow, and device commands
- **Compilation**: Lexer tokens → VM codes with schema validation
- **Execution**: Device communication and result collection
- **Output**: Test results and validation status

### Test Summary

**Purpose**: Comprehensive device health check with retry logic, conditional validation, and multi-phase testing

**Key Features Demonstrated**:
- ✅ Variable definitions and interpolation
- ✅ While loop with retry logic
- ✅ If/elseif/else conditional branches
- ✅ Pattern matching and data extraction (setvar)
- ✅ Device command execution
- ✅ QAID-based result tracking
- ✅ Centralized QAID management

**Test Phases**:
1. Connection retry (3 attempts with delays)
2. Device info extraction (version, serial, hostname)
3. Platform-specific validation (VM64 vs VM64-KVM)
4. System resources check (memory, HA status)
5. Storage validation with retry

---

## Stage 1: DSL Source Code

### Example 1: Variable Definitions and Section Header

**DSL Source** (`first_case.txt` lines 2-18):
```plaintext
[FGT_B]
    comment ========================================
    comment Starting Device Health Check Test
    comment ========================================
    
    # ========================================
    # TEST CASE IDs (QAIDs) - Centralized Definition
    # ========================================
    # Main test case
    <strset QAID_MAIN 205817>
    
    # Phase 1: Connection checks
    <strset QAID_CONN_RETRY 205801>
    
    # Phase 2: Device information extraction
    <strset QAID_VERSION_CHECK 205817>
    <strset QAID_SERIAL_CHECK 205802>
```

**What Happens Here**:
- `[FGT_B]` defines device section → executor will switch to FGT_B device
- `comment` lines → displayed to user during execution
- `<strset VAR value>` → creates user-defined variables
- Variables stored as `{$QAID_MAIN}` for later use

---

### Example 2: While Loop with Retry Logic

**DSL Source** (`first_case.txt` lines 37-59):
```plaintext
    <intset retry_count 0>
    <intset max_retries 3>
    <intset connection_ok 0>
    
    # Phase 1: Connection Health Check with Retry Logic
    comment Phase 1: Verifying device connectivity...
    
    <while {$retry_count} < {$max_retries}>
        <intchange {$retry_count} + 1>
        comment Attempt {$retry_count} of {$max_retries}...
        
        # Try to get system status with timeout
        get system status
        expect -e "Version: FortiGate" -for {$QAID_CONN_RETRY} -t 5
        
        # Try to extract version - if successful, connection is good
        setvar -e "Version: (FortiGate-\w+)" -to platform_check
        
        # Small delay before next retry if needed
        <if {$retry_count} < {$max_retries}>
            sleep 1
        <fi>
    <endwhile {$retry_count} eq {$max_retries}>
    
    comment Connection attempts completed: {$retry_count} tries
```

**What Happens Here**:
- `<intset>` creates integer variables
- `<while condition>` starts loop, evaluates expression
- `<intchange VAR + 1>` increments counter
- `get system status` → device command (not an API, sent as-is)
- `expect -e "pattern" -for {$VAR} -t 5` → API call with parameters:
  - `-e`: regex pattern to match
  - `-for`: QAID (from variable substitution)
  - `-t`: timeout in seconds
- `setvar -e "regex" -to varname` → extract data from device output
- Nested `<if>` inside `<while>` → conditional delay
- `<endwhile condition>` → loop until condition met

---

### Example 3: Conditional Branching

**DSL Source** (`first_case.txt` lines 96-110):
```plaintext
    # Phase 3: Conditional Testing Based on Platform Type
    comment Phase 3: Platform-specific validation...
    
    <if {$platform_type} eq FortiGate-VM64>
        comment Detected VM platform: FortiGate-VM64
        get system status
        expect -e "Virtual" -for {$QAID_VM64_CHECK} -t 5
        
    <elseif {$platform_type} eq FortiGate-VM64-KVM>
        comment Detected KVM platform: FortiGate-VM64-KVM
        expect -e "Virtual" -for {$QAID_VM64_KVM_CHECK} -t 5
        
    <else>
        comment Platform type: {$platform_type} (other platform)
        expect -e "Version:" -for {$QAID_OTHER_PLATFORM} -t 5
    <fi>
```

**What Happens Here**:
- `<if VAR eq value>` → compare variable to string literal
- Variable `{$platform_type}` evaluated at runtime
- Three branches: VM64, VM64-KVM, or other
- Only one branch executes based on condition
- Different QAIDs track different validation paths

---

### Example 4: Data Extraction with setvar

**DSL Source** (`first_case.txt` lines 64-83):
```plaintext
    # Phase 2: Extract and Validate Device Information
    comment Phase 2: Extracting device information...
    
    # Extract version information with extended timeout
    get system status
    expect -e "Version: FortiGate" -for {$QAID_VERSION_CHECK} -t 10 -clear no
    setvar -e "Version: (FortiGate-[\w-]+)" -to platform_type
    setvar -e "v(\d+\.\d+\.\d+)" -to firmware_version
    
    # Extract serial number with retry protection
    <intset sn_retry 0>
    <while {$sn_retry} < 2>
        get system status | grep 'Serial-Number'
        expect -e "Serial-Number:" -for {$QAID_SERIAL_CHECK} -t 5 -clear no
        setvar -e "Serial-Number: (FGVM\w+)" -to device_serial
        <intset sn_retry 3>  # Exit loop after first attempt
    <endwhile {$sn_retry} eq 3>
    
    # Extract hostname
    get system status
    setvar -e "Hostname: (\S+)" -to hostname
```

**What Happens Here**:
- `expect -clear no` → preserve buffer for multiple extractions
- `setvar -e "regex with (capture)" -to varname` → extracts matched group
- Multiple `setvar` on same output → extract different fields
- Variables `{$platform_type}`, `{$firmware_version}`, etc. now available
- Pipe command `get system status | grep 'Serial-Number'` → Unix-style filtering

---

## Stage 2: Lexical Analysis (Tokens)

### How Lexer Works

The lexer reads the DSL source line-by-line and classifies each element into tokens:

| Token Type | Description | Examples |
|------------|-------------|----------|
| `section` | Device name in brackets | `[FGT_B]`, `[PC_01]` |
| `comment` | Displayed text | `comment Phase 1...` |
| `keyword` | Control flow keywords | `if`, `while`, `strset`, `intset` |
| `api` | API function calls | `expect`, `setvar`, `sleep` |
| `command` | Device CLI commands | `get system status` |
| `identifier` | Variable names, values | `retry_count`, `205817` |
| `variable` | Variable references | `{$retry_count}`, `QAID_MAIN` |
| `string` | Quoted strings | `"Version: FortiGate"` |
| `number` | Numeric literals | `5`, `10`, `3` |
| `symbol` | Operators | `+`, `-`, `<`, `eq` |

### Real Token Output

**From Line 2** (`[FGT_B]`):
```json
{
    "data": "FGT_B",
    "type": "section",
    "line_number": 2
}
```

**From Line 11** (`<strset QAID_MAIN 205817>`):
```json
{
    "data": "strset",
    "type": "keyword",
    "line_number": 11
},
{
    "data": "QAID_MAIN",
    "type": "identifier",
    "line_number": 11
},
{
    "data": "205817",
    "type": "identifier",
    "line_number": 11
}
```

**From Line 44** (`<while {$retry_count} < {$max_retries}>`):
```json
{
    "data": "while",
    "type": "keyword",
    "line_number": 44
},
{
    "data": "{$retry_count} < {$max_retries}",
    "type": "identifier",
    "line_number": 44
}
```

**From Line 49** (`get system status`):
```json
{
    "data": "get system status",
    "type": "command",
    "line_number": 49
}
```

**From Line 50** (`expect -e "Version: FortiGate" -for {$QAID_CONN_RETRY} -t 5`):
```json
{
    "data": "expect",
    "type": "api",
    "line_number": 50
},
{
    "data": "-e",
    "type": "identifier",
    "line_number": 50
},
{
    "data": "Version: FortiGate",
    "type": "string",
    "line_number": 50
},
{
    "data": "-for",
    "type": "identifier",
    "line_number": 50
},
{
    "data": "QAID_CONN_RETRY",
    "type": "variable",
    "line_number": 50
},
{
    "data": "-t",
    "type": "identifier",
    "line_number": 50
},
{
    "data": "5",
    "type": "number",
    "line_number": 50
}
```

**From Line 53** (`setvar -e "Version: (FortiGate-\w+)" -to platform_check`):
```json
{
    "data": "setvar",
    "type": "api",
    "line_number": 53
},
{
    "data": "-e",
    "type": "identifier",
    "line_number": 53
},
{
    "data": "Version: (FortiGate-\\w+)",
    "type": "string",
    "line_number": 53
},
{
    "data": "-to",
    "type": "identifier",
    "line_number": 53
},
{
    "data": "platform_check",
    "type": "identifier",
    "line_number": 53
}
```

**From Line 56-58** (if/fi block):
```json
{
    "data": "if",
    "type": "keyword",
    "line_number": 56
},
{
    "data": "retry_count",
    "type": "variable",
    "line_number": 56
},
{
    "data": "<",
    "type": "symbol",
    "line_number": 56
},
{
    "data": "max_retries",
    "type": "variable",
    "line_number": 56
},
{
    "data": "sleep",
    "type": "api",
    "line_number": 57
},
{
    "data": "1",
    "type": "number",
    "line_number": 57
},
{
    "data": "fi",
    "type": "keyword",
    "line_number": 58
}
```

### Lexer Output Statistics

**Total Tokens**: 1,344 tokens generated from 168 lines of DSL

**Token Distribution**:
- Comments: ~30 tokens
- Keywords (if/while/strset/etc): ~45 tokens
- APIs (expect/setvar/command): ~20 API calls
- Identifiers/Variables: ~900 tokens
- Strings: ~25 quoted strings
- Numbers: ~50 numeric values

**File**: `outputs/.../first_case/compiled/tokens.json` (1,344 lines)

---

## Stage 3: VM Code Generation

### What are VM Codes?

VM Codes are **executable instructions** generated from parsed DSL. Each VM code represents:
- A line number (for debugging)
- An operation (API name or control flow marker)
- Parameters (as single space-separated string or tuple)

### VM Code Format

```
<line_number> <operation> <param1> <param2> ... <paramN>
```

### Real VM Code Output

**Device Section** (Line 2):
```plaintext
2 switch_device FGT_B
```
- **Operation**: `switch_device`
- **Parameter**: `FGT_B`
- **Execution**: Sets `executor.cur_device = devices['FGT_B']`

---

**Comments** (Lines 3-5):
```plaintext
3 comment ========================================
4 comment Starting Device Health Check Test
5 comment ========================================
```
- **Operation**: `comment`
- **Parameter**: Text to display
- **Execution**: Prints to console/log

---

**Variable Definitions** (Lines 11-32):
```plaintext
11 strset QAID_MAIN 205817
14 strset QAID_CONN_RETRY 205801
17 strset QAID_VERSION_CHECK 205817
18 strset QAID_SERIAL_CHECK 205802
...
37 intset retry_count 0
38 intset max_retries 3
39 intset connection_ok 0
```
- **Operation**: `strset` / `intset`
- **Parameters**: `<variable_name> <value>`
- **Execution**: Stores in executor's variable dictionary
  - `executor.vars['QAID_MAIN'] = '205817'`
  - `executor.vars['retry_count'] = 0`

---

**While Loop** (Lines 44-59):
```plaintext
44 loop {$retry_count} < {$max_retries}
45 intchange retry_count + 1
46 comment Attempt {$retry_count} of {$max_retries}...
49 command get system status
50 expect Version: FortiGate QAID_CONN_RETRY 5 unmatch None None yes None 3
53 setvar Version: (FortiGate-\w+) platform_check
56 if_not_goto retry_count < max_retries 58
57 sleep 1
58 endif
59 until 44 retry_count eq max_retries
```

**Breakdown**:

**Line 44**: `loop {$retry_count} < {$max_retries}`
- **Operation**: `loop`
- **Parameter**: Condition expression
- **Execution**: Evaluates expression, if false jumps to matching `until`

**Line 45**: `intchange retry_count + 1`
- **Operation**: `intchange`
- **Parameters**: `retry_count + 1`
- **Execution**: `executor.vars['retry_count'] += 1`

**Line 49**: `command get system status`
- **Operation**: `command`
- **Parameter**: `get system status`
- **Execution**: `executor.cur_device.send_command("get system status")`

**Line 50**: `expect Version: FortiGate QAID_CONN_RETRY 5 unmatch None None yes None 3`
- **Operation**: `expect`
- **Parameters** (positional):
  1. `Version: FortiGate` - pattern
  2. `QAID_CONN_RETRY` - qaid (variable name, will be resolved)
  3. `5` - timeout
  4. `unmatch` - fail on match mode
  5. `None` - invert_check
  6. `None` - allow_ctrl_c
  7. `yes` - need_clear
  8. `None` - msg
  9. `3` - retry_count
- **Execution**: 
  ```python
  device.expect("Version: FortiGate", timeout=5)
  result_manager.add_qaid_expect_result("205801", is_succeeded, output)
  ```

**Line 53**: `setvar Version: (FortiGate-\w+) platform_check`
- **Operation**: `setvar`
- **Parameters**: `<pattern> <variable_name>`
- **Execution**: Extract regex match from buffer, store in variable

**Line 56**: `if_not_goto retry_count < max_retries 58`
- **Operation**: `if_not_goto`
- **Parameters**: `<condition> <jump_target>`
- **Execution**: If condition is FALSE, jump to line 58 (skip sleep)

**Line 59**: `until 44 retry_count eq max_retries`
- **Operation**: `until`
- **Parameters**: `<loop_start_line> <exit_condition>`
- **Execution**: If condition is true, exit loop; else jump back to line 44

---

**Conditional Branches** (Lines 98-110):
```plaintext
98  if_not_goto platform_type eq FortiGate-VM64 103
99  comment Detected VM platform: FortiGate-VM64
100 command get system status
101 expect Virtual QAID_VM64_CHECK 5 unmatch None None yes None 3
103 elseif platform_type eq FortiGate-VM64-KVM 107
104 comment Detected KVM platform: FortiGate-VM64-KVM
105 expect Virtual QAID_VM64_KVM_CHECK 5 unmatch None None yes None 3
107 else 110
108 comment Platform type: {$platform_type} (other platform)
109 expect Version: QAID_OTHER_PLATFORM 5 unmatch None None yes None 3
110 endif
```

**Control Flow Logic**:

| Line | VM Code | Condition | Action |
|------|---------|-----------|--------|
| 98 | `if_not_goto platform_type eq FortiGate-VM64 103` | If NOT VM64 | Jump to line 103 (elseif) |
| 99-101 | VM64 branch code | Only executes if VM64 | - |
| 103 | `elseif platform_type eq FortiGate-VM64-KVM 107` | If NOT VM64-KVM | Jump to line 107 (else) |
| 104-105 | VM64-KVM branch code | Only executes if VM64-KVM | - |
| 107 | `else 110` | Always | Jump to line 110 (endif) |
| 108-109 | Else branch code | Only if neither VM64 nor VM64-KVM | - |
| 110 | `endif` | N/A | Continue to next line |

**Actual Execution Path** (for FortiGate-VM64-KVM):
```
Line 98:  Evaluate: platform_type == "FortiGate-VM64"? → FALSE → Jump to 103
Line 103: Evaluate: platform_type == "FortiGate-VM64-KVM"? → TRUE → Continue to 104
Line 104: Execute: comment
Line 105: Execute: expect Virtual
Line 107: Jump to 110 (skip else branch)
Line 110: Continue execution
```

---

**Report Final Result** (Line 166):
```plaintext
166 report QAID_MAIN
```
- **Operation**: `report`
- **Parameter**: `QAID_MAIN` (variable name)
- **Execution**: 
  ```python
  qaid_value = executor.vars['QAID_MAIN']  # "205817"
  result_manager.report_qaid(qaid_value)
  ```

---

### Complete VM Code File

**File**: `outputs/.../first_case/compiled/codes.vm` (168 lines)

**Structure**:
```
Line  Operation       Parameters
════  ══════════════  ══════════════════════════════════════
2     switch_device   FGT_B
3-5   comment         [Header comments]
11-32 strset/intset   [Variable definitions]
37-39 intset          [Loop counters]
42    comment         Phase 1...
44-59 loop/until      [While loop with retry logic]
67-83 command/expect  [Data extraction]
98-110 if/elseif/else [Platform validation]
116-141 command/expect [Resource checks with nested if]
147-153 loop/until    [Storage validation retry]
166   report          QAID_MAIN
168   comment         Completion message
```

**Key Transformations**:

| DSL | VM Code |
|-----|---------|
| `<while {$retry_count} < {$max_retries}>` | `loop {$retry_count} < {$max_retries}` |
| `<endwhile {$retry_count} eq {$max_retries}>` | `until 44 retry_count eq max_retries` |
| `<if {$platform_type} eq FortiGate-VM64>` | `if_not_goto platform_type eq FortiGate-VM64 103` |
| `expect -e "..." -for {$VAR} -t 5` | `expect ... VAR 5 unmatch None None yes None 3` |
| `{$QAID_CONN_RETRY}` | `QAID_CONN_RETRY` (variable name stored) |

---

## Stage 4: Execution

### Execution Environment

**Device Connection**:
```ini
[FGT_B]
Platform: FGVM
CONNECTION: ssh admin@10.96.234.41 -p 62022
USERNAME: admin
PASSWORD: admin
```

**Connection Established**:
- Protocol: SSH
- Host: 10.96.234.41
- Port: 62022
- Login: admin/admin
- Session: Active FortiGate CLI prompt

---

### Execution Flow

#### Phase 1: Connection Retry Loop

**VM Codes Executed**:
```plaintext
44 loop {$retry_count} < {$max_retries}     # PC=0: Check 0 < 3 → TRUE, continue
45 intchange retry_count + 1                # PC=1: retry_count = 1
46 comment Attempt {$retry_count} of {$max_retries}...  # PC=2: Display
49 command get system status                # PC=3: Send to device
50 expect Version: FortiGate ...            # PC=4: Match pattern
59 until 44 retry_count eq max_retries      # PC=5: Check 1 == 3 → FALSE, loop back

# Second iteration
44 loop {$retry_count} < {$max_retries}     # PC=0: Check 1 < 3 → TRUE, continue
45 intchange retry_count + 1                # PC=1: retry_count = 2
...

# Third iteration
44 loop {$retry_count} < {$max_retries}     # PC=0: Check 2 < 3 → TRUE, continue
45 intchange retry_count + 1                # PC=1: retry_count = 3
...
59 until 44 retry_count eq max_retries      # PC=5: Check 3 == 3 → TRUE, exit loop
```

**Device Interaction** (Attempt 1):
```
SEND: get system status

RECEIVE:
Version: FortiGate-VM64-KVM v8.0.0,build0129,260211 (interim)
First GA patch build date: 240724
Current Security Level: Low
Firmware Signature: not-certified
...
Serial-Number: FGVMULTM25002684
...
Hostname: FGTB
...

PATTERN MATCH: "Version: FortiGate" → FOUND ✓
QAID 205801 (QAID_CONN_RETRY): PASS
```

**Variables After Loop**:
```python
{
    'retry_count': 3,
    'max_retries': 3,
    'connection_ok': 0,
    'platform_check': 'FortiGate-VM64-KVM'  # From setvar
}
```

---

#### Phase 2: Data Extraction

**VM Codes Executed**:
```plaintext
67 command get system status
68 expect Version: FortiGate QAID_VERSION_CHECK 10 unmatch None None no None 3
69 setvar Version: (FortiGate-[\w-]+) platform_type
70 setvar v(\d+\.\d+\.\d+) firmware_version
```

**Execution Steps**:

1. **Send Command**: `get system status`

2. **Expect Pattern**: Wait for "Version: FortiGate" (max 10 seconds)
   - Buffer contains:
     ```
     Version: FortiGate-VM64-KVM v8.0.0,build0129,260211 (interim)
     ```
   - Match found: ✓
   - QAID 205817: PASS
   - Buffer preserved (`-clear no`)

3. **Extract Platform** (`setvar -e "Version: (FortiGate-[\w-]+)" -to platform_type`):
   - Regex: `Version: (FortiGate-[\w-]+)`
   - Match: `FortiGate-VM64-KVM`
   - Variable: `platform_type = "FortiGate-VM64-KVM"`

4. **Extract Firmware** (`setvar -e "v(\d+\.\d+\.\d+)" -to firmware_version`):
   - Regex: `v(\d+\.\d+\.\d+)`
   - Match: `8.0.0`
   - Variable: `firmware_version = "8.0.0"`

**Next Extraction** (Serial Number):
```plaintext
75 command get system status | grep 'Serial-Number'
76 expect Serial-Number: QAID_SERIAL_CHECK 5 unmatch None None no None 3
77 setvar Serial-Number: (FGVM\w+) device_serial
```

**Device Response**:
```
Serial-Number: FGVMULTM25002684
```

**Extracted**:
- `device_serial = "FGVMULTM25002684"`

**Hostname Extraction**:
```plaintext
82 command get system status
83 setvar Hostname: (\S+) hostname
```

**Extracted**:
- `hostname = "FGTB"`

**Variables Now Available**:
```python
{
    'platform_type': 'FortiGate-VM64-KVM',
    'firmware_version': '8.0.0',
    'device_serial': 'FGVMULTM25002684',
    'hostname': 'FGTB',
    'retry_count': 3,
    ...
}
```

**Display Summary**:
```plaintext
86-93 comment ========================================
      comment Device Information Summary:
      comment   Platform: FortiGate-VM64-KVM      ← Variable interpolated
      comment   Firmware: 8.0.0                    ← Variable interpolated
      comment   Serial: FGVMULTM25002684           ← Variable interpolated
      comment   Hostname: FGTB                     ← Variable interpolated
      comment   Retry Count: 3                     ← Variable interpolated
      comment ========================================
```

---

#### Phase 3: Conditional Platform Validation

**VM Codes**:
```plaintext
98  if_not_goto platform_type eq FortiGate-VM64 103
99  comment Detected VM platform: FortiGate-VM64
100 command get system status
101 expect Virtual QAID_VM64_CHECK 5 unmatch None None yes None 3
103 elseif platform_type eq FortiGate-VM64-KVM 107
104 comment Detected KVM platform: FortiGate-VM64-KVM
105 expect Virtual QAID_VM64_KVM_CHECK 5 unmatch None None yes None 3
107 else 110
108 comment Platform type: {$platform_type} (other platform)
109 expect Version: QAID_OTHER_PLATFORM 5 unmatch None None yes None 3
110 endif
```

**Execution Path**:

**Line 98**: Evaluate `platform_type eq FortiGate-VM64`
- Current value: `platform_type = "FortiGate-VM64-KVM"`
- Condition: `"FortiGate-VM64-KVM" == "FortiGate-VM64"` → **FALSE**
- Action: **Jump to line 103** (skip lines 99-101)

**Line 103**: Evaluate `platform_type eq FortiGate-VM64-KVM`
- Condition: `"FortiGate-VM64-KVM" == "FortiGate-VM64-KVM"` → **TRUE**
- Action: **Continue to line 104** (execute elseif branch)

**Line 104**: Execute comment
```
Output: "Detected KVM platform: FortiGate-VM64-KVM"
```

**Line 105**: Execute expect
```
SEND: (use previous buffer or implicit device query)
PATTERN: "Virtual"
MATCH: ✓ (Output contains "Virtual domain")
QAID: 205819 (QAID_VM64_KVM_CHECK): PASS
```

**Line 107**: else → **Jump to line 110** (skip lines 108-109)

**Line 110**: endif → Continue execution

**Lines Executed**: 98, 103, 104, 105, 107, 110  
**Lines Skipped**: 99-101, 108-109

---

#### Phase 4: System Resources Check

**VM Codes**:
```plaintext
116 command get system performance status
117 expect Memory: QAID_MEMORY_CHECK 10 unmatch None None yes None 3
120 command get system ha status
121 expect Mode: QAID_HA_MODE_CHECK 15 unmatch None None yes None 3
122 setvar Mode: (\w+) ha_mode
```

**Device Interaction**:

**Memory Check**:
```
SEND: get system performance status

RECEIVE:
CPU states: 2% user 0% system 0% nice 98% idle
CPU0 states: 2% user 0% system 0% nice 98% idle
...
Memory: 3946260k total, 1847720k used (46.8%), 2098540k free (53.2%)

PATTERN: "Memory:" → FOUND ✓
QAID 205803: PASS
```

**HA Status Check**:
```
SEND: get system ha status

RECEIVE:
HA Health Status: OK
Model: FortiGate-VM64-KVM
Mode: standalone
...

PATTERN: "Mode:" → FOUND ✓
QAID 205804: PASS
```

**Extract HA Mode**:
```
Regex: Mode: (\w+)
Match: "standalone"
Variable: ha_mode = "standalone"
```

**Nested If for HA Mode**:
```plaintext
126 if_not_goto ha_mode eq standalone 129
127 comment HA: Operating in standalone mode (no HA)
129 elseif ha_mode eq master 134
...
139 else 141
...
141 endif
```

**Execution**:
- Line 126: `ha_mode == "standalone"` → **TRUE** → Continue to 127
- Line 127: Display comment
- Line 129: elseif → **Jump to 141** (endif)

**Output**:
```
HA Configuration: standalone
HA: Operating in standalone mode (no HA)
```

---

#### Phase 5: Storage Validation with Retry

**VM Codes**:
```plaintext
147 intset vdom_check_retries 0
148 loop {$vdom_check_retries} < 2
149 command get system storage
151 expect Virtual-Disk NO_QAID 8 unmatch None None yes None 3
152 intchange vdom_check_retries + 1
153 until 148 vdom_check_retries eq 2
```

**First Iteration**:
```
vdom_check_retries = 0
Check: 0 < 2 → TRUE

SEND: get system storage
RECEIVE:
Disk       Ref sz Free/total   MB Free/total %
vd-root      1  4k   59%   4698/ 7951  59% /  79%
vd-vd1       0  4k  100%    511/  511 100% / 100%

PATTERN: "Virtual-Disk" → NOT FOUND (actual output uses "Disk")
QAID: NO_QAID (no result recorded)

vdom_check_retries = 1
Check: 1 == 2 → FALSE → Loop back
```

**Second Iteration**:
```
vdom_check_retries = 1
Check: 1 < 2 → TRUE

SEND: get system storage
RECEIVE: (same as above)

PATTERN: "Virtual-Disk" → NOT FOUND
QAID: NO_QAID

vdom_check_retries = 2
Check: 2 == 2 → TRUE → Exit loop
```

**Note**: Pattern didn't match actual output format, but test continued (non-strict mode or NO_QAID doesn't fail test)

---

#### Final Summary and Report

**VM Codes**:
```plaintext
156-163 comment [Summary with variable interpolation]
166 report QAID_MAIN
168 comment Test execution completed successfully
```

**Output**:
```
========================================
Test Execution Summary:
  Total Connection Retries: 3
  Serial Number Retries: 3
  Storage Check Retries: 2
  Device: FGTB
  Status: ALL CHECKS COMPLETED
========================================

Report QAID: 205817 (QAID_MAIN)
Test execution completed successfully
```

**Final Variables State**:
```python
{
    'QAID_MAIN': '205817',
    'QAID_CONN_RETRY': '205801',
    'QAID_VERSION_CHECK': '205817',
    'QAID_SERIAL_CHECK': '205802',
    'QAID_VM64_KVM_CHECK': '205819',
    'QAID_MEMORY_CHECK': '205803',
    'QAID_HA_MODE_CHECK': '205804',
    'retry_count': 3,
    'max_retries': 3,
    'platform_type': 'FortiGate-VM64-KVM',
    'firmware_version': '8.0.0',
    'device_serial': 'FGVMULTM25002684',
    'hostname': 'FGTB',
    'ha_mode': 'standalone',
    'sn_retry': 3,
    'vdom_check_retries': 2
}
```

---

## Stage 5: Results

### Test Execution Summary

**Status**: ✅ PASSED

**Duration**: ~47 seconds (17:10:44 - 17:11:31)

**Commands Sent**: ~15 device commands

**QAIDs Tracked**:
| QAID | Purpose | Result |
|------|---------|--------|
| 205801 | Connection retry | PASS |
| 205817 | Version check | PASS |
| 205802 | Serial check | PASS |
| 205819 | VM64-KVM validation | PASS |
| 205803 | Memory check | PASS |
| 205804 | HA mode check | PASS |
| NO_QAID | Storage check | N/A (no report) |
| 205817 | Main report | PASS |

### Terminal Output Summary

**From**: `summary/brief_summary.txt`

```plaintext
========================================
Starting Device Health Check Test
========================================
Phase 1: Verifying device connectivity...
Attempt 1 of 3...
Attempt 2 of 3...
Attempt 3 of 3...
Connection attempts completed: 3 tries
Phase 2: Extracting device information...
========================================
Device Information Summary:
Platform: FortiGate-VM64-KVM
Firmware: 8.0.0
Serial: FGVMULTM25002684
Hostname: FGTB
Retry Count: 3
========================================
Phase 3: Platform-specific validation...
Detected KVM platform: FortiGate-VM64-KVM
Phase 4: Checking system resources...
HA Configuration: standalone
HA: Operating in standalone mode (no HA)
Phase 5: Validating configuration integrity...
========================================
Test Execution Summary:
Total Connection Retries: 3
Serial Number Retries: 3
Storage Check Retries: 2
Device: FGTB
Status: ALL CHECKS COMPLETED
========================================
Test execution completed successfully

first_case     testcase/ips/testcase_nm/first_case.txt     PASSED
```

### Device Interaction Logs

**File**: `terminal/FGT_B_interaction.log` (311 lines)

**Sample Interaction**:
```
get system status
get system status

Version: FortiGate-VM64-KVM v8.0.0,build0129,260211 (interim)
First GA patch build date: 240724
Current Security Level: Low
Firmware Signature: not-certified
Virus-DB: 1.00000(2018-04-09 18:07)
...
Serial-Number: FGVMULTM25002684
License Status: Valid
License Expiration Date: 2026-07-23
VM Resources: 4 CPU, 3946 MB RAM
Log hard disk: Available
Hostname: FGTB
...
Current HA mode: standalone
...
System time: Tue Feb 17 17:10:46 2026
Last reboot reason: warm reboot

FGTB (Interim)# get system status
...
```

### Compilation Artifacts

**Tokens**: `compiled/tokens.json` (1,344 tokens)
- Complete tokenization of all DSL elements
- Preserves line numbers for debugging
- Shows exact lexical classification

**VM Codes**: `compiled/codes.vm` (168 VM instructions)
- Optimized executable representation
- Control flow with jump addresses
- Variable references (not values)
- Ready for interpreter execution

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: DSL SOURCE CODE                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
        │  [FGT_B]                                          │
        │      <strset QAID_MAIN 205817>                    │
        │      <intset retry_count 0>                       │
        │      <while {$retry_count} < {$max_retries}>      │
        │          get system status                        │
        │          expect -e "Version:" -for {$QAID} -t 5   │
        │          setvar -e "Version: (.*)" -to version    │
        │      <endwhile>                                   │
        │      <if {$platform_type} eq FortiGate-VM64-KVM>  │
        │          comment Detected KVM platform            │
        │      <fi>                                          │
        │      report {$QAID_MAIN}                          │
        │                                                   │
        └───────────────────────┬───────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                 STAGE 2: LEXICAL ANALYSIS (TOKENS)                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        │  {"type": "section", "data": "FGT_B"}         │
        │  {"type": "keyword", "data": "strset"}        │
        │  {"type": "identifier", "data": "QAID_MAIN"}  │
        │  {"type": "identifier", "data": "205817"}     │
        │  {"type": "keyword", "data": "while"}         │
        │  {"type": "api", "data": "expect"}            │
        │  {"type": "string", "data": "Version:"}       │
        │  {"type": "variable", "data": "QAID"}         │
        │  ...                                          │
        │  Total: 1,344 tokens                          │
        │                                               │
        └───────────────────────┬───────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────────┐
│              STAGE 3: VM CODE GENERATION                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────────┐
        │                                                   │
        │  2   switch_device FGT_B                          │
        │  11  strset QAID_MAIN 205817                      │
        │  37  intset retry_count 0                         │
        │  44  loop {$retry_count} < {$max_retries}         │
        │  49  command get system status                    │
        │  50  expect Version: QAID 5 ... yes ...           │
        │  53  setvar Version: (.*) version                 │
        │  59  until 44 retry_count eq max_retries          │
        │  98  if_not_goto platform_type eq ... 103         │
        │  104 comment Detected KVM platform                │
        │  110 endif                                        │
        │  166 report QAID_MAIN                             │
        │  Total: 168 VM codes                              │
        │                                                   │
        └───────────────────────┬───────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                   STAGE 4: EXECUTION                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────────┐
        │                                                   │
        │  Executor Loop (PC = Program Counter)            │
        │  ════════════════════════════════════             │
        │  PC=0:  switch_device FGT_B                       │
        │         → Set cur_device = devices['FGT_B']       │
        │                                                   │
        │  PC=11: strset QAID_MAIN 205817                   │
        │         → vars['QAID_MAIN'] = '205817'            │
        │                                                   │
        │  PC=44: loop retry_count < max_retries            │
        │         → Evaluate: 0 < 3 → TRUE, continue        │
        │                                                   │
        │  PC=49: command get system status                 │
        │         → SSH: admin@10.96.234.41:62022           │
        │         → SEND: "get system status\n"             │
        │         → RECV: "Version: FortiGate-VM64-KVM..."  │
        │                                                   │
        │  PC=50: expect Version: QAID 5...                 │
        │         → Pattern: "Version:"                     │
        │         → Buffer search → MATCH FOUND ✓           │
        │         → result_manager.add_qaid(205801, PASS)   │
        │                                                   │
        │  PC=53: setvar Version: (.*) version              │
        │         → Regex match: "FortiGate-VM64-KVM"       │
        │         → vars['version'] = "FortiGate-VM64-KVM"  │
        │                                                   │
        │  PC=59: until retry_count eq max_retries          │
        │         → Evaluate: 1 == 3 → FALSE                │
        │         → Jump to PC=44 (loop again)              │
        │                                                   │
        │  [Loop iterations 2-3...]                         │
        │                                                   │
        │  PC=98:  if_not_goto platform_type eq VM64 103    │
        │          → Evaluate: "VM64-KVM" == "VM64" → FALSE │
        │          → Jump to PC=103                         │
        │                                                   │
        │  PC=103: elseif platform_type eq VM64-KVM 107     │
        │          → Evaluate: "VM64-KVM" == "VM64-KVM" ✓   │
        │          → Continue to PC=104                     │
        │                                                   │
        │  PC=104: comment Detected KVM platform            │
        │          → Display to console                     │
        │                                                   │
        │  PC=166: report QAID_MAIN                         │
        │          → qaid = vars['QAID_MAIN'] = '205817'    │
        │          → result_manager.report('205817')        │
        │                                                   │
        └───────────────────────┬───────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────────┐
│                      STAGE 5: RESULTS                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────────┐
        │                                                   │
        │  Test Summary                                     │
        │  ════════════════════════════════════             │
        │  Status: PASSED ✓                                 │
        │  Duration: 47 seconds                             │
        │  QAIDs Passed: 7/7                                │
        │                                                   │
        │  Extracted Data:                                  │
        │    Platform: FortiGate-VM64-KVM                   │
        │    Firmware: 8.0.0                                │
        │    Serial: FGVMULTM25002684                       │
        │    Hostname: FGTB                                 │
        │    HA Mode: standalone                            │
        │                                                   │
        │  Output Files:                                    │
        │    ├─ summary/brief_summary.txt                   │
        │    ├─ terminal/FGT_B_interaction.log              │
        │    ├─ compiled/tokens.json                        │
        │    └─ compiled/codes.vm                           │
        │                                                   │
        └───────────────────────────────────────────────────┘
```

---

## Key Insights

### 1. Two-Pass Variable Handling

**Compile-time** (Environment Variables):
```ini
[GLOBAL]
VERSION: trunk
```
```plaintext
DSL:  include testcase/GLOBAL:VERSION/test.txt
      ↓
VM:   include testcase/trunk/test.txt
```

**Runtime** (User Variables):
```plaintext
DSL:  <strset QAID_MAIN 205817>
      expect -e "..." -for {$QAID_MAIN}
      ↓
VM:   strset QAID_MAIN 205817
      expect ... QAID_MAIN ...
      ↓
Exec: vars['QAID_MAIN'] = '205817'
      qaid = vars['QAID_MAIN']  # "205817"
```

### 2. Control Flow Jump Optimization

**DSL**: Nested if/elseif/else structure
```plaintext
<if condition1>
    branch1
<elseif condition2>
    branch2
<else>
    branch3
<fi>
```

**VM Codes**: Jump-based optimization
```plaintext
98  if_not_goto condition1 103    # If FALSE, skip branch1
99  branch1 code
103 elseif condition2 107          # Check next condition
104 branch2 code
107 else 110                       # Jump to end
108 branch3 code
110 endif
```

**Execution**: Only one branch runs, others skipped via jumps

### 3. Buffer Management Strategy

**expect -clear yes** (default):
```
Device Output: "Version: FortiGate-VM64-KVM v8.0.0..."
expect "Version:" → Match → Clear buffer from start to match.end()
Buffer after: "FortiGate-VM64-KVM v8.0.0..."
```

**expect -clear no**:
```
Device Output: "Version: FortiGate-VM64-KVM v8.0.0..."
expect "Version:" → Match → Buffer preserved
setvar "Version: (FortiGate-[\w-]+)" → Match from same buffer
setvar "v(\d+\.\d+\.\d+)" → Match from same buffer
```

### 4. Loop Implementation

**DSL while loop**:
```plaintext
<while {$counter} < 5>
    ...commands...
<endwhile {$counter} eq 5>
```

**VM Code loop**:
```plaintext
44 loop {$counter} < 5         # Entry: check condition
45 ...commands...
59 until 44 counter eq 5       # Exit: check condition OR jump to 44
```

**Execution**:
- Line 44: If condition FALSE → jump past line 59
- Lines 45-58: Loop body
- Line 59: If condition TRUE → exit; else jump to line 44

### 5. QAID Tracking vs NO_QAID

**With QAID**:
```plaintext
expect -e "pattern" -for {$QAID_CHECK} -t 5
→ Result recorded with QAID 205802
→ Appears in report
→ Uploaded to Oriole
```

**With NO_QAID**:
```plaintext
expect -e "pattern" -t 8
→ Schema default: NO_QAID
→ No result recorded
→ Used for intermediate checks
```

### 6. Schema-Driven Parameter Mapping

**DSL**:
```plaintext
expect -e "Version:" -for {$QAID} -t 5
```

**Schema** (cli_syntax.json):
```json
{
  "expect": {
    "parameters": [
      {"-e": {"alias": "rule", "position": 0}},
      {"-for": {"alias": "qaid", "position": 1}},
      {"-t": {"alias": "timeout", "position": 2, "default": 10}}
    ]
  }
}
```

**VM Code**:
```plaintext
expect Version: QAID 5 unmatch None None yes None 3
       │        │    │  └─────── (other defaults)
       │        │    └─────────── timeout (position 2)
       │        └──────────────── qaid (position 1)
       └───────────────────────── rule (position 0)
```

**Python API**:
```python
def expect(executor, params):
    # ApiParams provides named access
    pattern = params.rule        # "Version:"
    qaid = params.qaid           # "QAID" (variable name)
    timeout = params.timeout     # 5
```

### 7. Variable Interpolation in Output

**VM Code with Variables**:
```plaintext
88 comment Platform: {$platform_type}
89 comment Firmware: {$firmware_version}
90 comment Serial: {$device_serial}
```

**Variable State**:
```python
vars = {
    'platform_type': 'FortiGate-VM64-KVM',
    'firmware_version': '8.0.0',
    'device_serial': 'FGVMULTM25002684'
}
```

**Output After Interpolation**:
```
Platform: FortiGate-VM64-KVM
Firmware: 8.0.0
Serial: FGVMULTM25002684
```

---

## Summary

This walkthrough demonstrated the **complete journey** from DSL source code to test execution results:

✅ **Stage 1 (DSL)**: Human-readable test script with variables, loops, conditionals  
✅ **Stage 2 (Tokens)**: 1,344 tokens classified by type (section, keyword, api, command, etc.)  
✅ **Stage 3 (VM Codes)**: 168 executable instructions with control flow jumps  
✅ **Stage 4 (Execution)**: Device commands, pattern matching, variable extraction, conditional branching  
✅ **Stage 5 (Results)**: PASSED with 7 QAIDs tracked, device info collected

### Key Takeaways

1. **DSL Abstraction**: High-level syntax (`<while>`, `<if>`, `setvar`) compiled to low-level VM codes
2. **Control Flow**: Jump-based implementation enables efficient branching and looping
3. **Variable System**: Two-tier (environment + user) with compile-time and runtime interpolation
4. **Pattern Matching**: Regex-based extraction with buffer management strategies
5. **Result Tracking**: QAID-based validation with centralized management
6. **Device Communication**: SSH/Telnet sessions with output buffering and timeout handling

### Files Generated

| File | Purpose | Size |
|------|---------|------|
| `tokens.json` | Lexical analysis output | 1,344 tokens |
| `codes.vm` | Compiled VM instructions | 168 lines |
| `FGT_B_interaction.log` | Complete device I/O | 311 lines |
| `brief_summary.txt` | Test execution summary | Human-readable |
| `Oriole_report_all.json` | Results for upload | JSON format |

### Related Documentation

- [DSL Compilation Flow](DSL_COMPILATION_FLOW.md) - High-level compilation stages
- [Compiler Deep Dive](COMPILER_DEEP_DIVE.md) - Lexer/parser internals, control flow compilation, line number tracking
- [Executor Deep Dive](EXECUTOR_DEEP_DIVE.md) - VM code execution, program counter, and control flow internals
- [Variable Usage Guide](VARIABLE_USAGE_AND_TROUBLESHOOTING.md) - Variable syntax and troubleshooting
- [Include Directive](INCLUDE_DIRECTIVE.md) - Script modularization
- [AutoLib v3 Workflow](AUTOLIB_V3_WORKFLOW.md) - High-level architecture

---

**Document Version**: 1.0  
**Test Case**: first_case.txt  
**Execution**: 2026-02-17 17:10:44  
**Framework**: AutoLib v3 V3R10B0007
