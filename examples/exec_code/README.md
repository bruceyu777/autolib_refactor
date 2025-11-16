# exec_code Examples

This directory contains examples demonstrating how to use the `exec_code` API for executing Python and Bash code within your automation test scripts.

## What is exec_code?

`exec_code` is a powerful API that allows you to execute external code files (Python, Bash, JavaScript, Ruby) during test execution and store the results in variables. The code runs on your **control PC**, not on the device under test.

---

## ⚠️ CRITICAL: Python Sandboxing & Import Restrictions

**Python code runs in a SANDBOXED environment for security. The `import` statement is DISABLED.**

### ❌ DO NOT DO THIS (Will cause ImportError):

```python
import re          # ❌ ImportError: __import__ not found
import json        # ❌ ImportError: __import__ not found
import datetime    # ❌ ImportError: __import__ not found
import math        # ❌ ImportError: __import__ not found
import os          # ❌ ImportError: __import__ not found
```

### ✅ DO THIS INSTEAD (Modules are pre-loaded):

```python
# Modules are already available - use them directly!
pattern = re.search(r'test', text)          # ✅ Works!
data = json.loads(string)                   # ✅ Works!
now = datetime.datetime.now()               # ✅ Works!
result = math.sqrt(16)                      # ✅ Works!
```

### Available Pre-loaded Modules:

- ✅ `re` - Regular expressions
- ✅ `json` - JSON parsing
- ✅ `datetime` - Date and time operations
- ✅ `math` - Mathematical functions
- ❌ `os`, `sys`, `subprocess` - NOT available (security)
- ❌ Any other modules - NOT available

**For file operations:** Use Bash scripts (`exec_code -lang bash`) instead of Python, as the `os` module is not available.

---

## Context Access: Python vs Bash

**IMPORTANT:** Different languages have different levels of access to the execution context:

### Python: FULL Context Access ✓

Python scripts have **complete access** to all context keys via the `context` dictionary:

- ✅ `last_output` - Device command output
- ✅ `device` - Current device object
- ✅ `devices` - All device objects
- ✅ `variables` - Runtime variables
- ✅ `config` - Configuration
- ✅ `get_variable()` - Get variable function
- ✅ `set_variable()` - Set variable function
- ✅ `workspace` - Workspace path
- ✅ `logger` - Logger instance

### Bash: EXPANDED Context Access via Environment Variables ⚠️

Bash scripts have **environment variable access** to most context data:

- ✅ Runtime variables (as `$VAR_NAME` uppercase)
- ✅ Config values (as `$SECTION__OPTION` uppercase)
- ✅ **last_output** (as `$LAST_OUTPUT`)
- ✅ **workspace** (as `$WORKSPACE`)
- ✅ **Current device name** (as `$CURRENT_DEVICE_NAME`)
- ✅ **All device names** (as `$DEVICE_NAMES` comma-separated)
- ❌ device object - NOT available (cannot call methods)
- ❌ devices objects - NOT available (only names, not objects)
- ❌ logger object - NOT available
- ❌ get_variable/set_variable functions - NOT available

**Environment Variable Safety:** All environment variables are **subprocess-only** and do NOT affect:

- ❌ Parent Python process
- ❌ System-wide environment
- ❌ Other exec_code calls
- ❌ User's shell environment

**Use Python when you need:** Device objects, logger, setting variables, or calling functions. **Use Bash when you need:** Simple parsing, string manipulation, or calling external tools.

## Basic Syntax

```
exec_code -lang <language> -var <variable_name> -file <file_path> [-func <function>] [-args <arguments>] [-timeout <seconds>]
```

### Parameters

| Parameter  | Required | Description                                                  | Default |
| ---------- | -------- | ------------------------------------------------------------ | ------- |
| `-lang`    | Yes      | Programming language: `python`, `bash`, `javascript`, `ruby` | -       |
| `-var`     | Yes      | Variable name to store the result                            | -       |
| `-file`    | Yes      | Path to code file (relative to workspace)                    | -       |
| `-func`    | No       | Function name to call (Python only)                          | -       |
| `-args`    | No       | Comma-separated arguments for function                       | -       |
| `-timeout` | No       | Execution timeout in seconds                                 | 30      |

---

## Environment Variable Safety (Bash)

### Are Bash environment variables safe?

**YES! Absolutely safe.** When you execute Bash code via `exec_code`, environment variables are injected into a **subprocess only** and have **zero impact** on system-wide or parent process environments.

### How it works:

