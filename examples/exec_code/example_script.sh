#!/bin/bash

################################################################################
# Example Bash script demonstrating exec_code API context usage
#
# ENVIRONMENT VARIABLE SAFETY:
#   ✓ Environment variables are injected into THIS SCRIPT ONLY
#   ✓ Does NOT affect parent Python process or system-wide environment
#   ✓ Does NOT affect other exec_code calls or user shell
#   ✓ Variables only exist during this script's execution
#
# Available Context (as environment variables):
#   ✓ Runtime variables → $VAR_NAME (uppercase)
#   ✓ Config values → $SECTION__OPTION (uppercase, double underscore)
#   ✓ Last device output → $LAST_OUTPUT
#   ✓ Workspace path → $WORKSPACE
#   ✓ Current device → $CURRENT_DEVICE_NAME
#   ✓ All devices → $DEVICE_NAMES (comma-separated)
#
# NOT Available in Bash (use Python for these):
#   ✗ device object (no methods like send(), expect())
#   ✗ logger object (cannot call logger.info(), etc.)
#   ✗ get_variable() / set_variable() functions
#
# For full object access and advanced features, use Python instead!
#
# Usage examples:
#     exec_code -lang bash -var result -file "examples/exec_code/example_script.sh"
################################################################################


################################################################################
# CONTEXT DEMONSTRATION: Runtime Variables
################################################################################
# All variables set in your test script are available as environment variables
# They are automatically converted to UPPERCASE
#
# Example test script:
#   <strset device_name FGT-100E>
#   <intset port_number 8443>
#   <strset status success>
#   exec_code -lang bash -var result -file "examples/exec_code/example_script.sh"
#
# In this Bash script, you can access:
#   $DEVICE_NAME (from device_name)
#   $PORT_NUMBER (from port_number)
#   $STATUS (from status)
################################################################################

# Example 1: Access runtime variables with defaults
DEVICE="${DEVICE_NAME:-unknown_device}"
PORT="${PORT_NUMBER:-443}"
STATUS="${STATUS:-pending}"

echo "=== Runtime Variables from Context ==="
echo "Device: $DEVICE"
echo "Port: $PORT"
echo "Status: $STATUS"


################################################################################
# CONTEXT DEMONSTRATION: Config Variables
################################################################################
# Config values from your env file are available as SECTION__OPTION (uppercase)
#
# Example config file (env.yaml):
#   [device1]
#   ip = 192.168.1.100
#   port = 22
#   username = admin
#
#   [device2]
#   ip = 192.168.1.200
#   port = 8443
#
# In this Bash script, you can access:
#   $DEVICE1__IP (from [device1] ip)
#   $DEVICE1__PORT (from [device1] port)
#   $DEVICE1__USERNAME (from [device1] username)
#   $DEVICE2__IP (from [device2] ip)
#   $DEVICE2__PORT (from [device2] port)
################################################################################

# Example 2: Access config variables
echo ""
echo "=== Config Variables from Context ==="

# Check if config variables are available
if [ -n "$DEVICE1__IP" ]; then
    echo "Device1 IP: $DEVICE1__IP"
    echo "Device1 Port: ${DEVICE1__PORT:-22}"
    echo "Device1 Username: ${DEVICE1__USERNAME:-admin}"
else
    echo "Device1 config not available"
fi

if [ -n "$DEVICE2__IP" ]; then
    echo "Device2 IP: $DEVICE2__IP"
    echo "Device2 Port: ${DEVICE2__PORT:-8443}"
else
    echo "Device2 config not available"
fi


################################################################################
# CONTEXT DEMONSTRATION: Last Device Output
################################################################################
# The last command output from the device is available as $LAST_OUTPUT
# This is the same as context['last_output'] in Python
#
# Example test script:
#   dev $device1
#   cmd show system interface
#   expect -p "port1" -for 801840
#   exec_code -lang bash -var result -file "examples/exec_code/example_script.sh"
################################################################################

# Example showing last_output access
echo ""
echo "=== Last Device Output from Context ==="

