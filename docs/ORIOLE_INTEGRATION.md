# Oriole Integration Guide

## Overview

Oriole is Fortinet's test result submission system hosted at `releaseqa-imageserver.corp.fortinet.com`. AutoLib v3 automatically collects device information and submits test results to Oriole after test execution.

## Architecture

```
Test Execution → Collect Device Info → Generate Report → Submit to Oriole
     ↓                    ↓                   ↓              ↓
  first_case.txt    get system status    JSON format    HTTPS POST
                    diag autoupdate
```

## Configuration

### Environment File Settings

In your `.env` file, configure the `[ORIOLE]` section:

```ini
[ORIOLE]
# Oriole credentials (required for submission)
USER: ssun
ENCODE_PASSWORD: UW14blFrTXhZMEpCVVZwS1ZteGFVbGhDTVZGQ1VVSlRVMUZWUkVGQlJrcFZiRTVTUVVaU1ZsZG5UbFZWWjFGUA==

# Release tag (optional, defaults to DUT version)
RELEASE: 7.6.5

# Task path template (optional)
TASK_PATH: /FOS/7.6.7/Regression

# Custom result fields (optional)
RES_FIELD_MARK: AutoLib_v3
RES_FIELD_BUILD_TYPE: custom_build
```

### Command Line Options

```bash
# -s: Submission flag
python autotest.py -e env.conf -t test.txt -s all     # Submit all tests
python autotest.py -e env.conf -t test.txt -s success # Submit only passed tests
python autotest.py -e env.conf -t test.txt -s none    # Don't submit

# --task_path: Override Oriole task path
python autotest.py -e env.conf -t test.txt -s all --task_path "/FOS/7.6.7/Regression"

# --non_strict: Allow submission even if some validations fail
python autotest.py -e env.conf -t test.txt -s all --non_strict
```

## How It Works

### 1. **Test Execution Phase**
```
Device Initialization (FGT_A)
    ↓
Execute Test Script
    ↓
Record Test Results (PASSED/FAILED)
```

### 2. **Device Info Collection Phase**
When test completes and Oriole submission is enabled:

```python
# lib/core/executor/executor.py
def report_script_result(self):
    device_require_collect = self.result_manager.get_require_info_collection_devices()
    devices_info = {
        dev: self.__collect_dut_info(dev) for dev in device_require_collect
    }
    self.result_manager.report_script_result(devices_info)
```

**Commands executed on device:**
- `get system status` - System information, platform, serial, version, etc.
- `diag autoupdate versions` - All database versions (AV, IPS, APP, etc.)

**Device Info Collected:**
```python
{
    "platform": "FortiGate-VM64-KVM",
    "Serial-Number": "FGVMULTM25002281",
    "Version": "v8.0.0,build0129,260213 (Interim)",
    "build": "0129",
    "BIOS version": "04000002",
    "Hostname": "FGTA",
    "Operation Mode": "NAT",
    "Virtual domain configuration": "disable",
    "AV Engine": "8.00009",
    "Virus Definitions": "1.00000",
    "Attack Definitions": "6.00741",
    "Application Definitions": "6.00741",
    "IPS Attack Engine": "8.00011",
    # ... many more database versions
}
```

### 3. **Report Generation Phase**
```python
# lib/services/oriole/client.py - OrioleClient.generate_product_report()
```

**Report Structure:**
```json
{
    "total": "1",
    "bios": "04000002",
    "SN": "FGVMULTM25002281",
    "platform": "FortiGate-VM64-KVM",
    "platform_id": "FGT_VM64_KVM",
    "pltgen": "7",
    "build": "0129",
    "avdb": "1.00000",
    "aven": "8.00009",
    "ipsdef": "6.00741",
    "flen": "8.00011",
    "apdb": "6.00741",
    "time": "2026-02-13, 17:51:54",
    "results": [
        {
            "testcase_id": "205817",
            "result": "1",  // 1=PASSED, 2=FAILED
            "mark": "AutoLib_v3"
        }
    ]
}
```

**Field Mapping Logic:**
The system maps device info to Oriole fields using `ORIOLE_FIELD_FOS_SOURCE`:

