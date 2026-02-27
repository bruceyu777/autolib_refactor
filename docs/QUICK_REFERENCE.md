# AutoLib v3 - Quick Reference

## Command Line

```bash
# Single test
python3 autotest.py -e <env.env> -t <test.txt>

# Test group
python3 autotest.py -e <env.env> -g <grp.full>

# Debug mode
python3 autotest.py -e <env.env> -t <test.txt> -d

# Syntax check only
python3 autotest.py -e <env.env> -t <test.txt> -c

# With web portal
python3 autotest.py -e <env.env> -g <grp.full> --portal

# No Oriole submission
python3 autotest.py -e <env.env> -t <test.txt> -s none
```

## Environment File Template

```ini
[DEVICE_NAME]
    CONNECTION: <IP> <PORT>
    USERNAME: <username>
    PASSWORD: <password>
    MGMT_IP: <mgmt_ip>
    MGMT_MASK: <subnet_mask>

[GLOBAL]
    LICENSE_INFORMATION: /path/to/license.csv
    LOCAL_HTTP_SERVER_IP: <ip>
    LOCAL_HTTP_SERVER_PORT: <port>

[ORIOLE]
    FIELD_MARK: autolib_v3
    USER: <username>
```

## Test Script Template

```plaintext
# Test: <Test Name>
# QAID: <TC_ID>
# Description: <Description>

[DEVICE_NAME]
    # Setup
    comment: ===== Setup Phase =====
    # setup commands...
    
    # Test
    comment: ===== Test Phase =====
    # test commands...
    expect -e "<pattern>" -for <QAID> -t 5
    
    # Cleanup
    comment: ===== Cleanup Phase =====
    # cleanup commands...
    
# Report
report <QAID>
```

## Test Group Template

```plaintext
# Test Group: <Group Name>
# Category: <Critical/Normal>

#-SETUP-
**setup testcase/setup.txt Setup environment

#-TEST CASES-
**TC_001 testcase/test1.txt Description 1
**TC_002 testcase/test2.txt Description 2

#-CLEANUP-
**cleanup testcase/cleanup.txt Restore config
```

## Common APIs

### Expect (Validation)
```plaintext
expect -e "<pattern>" -for <QAID> -t <timeout> -fail <match|unmatch>
expect -e "Version: FortiGate" -for TC_001 -t 5
```

### Variable Extraction
```plaintext
setvar -e "<pattern_with_group>" -to <varname>
setvar -e "Serial-Number: (.*)" -to serial
```

### Variable Check
```plaintext
check_var -name <var> -value <value> -for <QAID>
check_var -name build -value 3645 -for TC_001
```

### Variable Set
```plaintext
<strset varname value>
<intset varname 123>
<listset varname val1,val2,val3>
```

### Compare Variables
```plaintext
compare -v1 <var1> -v2 <var2> -for <QAID> -fail <eq|uneq>
```

### Sleep
```plaintext
sleep <seconds>
sleep 60
```

### Comment
```plaintext
comment: <text>
comment <text with $variables>
```

### Device Control
```plaintext
forcelogin                  # Force re-login
clear_buffer               # Clear output buffer
auto_login <0|1>           # Enable/disable auto-login
```

## Control Structures

### If Statement
```plaintext
<if $var eq value>
    # commands...
<elseif $var eq other>
    # commands...
<else>
    # commands...
<fi>
```

### While Loop
```plaintext
<intset counter 1>
<while $counter < 10>
    # commands...
    <intchange counter + 1>
<endwhile $counter > 9>
```

### Loop/Until
```plaintext
<loop $count < 5>
    # commands...
<until $count eq 5>
```

### Integer Change
```plaintext
<intchange $var + 1>    # Add
<intchange $var - 1>    # Subtract
<intchange $var * 2>    # Multiply
<intchange $var / 2>    # Divide
```

## Comparison Operators

- `eq` - Equal
- `ne` - Not equal  
- `lt` - Less than
- `>` - Greater than
- `<` - Less than

## Device Sections

```plaintext
[FGT_A]
    # Commands for FortiGate A
    get system status

[FGT_B]
    # Commands for FortiGate B
    get system interface

[PC1]
    # Commands for PC
    ping -c 5 192.168.1.1

[FSW1]
    # Commands for FortiSwitch
    get system status
```

## Common Patterns

### Health Check
```plaintext
[FGT_A]
    get system status
    expect -e "Version: FortiGate" -for TC_001 -t 5
    setvar -e "Serial-Number: (.*)" -to serial
    comment: Device serial: $serial
```

### Configuration + Validation
```plaintext
[FGT_A]
    config system global
        set hostname FGT-TEST
    end
    
    get system global | grep hostname
    expect -e "hostname: FGT-TEST" -for TC_001 -t 5
```

### Extract and Validate
```plaintext
[FGT_A]
    get system status
    setvar -e "Version: .*build(\\d+)" -to build
    check_var -name build -pattern "^\\d{4}$" -for TC_001
```

### Retry Logic
```plaintext
[FGT_A]
    get system ha status
    expect -e "HA Health Status: OK" \
        -for TC_HA_001 \
        -t 10 \
        -retry_command "get system ha status" \
        -retry_cnt 5
```