```python
# In BashExecutor (lib/core/executor/code_executor.py):
bash_env = os.environ.copy()  # Creates a COPY, not a reference
bash_env['LAST_OUTPUT'] = context['last_output']  # Modifies the COPY
subprocess.run(code, env=bash_env)  # Subprocess uses the COPY
# When subprocess exits, bash_env is discarded
```

### Scope of environment variables:

| Scope                          | Affected? | Explanation                                   |
| ------------------------------ | --------- | --------------------------------------------- |
| **Bash script being executed** | ✅ YES    | Variables are available via `$VAR_NAME`       |
| Parent Python process          | ❌ NO     | Original `os.environ` unchanged               |
| System-wide environment        | ❌ NO     | `/etc/environment`, system settings unchanged |
| User's shell                   | ❌ NO     | Your terminal environment unchanged           |
| Other exec_code calls          | ❌ NO     | Each call gets its own fresh copy             |
| Subsequent commands            | ❌ NO     | Expires when script finishes                  |

### Example demonstrating isolation:

```bash
# Test script:
<strset MY_VAR original_value>
exec_code -lang bash -var result1 -file "script1.sh"
exec_code -lang bash -var result2 -file "script2.sh"

# In script1.sh:
echo "MY_VAR in script1: $MY_VAR"  # Prints: original_value
export MY_VAR="modified_in_script1"
echo "Modified: $MY_VAR"  # Prints: modified_in_script1

# In script2.sh (runs AFTER script1):
echo "MY_VAR in script2: $MY_VAR"  # Prints: original_value (NOT modified_in_script1!)
```

**Result:** Each Bash script gets its own isolated environment. Changes in one script don't affect others.

### Why this matters:

- ✅ **Safe to experiment** - Can't accidentally break system
- ✅ **No cleanup needed** - Variables auto-expire with subprocess
- ✅ **Parallel execution safe** - Multiple exec_code calls won't interfere
- ✅ **Reproducible** - Same inputs always produce same results

---

## File Structure

```
examples/exec_code/
├── README.md                 # This file
├── example_parser.py        # Python examples
├── example_script.sh        # Bash examples
└── sample_test_script.txt   # Sample test script using exec_code
```

---

## Python Examples

The `example_parser.py` file contains 10 different examples showing various use cases.

