# AutoLib v3 - Getting Started Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Understanding the Components](#understanding-the-components)
4. [Setting Up Environment Files](#setting-up-environment-files)
5. [Creating Test Scripts](#creating-test-scripts)
6. [Organizing Test Groups](#organizing-test-groups)
7. [Running Tests](#running-tests)
8. [Understanding Test Output](#understanding-test-output)
9. [Practical Examples](#practical-examples)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

AutoLib v3 is a comprehensive test automation framework for FortiOS devices. It handles everything you need for automated testing:

✅ **Automatic Device Connections** - No manual SSH/Telnet login required  
✅ **Command Execution** - Send CLI commands and capture output automatically  
✅ **Pattern Matching** - Validate device output with regex patterns  
✅ **Result Reporting** - Track test pass/fail with QA IDs (QAID)  
✅ **Log Management** - Comprehensive logging of all test activities  
✅ **System Integration** - Hook into Oriole and other support systems  

### What AutoLib Does For You

When you run a test with AutoLib, it automatically:

1. **Loads your environment file** - Reads device IPs, credentials, and configuration
2. **Establishes connections** - Connects to all devices (FortiGate, PC, KVM, etc.)
3. **Executes your test script** - Runs DSL commands on the correct devices
4. **Validates results** - Checks output against expected patterns
5. **Collects logs** - Saves terminal output, device info, and test results
6. **Generates reports** - Creates HTML summaries and detailed logs
7. **Submits results** - (Optional) Sends results to Oriole tracking system

You just write the test logic in DSL - AutoLib handles all the infrastructure!

---

## Quick Start

### Installation

```bash
# Navigate to autolib_v3 directory
cd /home/fosqa/autolibv3/autolib_v3

# Verify installation
python3 autotest.py --version
```

### Your First Test

**1. Create a simple test script** (`testcase/my_first_test.txt`):

```plaintext
# Simple health check test
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_001 -t 5
    
    comment: Test completed successfully
```

**2. Create an environment file** (`testcase/my_env.env`):

```ini
[FGT_A]
    CONNECTION: 192.168.1.99 22
    USERNAME: admin
    PASSWORD: admin

[GLOBAL]
    LICENSE_INFORMATION: /path/to/license.csv
```

**3. Run the test**:

```bash
python3 autotest.py -e testcase/my_env.env -t testcase/my_first_test.txt
```

**4. View results**:

```bash
# Results are saved to outputs/YYYY-MM-DD/HH-MM-SS--testcase--filename/
cd outputs/$(date +%Y-%m-%d)
ls -lt | head -5
```

That's it! AutoLib handled the connection, command execution, validation, and logging.

---

## Understanding the Components

### The Three Key Files

1. **Environment File (.env)** - Device configuration
2. **Test Script (.txt)** - DSL test logic  
3. **Test Group (.full)** - Organized collection of test scripts

### Workflow Diagram

```
┌─────────────────────┐
│  Environment File   │  → Device IPs, credentials, settings
│   (*.env)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Test Script       │  → Test logic in DSL
│   (*.txt)           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   AutoLib Engine    │  → Executes test automatically
│   (autotest.py)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Test Results       │  → Logs, reports, pass/fail status
│   (outputs/)        │
└─────────────────────┘
```

---

## Setting Up Environment Files

### Environment File Structure

An environment file defines devices and their connection parameters.

#### Basic Example

```ini
[FGT_A]
    CONNECTION: 192.168.1.99 22
    USERNAME: admin
    PASSWORD: fortinet
    MGMT_IP: 10.10.10.1
    MGMT_MASK: 255.255.255.0

[FGT_B]
    CONNECTION: 192.168.1.100 22
    USERNAME: admin
    PASSWORD: fortinet

[PC1]
    CONNECTION: 192.168.1.50 22
    USERNAME: root
    PASSWORD: password

[GLOBAL]
    LICENSE_INFORMATION: /home/fosqa/licenses/license.csv
    LOCAL_HTTP_SERVER_IP: 192.168.1.10
    LOCAL_HTTP_SERVER_PORT: 8080
```

### Device Section: `[DEVICE_NAME]`

Each device section defines connection parameters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `CONNECTION` | IP address and port | `192.168.1.99 22` |
| `USERNAME` | Login username | `admin` |
| `PASSWORD` | Login password | `fortinet` |
| `MGMT_IP` | Management IP (optional) | `10.10.10.1` |
| `MGMT_MASK` | Management subnet mask | `255.255.255.0` |
| `MGMT_GW` | Management gateway | `10.10.10.254` |

### Global Section: `[GLOBAL]`

The `[GLOBAL]` section defines shared settings:

```ini
[GLOBAL]
    # License file for VM licensing
    LICENSE_INFORMATION: /path/to/VMLicense.csv
    
    # HTTP server for file transfers
    LOCAL_HTTP_SERVER_IP: 192.168.1.10
    LOCAL_HTTP_SERVER_PORT: 8080
    
    # Shared network configuration
    IPV4_MASK: 255.255.255.0
    DNS_SERVER: 8.8.8.8
    
    # Variables (can be referenced by devices)
    MGMT_IP: GLOBAL:IP_ADDRESS1 GLOBAL:IPV4_MASK
    IP_ADDRESS1: 172.18.57.22
```

### Variable References

You can reference global variables in device sections:

```ini
[GLOBAL]
    BASE_IP: 192.168.1.100
    BASE_PASSWORD: test123

[FGT_A]
    CONNECTION: GLOBAL:BASE_IP 22
    PASSWORD: GLOBAL:BASE_PASSWORD
```

### Oriole Integration (Optional)

To submit results to Oriole tracking system:

```ini
[ORIOLE]
    FIELD_MARK: autolib_v3
    USER: your_username
```

### Multiple Device Example

```ini
# HA Cluster Environment
[FGT_PRIMARY]
    CONNECTION: 10.10.10.10 22
    USERNAME: admin
    PASSWORD: fortinet
    ROLE: primary
    HA_PRIORITY: 200

[FGT_SECONDARY]
    CONNECTION: 10.10.10.11 22
    USERNAME: admin
    PASSWORD: fortinet
    ROLE: secondary
    HA_PRIORITY: 100

[FSW1]
    CONNECTION: 10.10.10.20 22
    USERNAME: admin
    PASSWORD: fortinet
    UPLINK_PORT: port1

[PC1]
    CONNECTION: 10.10.10.50 22
    USERNAME: testuser
    PASSWORD: test123

[GLOBAL]
    LICENSE_INFORMATION: /home/fosqa/licenses/ha_license.csv
    HA_GROUP_NAME: ha-cluster
    HA_PASSWORD: ha-secret
```

### Environment File Best Practices

1. ✅ **Use descriptive device names**: `FGT_PRIMARY`, `FGT_SECONDARY` instead of `FGT1`, `FGT2`
2. ✅ **Keep passwords secure**: Use environment variables or secure vaults in production
3. ✅ **Document custom variables**: Add comments explaining non-obvious settings
4. ✅ **Use GLOBAL for shared config**: Avoid duplication across device sections
5. ✅ **Organize by test scenario**: Create separate env files for different test setups

---

## Creating Test Scripts

### Test Script Basics

Test scripts are written in AutoLib DSL and saved as `.txt` files.

#### Script Structure

```plaintext
# Test metadata (comments)
# Test ID: TC_BASIC_001
# Description: Basic health check

# Device section - commands run on FGT_A
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_001_01 -t 5
    
    # Extract serial number
    setvar -e "Serial-Number: (.*)" -to serial
    
    # Report result
    comment: Device serial: $serial
    report TC_001
```

### Device Sections

Use `[DEVICE_NAME]` to specify which device executes commands:

```plaintext
[FGT_A]
    # Commands for FGT_A
    get system status
    config system global
        set hostname FGT-PRIMARY
    end

[FGT_B]
    # Commands for FGT_B
    get system status
    config system global
        set hostname FGT-SECONDARY
    end

[PC1]
    # Commands for PC1
    ping -c 5 192.168.1.99
```

### Common API Patterns

#### Pattern 1: Command + Expect

```plaintext
[FGT_A]
    # Execute command and validate output
    get system status
    expect -e "Version: FortiGate" -for TC_001 -t 5
```

#### Pattern 2: Extract Variable

```plaintext
[FGT_A]
    # Extract value from output
    get system status
    setvar -e "Serial-Number: (.*)" -to serial_number
    
    # Use variable
    comment: Serial is $serial_number
```

#### Pattern 3: Configuration + Validation

```plaintext
[FGT_A]
    # Configure device
    config system global
        set hostname FGT-TEST
    end
    
    # Verify configuration
    get system global | grep hostname
    expect -e "hostname: FGT-TEST" -for TC_002 -t 5
```

#### Pattern 4: Multi-Step Test

```plaintext
[FGT_A]
    # Step 1: Setup
    comment: ===== Setup Phase =====
    config system interface
        edit port1
            set ip 192.168.1.99 255.255.255.0
        next
    end
    
    # Step 2: Test
    comment: ===== Test Phase =====
    get system interface port1
    expect -e "192.168.1.99" -for TC_003_01 -t 5
    
    # Step 3: Cleanup
    comment: ===== Cleanup Phase =====
    config system interface
        edit port1
            set ip 0.0.0.0 0.0.0.0
        next
    end
```

### Control Structures

#### Conditionals

```plaintext
[FGT_A]
    get system status
    setvar -e "Version: .*build(\\d+)" -to build
    
<if $build > 3600>
    [FGT_A]
        comment: Running latest build
<else>
    [FGT_A]
        comment: Old build detected
<fi>
```

#### Loops

```plaintext
<intset counter 1>
<intset max 5>

[FGT_A]
    <while $counter < 6>
        comment: Iteration $counter
        get system status
        sleep 5
        <intchange counter + 1>
    <endwhile $counter > $max>
```

### Variables

```plaintext
# String variables
<strset test_hostname FGT-PRIMARY>
<strset test_ip 192.168.1.99>

# Integer variables
<intset retry_count 3>
<intset timeout 30>

# List variables
<listset interface_list port1,port2,port3>

[FGT_A]
    config system global
        set hostname $test_hostname
    end
```

### Comments and Documentation

```plaintext
# Header comment - describes the test
# Test: HA Configuration
# QAID: TC_HA_001
# Author: John Doe
# Date: 2026-02-13

[FGT_A]
    # Inline comment - explains the step
    get system status
    
    # Comment API - appears in logs and results
    comment: Starting HA configuration
    
    config system ha
        set mode a-p
    end
```

---

## Organizing Test Groups

### What is a Test Group?

A test group (`.full` file) organizes multiple test scripts into a logical suite.

### Test Group Format

```plaintext
# Group metadata
# Written By: John Doe
# Modified Date: Feb 13, 2026
# Test Case ID: grp.basic_tests.full
# Objective: Basic functionality tests
# Category: Critical

# Section: Setup
**setup_env testcase/common/setup.txt Setup test environment

# Section: Basic Tests
**TC_001 testcase/basic/test_status.txt Verify system status
**TC_002 testcase/basic/test_interface.txt Verify interface configuration
**TC_003 testcase/basic/test_routing.txt Verify routing table

# Section: Advanced Tests
**TC_101 testcase/advanced/test_ha.txt Test HA configuration
**TC_102 testcase/advanced/test_vpn.txt Test VPN setup

# Section: Cleanup
**cleanup testcase/common/cleanup.txt Cleanup test environment
```

### Test Group Entry Format

Each test entry follows this pattern:

```
**<TEST_ID> <SCRIPT_PATH> <DESCRIPTION>
```

- `**` - Prefix (required)
- `<TEST_ID>` - Unique test identifier
- `<SCRIPT_PATH>` - Path to test script (relative or absolute)
- `<DESCRIPTION>` - Human-readable description

### Organizing by Category

```plaintext
#-SETUP-
**setup_nat testcase/setup/setup_nat.txt Setup NAT environment
**setup_vdom testcase/setup/setup_vdom.txt Setup VDOM environment

#-BASIC FUNCTIONALITY-
**TC_001 testcase/basic/system_status.txt System status check
**TC_002 testcase/basic/interface_test.txt Interface configuration

#-ADVANCED FEATURES-
**TC_101 testcase/advanced/ha_config.txt HA configuration
**TC_102 testcase/advanced/ipsec_vpn.txt IPSec VPN setup

#-PERFORMANCE TESTS-
**PERF_001 testcase/performance/throughput.txt Throughput test
**PERF_002 testcase/performance/latency.txt Latency test

#-CLEANUP-
**cleanup testcase/common/cleanup.txt Restore default config
```

### Example: Complete Test Group

```plaintext
# ============================================================
# Test Group: Web Filter Basic Tests
# Written By: Test Team
# Modified Date: Feb 13, 2026
# Test Case ID: grp.webfilter_basic.full
# Objective: Test web filtering functionality
# Robot Category: Critical
# ============================================================

#-SETUP-
**setup_nat testcase/webfilter/setup_nat.txt Setup NAT test environment
**setup_policy testcase/webfilter/setup_policy.txt Setup firewall policies

#-WEB FILTER BASIC-
**WF_001 testcase/webfilter/01-basic/wf_001 Test URL filtering - block category
**WF_002 testcase/webfilter/01-basic/wf_002 Test URL filtering - allow category
**WF_003 testcase/webfilter/01-basic/wf_003 Test static URL filter
**WF_004 testcase/webfilter/01-basic/wf_004 Test HTTPS inspection

#-WEB FILTER ADVANCED-
**WF_101 testcase/webfilter/02-advanced/wf_101 Test content filtering
**WF_102 testcase/webfilter/02-advanced/wf_102 Test script filtering
**WF_103 testcase/webfilter/02-advanced/wf_103 Test FortiGuard override

#-CLEANUP-
**cleanup testcase/webfilter/cleanup.txt Restore default configuration
```

### Test Group Best Practices

1. ✅ **Group related tests together**: Keep similar functionality in one group
2. ✅ **Use clear section headers**: Organize with `#-SECTION NAME-`
3. ✅ **Include setup and cleanup**: Always prepare and restore test environment
4. ✅ **Use meaningful test IDs**: `WF_001` for Web Filter, `HA_001` for HA tests
5. ✅ **Add descriptions**: Make it clear what each test does
6. ✅ **Order matters**: Tests run sequentially - put dependencies first

---

## Running Tests

### Command Line Interface

```bash
python3 autotest.py [OPTIONS]
```

### Running a Single Test Script

```bash
# Basic syntax
python3 autotest.py -e <env_file> -t <test_script>

# Example
python3 autotest.py -e testcase/my_env.env -t testcase/my_test.txt
```

### Running a Test Group

```bash
# Basic syntax
python3 autotest.py -e <env_file> -g <group_file>

# Example
python3 autotest.py -e testcase/env.conf -g testcase/grp.basic_tests.full
```

### Command Line Options

#### Essential Options

| Option | Description | Example |
|--------|-------------|---------|
| `-e, --environment` | Environment file | `-e testcase/env.conf` |
| `-t, --testcase` | Single test script | `-t testcase/test.txt` |
| `-g, --group` | Test group file | `-g testcase/grp.tests.full` |
| `-d, --debug` | Enable debug logging | `-d` |

#### Advanced Options

| Option | Description | Example |
|--------|-------------|---------|
| `-c, --check` | Syntax check only (no execution) | `-c` |
| `-r, --release` | FortiOS release version | `-r 7` |
| `-b, --build` | FortiOS build number | `-b 3645` |
| `-s, --submit` | Submit results to Oriole | `-s all` |
| `--portal` | Start web portal during test | `--portal` |
| `--task_path` | Oriole task path | `--task_path /path/to/task` |

#### Submit Options (Oriole Integration)

```bash
# Don't submit any results
python3 autotest.py -e env.conf -g tests.full -s none

# Submit only passed tests (default)
python3 autotest.py -e env.conf -g tests.full -s succeeded

# Submit all results (pass and fail)
python3 autotest.py -e env.conf -g tests.full -s all
```

### Common Usage Patterns

#### 1. Development Mode (Debug + No Submit)

```bash
python3 autotest.py \
  -e testcase/my_env.env \
  -t testcase/my_test.txt \
  -d \
  -s none
```

#### 2. Production Test Run

```bash
python3 autotest.py \
  -e testcase/production.env \
  -g testcase/grp.full_suite.full \
  -s succeeded
```

#### 3. Syntax Check Only

```bash
python3 autotest.py \
  -e testcase/env.conf \
  -t testcase/test.txt \
  -c
```

#### 4. Test with Web Portal

```bash
python3 autotest.py \
  -e testcase/env.conf \
  -g testcase/grp.tests.full \
  --portal
```

Then open browser to: `http://localhost:8080`

#### 5. Specify Build/Release

```bash
python3 autotest.py \
  -e testcase/env.conf \
  -g testcase/grp.tests.full \
  -r 7 \
  -b 3645
```

### Viewing Test Progress

While tests run, you'll see output like:

```
2026-02-13 14:30:15 INFO **** Start test job with AUTOLIB - V3R10B0123. ****
2026-02-13 14:30:15 INFO Test Environment: testcase/env.conf
2026-02-13 14:30:16 INFO Compiling script: testcase/test.txt
2026-02-13 14:30:16 INFO Connecting to FGT_A (192.168.1.99:22)...
2026-02-13 14:30:17 INFO FGT_A: Connection established
2026-02-13 14:30:17 INFO Executing: get system status
2026-02-13 14:30:18 INFO TC_001: PASS
2026-02-13 14:30:18 INFO Test job completed
```

---

## Understanding Test Output

### Output Directory Structure

After running tests, results are saved to:

```
outputs/
└── YYYY-MM-DD/
    └── HH-MM-SS--type--name/
        ├── summary/               # HTML and text summaries
        │   ├── summary.html      # Web-viewable results
        │   └── summary.txt       # Text results
        ├── terminal/              # Device terminal outputs
        │   ├── FGT_A.log
        │   ├── FGT_B.log
        │   └── PC1.log
        ├── compiled/              # Compiled VM code
        │   └── compiled_script.json
        └── logs/                  # Framework logs
            └── autotest.log
```

### Example Directory

```
outputs/2026-02-13/14-30-15--testcase--my_test/
```

Breakdown:
- `2026-02-13` - Date
- `14-30-15` - Time (14:30:15)
- `testcase` - Test type (testcase or group)
- `my_test` - Test name (from filename)

### Summary Report

#### HTML Summary (`summary/summary.html`)

Open in browser for interactive results:

```html
Test Summary
=====================================
Total Tests: 10
Passed: 8
Failed: 2
Pass Rate: 80%

Test Details:
TC_001 - System Status Check: PASS
TC_002 - Interface Test: PASS
TC_003 - Routing Test: FAIL
...
```

#### Text Summary (`summary/summary.txt`)

```
============================================================
Test Execution Summary
============================================================
Start Time: 2026-02-13 14:30:15
End Time: 2026-02-13 14:45:30
Duration: 15 minutes 15 seconds
Environment: testcase/env.conf
Test: testcase/my_test.txt

Results:
--------
TC_001: PASS - System status check
TC_002: PASS - Interface configuration
TC_003: FAIL - Routing table verification
  Expected: "route added"
  Got: "route already exists"

Summary:
--------
Total: 3
Passed: 2
Failed: 1
Pass Rate: 66.7%
============================================================
```

### Terminal Logs

Device terminal logs capture all commands and output:

```
# terminal/FGT_A.log
[2026-02-13 14:30:17]
FGT-A # get system status
Version: FortiGate-VM64-KVM v7.0.3,build3645,231204 (GA)
Serial-Number: FGVMEV0000000000
...

[2026-02-13 14:30:20]
FGT-A # config system global
FGT-A (global) # set hostname FGT-PRIMARY
FGT-A (global) # end
```

### Framework Logs

Detailed execution logs (`logs/autotest.log`):

```
2026-02-13 14:30:15,123 INFO [main] Starting AutoLib v3
2026-02-13 14:30:16,234 INFO [compiler] Compiling script: testcase/my_test.txt
2026-02-13 14:30:16,345 INFO [compiler] Compilation successful: 45 VM codes generated
2026-02-13 14:30:16,456 INFO [scheduler] Creating test job
2026-02-13 14:30:17,567 INFO [device] Connecting to FGT_A (192.168.1.99:22)
2026-02-13 14:30:17,678 INFO [device] FGT_A: Login successful
2026-02-13 14:30:18,789 INFO [executor] Executing: get system status
2026-02-13 14:30:19,890 INFO [expect] TC_001: Pattern matched - PASS
...
```

### Finding Your Results

```bash
# Find latest test results
cd outputs/
ls -lt | head -5

# Or by date
cd outputs/2026-02-13/
ls -lt

# Open HTML summary in browser
firefox outputs/2026-02-13/14-30-15--testcase--my_test/summary/summary.html
```

---

## Practical Examples

### Example 1: Simple Health Check

**Purpose**: Verify FortiGate is responding and running expected version.

**Environment**: `testcase/examples/health_check.env`

```ini
[FGT_A]
    CONNECTION: 192.168.1.99 22
    USERNAME: admin
    PASSWORD: fortinet

[GLOBAL]
    LICENSE_INFORMATION: /home/fosqa/licenses/license.csv
```

**Test Script**: `testcase/examples/health_check.txt`

```plaintext
# Health Check Test
# QAID: TC_HEALTH_001

[FGT_A]
    # Check system is responding
    get system status
    expect -e "Version: FortiGate" -for TC_HEALTH_001_01 -t 5
    
    # Extract and validate build
    setvar -e "Version: .*build(\\d+)" -to build_number
    check_var -name build_number -pattern "^\\d{4}$" -for TC_HEALTH_001_02
    
    # Check serial number format
    setvar -e "Serial-Number: (\\w+)" -to serial
    check_var -name serial -pattern "^FG.*" -for TC_HEALTH_001_03
    
    # Report overall test
    report TC_HEALTH_001
    comment: Health check complete - Build: $build_number
```

**Run**:

```bash
python3 autotest.py \
  -e testcase/examples/health_check.env \
  -t testcase/examples/health_check.txt \
  -d
```

---

### Example 2: Interface Configuration Test

**Purpose**: Configure and verify network interface settings.

**Test Script**: `testcase/examples/interface_config.txt`

```plaintext
# Interface Configuration Test
# QAID: TC_INTERFACE_001

[FGT_A]
    comment: ===== Configuring port1 interface =====
    
    # Configure interface
    config system interface
        edit port1
            set vdom root
            set mode static
            set ip 192.168.1.99 255.255.255.0
            set allowaccess ping https ssh
            set description "LAN Interface"
        next
    end
    
    # Verify configuration
    get system interface port1
    expect -e "ip: 192.168.1.99" -for TC_INTERFACE_001_01 -t 5
    expect -e "255.255.255.0" -for TC_INTERFACE_001_02 -t 5
    
    # Extract interface status
    show system interface port1 | grep "status"
    setvar -e "status: (\\w+)" -to if_status
    check_var -name if_status -value "up" -for TC_INTERFACE_001_03
    
    # Test connectivity
    execute ping 192.168.1.1
    expect -e "packets received" -for TC_INTERFACE_001_04 -t 30
    
    report TC_INTERFACE_001
    comment: Interface configuration test complete
```

---

### Example 3: HA Configuration

**Purpose**: Configure High Availability between two FortiGates.

**Environment**: `testcase/examples/ha_config.env`

```ini
[FGT_PRIMARY]
    CONNECTION: 192.168.1.10 22
    USERNAME: admin
    PASSWORD: fortinet

[FGT_SECONDARY]
    CONNECTION: 192.168.1.11 22
    USERNAME: admin
    PASSWORD: fortinet

[GLOBAL]
    HA_GROUP_NAME: production-ha
    HA_PASSWORD: ha-secret-123
```

**Test Script**: `testcase/examples/ha_config.txt`

```plaintext
# HA Configuration Test
# QAID: TC_HA_001

# Get device information
[FGT_PRIMARY]
    get system status
    setvar -e "Serial-Number: (\\w+)" -to primary_sn
    comment: Primary serial: $primary_sn

[FGT_SECONDARY]
    get system status
    setvar -e "Serial-Number: (\\w+)" -to secondary_sn
    comment: Secondary serial: $secondary_sn

# Configure HA on primary
[FGT_PRIMARY]
    comment: ===== Configuring HA on primary =====
    config system ha
        set mode a-p
        set group-name "production-ha"
        set password "ha-secret-123"
        set priority 200
        set pingserver-monitor-interface port1
    end
    expect -e "#" -for TC_HA_001_01 -t 5

# Configure HA on secondary
[FGT_SECONDARY]
    comment: ===== Configuring HA on secondary =====
    config system ha
        set mode a-p
        set group-name "production-ha"
        set password "ha-secret-123"
        set priority 100
        set pingserver-monitor-interface port1
    end
    expect -e "#" -for TC_HA_001_02 -t 5

# Wait for sync
comment: Waiting for HA synchronization (2 minutes)
sleep 120

# Verify HA status on primary
[FGT_PRIMARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001_03 -t 15
    
    setvar -e "Mode: (\\w+)" -to ha_mode
    check_var -name ha_mode -value "Primary" -for TC_HA_001_04

# Verify HA status on secondary
[FGT_SECONDARY]
    get system ha status
    expect -e "HA Health Status: OK" -for TC_HA_001_05 -t 15
    
    setvar -e "Mode: (\\w+)" -to ha_mode
    check_var -name ha_mode -value "Slave" -for TC_HA_001_06

report TC_HA_001
comment: HA configuration and verification complete
```

---

### Example 4: Test Group for Basic Suite

**Test Group**: `testcase/examples/grp.basic_suite.full`

```plaintext
# ============================================================
# Test Group: Basic Functionality Suite
# Written By: Automation Team
# Modified Date: Feb 13, 2026
# Objective: Basic FortiGate functionality tests
# Category: Critical
# ============================================================

#-SETUP-
**setup testcase/examples/setup_environment.txt Setup test environment

#-SYSTEM TESTS-
**TC_HEALTH testcase/examples/health_check.txt System health check
**TC_INTERFACE testcase/examples/interface_config.txt Interface configuration

#-NETWORK TESTS-
**TC_ROUTING testcase/examples/routing_test.txt Static routing test
**TC_PING testcase/examples/connectivity_test.txt Network connectivity

#-SECURITY TESTS-
**TC_FIREWALL testcase/examples/firewall_policy.txt Firewall policy test
**TC_NAT testcase/examples/nat_test.txt NAT configuration test

#-CLEANUP-
**cleanup testcase/examples/cleanup.txt Restore default configuration
```

**Run the suite**:

```bash
python3 autotest.py \
  -e testcase/examples/basic_suite.env \
  -g testcase/examples/grp.basic_suite.full \
  -s succeeded
```

---

### Example 5: Multi-Device Test with PC

**Purpose**: Test connectivity from PC through FortiGate.

**Environment**: `testcase/examples/multi_device.env`

```ini
[FGT_A]
    CONNECTION: 192.168.1.99 22
    USERNAME: admin
    PASSWORD: fortinet

[PC1]
    CONNECTION: 192.168.1.50 22
    USERNAME: testuser
    PASSWORD: test123

[GLOBAL]
    TARGET_SERVER: 8.8.8.8
```

**Test Script**: `testcase/examples/connectivity_test.txt`

```plaintext
# Multi-Device Connectivity Test
# QAID: TC_CONN_001

# Configure FortiGate
[FGT_A]
    comment: ===== Configuring FortiGate =====
    
    config system interface
        edit port1
            set ip 192.168.1.99 255.255.255.0
        next
    end
    
    config firewall policy
        edit 1
            set name "LAN-to-WAN"
            set srcintf port1
            set dstintf wan1
            set srcaddr all
            set dstaddr all
            set action accept
            set schedule always
            set service ALL
        next
    end

# Test from PC
[PC1]
    comment: ===== Testing from PC =====
    
    # Ping FortiGate
    ping -c 5 192.168.1.99
    expect -e "5 received" -for TC_CONN_001_01 -t 30
    
    # Ping external server
    ping -c 5 8.8.8.8
    expect -e "5 received" -for TC_CONN_001_02 -t 30

# Verify on FortiGate
[FGT_A]
    comment: ===== Checking logs =====
    
    execute log filter category 0
    execute log display
    expect -e "traffic-forward" -for TC_CONN_001_03 -t 10

report TC_CONN_001
comment: Multi-device connectivity test complete
```

---

## Best Practices

### 1. Test Organization

```
testcase/
├── common/                    # Shared utilities
│   ├── setup.txt
│   ├── cleanup.txt
│   └── helpers.txt
├── basic/                     # Basic functionality
│   ├── grp.basic.full
│   ├── test_status.txt
│   └── test_interface.txt
├── advanced/                  # Advanced features
│   ├── grp.advanced.full
│   ├── test_ha.txt
│   └── test_vpn.txt
└── env/                       # Environment files
    ├── lab_env.env
    ├── production_env.env
    └── ha_env.env
```

### 2. Naming Conventions

#### Environment Files
- ✅ `env.<scenario>.env` - e.g., `env.ha_cluster.env`
- ✅ `<feature>.env` - e.g., `vpn.env`, `webfilter.env`

#### Test Scripts
- ✅ `test_<feature>.txt` - e.g., `test_interface.txt`
- ✅ `<QAID>.txt` - e.g., `TC_001.txt`
- ✅ Descriptive names - `ha_failover_test.txt`

#### Test Groups
- ✅ `grp.<category>.full` - e.g., `grp.basic_tests.full`
- ✅ `grp.<feature>_<type>.full` - e.g., `grp.webfilter_critical.full`

### 3. Test Structure

```plaintext
# ============================================================
# Test: <Feature Name>
# QAID: <Test Case ID>
# Description: <What this test does>
# Prerequisites: <What's needed>
# Expected Result: <What should happen>
# ============================================================

# Setup phase
comment: ===== Setup Phase =====
[DEVICE]
    # Setup commands...

# Test phase
comment: ===== Test Phase =====
[DEVICE]
    # Test commands...
    # Validations...

# Cleanup phase
comment: ===== Cleanup Phase =====
[DEVICE]
    # Cleanup commands...

# Report
report <QAID>
comment: Test complete
```

### 4. Error Handling

```plaintext
# Use retry logic for flaky checks
[FGT_A]
    get system ha status
    expect -e "HA Health Status: OK" \
        -for TC_HA_001 \
        -t 10 \
        -retry_command "get system ha status" \
        -retry_cnt 5

# Use fail=match to ensure no errors
[FGT_A]
    get system status
    expect -e "ERROR|FAIL" -for TC_NO_ERRORS -fail match

# Add breakpoints for debugging
[FGT_A]
    get system status
    breakpoint  # Pause here if something unexpected
    config system settings
        # ...
```

### 5. Documentation

```plaintext
# Always document:
# - What the test does
# - What QA IDs are tested
# - Prerequisites
# - Expected results
# - Any special conditions

# Good example:
# ============================================================
# Test: Interface DHCP Configuration
# QAID: TC_DHCP_001
# Description: Verify FortiGate can obtain IP via DHCP
# Prerequisites: 
#   - DHCP server available on port1 network
#   - FGT port1 connected to DHCP network
# Expected Result:
#   - Port1 gets IP from DHCP server
#   - Default route created
#   - DNS servers configured
# ============================================================
```

### 6. Version Control

```bash
# Track your test changes
git add testcase/my_new_test.txt
git commit -m "Add test for feature XYZ (TC_XYZ_001)"

# Use branches for development
git checkout -b feature/add-vpn-tests
# ... develop tests ...
git commit -am "Add VPN test suite"
git push origin feature/add-vpn-tests
```

### 7. Debugging

```bash
# Enable debug mode
python3 autotest.py -e env.conf -t test.txt -d

# Syntax check only (no execution)
python3 autotest.py -e env.conf -t test.txt -c

# Run without Oriole submission
python3 autotest.py -e env.conf -t test.txt -s none

# Add breakpoints in your test
[FGT_A]
    get system status
    breakpoint  # Execution stops here
    # You can inspect variables and state
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Connection Failed

**Error**: `Connection to FGT_A failed: timeout`

**Solutions**:
```bash
# 1. Verify device is reachable
ping 192.168.1.99

# 2. Check SSH is enabled on device
# On FortiGate:
config system interface
    edit port1
        set allowaccess ping ssh https
    next
end

# 3. Verify credentials in env file
[FGT_A]
    CONNECTION: 192.168.1.99 22  # Correct IP and port?
    USERNAME: admin               # Correct username?
    PASSWORD: fortinet           # Correct password?
```

#### Issue 2: Pattern Not Matching

**Error**: `TC_001: FAIL - Pattern not found`

**Solutions**:
```plaintext
# 1. Clear buffer before expecting
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_001 -clear yes

# 2. Increase timeout
expect -e "Pattern" -for TC_001 -t 30  # Wait 30 seconds

# 3. Check regex escaping
# Wrong: expect -e "CPU: 5%" -for TC_001
# Correct: escape the %
expect -e "CPU: 5\\%" -for TC_001

# 4. Use debug mode to see actual output
python3 autotest.py -e env.conf -t test.txt -d
# Check logs/autotest.log for actual device output
```

#### Issue 3: Variable Not Interpolating

**Error**: Variable shows as `$varname` instead of value

**Solutions**:
```plaintext
# Variables work in device commands
[FGT_A]
    <strset hostname FGT-TEST>
    config system global
        set hostname $hostname  # ✅ Works
    end

# Variables work in API parameters
expect -e "$hostname" -for TC_001  # ✅ Works

# But NOT in comment colons
# Wrong: comment: Hostname is $hostname
# Correct:
comment Hostname is $hostname  # Without colon
```

#### Issue 4: Syntax Errors

**Error**: `Compilation failed: Invalid syntax at line 45`

**Solutions**:
```bash
# 1. Use syntax check mode
python3 autotest.py -e env.conf -t test.txt -c

# 2. Common syntax errors:
# - Missing <fi> after <if>
# - Missing <endwhile> after <while>
# - Unclosed quotes in strings
# - Wrong parameter names in APIs

# 3. Check DSL_USAGE_GUIDE.md for correct syntax
```

#### Issue 5: Test Hangs

**Problem**: Test doesn't complete, appears frozen

**Solutions**:
```plaintext
# 1. Add timeouts to all expects
expect -e "pattern" -for TC_001 -t 10  # Always specify -t

# 2. Avoid infinite loops
<intset counter 0>
<while $counter < 100>  # Add upper limit
    # ... test logic ...
    <intchange counter + 1>  # Don't forget to increment
<endwhile $counter > 99>

# 3. Use Ctrl+C to interrupt and check logs
# Terminal logs show where execution stopped
```

#### Issue 6: Can't Find Output

**Problem**: Don't know where test results are saved

**Solutions**:
```bash
# Results are always in outputs/YYYY-MM-DD/
cd outputs/

# Find latest results
ls -lt | head -5

# Or search by name
find outputs/ -name "*my_test*" -type d

# Open HTML summary
firefox outputs/$(date +%Y-%m-%d)/*/summary/summary.html
```

### Getting Help

#### 1. Check Logs

```bash
# Framework logs
cat outputs/YYYY-MM-DD/HH-MM-SS--*/logs/autotest.log

# Device terminal logs
cat outputs/YYYY-MM-DD/HH-MM-SS--*/terminal/FGT_A.log
```

#### 2. Enable Debug Mode

```bash
python3 autotest.py -e env.conf -t test.txt -d
```

Debug mode shows:
- Detailed connection attempts
- All commands sent to devices  
- All device responses
- Variable values
- Compilation steps

#### 3. Use Breakpoints

```plaintext
[FGT_A]
    get system status
    breakpoint  # Stop here for inspection
    # Variables and state can be examined
```

#### 4. Consult Documentation

- **DSL Syntax**: Read `docs/DSL_USAGE_GUIDE.md`
- **API Reference**: Run `python3 autotest.py api_docs`
- **Examples**: Check `testcase/` directory for working examples

---

## Summary

### What You Learned

✅ **AutoLib automates everything**: Connections, commands, validations, logging  
✅ **Three key files**: Environment (.env), Test Script (.txt), Test Group (.full)  
✅ **Simple workflow**: Write DSL → Run autotest.py → View results  
✅ **Test organization**: Group related tests, use clear naming conventions  
✅ **Best practices**: Comment tests, handle errors, use version control  

### Next Steps

1. **Try the quick start example** - Create your first test
2. **Study the DSL guide** - Learn all available APIs and syntax
3. **Review existing tests** - Look at testcase/ for real examples
4. **Create your first test suite** - Organize tests into groups
5. **Integrate with CI/CD** - Automate test execution

### Quick Reference

```bash
# Run single test
python3 autotest.py -e env.env -t test.txt

# Run test group
python3 autotest.py -e env.env -g grp.full

# Debug mode
python3 autotest.py -e env.env -t test.txt -d

# Syntax check
python3 autotest.py -e env.env -t test.txt -c

# Check API docs
python3 autotest.py api_docs -a expect

# View results
firefox outputs/$(date +%Y-%m-%d)/*/summary/summary.html
```

---

**Happy Testing! 🚀**

For more details, see:
- [DSL Usage Guide](DSL_USAGE_GUIDE.md) - Complete DSL syntax reference
- [README.md](../README.md) - Framework architecture and development

**Document Version**: 1.0  
**Last Updated**: February 13, 2026  
**AutoLib Version**: V3R10+