### Multi-Device Test
```plaintext
[FGT_A]
    config system global
        set hostname FGT-PRIMARY
    end
    setvar -e "Hostname: (.*)" -to primary_host

[FGT_B]
    config system global
        set hostname FGT-SECONDARY  
    end

[PC1]
    ping -c 5 192.168.1.99
    expect -e "5 received" -for TC_001 -t 30
```

## Output Locations

```
outputs/
└── YYYY-MM-DD/
    └── HH-MM-SS--type--name/
        ├── summary/
        │   ├── summary.html      ← Open in browser
        │   └── summary.txt
        ├── terminal/
        │   ├── FGT_A.log        ← Device output
        │   ├── FGT_B.log
        │   └── PC1.log
        ├── compiled/
        │   └── *.json
        └── logs/
            └── autotest.log      ← Framework log
```

## Finding Results

```bash
# Latest results
cd outputs/
ls -lt | head -5

# By date
cd outputs/2026-02-13/
ls -lt

# Open HTML summary
firefox outputs/2026-02-13/*/summary/summary.html

# View logs
cat outputs/2026-02-13/*/logs/autotest.log
cat outputs/2026-02-13/*/terminal/FGT_A.log
```

## Debugging

### Enable Debug
```bash
python3 autotest.py -e env.env -t test.txt -d
```

### Add Breakpoint
```plaintext
[FGT_A]
    get system status
    breakpoint  # Execution stops here
    config system global
```

### Syntax Check
```bash
python3 autotest.py -e env.env -t test.txt -c
```

### View Logs
```bash
# Framework log
tail -f outputs/YYYY-MM-DD/HH-MM-SS--*/logs/autotest.log

# Device log
tail -f outputs/YYYY-MM-DD/HH-MM-SS--*/terminal/FGT_A.log
```

## API Documentation

```bash
# List all APIs
python3 autotest.py api_docs

# List categories
python3 autotest.py api_docs --list-categories

# Show specific API
python3 autotest.py api_docs -a expect

# APIs by category
python3 autotest.py api_docs -c expect
```

## Subcommands

### Upgrade AutoLib
```bash
python3 autotest.py upgrade --build 0123
python3 autotest.py upgrade --branch V3R10
```

### Web Server
```bash
python3 autotest.py webserver --action start --port 8080
python3 autotest.py webserver --action stop
```

### Image Service
```bash
# Query image info
python3 autotest.py imageservice -r 7 -b 3645 -q

# Download image
python3 autotest.py imageservice -r 7 -b 3645 -d /tftpboot/
```

## Regex Examples

```plaintext
# Extract serial number
setvar -e "Serial-Number: (.*)" -to serial

# Extract build number
setvar -e "Version: .*build(\\d+)" -to build

# Extract IP address
setvar -e "IP Address: (\\d+\\.\\d+\\.\\d+\\.\\d+)" -to ip

# Extract version
setvar -e "Version: FortiGate.*v(\\d+\\.\\d+\\.\\d+)" -to version

# Multi-line match
setvar -e "(?s)config system global.*?set hostname (.*?)\\n" -to hostname
```

## Common Errors

### Connection Failed
```ini
# Check environment file
[DEVICE]
    CONNECTION: <correct_ip> <correct_port>
    USERNAME: <correct_user>
    PASSWORD: <correct_pass>
```

### Pattern Not Matching
```plaintext
# Add clear buffer
expect -e "pattern" -for TC_001 -clear yes

# Increase timeout
expect -e "pattern" -for TC_001 -t 30

# Escape special chars
expect -e "CPU: 5\\%" -for TC_001
```

### Variable Not Working
```plaintext
# Works: in commands
set hostname $hostname

# Works: in API params
expect -e "$hostname" -for TC_001

# Doesn't work: in comment colons
# Wrong: comment: Value is $hostname
# Right: comment Value is $hostname
```

## File Structure

```
testcase/
├── env/                  # Environment files
│   └── *.env
├── common/               # Shared scripts
│   ├── setup.txt
│   └── cleanup.txt
├── feature1/             # Feature tests
│   ├── grp.feature1.full
│   ├── test1.txt
│   └── test2.txt
└── feature2/
    └── ...
```

## Naming Conventions

### Environment Files
- `env.<scenario>.env`
- `<feature>.env`

### Test Scripts  
- `test_<feature>.txt`
- `<QAID>.txt`

### Test Groups
- `grp.<category>.full`
- `grp.<feature>_<type>.full`

## Version Info

```bash
# Check version
python3 autotest.py --version

# Help
python3 autotest.py --help
python3 autotest.py upgrade --help
python3 autotest.py webserver --help
```

## Tips

1. Always use `-d` for debugging
2. Always add timeouts to `expect`
3. Use `comment` for progress tracking
4. Clear buffer before critical expects
5. Test syntax with `-c` before running
6. Use meaningful QAID names
7. Document your tests
8. Use version control
9. Organize tests in groups
10. Check logs when things fail

---

**Quick Links:**
- Full Guide: [GETTING_STARTED.md](GETTING_STARTED.md)
- DSL Reference: [DSL_USAGE_GUIDE.md](DSL_USAGE_GUIDE.md)
- Framework Docs: [README.md](../README.md)