> **⚠️ REMINDER:** Python code runs in a **sandboxed environment**. Do NOT use `import` statements - modules `re`, `json`, `datetime`, `math` are pre-loaded. See [CRITICAL section above](#️-critical-python-sandboxing--import-restrictions) for details.

### Example 1: Basic Execution

Execute entire script and return a value:

```python
# In example_parser.py
simple_calculation = 42 * 2
__result__ = simple_calculation
```

Usage in test script:

```
exec_code -lang python -var result -file "examples/exec_code/example_parser.py"
# $result now contains 84
```

**Key Point:** Use `__result__` to specify what value to return.

### Example 2: Call Specific Function

Execute a specific function from the file:

```python
def parse_output():
    """Parse device output from context."""
    output = context.get('last_output', '')
    # ... parse output ...
    return parsed_data
```

Usage in test script:

```
exec_code -lang python -var parsed_data -file "examples/exec_code/example_parser.py" -func "parse_output"
# $parsed_data now contains the function's return value
```

### Example 3: Function with Arguments

Call a function with arguments:

```python
def extract_ip(ip_string):
    """Extract and validate IP address."""
    # ... process ip_string ...
    return {'ip': ip, 'valid': True}
```

Usage in test script:

```
exec_code -lang python -var ip_info -file "examples/exec_code/example_parser.py" -func "extract_ip" -args "'192.168.1.1'"
# $ip_info now contains the dictionary
```

**Note:** Arguments are passed as a comma-separated string. For string arguments, use nested quotes.

### Example 4: Access Execution Context

Python code has access to a `context` dictionary with runtime information:

```python
def access_context_example():
    # Access last device output
    output = context.get('last_output', '')

    # Access all variables
    variables = context.get('variables', {})

    # Use logger
    logger = context.get('logger')
    logger.info("Processing data")

    # Get/set variables
    get_var = context.get('get_variable')
    set_var = context.get('set_variable')

    count = get_var('count')
    set_var('new_var', 'new_value')

    return result
```

**IMPORTANT: Sandboxed Environment**

Python code runs in a **sandboxed environment** for security:
- ✅ **Available modules** (pre-loaded, no import needed): `re`, `json`, `datetime`, `math`
- ✅ **Safe built-ins**: `abs`, `all`, `any`, `bool`, `dict`, `enumerate`, `filter`, `float`, `int`, `len`, `list`, `map`, `max`, `min`, `range`, `str`, `sum`, `tuple`, `zip`
- ❌ **NOT available**: `import`, `__import__`, `open`, `os`, `sys`, `subprocess`, and other potentially unsafe operations
- ❌ **Do NOT use import statements** - they will fail with `ImportError: __import__ not found`

**Use pre-loaded modules directly:**
```python
# CORRECT - modules are pre-loaded
result = re.search(r'pattern', text)
data = json.loads(string)
now = datetime.datetime.now()

# WRONG - will cause ImportError
import re  # Don't do this!
```

**For file operations:** Use Bash scripts via `exec_code -lang bash` instead of Python, as the `os` module is not available in Python for security reasons.

#### Available Context Keys:

| Key            | Type     | Description                                   |
| -------------- | -------- | --------------------------------------------- |
| `last_output`  | str      | Most recent device command output             |
| `device`       | object   | Current device connection object              |
| `devices`      | dict     | All device connections                        |
| `variables`    | dict     | Runtime variables dictionary                  |
| `config`       | object   | Parsed configuration (FosConfigParser)        |
| `get_variable` | function | Get variable value: `get_variable(name)`      |
| `set_variable` | function | Set variable value: `set_variable(name, val)` |
| `workspace`    | str      | Workspace directory path                      |
| `logger`       | object   | Logger instance                               |

### Example 5: Return Different Data Types

Python code can return various types:

```python
# Integer
def return_int():
    return 42

# String
def return_string():
    return "Hello World"

# List
def return_list():
    return [1, 2, 3, 4, 5]

# Dictionary
def return_dict():
    return {'key': 'value', 'count': 10}

# Boolean
def return_bool():
    return True
```

All types are properly stored in the variable.

### Example 6: Comprehensive Context Demonstrations

The `example_parser.py` file includes dedicated functions for each context key:

```python
# Demonstrate last_output
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_last_output"

# Demonstrate device object
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_device"

# Demonstrate all devices
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_devices"

# Demonstrate variables
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_variables"

# Demonstrate config
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_config"

# Demonstrate get/set variable functions
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_variable_functions"

# Demonstrate workspace
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_workspace"

# Demonstrate logger
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_logger"

# Demonstrate ALL context keys at once
exec_code -lang python -var result -file "examples/exec_code/example_parser.py" -func "demo_all_context_keys"
```

---

## Bash Examples

The `example_script.sh` file contains 17 different examples for Bash scripting with full context coverage.

**IMPORTANT:** Bash scripts access context via environment variables. Most context data is now available!

### Context Access in Bash

Bash scripts receive context through **subprocess-only environment variables** (safe, no system-wide changes).

#### 1. Runtime Variables

Variables set in your test script are available as uppercase environment variables:

```bash
# In test script:
# <strset device_name FGT-100E>
# <intset port 8443>
# <strset status success>

# In Bash script:
echo "Device: $DEVICE_NAME"      # Accesses device_name
echo "Port: $PORT"                # Accesses port
echo "Status: $STATUS"            # Accesses status
```

#### 2. Config Variables

Config values from your environment file are available as `SECTION__OPTION` (uppercase, double underscore):

```bash
# In config file:
# [device1]
# ip = 192.168.1.100
# port = 22
# username = admin

# In Bash script:
echo "IP: $DEVICE1__IP"           # Accesses [device1] ip
echo "Port: $DEVICE1__PORT"       # Accesses [device1] port
echo "User: $DEVICE1__USERNAME"   # Accesses [device1] username
```

#### 3. Last Device Output

Device command output is available as `$LAST_OUTPUT`:

```bash
# In test script:
# dev $device1
# cmd show system interface
# exec_code -lang bash -var result -file "script.sh"

# In Bash script:
if [ -n "$LAST_OUTPUT" ]; then
    # Extract IP addresses
    echo "$LAST_OUTPUT" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'

    # Count lines
    echo "$LAST_OUTPUT" | wc -l

    # Search for patterns
    if echo "$LAST_OUTPUT" | grep -q "port1"; then
        echo "Found port1 in output"
    fi
fi
```

#### 4. Workspace Path

Workspace directory path is available as `$WORKSPACE`:

```bash
# In Bash script:
if [ -n "$WORKSPACE" ]; then
    # Access files in workspace
    CONFIG_FILE="$WORKSPACE/config/test.conf"

    # List directories
    ls "$WORKSPACE/lib"

    # Create temp files safely
    TEMP_FILE="$WORKSPACE/temp_$$.txt"
    echo "data" > "$TEMP_FILE"
fi
```

#### 5. Current Device Name

Current active device name is available as `$CURRENT_DEVICE_NAME`:

```bash
# In Bash script:
if [ -n "$CURRENT_DEVICE_NAME" ]; then
    echo "Current device: $CURRENT_DEVICE_NAME"

    # Device-specific logic
    case "$CURRENT_DEVICE_NAME" in
        device1)
            echo "Primary device"
            ;;
        device2)
            echo "Secondary device"
            ;;
    esac
fi
```

#### 6. All Device Names

All configured device names as `$DEVICE_NAMES` (comma-separated):

```bash
# In Bash script:
if [ -n "$DEVICE_NAMES" ]; then
    # Convert to array
    IFS=',' read -ra DEVICES <<< "$DEVICE_NAMES"

    echo "Found ${#DEVICES[@]} device(s)"

    # Iterate
    for device in "${DEVICES[@]}"; do
        echo "Device: $device"

        # Access config for each device
        device_upper="${device^^}"
        ip_var="${device_upper}__IP"
        echo "IP: ${!ip_var}"
    done
fi
```

### Example 1: Simple Command

Execute bash commands and capture output:

```bash
#!/bin/bash
echo "Hello from Bash"
```

Usage in test script:

```
exec_code -lang bash -var greeting -file "examples/exec_code/example_script.sh"
# $greeting now contains "Hello from Bash"
```

### Example 2: Calculations

Perform arithmetic operations:

```bash
#!/bin/bash
NUM1=10
NUM2=20
RESULT=$((NUM1 + NUM2))
echo "$RESULT"
```

Usage:

```
exec_code -lang bash -var sum -file "examples/exec_code/example_script.sh"
# $sum now contains "30"
```

### Example 3: Access Framework Variables

Variables from your test script are available as environment variables:

```bash
#!/bin/bash
# If you set: <strset DEVICE_NAME FGT-100E>
# You can access it as: $DEVICE_NAME

if [ -n "$DEVICE_NAME" ]; then
    echo "Device: $DEVICE_NAME"
else
    echo "Device not set"
fi
```

### Example 4: String Processing

Process text with bash utilities:

```bash
#!/bin/bash
TEXT="Server IP is 192.168.1.1 and backup is 10.0.0.1"
IP=$(echo "$TEXT" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | head -1)
echo "Extracted IP: $IP"
```

### Example 5: Return Structured Data

Return JSON-like output as a string:

```bash
#!/bin/bash
echo '{"status": "success", "count": 42, "message": "Done"}'
```

Usage:

```
exec_code -lang bash -var result -file "examples/exec_code/example_script.sh"
# $result contains the JSON string
```

---

## Complete Test Script Example

Here's a complete example showing how to use `exec_code` in a test script:

```
# Test case: Parse device configuration and validate
# QAID: 801840

# Step 1: Get device configuration
dev $device1
cmd show system interface
expect -p "port1" -for 801840

# Step 2: Set a variable for use in Python code
<strset INTERFACE_NAME port1>

# Step 3: Execute Python code to parse the output
exec_code -lang python -var parsed_result -file "examples/exec_code/example_parser.py" -func "parse_output"

# Step 4: Use Bash to extract IP from result
exec_code -lang bash -var ip_addr -file "examples/exec_code/example_script.sh"

# Step 5: Check the parsed variable
check_var -name parsed_result -contains "port1" -for 801841

# Step 6: Use the result in further testing
dev $device1
cmd config system interface
cmd edit $INTERFACE_NAME
expect -p "edit port1" -for 801842
```

---

## Common Use Cases

### 1. Parse Complex Device Output

Use Python when the output requires complex parsing:

```python
def parse_routing_table():
    """Parse routing table from device output."""
    import re
    output = context.get('last_output', '')

    routes = []
    for line in output.split('\n'):
        match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)\s+via\s+(\d+\.\d+\.\d+\.\d+)', line)
        if match:
            routes.append({
                'network': match.group(1),
                'gateway': match.group(2)
            })

    return routes
```

### 2. Calculate Values

Use Python for complex calculations:

```python
def calculate_throughput(duration):
    """Calculate throughput from test results."""
    bytes_transferred = context.get_variable('bytes_transferred')
    duration_sec = int(duration)

    throughput_mbps = (int(bytes_transferred) * 8) / (duration_sec * 1000000)

    return round(throughput_mbps, 2)
```

Usage:

```
exec_code -lang python -var throughput -file "lib/calculator.py" -func "calculate_throughput" -args "60"
```

### 3. Data Transformation

Transform data between different formats:

```python
def json_to_variables():
    """Extract JSON data and set individual variables."""
    import json

    output = context.get('last_output', '')
    set_var = context.get('set_variable')

    data = json.loads(output)

    for key, value in data.items():
        set_var(key, value)

    return len(data)
```

### 4. External Tool Integration

Use Bash to call external tools:

```bash
#!/bin/bash
# Call external validation tool
./tools/validate_config.sh "$CONFIG_FILE" > /tmp/validation_result.txt
cat /tmp/validation_result.txt
```

### 5. Multi-Step Processing Pipeline

Chain multiple exec_code calls:

```
# Step 1: Get raw data
dev $device1
cmd diagnose debug rating
expect -p "Rating" -for 801850

# Step 2: Parse with Python
exec_code -lang python -var raw_data -file "lib/parser.py" -func "parse_rating"

# Step 3: Process with Bash
exec_code -lang bash -var formatted_data -file "scripts/format.sh"

# Step 4: Validate result
check_var -name formatted_data -pattern "^Rating:.*" -for 801851
```

---

## Best Practices

### 1. File Organization

- Keep code files in organized directories (e.g., `lib/`, `scripts/`, `examples/`)
- Use descriptive filenames that indicate purpose
- Group related functions in the same file

### 2. Error Handling

Always include error handling in your Python code:

```python
def safe_operation():
    try:
        # Your code here
        result = perform_operation()
        return {'success': True, 'data': result}
    except Exception as e:
        logger = context.get('logger')
        if logger:
            logger.error(f"Operation failed: {e}")
        return {'success': False, 'error': str(e)}
```

### 3. Logging

Use the logger from context for debugging:

```python
logger = context.get('logger')
if logger:
    logger.info("Starting processing")
    logger.debug(f"Input data: {data}")
    logger.error("An error occurred")
```

### 4. Return Values

- Python: Use `__result__` or function return value
- Bash: Use `echo` for output (captured as return value)
- Return simple types when possible (string, int, bool)
- For complex data, return dict or list from Python

### 5. Timeout Management

Set appropriate timeout based on operation:

```
# Short operation
exec_code -lang python -var result -file "lib/quick_parse.py" -timeout 5

# Long operation
exec_code -lang bash -var result -file "scripts/long_process.sh" -timeout 300
```

### 6. Variable Naming

Use clear, descriptive variable names:

```
# Good
exec_code -lang python -var parsed_interface_config -file "lib/parser.py"

# Bad
exec_code -lang python -var data -file "lib/parser.py"
```

---

## Troubleshooting

### ⚠️ Issue: "ImportError: __import__ not found" (MOST COMMON)

**Cause:** Using `import` statements in Python code. The sandboxed environment doesn't include `import` for security.

**This is THE MOST COMMON ERROR!** Python runs in a sandbox where `import` is disabled.

**Solution:** Do NOT use `import` statements. Use pre-loaded modules directly:

```python
# ❌ WRONG - causes ImportError
import re
import json
import datetime
from datetime import datetime

# ✅ CORRECT - modules are pre-loaded, use directly
pattern = re.search(r'test', string)
data = json.loads(text)
now = datetime.datetime.now()
result = math.sqrt(16)
```

**Available pre-loaded modules:** `re`, `json`, `datetime`, `math`

**See the [CRITICAL section at top](#️-critical-python-sandboxing--import-restrictions) for more details.**

---

### Issue: "File not found"

**Cause:** File path is incorrect or not relative to workspace.

**Solution:** Ensure the file path is relative to your workspace directory:

```
# Correct
exec_code -lang python -var result -file "examples/exec_code/example_parser.py"

# Incorrect
exec_code -lang python -var result -file "/home/user/example_parser.py"
```

### Issue: "Unsupported language"

**Cause:** Language parameter is incorrect.

**Solution:** Use one of the supported languages: `python`, `bash`, `javascript`, `ruby`

### Issue: "Timeout error"

**Cause:** Code execution took longer than timeout period.

**Solution:** Increase timeout or optimize your code:

```
exec_code -lang python -var result -file "lib/slow_operation.py" -timeout 60
```

### Issue: "Variable not set"

**Cause:** Code didn't return a value or `__result__` not set.

**Solution:** Ensure Python code sets `__result__` or function returns a value:

```python
# Make sure to set result
__result__ = my_value

# Or return from function
def my_func():
    return my_value
```

### Issue: "Context not accessible"

**Cause:** Trying to access `context` outside of function scope in Python.

**Solution:** Access context inside functions or at module level (not in class definitions):

```python
# Works
def my_func():
    output = context.get('last_output')

# Also works
output = context.get('last_output')
__result__ = len(output)
```

---

### Issue: "NameError: name 'os' is not defined"

**Cause:** Trying to use `os` module for file operations in Python.

**Solution:** The `os` module is NOT available in the sandbox for security. Use Bash scripts for file operations:

```bash
# Instead of Python with os module, use Bash:
exec_code -lang bash -var result -file "scripts/file_ops.sh"

# In file_ops.sh:
if [ -f "$WORKSPACE/config/test.conf" ]; then
    cat "$WORKSPACE/config/test.conf"
fi
```

---

## Context Reference

This section provides comprehensive documentation for all available context keys.

### Python Context Dictionary

In Python scripts, all context is available via the `context` dictionary. Access with `context.get('key_name')`.

**Sandboxing Note:** Python code runs in a sandboxed environment. Pre-loaded modules (`re`, `json`, `datetime`, `math`) are available without import. Do NOT use `import` statements - they will fail. For file operations, use Bash scripts instead.

#### 1. last_output (string)

Most recent device command output.

```python
output = context.get('last_output', '')
# Parse device output
lines = output.split('\n')
contains_error = 'error' in output.lower()
```

**Use cases:**

- Parsing device command output
- Extracting information from show commands
- Checking for error messages
- Processing diagnostic output

#### 2. device (object)

Current device connection object.

```python
device = context.get('device')
if device:
    # Access connection
    conn = device.conn

    # Get output buffer
    output = str(conn.output_buffer)
```

**Use cases:**

- Accessing device connection properties
- Reading output buffer directly
- Inspecting device state

**Note:** For sending commands, use test script syntax. Use `device` for read-only access.

#### 3. devices (dictionary)

All device connections as `{device_name: device_object}`.

```python
devices = context.get('devices', {})
for name, device in devices.items():
    print(f"Device: {name}")
```

**Use cases:**

- Iterating over all devices
- Getting information from multiple devices
- Checking which devices are configured

#### 4. variables (dictionary)

Runtime variables dictionary (defaultdict).

```python
variables = context.get('variables', {})
# Access all variables
for key, value in variables.items():
    print(f"{key} = {value}")
```

**Use cases:**

- Inspecting all runtime variables
- Counting variables
- Processing multiple variables at once

**Note:** Prefer using `get_variable()` and `set_variable()` functions for individual variable access.

#### 5. config (FosConfigParser)

Parsed configuration file (INI-style sections and options).

```python
config = context.get('config')
if config:
    # Get sections
    sections = config.sections()

    # Get value from section
    ip = config.get('device1', 'ip')
    port = config.get('device1', 'port')
```

**Use cases:**

- Reading device configuration
- Getting connection parameters
- Accessing environment-specific settings

#### 6. get_variable (function)

Function to get variable value by name.

```python
get_var = context.get('get_variable')
hostname = get_var('hostname')
port = get_var('port')
```

**Signature:** `get_variable(name: str) -> Any`

**Use cases:**

- Getting individual variable values
- Checking if a variable exists (returns None if not found)
- Retrieving variables set earlier in test

#### 7. set_variable (function)

Function to set variable value by name.

```python
set_var = context.get('set_variable')
set_var('parsed_ip', '192.168.1.1')
set_var('count', 42)
set_var('status', 'completed')
```

**Signature:** `set_variable(name: str, value: Any) -> None`

**Use cases:**

- Storing parsed results
- Setting variables for later use in test
- Sharing data between exec_code calls

#### 8. workspace (string)

Path to the workspace directory.

```python
workspace = context.get('workspace')

# Build file paths manually (os module not available)
file_path = f"{workspace}/data/config.json"
lib_path = f"{workspace}/lib"
examples_path = f"{workspace}/examples"

logger = context.get('logger')
if logger:
    logger.info(f"Workspace: {workspace}")
```

**Use cases:**

- Building file paths (construct manually with f-strings)
- Passing paths to Bash scripts for file operations
- Logging workspace location

**Note:** The `os` module is NOT available in the sandboxed Python environment for security. For actual file operations (reading, writing, listing), use Bash scripts via `exec_code -lang bash` with the `$WORKSPACE` environment variable.

#### 9. logger (object)

Logger instance with multiple log levels.

```python
logger = context.get('logger')
if logger:
    logger.debug("Detailed debug info")
    logger.info("General information")
    logger.warning("Warning message")
    logger.error("Error occurred")
```

**Available methods:**

- `logger.debug(msg)` - Detailed diagnostic information
- `logger.info(msg)` - General informational messages
- `logger.warning(msg)` - Warning messages
- `logger.error(msg)` - Error messages
- `logger.critical(msg)` - Critical errors

**Use cases:**

- Debugging code execution
- Logging parsed results
- Recording processing steps
- Reporting errors

### Bash Context (Environment Variables)

In Bash scripts, context is accessed via **subprocess-only environment variables** (safe - no system-wide changes).

#### Available Context Variables

| Variable          | Format                 | Description                        | Example                   |
| ----------------- | ---------------------- | ---------------------------------- | ------------------------- |
| Runtime variables | `$VAR_NAME`            | Uppercase variable names           | `$DEVICE_NAME`, `$PORT`   |
| Config variables  | `$SECTION__OPTION`     | Section + option (uppercase, `__`) | `$DEVICE1__IP`            |
| Last output       | `$LAST_OUTPUT`         | Device command output              | Parse with grep/sed/awk   |
| Workspace         | `$WORKSPACE`           | Workspace directory path           | `$WORKSPACE/lib/file.txt` |
| Current device    | `$CURRENT_DEVICE_NAME` | Active device name                 | `device1`, `device2`      |
| Device list       | `$DEVICE_NAMES`        | Comma-separated device names       | `device1,device2,device3` |

#### 1. Runtime Variables

Format: `$VAR_NAME` (automatically uppercase)

```bash
# Test script: <strset device_name FGT-100E>
# Bash script:
DEVICE="${DEVICE_NAME:-default}"
PORT="${PORT:-443}"
STATUS="${STATUS:-unknown}"
```

#### 2. Config Variables

Format: `$SECTION__OPTION` (uppercase, double underscore separator)

```bash
# Config: [device1] ip=192.168.1.1
# Bash script:
IP="$DEVICE1__IP"

# Config: [server] host=example.com
# Bash script:
HOST="$SERVER__HOST"
```

**Pattern:** `$<SECTION>__<OPTION>` (both uppercase)

#### 3. Last Device Output

Format: `$LAST_OUTPUT` (multi-line string)

```bash
# Parse device output
if [ -n "$LAST_OUTPUT" ]; then
    # Extract IPs
    echo "$LAST_OUTPUT" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'

    # Count lines
    LINE_COUNT=$(echo "$LAST_OUTPUT" | wc -l)

    # Search patterns
    if echo "$LAST_OUTPUT" | grep -q "error"; then
        echo "Error found in output"
    fi
fi
```

#### 4. Workspace Path

Format: `$WORKSPACE` (absolute path)

```bash
if [ -n "$WORKSPACE" ]; then
    # Access files
    cat "$WORKSPACE/config/test.conf"

    # Create temp files
    echo "data" > "$WORKSPACE/temp_$$.txt"

    # Check directories
    [ -d "$WORKSPACE/lib" ] && echo "lib exists"
fi
```

#### 5. Current Device Name

Format: `$CURRENT_DEVICE_NAME` (string)

```bash
if [ -n "$CURRENT_DEVICE_NAME" ]; then
    echo "Active device: $CURRENT_DEVICE_NAME"

    case "$CURRENT_DEVICE_NAME" in
        device1) echo "Primary" ;;
        device2) echo "Secondary" ;;
    esac
fi
```

#### 6. All Device Names

Format: `$DEVICE_NAMES` (comma-separated)

```bash
if [ -n "$DEVICE_NAMES" ]; then
    # Convert to array
    IFS=',' read -ra DEVICES <<< "$DEVICE_NAMES"

    # Iterate
    for device in "${DEVICES[@]}"; do
        echo "Device: $device"

        # Access config for each
        dev_upper="${device^^}"
        echo "IP: ${!dev_upper}__IP"
    done
fi
```

#### What's NOT Available in Bash

The following context items are **not accessible** in Bash scripts:

- ❌ `device` object - Cannot call device methods (send(), expect())
- ❌ `devices` objects - Only names available, not device objects
- ❌ `logger` object - Cannot call logger.info(), logger.debug()
- ❌ `get_variable()` function - Variables already in environment
- ❌ `set_variable()` function - Cannot set variables back to context

**When to use Bash vs Python:**

- **Use Bash for:** Parsing output with grep/sed/awk, string manipulation, calling external tools, file operations
- **Use Python for:** Device method calls, complex parsing, setting variables, logging, object-oriented operations

**Environment Safety:** All Bash environment variables are subprocess-only. They do NOT affect parent process, system environment, or other exec_code calls.

---

## Advanced Topics

### Custom Context Usage

Store intermediate results back to variables:

```python
def multi_step_processing():
    """Process data in multiple steps and store intermediate results."""
    set_var = context.get('set_variable')

    # Step 1
    step1_result = process_step_1()
    set_var('step1_result', step1_result)

    # Step 2
    step2_result = process_step_2(step1_result)
    set_var('step2_result', step2_result)

    # Step 3
    final_result = process_step_3(step2_result)

    return final_result
```

### Device Interaction

Access device objects from context:

```python
def send_device_command():
    """Send command directly to device."""
    device = context.get('device')

    if device:
        # Send command
        device.send('show version')

        # Get output
        output = device.conn.output_buffer

        return str(output)

    return None
```

### Working with Configuration

Access parsed configuration:

```python
def get_config_value():
    """Get value from parsed configuration."""
    config = context.get('config')

    # Access config sections
    device_ip = config.get('device1', 'ip')
    device_port = config.get('device1', 'port')

    return {'ip': device_ip, 'port': device_port}
```

---

## Python vs Bash Context Comparison

Complete comparison of context access between Python and Bash:

| Context Item              | Python                          | Bash                      | Notes                                    |
| ------------------------- | ------------------------------- | ------------------------- | ---------------------------------------- |
| **Runtime variables**     | ✅ `context['variables']`       | ✅ `$VAR_NAME`            | Both have full access                    |
| **Config**                | ✅ `context['config']`          | ✅ `$SECTION__OPTION`     | Both have full access                    |
| **Last output**           | ✅ `context['last_output']`     | ✅ `$LAST_OUTPUT`         | Both have full access                    |
| **Workspace path**        | ✅ `context['workspace']`       | ✅ `$WORKSPACE`           | Both have full access                    |
| **Current device name**   | ✅ `device.name`                | ✅ `$CURRENT_DEVICE_NAME` | Both have access to name                 |
| **All device names**      | ✅ `context['devices'].keys()`  | ✅ `$DEVICE_NAMES`        | Both have access to names                |
| **Device object**         | ✅ `context['device']`          | ❌                        | Python only - object with methods        |
| **Devices objects**       | ✅ `context['devices']`         | ❌                        | Python only - dict of objects            |
| **Logger**                | ✅ `context['logger']`          | ❌                        | Python only - logging methods            |
| **Get variable function** | ✅ `get_variable(name)`         | ❌                        | Python only - already in env for Bash    |
| **Set variable function** | ✅ `set_variable(name, val)`    | ❌                        | Python only - Bash cannot set            |
| **Call device methods**   | ✅ `device.send()`, `.expect()` | ❌                        | Python only - OOP features               |
| **Access device buffer**  | ✅ `device.conn.output_buffer`  | ❌                        | Python only - use `$LAST_OUTPUT` in Bash |

### Summary:

**Python: Complete Access**

- All 9 context keys available
- Full object-oriented features
- Can call device methods
- Can set variables
- Can use logger

**Bash: Data Access via Environment Variables**

- 6 context items as environment variables
- String/text manipulation only
- Cannot call object methods
- Cannot set variables back to context
- Cannot use logger

**Both Languages:**

- ✅ Can access runtime variables
- ✅ Can access config
- ✅ Can access last device output
- ✅ Can access workspace path
- ✅ Can access device names
- ✅ **Safe:** Environment variables are subprocess-only (Bash)

### Recommendation:

| Task                       | Recommended Language                              | Why                                                     |
| -------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| Parse device output        | Either (Bash for simple grep, Python for complex) | Bash: fast text processing; Python: regex, JSON parsing |
| Extract data from output   | Bash                                              | Quick grep/sed/awk operations                           |
| Send device commands       | Python                                            | Only Python has device object methods                   |
| Set variables              | Python                                            | Bash cannot set variables back to context               |
| Logging                    | Python                                            | Only Python has logger object                           |
| Call external tools        | Bash                                              | Native shell integration                                |
| Complex logic/calculations | Python                                            | Full programming language                               |
| String manipulation        | Bash                                              | Built-in text processing tools                          |

---

## See Also

- Main project README: `../../README.md`
- API documentation: `../../lib/core/executor/api/code_execution.py`
- Test examples: `../../lib/tests/test_code_execution.py`

---

## Questions or Issues?

If you encounter any problems or have questions about using `exec_code`, please refer to:

1. This README
2. The example files in this directory
3. The test suite in `lib/tests/test_code_execution.py`
4. The API implementation in `lib/core/executor/api/code_execution.py`