if [ -n "$LAST_OUTPUT" ]; then
    # Count lines in output
    LINE_COUNT=$(echo "$LAST_OUTPUT" | wc -l)
    CHAR_COUNT=$(echo "$LAST_OUTPUT" | wc -c)

    echo "Last output available: $CHAR_COUNT characters, $LINE_COUNT lines"

    # Show first line
    FIRST_LINE=$(echo "$LAST_OUTPUT" | head -1)
    echo "First line: $FIRST_LINE"

    # Check for patterns
    if echo "$LAST_OUTPUT" | grep -q "port1"; then
        echo "Output contains 'port1'"
    fi

    if echo "$LAST_OUTPUT" | grep -qi "error"; then
        echo "WARNING: Output contains 'error'"
    fi
else
    echo "No device output available (run device command first)"
fi


################################################################################
# CONTEXT DEMONSTRATION: Workspace Path
################################################################################
# The workspace directory path is available as $WORKSPACE
# Use this for file operations relative to workspace
################################################################################

echo ""
echo "=== Workspace Path from Context ==="

if [ -n "$WORKSPACE" ]; then
    echo "Workspace: $WORKSPACE"

    # Check if workspace exists
    if [ -d "$WORKSPACE" ]; then
        echo "Workspace directory exists"

        # List some directories
        for dir in lib examples testcase plugins; do
            if [ -d "$WORKSPACE/$dir" ]; then
                echo "  - Found: $dir/"
            fi
        done
    fi

    # Example: Access a file in workspace
    EXAMPLE_FILE="$WORKSPACE/examples/exec_code/example_script.sh"
    if [ -f "$EXAMPLE_FILE" ]; then
        LINES=$(wc -l < "$EXAMPLE_FILE")
        echo "This script has $LINES lines"
    fi
else
    echo "Workspace path not available"
fi


################################################################################
# CONTEXT DEMONSTRATION: Current Device Name
################################################################################
# The current device name is available as $CURRENT_DEVICE_NAME
# This is the device that is currently active in the test script
################################################################################

echo ""
echo "=== Current Device Name from Context ==="

if [ -n "$CURRENT_DEVICE_NAME" ]; then
    echo "Current device: $CURRENT_DEVICE_NAME"

    # You could use this to make device-specific decisions
    case "$CURRENT_DEVICE_NAME" in
        device1)
            echo "Working with primary device"
            ;;
        device2)
            echo "Working with secondary device"
            ;;
        *)
            echo "Working with device: $CURRENT_DEVICE_NAME"
            ;;
    esac
else
    echo "Current device name not available"
fi


################################################################################
# CONTEXT DEMONSTRATION: All Device Names
################################################################################
# All configured device names are available as $DEVICE_NAMES (comma-separated)
# Parse into array for iteration
################################################################################

echo ""
echo "=== All Device Names from Context ==="

if [ -n "$DEVICE_NAMES" ]; then
    # Convert comma-separated string to array
    IFS=',' read -ra DEVICES_ARRAY <<< "$DEVICE_NAMES"

    echo "Found ${#DEVICES_ARRAY[@]} device(s): $DEVICE_NAMES"

    # Iterate over devices
    for device in "${DEVICES_ARRAY[@]}"; do
        echo "  - Device: $device"

        # Access config for each device (if available)
        # Build variable name: DEVICE1__IP, DEVICE2__IP, etc.
        device_upper="${device^^}"  # Convert to uppercase
        ip_var="${device_upper}__IP"

        # Use indirect expansion to get the value
        ip_value="${!ip_var}"
        if [ -n "$ip_value" ]; then
            echo "    IP: $ip_value"
        fi
    done
else
    echo "Device names not available"
fi


################################################################################
# PRACTICAL EXAMPLE 1: Using runtime variables for conditional logic
################################################################################

# Example 3: Conditional execution based on variable
echo ""
echo "=== Conditional Logic Example ==="

if [ "$STATUS" = "success" ]; then
    echo "Test passed - proceeding with cleanup"
    RESULT="cleanup_completed"
elif [ "$STATUS" = "failure" ]; then
    echo "Test failed - generating error report"
    RESULT="error_report_generated"
else
    echo "Test status unknown - skipping"
    RESULT="skipped"
fi

echo "Result: $RESULT"