```python
ORIOLE_FIELD_FOS_SOURCE = {
    "avdb": ["Virus Definitions"],
    "aven": ["AV Engine"],
    "ipsdef": ["Attack Definitions", "Attack Extended Definitions"],
    "flen": ["IPS Attack Engine"],
    "apdb": ["Application Definitions"],
    "platform": ["platform"],
    "SN": ["Serial-Number"],
    "build": ["build"],
    # ... many more mappings
}
```

For each Oriole field, it searches device info for matching keys in priority order.

### 4. **Submission Phase**
```python
# lib/services/oriole/client.py - OrioleClient.send_oriole()
```

**HTTP Request:**
```
POST https://releaseqa-imageserver.corp.fortinet.com/api/oriole
Content-Type: application/x-www-form-urlencoded
Timeout: 600 seconds

Payload:
{
    "user": "ssun",
    "password": "UW14blFrTXhZMEpCVVZwS1ZteGFVbGhDTVZGQ1VVSlRVMUZWUkVGQlJrcFZiRTVT...",
    "report": "<JSON report content>",
    "release_tag": "7.6.5",
    "project": "FOS",  // or "FAP" for FortiAP
    "task_path": "/FOS/7.6.5/Regression"
}
```

**Success Response:**
```
HTTP 200 OK
Body: "Result submit success"
```

## Log Output Explanation

From your log:
```
2026-02-13 17:51:54,923 - root - DEBUG - self.user_env.get(ORIOLE, RELEASE, fallback=None): 7.6.5
```
☝️ Reading release tag from env file (7.6.5)

```
2026-02-13 17:51:55,025 - root - INFO - ** Finished executing script ==> testcase/ips/testcase_nm/first_case.txt
```
☝️ Test execution completed

```
2026-02-13 17:51:55,028 - urllib3.connectionpool - DEBUG - Starting new HTTPS connection (1): releaseqa-imageserver.corp.fortinet.com:443
```
☝️ Initiating connection to Oriole server

```
2026-02-13 17:51:59,885 - urllib3.connectionpool - DEBUG - https://releaseqa-imageserver.corp.fortinet.com:443 "POST /api/oriole HTTP/1.1" 200 21
```
☝️ HTTP POST successful (200 status, 21 bytes response)

```
2026-02-13 17:51:59,887 - root - INFO - Succeeded to report to oriole.
2026-02-13 17:51:59,888 - root - INFO - It takes 4.9 s to submit.
```
☝️ Submission successful, took 4.9 seconds

## Files Created

After test execution, these Oriole-related files are created in the output directory:

```
outputs/2026-02-13/17-51-40--script--first_case/summary/
├── Oriole_report_all.json        # All tests (passed + failed)
├── Oriole_report_succeeded.json  # Only passed tests
└── Oriole_report_none.json       # No submission (-s none)
```

## Code Flow Summary

### Entry Point
```python
# autotest.py → Job.run() → Task.execute()
with Executor(script, devices) as executor:
    executor.run()  # Test execution
# Context manager __exit__ triggers:
executor.report_script_result()
```

### Reporting Chain
```python
# 1. lib/core/executor/executor.py
def report_script_result(self):
    devices_info = {dev: self.__collect_dut_info(dev) for dev in device_require_collect}
    self.result_manager.report_script_result(devices_info)

# 2. lib/services/result_manager.py
def report_script_result_to_oriole(self, collected_device_info):
    for qaid in self.expect_result:
        dut_info = collected_device_info[dev]
        oriole.report(qaid, is_succeeded, dut_info)

# 3. lib/services/oriole/client.py
def report(self, testcase_id, is_passed, device_info):
    product_report = self.generate_product_report(testcase_id, is_passed, device_info)
    self.reports.append(product_report)
    self.dump()  # Save to JSON

# 4. lib/core/scheduler/task.py (after test completion)
if self.args.submit_flag != "None":
    oriole.submit()  # HTTP POST to Oriole server
```

## Key Classes and Modules

