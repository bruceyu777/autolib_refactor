# AutoLib v3 DSL Usage Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Syntax Structure](#basic-syntax-structure)
3. [Script Organization](#script-organization)
4. [Device Sections](#device-sections)
5. [Command Types](#command-types)
6. [API Categories](#api-categories)
7. [Variables](#variables)
8. [Control Structures](#control-structures)
9. [Pattern Matching and Expectations](#pattern-matching-and-expectations)
10. [Network Operations](#network-operations)
11. [Code Execution](#code-execution)
12. [Advanced Patterns](#advanced-patterns)
13. [Best Practices](#best-practices)
14. [Complete Examples](#complete-examples)

---

## Introduction

The AutoLib v3 DSL (Domain-Specific Language) is a powerful scripting language designed for automated testing of FortiGate and other Fortinet devices. It provides:

- **Device-centric scripting**: Execute commands on multiple devices in parallel
- **Pattern matching**: Validate device output with regex patterns
- **Control structures**: Conditional logic and loops for dynamic test flows
- **Variable management**: Store and manipulate test data
- **Result reporting**: Track test case pass/fail status with QA IDs
- **Code execution**: Run Python, Bash scripts for complex operations

### Schema Version

Current schema version: **2.0**

---

## Basic Syntax Structure

### Script Types

Every line in a DSL script is classified as one of the following types:

1. **API Call** - Built-in test automation APIs (e.g., `expect`, `setvar`)
2. **Section Header** - Device context (e.g., `[FGT_A]`, `[PC1]`)
3. **Command** - Device CLI commands (e.g., `get system status`)
4. **Keyword** - Control structures (e.g., `<if>`, `<while>`)
5. **Include** - Include other scripts (e.g., `include script.txt`)
6. **Comment** - Documentation (lines starting with `#` or `comment:`)

### Line Format

```plaintext
# Comment lines start with #
comment: Alternative comment format

[DEVICE_NAME]              # Device section header
    command                # Device command (indented)
    api_name -param value  # API call with options
    <keyword expression>   # Control structure keyword
```

---

## Script Organization

### Test Case Structure

```plaintext
# Test: Basic Configuration Check
# QAID: TC_001
# Description: Verify system status and configuration

[FGT_A]
    # Step 1: Check system status
    get system status
    expect -e "Version: FortiGate" -for TC_001_001 -t 5
    
    # Step 2: Extract serial number
    setvar -e "Serial-Number: (.*)" -to serial_num
    
    # Step 3: Report results
    report TC_001
```

### Multi-Device Scripts

```plaintext
# Configure HA between two FortiGates

[FGT_PRIMARY]
    config system ha
        set mode a-p
        set group-name "cluster1"
        set password "hapassword"
        set priority 200
    end

[FGT_SECONDARY]
    config system ha
        set mode a-p
        set group-name "cluster1"
        set password "hapassword"
        set priority 100
    end

[FGT_PRIMARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001 -t 30
```

---

## Device Sections

### Section Header Syntax

```plaintext
[DEVICE_NAME]
    commands and APIs executed on this device...
```

### Supported Device Types

Based on environment configuration:
- **FGT, FGT_A, FGT_B** - FortiGate devices
- **FSW, FSW1, FSW2** - FortiSwitch devices
- **FAP, FAP1, FAP2** - FortiAP devices
- **PC, PC1, PC2** - PC/Computer devices
- **FAZ** - FortiAnalyzer
- **FMG** - FortiManager
- **KVM** - KVM hypervisor

### Example: Device Context Switching

```plaintext
[FGT_A]
    get system status
    setvar -e "Version: .*v(\\d+\\.\\d+\\.\\d+)" -to fgt_version

[PC1]
    ping -c 4 192.168.1.99
    expect -e "4 received" -for TC_PING_001

[FGT_A]
    # Commands return to FGT_A context
    diag debug enable
```

---

## Command Types

### Valid FortiOS Commands

The DSL recognizes these FortiOS command prefixes:

```plaintext
set, edit, config, diag, exe, execute, del, next, end, unset,
show, append, select, unselect, purge, get, conf, clear, sh,
clone, dia, fnsysctl, con, y, rename, move, admin, sudo
```

### Command Execution

```plaintext
[FGT_A]
    # Configuration commands
    config system global
        set hostname FGT-PRIMARY
        set timezone 04
    end
    
    # Diagnostic commands
    diag debug enable
    diag debug application httpsd 255
    
    # Execute commands
    execute ping 8.8.8.8
    execute factoryreset keepvmlicense
    
    # Show/Get commands
    get system status
    show system interface
```

### Special Commands

```plaintext
[FGT_A]
    # Send Ctrl+C
    ctrl_c
    
    # Send without expecting prompt
    nan_enter
    
    # Force device login
    forcelogin
    
    # Reset firewall to factory defaults
    resetFirewall
```

---

## API Categories

### 1. Expectation APIs (`expect` category)

#### `expect` - Basic Pattern Matching

**Description**: Wait for a pattern to appear in device output and report pass/fail.

**Parameters**:
- `-e <pattern>` (required): Regular expression pattern to match
- `-for <qaid>` (required): Test case ID for reporting
- `-t <seconds>` (default: 5): Timeout in seconds
- `-fail <match|unmatch>` (default: unmatch): Fail condition
  - `unmatch`: Pass if pattern found, fail if not found
  - `match`: Pass if pattern NOT found, fail if found
- `-clear <yes|no>` (default: yes): Clear buffer before expecting
- `-retry_command <cmd>`: Command to retry if expect fails
- `-retry_cnt <count>` (default: 3): Maximum retry attempts

**Examples**:

```plaintext
[FGT_A]
    get system status
    # Expect pattern to be found (pass if found)
    expect -e "Version: FortiGate" -for TC_001 -t 5
    
    # Expect pattern NOT to be found (pass if NOT found)
    expect -e "ERROR" -for TC_002 -fail match
    
    # With retry logic
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001 -t 10 -retry_command "diag sys ha reset-uptime" -retry_cnt 5
```

**Use Cases**:
- ✅ Verify command output contains expected text
- ✅ Ensure error messages are NOT present
- ✅ Wait for status changes with retry logic
- ✅ Validate configuration changes

---

#### `expect_ctrl_c` - Ctrl+C + Expect

**Description**: Send Ctrl+C signal and then expect a pattern.

**Parameters**: Same as `expect`

**Example**:

```plaintext
[FGT_A]
    # Interrupt running process and verify prompt
    expect_ctrl_c -e "FGT-A #" -for TC_INTERRUPT_001 -t 5
```

---

#### `expect_OR` - Logical OR Pattern Matching

**Description**: Expect one of two patterns (logical OR operation).

**Parameters**:
- `-e1 <pattern>` (required): First pattern
- `-e2 <pattern>` (required): Second pattern
- `-fail1 <match|unmatch>` (default: unmatch): Fail condition for pattern 1
- `-fail2 <match|unmatch>` (default: unmatch): Fail condition for pattern 2
- `-for <qaid>` (required): Test case ID
- `-t <seconds>` (default: 5): Timeout

**Example**:

```plaintext
[FGT_A]
    execute ping 8.8.8.8
    # Pass if either "5 packets received" OR "100% packet loss" found
    expect_OR -e1 "5 packets received" -e2 "100% packet loss" -for TC_PING_002 -t 15
```

---

#### `varexpect` - Expect Variable Value

**Description**: Expect the value of a variable in device output.

**Parameters**:
- `-v <varname>` (required): Variable whose value to expect
- `-for <qaid>` (required): Test case ID
- `-t <seconds>` (default: 5): Timeout
- `-fail <match|unmatch>` (default: unmatch): Fail condition

**Example**:

```plaintext
[FGT_A]
    get system status
    setvar -e "Hostname: (.*)" -to expected_hostname
    
    show system global | grep hostname
    varexpect -v expected_hostname -for TC_HOSTNAME_001 -t 5
```

---

### 2. Variable APIs (`variable` category)

#### `setvar` - Extract and Store Variable

**Description**: Extract value from device output using regex and store in variable.

**Parameters**:
- `-e <pattern>` (required): Regex with capture group `(.*)`
- `-to <varname>` (required): Variable name to store captured value

**Examples**:

```plaintext
[FGT_A]
    get system status
    
    # Extract single value
    setvar -e "Serial-Number: (.*)" -to serial_number
    
    # Extract from complex pattern
    setvar -e "Version: FortiGate.*v(\\d+\\.\\d+\\.\\d+)" -to fgt_version
    
    # Extract IP address
    setvar -e "IP Address: (\\d+\\.\\d+\\.\\d+\\.\\d+)" -to mgmt_ip
    
    # Use extracted variable
    comment: Serial number is $serial_number
```

---

#### `setenv` - Set Device-Specific Environment Variable

**Description**: Set environment variable for a specific device.

**Parameters**:
- `-n <varname>` (required): Variable name
- `-v <value>` (required): Variable value
- `-d <device>` (required): Device name

**Example**:

```plaintext
[FGT_A]
    get system status
    setvar -e "Hostname: (.*)" -to hostname
    
    # Set environment variable for FGT_B
    setenv -n peer_hostname -v $hostname -d FGT_B

[FGT_B]
    # Access variable set from FGT_A
    comment: Peer hostname is $peer_hostname
```

---

#### `compare` - Compare Two Variables

**Description**: Compare two variables and report result.

**Parameters**:
- `-v1 <varname>` (required): First variable
- `-v2 <varname>` (required): Second variable
- `-for <qaid>` (required): Test case ID
- `-fail <eq|uneq>` (default: uneq): Fail condition
  - `uneq`: Pass if variables are equal, fail if unequal
  - `eq`: Pass if variables are NOT equal, fail if equal

**Example**:

```plaintext
[FGT_A]
    get system ha status
    setvar -e "Primary.*Serial Num: (.*)" -to primary_sn

[FGT_B]
    get system status
    setvar -e "Serial-Number: (.*)" -to device_sn

[FGT_A]
    # Verify FGT_B is the primary in HA cluster
    compare -v1 primary_sn -v2 device_sn -for TC_HA_PRIMARY_001 -fail uneq
```

---

#### `check_var` - Check Variable Value

**Description**: Check if variable matches expected value/pattern and report result.

**Parameters**:
- `-name <varname>` (required): Variable name to check
- `-value <exact_value>`: Exact value match (mutually exclusive with -pattern and -contains)
- `-pattern <regex>`: Regex pattern match (mutually exclusive with -value and -contains)
- `-contains <substring>`: Substring match (mutually exclusive with -value and -pattern)
- `-for <qaid>` (required): Test case ID
- `-fail <match|unmatch>` (default: unmatch): Fail condition

**Examples**:

```plaintext
[FGT_A]
    get system status
    setvar -e "Version: .*build(\\d+)" -to build_number
    
    # Check exact value
    check_var -name build_number -value 3645 -for TC_BUILD_001
    
    # Check pattern
    check_var -name build_number -pattern "^36\\d+$" -for TC_BUILD_002
    
    # Check contains substring
    check_var -name build_number -contains "364" -for TC_BUILD_003
```

---

### 3. Control Variables

#### `strset` - Set String Variable

**Syntax**: `<strset varname value>`

**Example**:

```plaintext
<strset platform_type FortiGate-100E>
<strset status_message "Configuration Complete">
<strset ip_address 192.168.1.1>

comment: Platform is $platform_type
```

---

#### `intset` - Set Integer Variable

**Syntax**: `<intset varname number>`

**Example**:

```plaintext
<intset retry_count 5>
<intset max_timeout 300>
<intset port_number 8080>

comment: Retry count is $retry_count
```

---

#### `listset` - Set List Variable

**Syntax**: `<listset varname comma_separated_values>`

**Example**:

```plaintext
<listset port_list 80,443,8080>
<listset device_list FGT1,FGT2,FGT3>
<listset ip_list 192.168.1.1,192.168.1.2,192.168.1.3>

comment: Testing ports $port_list
```

---

### 4. Network APIs (`network` category)

#### `myftp` - FTP with Pattern Matching

**Description**: Execute FTP commands and validate output.

**Parameters**:
- `-e <pattern>` (required): Pattern to match
- `-ip <address>` (required): FTP server IP
- `-u <username>` (required): FTP username
- `-p <password>` (required): FTP password
- `-c <command>`: FTP command to execute
- `-for <qaid>`: Test case ID
- `-t <seconds>` (default: 5): Timeout
- `-fail <match|unmatch>` (default: unmatch): Fail condition
- `-a <stop|continue|nextgroup>` (default: continue): Action on failure

**Example**:

```plaintext
[PC1]
    myftp -e "226 Transfer complete" -ip 192.168.1.100 -u ftpuser -p ftppass -c "get testfile.bin" -for TC_FTP_001 -t 60
```

---

#### `mytelnet` - Telnet with Pattern Matching

**Description**: Execute Telnet commands and validate output.

**Parameters**:
- `-e <pattern>` (required): Pattern to match
- `-ip <address>` (required): Telnet server IP
- `-u <username>` (required): Username
- `-p <password>` (required): Password
- `-for <qaid>` (required): Test case ID
- `-t <seconds>` (default: 5): Timeout
- `-fail <match|unmatch>` (default: unmatch): Fail condition

**Example**:

```plaintext
[PC1]
    mytelnet -e "Login successful" -ip 192.168.1.1 -u admin -p password -for TC_TELNET_001 -t 10
```

---

### 5. Report APIs (`report` category)

#### `report` - Mark Test Case for Reporting

**Description**: Mark a test case ID for result reporting.

**Syntax**: `report <qaid>`

**Example**:

```plaintext
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_STATUS_001
    expect -e "Serial-Number: FGV" -for TC_STATUS_002
    
    # Mark entire test case as complete
    report TC_STATUS_FULL
```

---

#### `collect_dev_info` - Collect Device Information

**Description**: Collect device information for test case documentation.

**Parameters**:
- `-for <qaid>` (required): Test case ID

**Example**:

```plaintext
[FGT_A]
    get system status
    collect_dev_info -for TC_001
```

---

#### `setlicense` - Set License Variable

**Description**: Set license information variable.

**Parameters**:
- `-t <lic_type>` (required): License type (e.g., "04V")
- `-for <sub_type>` (required): License sub-type (e.g., "VDOM")
- `-to <varname>` (required): Variable to store license info

**Example**:

```plaintext
[FGT_A]
    setlicense -t 04V -for VDOM -to vdom_license
    comment: License info: $vdom_license
```

---

### 6. Utility APIs (`utility` category)

#### `sleep` - Pause Execution

**Description**: Sleep for specified number of seconds.

**Syntax**: `sleep <seconds>`

**Example**:

```plaintext
[FGT_A]
    execute reboot
    sleep 120
    forcelogin
    get system status
```

---

#### `comment` - Add Comment

**Description**: Add comment to logs and test summary.

**Syntax**: `comment <text>` or `comment: <text>`

**Example**:

```plaintext
[FGT_A]
    comment: Starting HA configuration test
    comment Variables: primary=$primary_ip, secondary=$secondary_ip
```

---

#### `breakpoint` - Enter Debugger

**Description**: Pause execution and enter interactive debugger.

**Syntax**: `breakpoint`

**Example**:

```plaintext
[FGT_A]
    get system status
    breakpoint
    # Execution pauses here for debugging
    get system interface
```

---

#### `enter_dev_debugmode` - Python Debugger

**Description**: Enter Python pdb debugger for advanced debugging.

**Syntax**: `enter_dev_debugmode`

---

### 7. Device Control APIs (`device` category)

#### `forcelogin` - Force Device Login

**Description**: Force re-login to current device.

**Syntax**: `forcelogin`

**Example**:

```plaintext
[FGT_A]
    execute reboot
    sleep 120
    forcelogin
    get system status
```

---

#### `auto_login` - Enable/Disable Auto-Login

**Description**: Control automatic login behavior.

**Syntax**: `auto_login <0|1>`

**Example**:

```plaintext
[FGT_A]
    auto_login 0  # Disable auto-login
    # Manual login steps...
    auto_login 1  # Re-enable auto-login
```

---

#### `keep_running` - Keep Device Connection

**Description**: Keep device connection alive.

**Syntax**: `keep_running <0|1>`

**Example**:

```plaintext
[FGT_A]
    keep_running 1
    # Long-running operations...
```

---

#### `confirm_with_newline` - Confirmation Mode

**Description**: Control confirmation with newline.

**Syntax**: `confirm_with_newline <0|1>`

---

#### `wait_for_confirm` - Wait for Confirmation

**Description**: Wait for confirmation prompts.

**Syntax**: `wait_for_confirm <0|1>`

**Example**:

```plaintext
[FGT_A]
    wait_for_confirm 1
    execute factoryreset keepvmlicense
    # Will wait for "Do you want to continue? (y/n)"
```

---

#### `restore_image` - Restore Device Image

**Description**: Restore device to specific FortiOS version and build.

**Parameters**:
- `-v <release>` (required): Release version (e.g., "7")
- `-b <build>` (required): Build number (e.g., "3645")

**Example**:

```plaintext
[FGT_A]
    restore_image -v 7 -b 3645
    sleep 300
    forcelogin
```

---

#### `resetFirewall` - Factory Reset

**Description**: Reset firewall to factory defaults.

**Syntax**: `resetFirewall`

**Example**:

```plaintext
[FGT_A]
    resetFirewall
    sleep 60
    forcelogin
```

---

#### `resetFAP` - Reset FortiAP

**Description**: Reset FortiAP device.

**Syntax**: `resetFAP`

---

### 8. Buffer Control (`buffer` category)

#### `clear_buffer` - Clear Device Buffer

**Description**: Clear device output buffer.

**Syntax**: `clear_buffer`

**Example**:

```plaintext
[FGT_A]
    get system status
    clear_buffer
    # Fresh output from next command
    get system interface
```

---

### 9. Command Execution APIs (`command` category)

#### `send_literal` - Send Raw String

**Description**: Send literal string with escape sequences to device.

**Syntax**: `send_literal "<string_with_escapes>"`

**Supported Escape Sequences**:
- `\n` - Newline
- `\r` - Carriage return
- `\t` - Tab
- `\\` - Backslash
- `\"` - Double quote

**Example**:

```plaintext
[FGT_A]
    send_literal "config system global\n"
    send_literal "set hostname FGT-TEST\n"
    send_literal "end\n"
```

---

### 10. Script Management (`script` category)

#### `include` - Include External Script

**Description**: Include and execute another script file.

**Syntax**: `include <script_path>`

**Example**:

```plaintext
# main_test.txt
include common/login_setup.txt
include tests/ha_configuration.txt
include common/cleanup.txt
```

**File Structure**:
```
testcase/
├── main_test.txt
├── common/
│   ├── login_setup.txt
│   └── cleanup.txt
└── tests/
    └── ha_configuration.txt
```

---

### 11. Code Execution (`code_execution` category)

#### `exec_code` - Execute External Code

**Description**: Execute Python or Bash code and store result in variable.

**Parameters**:
- `-lang <python|bash>` (required): Programming language
- `-var <varname>` (required): Variable to store result
- `-file <path>` (required): Path to code file
- `-func <function_name>`: Function to call (Python only)
- `-args <arg1,arg2,...>`: Comma-separated arguments
- `-timeout <seconds>` (default: 30): Execution timeout

**Example**:

```plaintext
[FGT_A]
    get system status
    setvar -e "CPU: (\\d+)%" -to cpu_usage
    
    # Execute Python script to analyze CPU
    exec_code -lang python -var analysis_result -file examples/exec_code/example_parser.py -func analyze_cpu -args $cpu_usage -timeout 10
    
    comment: Analysis result: $analysis_result
```

**Python Function Example** (`examples/exec_code/example_parser.py`):

```python
def analyze_cpu(cpu_usage_str):
    """Analyze CPU usage and return status."""
    cpu = int(cpu_usage_str)
    if cpu < 50:
        return "NORMAL"
    elif cpu < 80:
        return "WARNING"
    else:
        return "CRITICAL"
```

**Bash Script Example** (`examples/exec_code/example_script.sh`):

```bash
#!/bin/bash
# Calculate network throughput
echo "Calculating throughput..."
result=$(echo "scale=2; $1 / $2" | bc)
echo "$result Mbps"
```

**Usage**:

```plaintext
exec_code -lang bash -var throughput -file examples/exec_code/example_script.sh -args 1000,8 -timeout 5
```

---

## Control Structures

### Conditional: `if / elseif / else / fi`

**Syntax**:

```plaintext
<if condition>
    script...
<fi>

<if condition>
    script...
<elseif condition>
    script...
<else>
    script...
<fi>
```

**Comparison Operators**:
- `eq` - Equal to
- `ne` - Not equal to
- `lt` - Less than
- `>` - Greater than
- `<` - Less than

**Examples**:

```plaintext
# Simple if
<if $count eq 5>
    comment: Count is exactly 5
<fi>

# If-else
<if $status eq success>
    comment: Test passed
<else>
    comment: Test failed
<fi>

# If-elseif-else
<if $cpu_usage < 50>
    comment: CPU is normal
<elseif $cpu_usage < 80>
    comment: CPU is elevated
<else>
    comment: CPU is critical
<fi>

# Variable comparison
[FGT_A]
    get system status
    setvar -e "Version: .*build(\\d+)" -to build

<if $build > 3600>
    [FGT_A]
        comment: Running latest build
<else>
    [FGT_A]
        comment: Upgrade required
<fi>
```

---

### Loops: `loop / until`

**Syntax**:

```plaintext
<loop condition>
    script...
<until condition>
```

**Example**:

```plaintext
<intset retry_count 0>

<loop $retry_count < 5>
    [FGT_A]
        get system ha status
        setvar -e "HA Health Status: (\\w+)" -to ha_status
    
    <if $ha_status eq OK>
        comment: HA is healthy
        <intset retry_count 10>  # Exit loop
    <else>
        comment: Waiting for HA to sync... attempt $retry_count
        sleep 10
        <intchange retry_count + 1>
    <fi>
<until $retry_count > 4>
```

---

### While Loops: `while / endwhile`

**Syntax**:

```plaintext
<while condition>
    script...
<endwhile condition>
```

**Example**:

```plaintext
<intset counter 1>
<intset max_vaps 5>

[FGT_A]
    config wireless-controller vap
        <while $counter < 6>
            edit "wifi_vap_$counter"
                set ssid "WiFi-$counter"
                set security wpa2-only-personal
                set passphrase "password123"
            next
            <intchange counter + 1>
        <endwhile $counter > $max_vaps>
    end
```

---

### `intchange` - Arithmetic Operations

**Syntax**: `<intchange $variable operator value>`

**Operators**:
- `+` - Addition
- `-` - Subtraction
- `*` - Multiplication
- `/` - Division

**Examples**:

```plaintext
<intset counter 0>
<intchange counter + 1>      # counter = 1
<intchange counter + 5>      # counter = 6
<intchange counter * 2>      # counter = 12
<intchange counter - 3>      # counter = 9
<intchange counter / 3>      # counter = 3
```

---

## Advanced Patterns

### Pattern 1: Loop with Dynamic Configuration

**Use Case**: Configure multiple VLANs dynamically.

```plaintext
<intset vlan_id 10>
<intset max_vlan 15>

[FGT_A]
    config system interface
        <while $vlan_id < 16>
            edit "vlan$vlan_id"
                set vdom "root"
                set type vlan
                set vlanid $vlan_id
                set interface "port1"
                set ip 192.168.$vlan_id.1 255.255.255.0
            next
            <intchange vlan_id + 1>
        <endwhile $vlan_id > $max_vlan>
    end
    
    # Verify all VLANs created
    show system interface | grep vlan
    expect -e "vlan15" -for TC_VLAN_CREATE_001 -t 5
```

---

### Pattern 2: Conditional Platform Configuration

**Use Case**: Different configuration based on device platform.

```plaintext
[FGT_A]
    get system status
    setvar -e "Version: (.*?) v" -to platform

<if $platform eq FortiGate-100E>
    [FGT_A]
        comment: Configuring FortiGate-100E
        config system interface
            edit "lan"
                set role undefined
            next
        end
<elseif $platform eq FortiGate-200F>
    [FGT_A]
        comment: Configuring FortiGate-200F
        config system interface
            edit "fortilink"
                unset member
            next
        end
<else>
    [FGT_A]
        comment: Unknown platform: $platform
<fi>
```

---

### Pattern 3: Retry with Exponential Backoff

**Use Case**: Retry operation with increasing delays.

```plaintext
<intset retry_count 0>
<intset wait_time 5>

<loop $retry_count < 5>
    [FGT_A]
        get system ha status
        setvar -e "Sync Status: (\\w+)" -to sync_status
    
    <if $sync_status eq synchronized>
        comment: HA synchronized successfully
        <intset retry_count 10>  # Force exit
    <else>
        comment: Retry $retry_count - waiting $wait_time seconds
        sleep $wait_time
        <intchange retry_count + 1>
        <intchange wait_time * 2>  # Double wait time
    <fi>
<until $retry_count > 4>
```

---

### Pattern 4: Variable Extraction and Validation Chain

**Use Case**: Extract multiple values and validate relationships.

```plaintext
[FGT_A]
    # Extract device information
    get system status
    setvar -e "Version: .*build(\\d+)" -to build_number
    setvar -e "Serial-Number: (\\w+)" -to serial_number
    setvar -e "Hostname: (.*)" -to hostname
    
    # Validate extracted values
    check_var -name build_number -pattern "^\\d{4}$" -for TC_BUILD_FORMAT_001
    check_var -name serial_number -pattern "^FG.*" -for TC_SERIAL_FORMAT_001
    
    # Get HA status
    get system ha status
    setvar -e "Primary.*Serial Num: (\\w+)" -to primary_serial
    
    # Verify this device is the primary
    compare -v1 serial_number -v2 primary_serial -for TC_HA_PRIMARY_001 -fail uneq
```

---

### Pattern 5: Multi-Device Orchestration

**Use Case**: Configure HA cluster across multiple devices.

```plaintext
# Extract information from primary
[FGT_PRIMARY]
    get system status
    setvar -e "Serial-Number: (\\w+)" -to primary_serial
    setvar -e "Hostname: (.*)" -to primary_hostname
    
    # Share with secondary
    setenv -n ha_primary_serial -v $primary_serial -d FGT_SECONDARY
    setenv -n ha_primary_hostname -v $primary_hostname -d FGT_SECONDARY

# Configure HA on primary
[FGT_PRIMARY]
    config system ha
        set mode a-p
        set group-name "ha-cluster"
        set password "ha-password-123"
        set priority 200
        set pingserver-monitor-interface "port1"
    end

# Configure HA on secondary
[FGT_SECONDARY]
    comment: Joining cluster with primary $ha_primary_hostname ($ha_primary_serial)
    
    config system ha
        set mode a-p
        set group-name "ha-cluster"
        set password "ha-password-123"
        set priority 100
        set pingserver-monitor-interface "port1"
    end

# Wait for sync
sleep 60

# Verify HA status on both
[FGT_PRIMARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_HEALTH_001 -t 30
    expect -e "Master" -for TC_HA_ROLE_PRIMARY_001

[FGT_SECONDARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_HEALTH_002 -t 30
    expect -e "Slave" -for TC_HA_ROLE_SECONDARY_001
```

---

### Pattern 6: Complex Validation with Python Code

**Use Case**: Validate configuration using custom Python logic.

```plaintext
[FGT_A]
    # Get full interface configuration
    show system interface
    setvar -e "(?s)edit \"port1\"(.*?)next" -to port1_config
    
    # Execute Python validation
    exec_code -lang python -var validation_result -file validators/interface_check.py -func validate_interface -args $port1_config -timeout 10
    
    # Check result
    check_var -name validation_result -value "PASS" -for TC_INTERFACE_VALIDATION_001
    
<if $validation_result ne PASS>
    comment: Interface validation failed: $validation_result
    breakpoint
<fi>
```

**Python Validator** (`validators/interface_check.py`):

```python
def validate_interface(config_text):
    """Validate interface configuration."""
    required_settings = ['set ip', 'set allowaccess']
    
    for setting in required_settings:
        if setting not in config_text:
            return f"FAIL: Missing {setting}"
    
    if 'set status down' in config_text:
        return "FAIL: Interface is down"
    
    return "PASS"
```

---

## Best Practices

### 1. Test Case Organization

```plaintext
# ============================================================
# Test Case: HA Configuration and Failover
# QAID: TC_HA_001
# Description: Configure HA cluster and test failover
# Prerequisites: Two FortiGates with matching firmware
# ============================================================

comment: ===== TC_HA_001: Starting HA Configuration Test =====

# Step 1: Pre-checks
[FGT_PRIMARY]
    get system status
    collect_dev_info -for TC_HA_001

[FGT_SECONDARY]
    get system status
    collect_dev_info -for TC_HA_001

# Step 2: Configuration
# ... configuration commands ...

# Step 3: Validation
# ... validation checks ...

# Step 4: Report
report TC_HA_001
comment: ===== TC_HA_001: Test Complete =====
```

---

### 2. Error Handling

```plaintext
# Use retry logic for flaky operations
[FGT_A]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001 -t 10 -retry_command "diag sys ha reset-uptime" -retry_cnt 3

# Use fail_match for error detection
[FGT_A]
    get system status
    expect -e "ERROR" -for TC_NO_ERRORS_001 -fail match

# Use breakpoint for debugging
[FGT_A]
    get system status
    setvar -e "Build: (\\d+)" -to build
    
<if $build < 3600>
    comment: WARNING: Build $build is too old
    breakpoint
<fi>
```

---

### 3. Variable Naming Conventions

```plaintext
# Use descriptive names
<strset expected_hostname FGT-PRIMARY>
<intset max_retry_count 5>
<listset target_interfaces port1,port2,port3>

# Use prefixes for related variables
<strset ha_group_name cluster1>
<strset ha_password secret123>
<intset ha_priority 200>

# Use device prefix for cross-device variables
[FGT_A]
    setvar -e "Serial-Number: (.*)" -to fgt_a_serial

[FGT_B]
    setvar -e "Serial-Number: (.*)" -to fgt_b_serial
```

---

### 4. Comment Documentation

```plaintext
# Header comments for test sections
comment: ===== Section: HA Configuration =====

# Inline comments for clarity
comment: Waiting for HA synchronization (may take 2-3 minutes)
sleep 180

# Variable state comments
[FGT_A]
    get system status
    setvar -e "Build: (\\d+)" -to build_number
    comment: Extracted build number: $build_number
```

---

### 5. Timeout Management

```plaintext
# Short timeouts for fast operations
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_001 -t 5

# Long timeouts for slow operations
[FGT_A]
    execute backup config tftp backup.conf 192.168.1.100
    expect -e "Upload completed" -for TC_BACKUP_001 -t 60

# Wait before retry
[FGT_A]
    execute reboot
    sleep 180  # Wait 3 minutes for reboot
    forcelogin
```

---

### 6. Buffer Management

```plaintext
# Clear buffer before expecting
[FGT_A]
    get system status
    clear_buffer
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001 -t 5 -clear yes

# Alternative: use -clear parameter
[FGT_A]
    get system status
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001 -t 5 -clear yes
```

---

### 7. Modular Script Design

**Main Test Script** (`tests/ha_full_test.txt`):

```plaintext
# Main HA Test Suite

# Setup
include common/device_discovery.txt
include common/pre_checks.txt

# Configuration
include ha/ha_setup.txt
include ha/ha_interfaces.txt

# Testing
include ha/ha_failover_test.txt
include ha/ha_sync_test.txt

# Cleanup
include common/cleanup.txt
include common/report_generation.txt
```

**Module Example** (`ha/ha_setup.txt`):

```plaintext
# HA Setup Module

[FGT_PRIMARY]
    config system ha
        set mode a-p
        set group-name "ha-cluster"
        set password "ha-secret"
        set priority 200
    end

[FGT_SECONDARY]
    config system ha
        set mode a-p
        set group-name "ha-cluster"
        set password "ha-secret"
        set priority 100
    end

sleep 60
comment: HA setup complete
```

---

## Complete Examples

### Example 1: Basic Device Health Check

```plaintext
# ============================================================
# Test: Basic FortiGate Health Check
# QAID: TC_HEALTH_001
# ============================================================

[FGT_A]
    # Get device status
    get system status
    
    # Verify version
    expect -e "Version: FortiGate" -for TC_HEALTH_001_01 -t 5
    
    # Extract and validate build
    setvar -e "Version: .*build(\\d+)" -to build_number
    check_var -name build_number -pattern "^\\d{4}$" -for TC_HEALTH_001_02
    
    # Check serial number format
    setvar -e "Serial-Number: (\\w+)" -to serial
    check_var -name serial -pattern "^FG.*" -for TC_HEALTH_001_03
    
    # Verify no errors in logs
    execute log filter category 1
    execute log display
    expect -e "ERROR" -for TC_HEALTH_001_04 -fail match
    
    # Report overall result
    report TC_HEALTH_001
    comment: Health check complete - Build: $build_number, Serial: $serial
```

---

### Example 2: Dynamic VLAN Configuration

```plaintext
# ============================================================
# Test: Create Multiple VLANs Dynamically
# QAID: TC_VLAN_001
# ============================================================

<intset vlan_start 10>
<intset vlan_end 20>
<intset current_vlan 10>

[FGT_A]
    comment: Creating VLANs $vlan_start to $vlan_end on port1
    
    config system interface
        <while $current_vlan < 21>
            edit "vlan$current_vlan"
                set vdom "root"
                set type vlan
                set vlanid $current_vlan
                set interface "port1"
                set ip 10.0.$current_vlan.1 255.255.255.0
                set allowaccess ping
            next
            <intchange current_vlan + 1>
        <endwhile $current_vlan > $vlan_end>
    end
    
    # Verify creation
    show system interface | grep vlan
    expect -e "vlan20" -for TC_VLAN_001_01 -t 5
    
    # Count VLANs
    exec_code -lang bash -var vlan_count -file scripts/count_vlans.sh -timeout 10
    check_var -name vlan_count -value "11" -for TC_VLAN_001_02
    
    report TC_VLAN_001
```

---

### Example 3: HA Configuration with Validation

```plaintext
# ============================================================
# Test: HA Active-Passive Configuration
# QAID: TC_HA_CONFIG_001
# ============================================================

# Extract device information
[FGT_PRIMARY]
    get system status
    setvar -e "Serial-Number: (\\w+)" -to primary_sn
    setvar -e "Hostname: (.*)" -to primary_host

[FGT_SECONDARY]
    get system status
    setvar -e "Serial-Number: (\\w+)" -to secondary_sn
    setvar -e "Hostname: (.*)" -to secondary_host

comment: Configuring HA between $primary_host and $secondary_host

# Configure HA on primary
[FGT_PRIMARY]
    config system ha
        set mode a-p
        set group-name "production-cluster"
        set password "StrongHA-Pass123!"
        set priority 200
        set pingserver-monitor-interface "port1"
        set pingserver-failover-threshold 3
    end
    
    expect -e "#" -for TC_HA_CONFIG_001_01 -t 5

# Configure HA on secondary
[FGT_SECONDARY]
    config system ha
        set mode a-p
        set group-name "production-cluster"
        set password "StrongHA-Pass123!"
        set priority 100
        set pingserver-monitor-interface "port1"
        set pingserver-failover-threshold 3
    end
    
    expect -e "#" -for TC_HA_CONFIG_001_02 -t 5

# Wait for HA synchronization
comment: Waiting for HA synchronization (3 minutes)
sleep 180

# Verify HA status with retry
[FGT_PRIMARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_CONFIG_001_03 -t 15 -retry_command "get system ha status" -retry_cnt 5
    
    # Verify role
    setvar -e "Mode: (\\w+)" -to ha_mode
    check_var -name ha_mode -value "Primary" -for TC_HA_CONFIG_001_04
    
    # Verify peer serial
    setvar -e "Slave.*Serial Num: (\\w+)" -to slave_sn
    compare -v1 slave_sn -v2 secondary_sn -for TC_HA_CONFIG_001_05 -fail uneq

[FGT_SECONDARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_CONFIG_001_06 -t 15
    
    # Verify role
    setvar -e "Mode: (\\w+)" -to ha_mode
    check_var -name ha_mode -value "Slave" -for TC_HA_CONFIG_001_07

# Report
report TC_HA_CONFIG_001
comment: HA configuration complete and verified
```

---

### Example 4: Complex Conditional Logic

```plaintext
# ============================================================
# Test: Platform-Specific Configuration
# QAID: TC_PLATFORM_001
# ============================================================

[FGT_A]
    # Detect platform and version
    get system status
    setvar -e "Version: (.*?) v" -to platform_model
    setvar -e "Version: .*v(\\d+\\.\\d+)" -to fos_version
    
    comment: Detected platform: $platform_model, Version: $fos_version

# Platform-specific configuration
<if $platform_model eq FortiGate-VM64-KVM>
    [FGT_A]
        comment: Configuring VM platform
        
        config system global
            set vdom-mode multi-vdom
        end
        
        config system settings
            set opmode nat
        end
        
        expect -e "#" -for TC_PLATFORM_001_01
        
<elseif $platform_model eq FortiGate-100E>
    [FGT_A]
        comment: Configuring 100E hardware platform
        
        config system interface
            edit "lan"
                set role undefined
            next
        end
        
        expect -e "#" -for TC_PLATFORM_001_02
        
<elseif $platform_model eq FortiGate-200F>
    [FGT_A]
        comment: Configuring 200F hardware platform with FortiLink
        
        config system interface
            edit "fortilink"
                set type aggregate
            next
        end
        
        expect -e "#" -for TC_PLATFORM_001_03
        
<else>
    [FGT_A]
        comment: Unknown platform $platform_model - using default config
        expect -e "#" -for TC_PLATFORM_001_04
<fi>

# Version-specific configuration
<strset min_version 7.0>

<if $fos_version > $min_version>
    [FGT_A]
        comment: FortiOS $fos_version supports new features
        
        config system settings
            set allow-traffic-redirect enable
        end
        
        expect -e "#" -for TC_PLATFORM_001_05
<else>
    [FGT_A]
        comment: FortiOS $fos_version - using legacy configuration
<fi>

report TC_PLATFORM_001
```

---

### Example 5: Network Connectivity Test Suite

```plaintext
# ============================================================
# Test: Network Connectivity Test Suite
# QAID: TC_NETWORK_001
# ============================================================

<listset test_ips 8.8.8.8,1.1.1.1,192.168.1.1>
<intset success_count 0>
<intset ip_index 0>

[FGT_A]
    # Configure interface
    config system interface
        edit "port1"
            set mode static
            set ip 192.168.1.99 255.255.255.0
            set allowaccess ping
        next
    end
    
    # Test each IP
    comment: Testing connectivity to: $test_ips

# Test 8.8.8.8
[FGT_A]
    execute ping 8.8.8.8
    setvar -e "(\\d+) packets received" -to received
    
<if $received > 0>
    comment: Ping to 8.8.8.8 successful
    <intchange success_count + 1>
    expect -e "packets received" -for TC_NETWORK_001_01
<else>
    comment: Ping to 8.8.8.8 failed
<fi>

# Test 1.1.1.1
[FGT_A]
    execute ping 1.1.1.1
    setvar -e "(\\d+) packets received" -to received
    
<if $received > 0>
    comment: Ping to 1.1.1.1 successful
    <intchange success_count + 1>
    expect -e "packets received" -for TC_NETWORK_001_02
<else>
    comment: Ping to 1.1.1.1 failed
<fi>

# Test local gateway
[FGT_A]
    execute ping 192.168.1.1
    setvar -e "(\\d+) packets received" -to received
    
<if $received > 0>
    comment: Ping to 192.168.1.1 successful
    <intchange success_count + 1>
    expect -e "packets received" -for TC_NETWORK_001_03
<else>
    comment: Ping to 192.168.1.1 failed
<fi>

# Summary
comment: Network test complete - $success_count of 3 tests passed

<if $success_count eq 3>
    comment: All network tests PASSED
<elseif $success_count > 0>
    comment: Some network tests passed ($success_count/3)
<else>
    comment: All network tests FAILED
<fi>

report TC_NETWORK_001
```

---

### Example 6: File Transfer with Validation

```plaintext
# ============================================================
# Test: FTP File Transfer and Validation
# QAID: TC_FTP_001
# ============================================================

<strset ftp_server 192.168.1.100>
<strset ftp_user fosqa>
<strset ftp_pass ftnt123>
<strset test_file firmware_image.out>

[PC1]
    comment: Starting FTP transfer test from PC to $ftp_server
    
    # Test FTP connection
    myftp -e "230 Login successful" -ip $ftp_server -u $ftp_user -p $ftp_pass -for TC_FTP_001_01 -t 10
    
    # Upload file
    myftp -e "226 Transfer complete" -ip $ftp_server -u $ftp_user -p $ftp_pass -c "put $test_file" -for TC_FTP_001_02 -t 120
    
    # Verify file on server
    exec_code -lang bash -var file_exists -file scripts/check_ftp_file.sh -args $ftp_server,$ftp_user,$ftp_pass,$test_file -timeout 30
    
    check_var -name file_exists -value "true" -for TC_FTP_001_03

[FGT_A]
    # Download file from FTP to FortiGate
    execute backup config ftp $test_file $ftp_server
    expect -e "OK" -for TC_FTP_001_04 -t 60
    
    # List files
    execute fmupdate disk list
    expect -e "$test_file" -for TC_FTP_001_05 -t 5

report TC_FTP_001
comment: FTP transfer test complete
```

---

## Troubleshooting Tips

### Common Issues and Solutions

#### 1. Pattern Not Matching

**Problem**: `expect` API reports failure even though text appears in output.

**Solutions**:
```plaintext
# Use -clear yes to clear old buffer
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_001 -clear yes

# Escape special regex characters
[FGT_A]
    get system status
    # Wrong: expect -e "CPU: 5%" -for TC_001
    # Correct: escape the %
    expect -e "CPU: 5\\%" -for TC_001

# Use (?s) for multi-line matching
[FGT_A]
    show full-configuration
    setvar -e "(?s)config system global.*?set hostname (.*?)\\n" -to hostname
```

#### 2. Variable Not Interpolating

**Problem**: Variable shows as `$varname` instead of value.

**Solutions**:
```plaintext
# Variables work in device commands and API parameters
[FGT_A]
    <strset hostname FGT-PRIMARY>
    config system global
        set hostname $hostname  # ✅ Works
    end
    
    expect -e "$hostname" -for TC_001  # ✅ Works in API params

# Variables don't work in comments
# Wrong: comment: Hostname is $hostname
# Correct:
comment Hostname is $hostname  # Without colon
```

#### 3. Loop Not Terminating

**Problem**: `while` or `loop` runs forever.

**Solutions**:
```plaintext
# Always increment counter
<intset counter 0>
<while $counter < 10>
    [FGT_A]
        get system status
    <intchange counter + 1>  # ⚠️ Don't forget this!
<endwhile $counter > 9>

# Add safety limit
<intset counter 0>
<intset max_iterations 100>
<while $counter < $max_iterations>
    # ... your logic ...
    <intchange counter + 1>
<endwhile $counter > 99>
```

---

## Summary

This DSL provides a powerful framework for:
- ✅ Multi-device test orchestration
- ✅ Dynamic configuration with loops and conditionals
- ✅ Pattern-based validation and reporting
- ✅ Variable extraction and comparison
- ✅ Code execution for complex logic
- ✅ Modular script organization

For more examples and updates, refer to:
- Test cases in `testcase/` directory
- Examples in `examples/` directory
- Syntax schema: `lib/core/compiler/static/cli_syntax.json`

---

**Document Version**: 1.0  
**Last Updated**: February 13, 2026  
**Schema Version**: 2.0