################################################################################
# PRACTICAL EXAMPLE 2: Build connection strings from config
################################################################################

# Example 4: Construct URLs/connection strings from config variables
echo ""
echo "=== Connection String Example ==="

if [ -n "$DEVICE1__IP" ]; then
    CONNECTION_URL="https://${DEVICE1__IP}:${DEVICE1__PORT:-443}/api"
    echo "Connection URL: $CONNECTION_URL"

    # You could use this in curl or other tools
    # curl -k "$CONNECTION_URL/status"
fi


################################################################################
# PRACTICAL EXAMPLE 3: Process variables with string operations
################################################################################

# Example 5: String manipulation on context variables
echo ""
echo "=== String Processing Example ==="

# Get hostname variable (if set in test script)
HOSTNAME="${HOSTNAME:-FGT-Branch-01}"

# Convert to uppercase
HOSTNAME_UPPER="${HOSTNAME^^}"

# Convert to lowercase
HOSTNAME_LOWER="${HOSTNAME,,}"

# Extract parts
HOSTNAME_PREFIX="${HOSTNAME%%-*}"  # Get part before first dash

echo "Original: $HOSTNAME"
echo "Uppercase: $HOSTNAME_UPPER"
echo "Lowercase: $HOSTNAME_LOWER"
echo "Prefix: $HOSTNAME_PREFIX"


################################################################################
# PRACTICAL EXAMPLE 4: Perform calculations with integer variables
################################################################################

# Example 6: Arithmetic with variables from context
echo ""
echo "=== Arithmetic Example ==="

# Variables set in test script with <intset>
COUNTER="${COUNTER:-0}"
INCREMENT="${INCREMENT:-1}"
MULTIPLIER="${MULTIPLIER:-2}"

NEW_COUNTER=$((COUNTER + INCREMENT))
RESULT_VALUE=$((NEW_COUNTER * MULTIPLIER))

echo "Counter: $COUNTER"
echo "After increment (+$INCREMENT): $NEW_COUNTER"
echo "After multiply (x$MULTIPLIER): $RESULT_VALUE"


################################################################################
# PRACTICAL EXAMPLE 5: List processing
################################################################################

# Example 7: Work with list variables
echo ""
echo "=== List Processing Example ==="

# If you set a list variable: <listset IP_LIST 192.168.1.1,192.168.1.2,192.168.1.3>
# It comes as a comma-separated string
IP_LIST="${IP_LIST:-10.0.0.1,10.0.0.2,10.0.0.3}"

# Convert to array
IFS=',' read -ra IPS <<< "$IP_LIST"

echo "Processing ${#IPS[@]} IP addresses:"
for ip in "${IPS[@]}"; do
    echo "  - $ip"
done

# Get first and last
FIRST_IP="${IPS[0]}"
LAST_IP="${IPS[-1]}"
echo "First IP: $FIRST_IP"
echo "Last IP: $LAST_IP"


################################################################################
# PRACTICAL EXAMPLE 6: Build test data from variables
################################################################################

# Example 8: Create JSON output using context variables
echo ""
echo "=== JSON Output Example ==="

# Build JSON from variables
TEST_ID="${QAID:-000000}"
TEST_NAME="${TEST_NAME:-example_test}"
BUILD="${BUILD_NUMBER:-1234}"