### `OrioleClient` (`lib/services/oriole/client.py`)
- Singleton instance: `oriole`
- **Methods:**
  - `set_user_cfg(args)` - Initialize from command args and env
  - `report(testcase_id, is_passed, device_info)` - Add test to report queue
  - `generate_product_report()` - Map device info to Oriole format
  - `gen_plt_info_for_oriole()` - Map database versions
  - `dump()` - Save report to JSON files
  - `send_oriole()` - HTTP POST to server
  - `submit()` - Main submission entry point

### Constants (`lib/services/oriole/meta.py`)
- `ORIOLE_SUBMIT_API_URL` - Oriole endpoint URL
- `ORIOLE_FIELD_FOS_SOURCE` - Device info → Oriole field mapping
- `ORIOLE_REPORT_FIXED_FIELDS` - Default report fields

### Integration Points
- `lib/services/result_manager.py` - Manages test results and calls oriole.report()
- `lib/core/scheduler/job.py` - Calls oriole.set_user_cfg() at job start
- `lib/core/scheduler/task.py` - Calls oriole.submit() after test completion

## Password Encoding

The password in env file is base64 encoded:
```python
import base64
encoded = "UW14blFrTXhZMEpCVVZwS1ZteGFVbGhDTVZGQ1VVSlRVMUZWUkVGQlJrcFZiRTVT..."
decoded = base64.b64decode(encoded).decode('utf-8')
# Use decoded password in API request
```

## Debugging Tips

### View Oriole Report
```bash
# Check generated report
cat outputs/YYYY-MM-DD/HH-MM-SS--script--test_name/summary/Oriole_report_all.json | jq
```

### Test Without Submission
```bash
# Generate report but don't submit
python autotest.py -e env.conf -t test.txt -s none
```

### Enable Debug Logging
```bash
# Use -d flag for debug output
python autotest.py -e env.conf -t test.txt -s all -d
```

### Check Oriole Configuration
```python
from lib.services.oriole import oriole
print(f"User: {oriole.user}")
print(f"Release: {oriole.release_tag}")
print(f"Task Path: {oriole.get_task_path()}")
```

## Common Issues

### 1. KeyError: 'platform'
**Cause:** Device info collection failed, missing platform information  
**Solution:** Ensure `get system status` returns complete output

### 2. Submission Timeout
**Cause:** Network issue or Oriole server slow  
**Solution:** Check network, default timeout is 600 seconds

### 3. Invalid Credentials
**Cause:** Wrong ENCODE_PASSWORD or USER  
**Solution:** Verify credentials in env file [ORIOLE] section

### 4. Missing Release Tag
**Cause:** No RELEASE in env and unable to parse from device version  
**Solution:** Add `RELEASE: X.Y.Z` to [ORIOLE] section

## Advanced Usage

### Custom Result Fields
Add custom metadata to each test result:
```ini
[ORIOLE]
RES_FIELD_BUILD_TYPE: interim
RES_FIELD_TESTER: john_doe
RES_FIELD_ENVIRONMENT: lab3
```

These appear in report as:
```json
{
    "results": [{
        "testcase_id": "205817",
        "result": "1",
        "build_type": "interim",
        "tester": "john_doe",
        "environment": "lab3"
    }]
}
```

### Conditional Submission
Only submit if specific conditions met:
```bash
# Submit only passed tests
python autotest.py -e env.conf -t test.txt -s success

# Submit all results
python autotest.py -e env.conf -t test.txt -s all
```

### Override Task Path
Specify custom Oriole task path:
```bash
python autotest.py -e env.conf -t test.txt \
    -s all \
    --task_path "/FOS/7.6.7/Special_Testing"
```

## Summary

**Oriole integration provides:**
1. ✅ Automatic device info collection
2. ✅ Structured test result reporting
3. ✅ Database version tracking
4. ✅ Centralized result storage
5. ✅ Release-based organization

**Default behavior:**
- Credentials from `[ORIOLE]` section in env file
- Release tag from env or device version
- Task path template: `/FOS/{RELEASE}/Regression`
- Submission controlled by `-s` flag
- Connection to `releaseqa-imageserver.corp.fortinet.com`
- 600-second timeout
- Automatic retry on failure (within timeout)

**Output:**
- JSON reports in `outputs/.../summary/` directory
- Console logs showing submission status
- Summary table showing "Oriole Reported: Yes/No"
