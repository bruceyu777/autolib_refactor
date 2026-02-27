# Device Configuration and DUT Management

## Overview

This guide explains how AutoLib v3 manages device configurations, the DUT (Device Under Test) concept, and common configuration issues.

## Table of Contents

1. [Device Configuration Basics](#device-configuration-basics)
2. [The DUT Field](#the-dut-field)
3. [Single vs Multiple Devices](#single-vs-multiple-devices)
4. [Common Issues and Solutions](#common-issues-and-solutions)
5. [Best Practices](#best-practices)

---

## Device Configuration Basics

### Environment File Structure

Devices are configured in the environment (`.conf`) file using INI-style sections:

```ini
[GLOBAL]
DUT: FGT_A
Platform: FGVM
log_level: 7

[FGT_A]
Platform: FGVM
CONNECTION: ssh admin@10.96.234.41 -p 61022
USERNAME: admin
PASSWORD: admin
Model: FGVM
PORT1: port1
IP_PORT1: 10.1.100.1 255.255.255.0

[FGT_B]
CONNECTION: ssh admin@10.96.234.42 -p 62022
USERNAME: admin
PASSWORD: admin

[PC_01]
CONNECTION: ssh root@10.6.30.11
PASSWORD: Qa123456!
BACKDOOR: eth1
```

### Required Fields

**For FortiGate/FortiVM devices:**
- `CONNECTION` - SSH/Telnet connection string (**REQUIRED**)
- `USERNAME` - Login username
- `PASSWORD` - Login password

**For PC devices:**
- `CONNECTION` - SSH connection string (**REQUIRED**)
- `PASSWORD` - Login password

---

## The DUT Field

### What is DUT?

DUT (Device Under Test) is a **single device** defined in the `[GLOBAL]` section that serves as:

1. **Primary test device** - Default device for test operations
2. **Fallback device** - Used when test script doesn't specify a device
3. **Oriole reporting source** - Device info collected for test result submission

### DUT Syntax

```ini
[GLOBAL]
DUT: FGT_A          ✅ Correct - single device name
DUT: FGT_A, FGT_B   ❌ Wrong - comma-separated not supported
DUT:FGT_A           ✅ Correct - spaces optional
```

### Code Implementation

```python
# lib/services/environment.py
def get_dut(self):
    return self.user_env.get("GLOBAL", "DUT")  # Returns single string
```

The DUT value is:
- **Not parsed** for separators (commas, spaces, etc.)
- **Used as-is** to look up device section
- **Single device only** - no multi-device support

---

## Single vs Multiple Devices

### Single Device Test (Simple)

**Environment file:**
```ini
[GLOBAL]
DUT: FGT_A

[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
USERNAME: admin
PASSWORD: admin
```

**Test script:**
```txt
# No device section needed - DUT is used automatically
get system status
expect "FortiGate"
report 12345
```

### Multiple Device Test (Advanced)

**Environment file:**
```ini
[GLOBAL]
DUT: FGT_A    # Primary device for Oriole reporting

[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
USERNAME: admin
PASSWORD: admin

[FGT_B]
CONNECTION: ssh admin@10.96.234.42 -p 62022
USERNAME: admin
PASSWORD: admin

[PC_01]
CONNECTION: ssh root@10.6.30.11
PASSWORD: Qa123456!
```

**Test script - Explicit device switching:**
```txt
[FGT_A]
    get system status
    setvar -e "Hostname:\s+(\S+)" -to hostname_a
    comment FGT_A hostname: $hostname_a

[FGT_B]
    get system status
    setvar -e "Hostname:\s+(\S+)" -to hostname_b
    comment FGT_B hostname: $hostname_b

[PC_01]
    command ping -c 3 10.96.234.41

[FGT_A]
    comment Back to FGT_A
    report 12345    # Uses FGT_A device info
```

### Device Collection Flow

```
┌─────────────────────────────────────────────────────┐
│  1. Parse Test Script                               │
│     - Find all [DEVICE] sections                    │
│     - Collect device names: {FGT_A, FGT_B, PC_01}   │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│  2. Add DUT from [GLOBAL]                           │
│     - Read DUT: FGT_A                               │
│     - devices = devices ∪ {FGT_A}                   │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│  3. Add FortiAP Controllers (if any)                │
│     - Check CONTROLLER fields                       │
│     - devices = devices ∪ {controller_names}        │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│  4. Initialize All Devices                          │
│     - For each device in set:                       │
│       - Load config from [DEVICE] section           │
│       - Create connection (SSH/Telnet)              │
│       - Login and initialize                        │
└─────────────────────────────────────────────────────┘
```

**Code locations:**
- Device parsing: `lib/core/compiler/parser.py:76`
- Device collection: `lib/core/scheduler/task.py:73-80`
- Device initialization: `lib/core/scheduler/task.py:51-58`

---

## Common Issues and Solutions

### Issue 1: KeyError: 'CONNECTION'

**Error:**
```
KeyError: 'CONNECTION'
File "lib/core/device/forti_vm.py", line 34, in is_serial_connection_used
    "telnet" in self.dev_cfg["CONNECTION"]
```

**Cause:**
Device section referenced in test script or DUT doesn't exist in environment file, or CONNECTION field is missing.

**Example of problem:**
```ini
[GLOBAL]
DUT: FGT_A    ← References FGT_A

# But [FGT_A] section is missing!

[FGT_B]       ← Only FGT_B exists
CONNECTION: ssh admin@10.96.234.41 -p 62022
```

**Solution:**

**Option A - Fix DUT to match existing section:**
```ini
[GLOBAL]
DUT: FGT_B    ← Changed to match existing section
```

**Option B - Add missing device section:**
```ini
[GLOBAL]
DUT: FGT_A

[FGT_A]       ← Add the missing section
CONNECTION: ssh admin@10.96.234.41 -p 61022
USERNAME: admin
PASSWORD: admin
```

**Option C - Remove device reference from test script:**
```txt
# Instead of:
[FGT_A]
    get system status

# Use DUT implicitly (no section):
get system status
```

**Prevention:**

After our fix in `v3r10b0007`, you now get a clear error message:

```
ValueError: Device FGT_A: CONNECTION not defined in environment file. 
Please add [FGT_A] section with CONNECTION field.
```

### Issue 2: Wrong Device Being Used

**Problem:**
Test runs on wrong FortiGate.

**Cause:**
DUT doesn't match test script device sections.

**Check:**
```bash
# Find what test expects
grep -n '^\[FGT' testcase/ips/testcase_nm/first_case.txt
# Output: [FGT_B]

# Find what env provides
grep -n '^DUT:' testcase/ips/testcase_nm/env.fortistack.ips_nm.conf
# Output: DUT: FGT_A

# Find what sections exist
grep -n '^\[FGT' testcase/ips/testcase_nm/env.fortistack.ips_nm.conf
# Output: [FGT_B]
```

**Solution:**
Align DUT with test script and available sections:
```ini
[GLOBAL]
DUT: FGT_B    # Match what test script uses
```

### Issue 3: Device Section Typo

**Problem:**
```
ValueError: Device FTG_A: CONNECTION not defined
```

**Cause:**
Typo in device name: `FTG_A` instead of `FGT_A`

**Solution:**
Check for typos in:
- `[GLOBAL]` DUT field
- Device section names `[FGT_A]`
- Test script device sections `[FGT_A]`

### Issue 4: Commented Out Device Section

**Problem:**
Device exists but is commented out.

**Example:**
```ini
; [FGT_A]
; CONNECTION: ssh admin@10.96.234.41 -p 61022
; USERNAME: admin
; PASSWORD: admin
```

**Solution:**
Uncomment the section by removing `;` prefix:
```ini
[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
USERNAME: admin
PASSWORD: admin
```

### Issue 5: Multiple DUT Values

**Problem:**
Trying to define multiple DUTs:
```ini
[GLOBAL]
DUT: FGT_A, FGT_B    ❌ Doesn't work
```

**Why it fails:**
AutoLib treats `"FGT_A, FGT_B"` as a literal device name, looks for section `[FGT_A, FGT_B]` which doesn't exist.

**Solution:**
Define one DUT, use test script for multiple devices:
```ini
[GLOBAL]
DUT: FGT_A    # Primary device only

[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
...

[FGT_B]
CONNECTION: ssh admin@10.96.234.42 -p 62022
...
```

```txt
# Test script handles multiple devices
[FGT_A]
    command setup

[FGT_B]
    command setup
```

---

## Best Practices

### 1. Always Define CONNECTION First

Put CONNECTION as the first field in device sections for easy visibility:

```ini
[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022  ← First field
USERNAME: admin
PASSWORD: admin
Platform: FGVM
# ... other fields
```

### 2. Use Consistent Naming

Follow naming conventions:
- FortiGate/FortiVM: `FGT_A`, `FGT_B`, `FGT_PRIMARY`, `FGT_SECONDARY`
- FortiAP: `FAP_01`, `FAP_02`
- PC/Linux: `PC_01`, `PC_CLIENT`, `PC_SERVER`

### 3. Document Device Purpose

Add comments above device sections:
```ini
# Primary DUT - FortiGate 500D in Lab 3
[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
...

# Secondary device for HA testing
[FGT_B]
CONNECTION: ssh admin@10.96.234.42 -p 62022
...

# Traffic generator PC
[PC_01]
CONNECTION: ssh root@10.6.30.11
...
```

### 4. Validate Configuration Before Testing

Create a simple validation script:
```bash
#!/bin/bash
# validate_env.sh

ENV_FILE="$1"

# Check DUT exists
DUT=$(grep "^DUT:" "$ENV_FILE" | cut -d: -f2 | xargs)
echo "DUT: $DUT"

# Check if DUT section exists
if grep -q "^\[$DUT\]" "$ENV_FILE"; then
    echo "✓ [$DUT] section found"
else
    echo "✗ [$DUT] section NOT found!"
    exit 1
fi

# Check CONNECTION in DUT section
if sed -n "/^\[$DUT\]/,/^\[/p" "$ENV_FILE" | grep -q "^CONNECTION:"; then
    echo "✓ CONNECTION defined"
else
    echo "✗ CONNECTION NOT defined!"
    exit 1
fi

echo "✓ Configuration valid"
```

Usage:
```bash
bash validate_env.sh testcase/ips/testcase_nm/env.fortistack.ips_nm.conf
```

### 5. Template for New Devices

Keep a template for quick device addition:
```ini
[DEVICE_NAME]
Platform: FGVM
CONNECTION: ssh admin@IP_ADDRESS -p PORT
USERNAME: admin
PASSWORD: admin
Model: FGVM
Burn_Interface: mgmt
PORT1: port1
PORT2: port2
IP_PORT1: 10.1.100.1 255.255.255.0
IP_PORT2: 172.16.200.1 255.255.255.0
TFTP_Server: 172.16.200.55
```

### 6. Multi-Device Test Organization

Organize multi-device tests clearly:
```txt
# ============================================
# Setup Phase - Configure All Devices
# ============================================
[FGT_A]
    comment === Configuring FGT_A ===
    command config system global
    command set hostname FGT_A
    command end

[FGT_B]
    comment === Configuring FGT_B ===
    command config system global
    command set hostname FGT_B
    command end

# ============================================
# Test Phase - Execute Tests
# ============================================
[FGT_A]
    comment === Testing FGT_A ===
    get system status
    expect "Hostname: FGT_A"

[FGT_B]
    comment === Testing FGT_B ===
    get system status
    expect "Hostname: FGT_B"

# ============================================
# Cleanup Phase
# ============================================
[FGT_A]
    command exec factoryreset

[FGT_B]
    command exec factoryreset
```

### 7. Use Variables for Shared Configuration

Define common values in GLOBAL:
```ini
[GLOBAL]
DUT: FGT_A
TFTP_SERVER: 172.16.200.55
SYSLOG_SERVER: 172.16.200.55
ADMIN_PASSWORD: admin

[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
PASSWORD: $ADMIN_PASSWORD
TFTP_Server: $TFTP_SERVER

[FGT_B]
CONNECTION: ssh admin@10.96.234.42 -p 62022
PASSWORD: $ADMIN_PASSWORD
TFTP_Server: $TFTP_SERVER
```

### 8. Comment Out Unused Devices

Keep unused devices commented for future reference:
```ini
[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 61022
USERNAME: admin
PASSWORD: admin

; [FGT_B]
; CONNECTION: ssh admin@10.96.234.42 -p 62022
; USERNAME: admin
; PASSWORD: admin
; # Commented out - not used in this test
```

---

## Architecture Reference

### Device Initialization Sequence

```
1. Job.run()
   ↓
2. Task.setup_devices()
   ↓
3. Task.compose_involved_devices()
   - Parse test script for [DEVICE] sections
   - Add DUT from GLOBAL
   - Add FortiAP controllers
   ↓
4. Task.init_devices()
   - For each device:
     ↓
     4.1 Load config from env file [DEVICE] section
         ↓
     4.2 Determine device class (FortiGate/FortiVM/PC/FortiAP)
         ↓
     4.3 Check CONNECTION field exists → ERROR if missing
         ↓
     4.4 Create connection (SSH/Telnet)
         ↓
     4.5 Login with USERNAME/PASSWORD
         ↓
     4.6 Initialize session
```

### Key Code Locations

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| DUT getter | `lib/services/environment.py` | 272-273 | Return DUT from GLOBAL |
| Device collection | `lib/core/scheduler/task.py` | 73-80 | Collect all devices |
| Device parsing | `lib/core/compiler/parser.py` | 74-76 | Parse [DEVICE] sections |
| Device init | `lib/core/scheduler/task.py` | 51-58 | Initialize connections |
| CONNECTION check | `lib/core/device/forti_vm.py` | 30-38 | Validate CONNECTION exists |
| CONNECTION check | `lib/core/device/fos_dev.py` | 50-58 | Validate CONNECTION exists |

---

## Debugging Tips

### 1. Enable Debug Logging

Run with `-d` flag to see device initialization:
```bash
python autotest.py -e env.conf -t test.txt -s none -d 2>&1 | grep -A 5 "Devices used"
```

Output:
```
Devices used during the test ['FGT_A', 'FGT_B']
Start connecting to device FGT_A.
Succeeded to connect to device FGT_A.
Start connecting to device FGT_B.
Succeeded to connect to device FGT_B.
```

### 2. Check Device Sections

List all device sections in env file:
```bash
grep -n '^\[.*\]' env.conf
```

### 3. Verify CONNECTION Fields

Check each device has CONNECTION:
```bash
for dev in FGT_A FGT_B; do
    echo "=== $dev ==="
    sed -n "/^\[$dev\]/,/^\[/p" env.conf | grep "CONNECTION"
done
```

### 4. Test Connection Manually

Before running AutoLib, test SSH connection:
```bash
# Extract connection from env file
CONNECTION=$(grep "^CONNECTION:" env.conf | head -1 | cut -d: -f2- | xargs)

# Test it
eval "$CONNECTION"
```

### 5. Minimal Test Case

Create minimal test to isolate issue:
```txt
# minimal_test.txt
[FGT_A]
    get system status
    comment Test passed
```

Run:
```bash
python autotest.py -e env.conf -t minimal_test.txt -s none
```

---

## Summary

### Key Takeaways

✅ **DUT is single device only** - no comma-separated support  
✅ **CONNECTION field is mandatory** - must exist in every device section  
✅ **Test script drives device usage** - explicitly specify [DEVICE] sections  
✅ **Device names must match** - between DUT, env sections, and test script  
✅ **Clear error messages** - after v3r10b0007 fix, missing CONNECTION shows helpful error  

### Quick Checklist

Before running tests, verify:

- [ ] DUT value matches an existing `[DEVICE]` section
- [ ] Every device section has `CONNECTION` field
- [ ] CONNECTION syntax is correct (ssh/telnet + credentials)
- [ ] Test script device sections match env file sections
- [ ] No typos in device names
- [ ] Required sections are not commented out

### Getting Help

If device configuration issues persist:

1. Check this document for similar issues
2. Run with `-d` debug flag for detailed logs
3. Verify environment file syntax with validation script
4. Test SSH/Telnet connection manually
5. Create minimal test case to isolate problem

For additional support, refer to:
- [GETTING_STARTED.md](GETTING_STARTED.md) - Basic usage guide
- [DSL_USAGE_GUIDE.md](DSL_USAGE_GUIDE.md) - Test script syntax
- [TROUBLESHOOTING_ORIOLE.md](TROUBLESHOOTING_ORIOLE.md) - Oriole reporting issues