cat << EOF
{
  "test_id": "$TEST_ID",
  "test_name": "$TEST_NAME",
  "build": "$BUILD",
  "device": "$DEVICE",
  "status": "$STATUS",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF


################################################################################
# PRACTICAL EXAMPLE 7: Validate variables
################################################################################

# Example 9: Variable validation
echo ""
echo "=== Variable Validation Example ==="

# Check if required variables are set
MISSING_VARS=()

if [ -z "$DEVICE1__IP" ]; then
    MISSING_VARS+=("DEVICE1__IP")
fi

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    echo "All required variables are set"
else
    echo "Missing variables: ${MISSING_VARS[*]}"
fi


################################################################################
# PRACTICAL EXAMPLE 8: File path operations using variables
################################################################################

# Example 10: Work with file paths from variables
echo ""
echo "=== File Path Example ==="

# Workspace directory path (if available in environment)
WORKSPACE="${WORKSPACE:-/tmp}"
LOG_FILE="${LOG_FILE:-test.log}"

FULL_PATH="$WORKSPACE/$LOG_FILE"
echo "Log file path: $FULL_PATH"

# Check if file exists
if [ -f "$FULL_PATH" ]; then
    LINES=$(wc -l < "$FULL_PATH")
    echo "Log file has $LINES lines"
else
    echo "Log file does not exist (this is expected for demo)"
fi


################################################################################
# PRACTICAL EXAMPLE 9: Multi-variable processing
################################################################################

# Example 11: Process multiple related variables
echo ""
echo "=== Multi-Variable Processing Example ==="

# Variables for network configuration
INTERFACE="${INTERFACE:-port1}"
IP_ADDR="${IP_ADDR:-192.168.1.1}"
NETMASK="${NETMASK:-255.255.255.0}"
GATEWAY="${GATEWAY:-192.168.1.254}"

# Calculate network info
IFS='.' read -ra IP_PARTS <<< "$IP_ADDR"
FIRST_OCTET="${IP_PARTS[0]}"

if [ "$FIRST_OCTET" -ge 1 ] && [ "$FIRST_OCTET" -le 127 ]; then
    CLASS="A"
elif [ "$FIRST_OCTET" -ge 128 ] && [ "$FIRST_OCTET" -le 191 ]; then
    CLASS="B"
else
    CLASS="C"
fi

echo "Interface: $INTERFACE"
echo "IP Address: $IP_ADDR"
echo "Netmask: $NETMASK"
echo "Gateway: $GATEWAY"
echo "Network Class: $CLASS"


################################################################################
# PRACTICAL EXAMPLE 10: Return formatted summary
################################################################################

# Example 12: Create formatted output summary
echo ""
echo "=== Test Summary ==="
cat << SUMMARY
╔════════════════════════════════════════════════════════════╗
║                      TEST EXECUTION SUMMARY                ║
╠════════════════════════════════════════════════════════════╣
║ Test ID:     ${TEST_ID:-N/A}
║ Device:      ${DEVICE:-N/A}
║ Status:      ${STATUS:-N/A}
║ Port:        ${PORT:-N/A}
║ Build:       ${BUILD_NUMBER:-N/A}
╚════════════════════════════════════════════════════════════╝
SUMMARY


################################################################################
# IMPORTANT NOTES ABOUT BASH CONTEXT
################################################################################
#
# ENVIRONMENT VARIABLE SAFETY:
#   ✓ All environment variables are SUBPROCESS-ONLY
#   ✓ Does NOT modify parent Python process or system environment
#   ✓ Does NOT affect other exec_code calls
#   ✓ Safe to add/modify variables - they only exist during this script
#
# What IS available in Bash (as environment variables):
#   ✓ Runtime variables → $VAR_NAME (uppercase)
#   ✓ Config values → $SECTION__OPTION (uppercase, double underscore)
#   ✓ Last device output → $LAST_OUTPUT
#   ✓ Workspace path → $WORKSPACE
#   ✓ Current device name → $CURRENT_DEVICE_NAME
#   ✓ All device names → $DEVICE_NAMES (comma-separated)
#   ✓ Standard Bash capabilities (calculations, string ops, file ops, etc.)
#
# What is NOT available in Bash:
#   ✗ device object (cannot call device.send(), device.expect(), etc.)
#   ✗ devices dict (cannot access device objects, only names)
#   ✗ logger object (cannot call logger.info(), logger.debug(), etc.)
#   ✗ get_variable() function (variables are already in environment)
#   ✗ set_variable() function (cannot set variables back to context)
#
# When to use Bash vs Python:
#   - Use Bash for: Simple parsing, string manipulation, calculations,
#                   calling external tools, file operations, device output grep
#   - Use Python for: Complex parsing, accessing device objects, calling device methods,
#                     setting variables, using logger, object-oriented operations
#
################################################################################


################################################################################
# PRACTICAL EXAMPLE: Parse device output from $LAST_OUTPUT
################################################################################

# Example 14: Extract IP addresses from device output
echo ""
echo "=== Parsing Device Output Example ==="

if [ -n "$LAST_OUTPUT" ]; then
    # Extract all IP addresses
    IPS=$(echo "$LAST_OUTPUT" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b')

    if [ -n "$IPS" ]; then
        IP_COUNT=$(echo "$IPS" | wc -l)
        echo "Found $IP_COUNT IP address(es) in device output:"
        echo "$IPS" | head -5
    else
        echo "No IP addresses found in device output"
    fi

    # Search for specific patterns
    if echo "$LAST_OUTPUT" | grep -q "interface"; then
        echo "Device output contains interface information"
    fi

    # Extract lines containing "status"
    STATUS_LINES=$(echo "$LAST_OUTPUT" | grep -i "status" | head -3)
    if [ -n "$STATUS_LINES" ]; then
        echo "Status lines found:"
        echo "$STATUS_LINES"
    fi
else
    echo "No device output available to parse"
fi


################################################################################
# PRACTICAL EXAMPLE: Use workspace for file operations
################################################################################

# Example 15: Read/write files in workspace
echo ""
echo "=== Workspace File Operations Example ==="

if [ -n "$WORKSPACE" ]; then
    # Create a temporary data file in workspace
    DATA_FILE="$WORKSPACE/test_data_$$.txt"

    # Write some data
    echo "Test data from Bash script" > "$DATA_FILE"
    echo "Device: ${CURRENT_DEVICE_NAME:-unknown}" >> "$DATA_FILE"
    echo "Timestamp: $(date)" >> "$DATA_FILE"

    if [ -f "$DATA_FILE" ]; then
        echo "Created data file: $DATA_FILE"
        CONTENT=$(cat "$DATA_FILE")
        echo "Content:"
        echo "$CONTENT"

        # Clean up
        rm -f "$DATA_FILE"
        echo "Cleaned up temporary file"
    fi
else
    echo "Workspace not available"
fi


################################################################################
# PRACTICAL EXAMPLE: Multi-device operations
################################################################################

# Example 16: Process all devices
echo ""
echo "=== Multi-Device Processing Example ==="

if [ -n "$DEVICE_NAMES" ]; then
    IFS=',' read -ra ALL_DEVICES <<< "$DEVICE_NAMES"

    echo "Processing ${#ALL_DEVICES[@]} device(s)..."

    for device in "${ALL_DEVICES[@]}"; do
        device_upper="${device^^}"

        # Check if this is the current device
        if [ "$device" = "$CURRENT_DEVICE_NAME" ]; then
            echo "  ★ $device (CURRENT)"
        else
            echo "  - $device"
        fi

        # Get device config if available
        ip_var="${device_upper}__IP"
        port_var="${device_upper}__PORT"

        ip="${!ip_var}"
        port="${!port_var}"

        if [ -n "$ip" ]; then
            echo "    Config: $ip:${port:-443}"
        fi
    done
else
    echo "No devices configured"
fi


################################################################################
# DEMONSTRATION: Show all available environment variables
################################################################################

# Example 17: List all available context variables (useful for debugging)
echo ""
echo "=== Available Context Variables (non-system) ==="

# Show key context variables
echo "Runtime variables and context:"
for var in LAST_OUTPUT WORKSPACE CURRENT_DEVICE_NAME DEVICE_NAMES; do
    value="${!var}"
    if [ -n "$value" ]; then
        # Truncate long values
        display_value="${value:0:50}"
        if [ ${#value} -gt 50 ]; then
            display_value="$display_value..."
        fi
        echo "  $var = $display_value"
    fi
done

echo ""
echo "User variables (sample):"
env | grep -E '^[A-Z][A-Z_0-9]*=' | grep -v -E '^(PATH|HOME|USER|SHELL|PWD|OLDPWD|LANG|TERM|SHLVL|_|LAST_OUTPUT|WORKSPACE|CURRENT_DEVICE_NAME|DEVICE_NAMES)=' | head -10


################################################################################
# Default return value
################################################################################

# Final output - this is what gets returned to the test script
echo ""
echo "════════════════════════════════════════════════"
echo "Bash context demonstration completed successfully"
echo "All environment variables are SUBPROCESS-ONLY"
echo "No system-wide environment changes were made"
echo "════════════════════════════════════════════════"
