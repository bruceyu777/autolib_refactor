# Troubleshooting Oriole Reporting Issues

## Issue: KeyError: 'platform' during Oriole reporting

### Symptoms
```
KeyError: 'platform'
  File "/home/fosqa/autolibv3/autolib_v3/lib/core/device/fos_dev.py", line 44, in get_parsed_system_status
    self.model = platform_manager.normalize_platform(system_status["platform"])
```

### Root Causes

1. **Incorrect CONNECTION format in environment file**
2. **System status parsing failure**
3. **Authentication failure during device info collection**

---

## Solutions

### 1. Fix Environment File CONNECTION Format

❌ **Wrong**:
```ini
[FGT_A]
CONNECTION: ssh admin@10.96.234.41 -p 62022
USERNAME: admin
PASSWORD: admin
```

✅ **Correct**:
```ini
[FGT_A]
CONNECTION: 10.96.234.41 62022
USERNAME: admin
PASSWORD: admin
```

**Format**: `CONNECTION: <IP> <PORT>`

---

### 2. Fix Greedy Regex in setvar

❌ **Wrong** (captures multiple lines):
```plaintext
setvar -e "Serial-Number: (.*)" -to serial
```

✅ **Correct** (captures only serial number):
```plaintext
setvar -e "Serial-Number:\\s+(\\S+)" -to serial
```

**Explanation**: 
- `\s+` - Matches one or more whitespace characters
- `\S+` - Matches non-whitespace characters only (stops at newline)

---

### 3. Disable Oriole Reporting (Workaround)

If you don't need Oriole integration, comment out or remove the `[ORIOLE]` section:

```ini
; [ORIOLE]
; USER: ssun
; ENCODE_PASSWORD: ...
; RELEASE: 7.6.5
; RES_FIELD_MARK: Fortistack_Autolib_v3
```

Or use the `-s none` flag to disable submission:

```bash
python3 autotest.py \
  -e env.fortistack.ips_nm.conf \
  -t first_case.txt \
  -s none
```

---

### 4. Ensure Device Connectivity

The error shows authentication failure during reconnection:
```
admin@10.96.234.41's password: get system status
Permission denied, please try again.
```

**Check**:
1. ✅ Device is reachable: `ping 10.96.234.41`
2. ✅ SSH port is open: `telnet 10.96.234.41 62022`
3. ✅ Credentials are correct: `ssh admin@10.96.234.41 -p 62022`
4. ✅ Device allows SSH access:
   ```
   config system interface
       edit mgmt
           set allowaccess ping ssh https
       next
   end
   ```

---

## Testing After Fixes

### Test 1: Without Oriole
```bash
python3 autotest.py \
  -e testcase/ips/testcase_nm/env.fortistack.ips_nm.conf \
  -t testcase/ips/testcase_nm/first_case.txt \
  -s none \
  -d
```

### Test 2: With Oriole (if needed)
```bash
python3 autotest.py \
  -e testcase/ips/testcase_nm/env.fortistack.ips_nm.conf \
  -t testcase/ips/testcase_nm/first_case.txt \
  -s succeeded
```

---

## Expected Output (Success)

```
**** Start test job with AUTOLIB - V3R10B0007. ****
Test Environment: /home/fosqa/autolibv3/autolib_v3/testcase/ips/testcase_nm/env.fortistack.ips_nm.conf
Compiled /home/fosqa/autolibv3/autolib_v3/testcase/ips/testcase_nm/first_case.txt
Start connecting to device FGT_A.
Succeeded to connect to device FGT_A.
** Start executing script ==> first_case.txt
get system status
Succeeded to set variable serial to 'FGVMULTM25002684'
Device serial: FGVMULTM25002684
Test completed successfully

             Testcase Results             
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Oriole QAID ┃ Result ┃ Oriole Reported ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│   TC_001    │  PASS  │      N/A        │
└─────────────┴────────┴─────────────────┘

Test job completed successfully.
```

---

## Common Issues with Oriole

### Issue: "Unable to connect to Oriole"
**Solution**: Check network connectivity to Oriole server

### Issue: "Authentication failed"
**Solution**: Verify ORIOLE USER and ENCODE_PASSWORD in env file

### Issue: "Test not found in Oriole"
**Solution**: Ensure QAID (e.g., TC_001) exists in Oriole system

---

## Prevention

### Best Practices for Environment Files

1. ✅ Use simple CONNECTION format: `IP PORT`
2. ✅ Test SSH connection manually first
3. ✅ Keep USERNAME and PASSWORD separate from CONNECTION
4. ✅ Use debug mode (`-d`) for troubleshooting
5. ✅ Start with `-s none` until test works, then enable Oriole

### Best Practices for Test Scripts

1. ✅ Use specific regex patterns (avoid greedy `.*`)
2. ✅ Always test regex with expected output
3. ✅ Add timeouts to all `expect` statements
4. ✅ Use `comment` (without colon) for variable interpolation
5. ✅ Test locally before enabling Oriole submission

---

## Quick Fix Checklist

- [ ] Fix CONNECTION format: `IP PORT` (not ssh command)
- [ ] Fix greedy regex: Use `\S+` instead of `.*`
- [ ] Remove colon from comment: `comment` not `comment:`
- [ ] Test connection manually: `ssh admin@IP -p PORT`
- [ ] Try with `-s none` first
- [ ] Check logs: `outputs/YYYY-MM-DD/*/logs/autotest.log`

---

## Related Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) - Environment file setup
- [DSL_USAGE_GUIDE.md](DSL_USAGE_GUIDE.md) - Regex patterns and APIs
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick syntax reference
