"""
Example Python script demonstrating exec_code API usage with FULL context access.

################################################################################
#                                                                              #
#   ✅  IMPORT STATEMENTS NOW SUPPORTED (for whitelisted modules) ✅           #
#                                                                              #
#   This code runs in a SANDBOXED environment for security.                   #
#   You can NOW use 'import' for whitelisted modules!                         #
#                                                                              #
#   ✅ BOTH STYLES WORK:                                                       #
#   import re                            # ✅ Now works!                       #
#   result = re.search(...)              # ✅ Works!                          #
#                                                                              #
#   import json                          # ✅ Now works!                       #
#   data = json.loads(...)               # ✅ Works!                          #
#                                                                              #
#   from datetime import datetime        # ✅ Now works!                       #
#   now = datetime.now()                 # ✅ Works!                          #
#                                                                              #
#   Whitelisted modules: re, json, datetime, math                             #
#   Non-whitelisted modules (os, sys, etc.) will raise ImportError            #
#                                                                              #
################################################################################

Python scripts have COMPLETE access to the execution context, unlike Bash scripts.

Available context keys:
    - last_output: str - Most recent device command output
    - device: object - Current device connection object
    - devices: dict - All device connections {name: device_obj}
    - variables: dict - Runtime variables dictionary
    - config: FosConfigParser - Parsed configuration
    - get_variable: function - Get variable value: get_variable(name)
    - set_variable: function - Set variable value: set_variable(name, val)
    - workspace: str - Workspace directory path
    - logger: object - Logger instance

Pre-loaded modules (NO IMPORT NEEDED - use directly):
    - re: Regular expressions
    - json: JSON parsing
    - datetime: Date and time operations
    - math: Mathematical functions

Usage in test script:
    exec_code -lang python -var result -file "examples/exec_code/example_parser.py"
    exec_code -lang python -var parsed_data -file "examples/exec_code/example_parser.py" -func "parse_output"
    exec_code -lang python -var ip_addr -file "examples/exec_code/example_parser.py" -func "extract_ip" -args "'192.168.1.1'"
"""

################################################################################
# ✅  IMPORT STATEMENTS NOW WORK! ✅
#
# You can now use standard Python import statements for whitelisted modules.
# Modules are also PRE-LOADED, so you can use them directly without import.
#
# BOTH APPROACHES WORK:
#
# With import (now supported):    Without import (pre-loaded):
# import re                        pattern = re.search(r'test', text)
# pattern = re.search(...)         data = json.loads(string)
#                                  now = datetime.datetime.now()
# import json                      result = math.sqrt(16)
# data = json.loads(...)
#
# from datetime import datetime
# now = datetime.now()
#
# Whitelisted: re, json, datetime, math
# Non-whitelisted (os, sys, etc.): ImportError with clear message
################################################################################
# pylint: disable=undefined-variable

# Example 1: Simple calculation returning a value
# When executed without -func, the script runs top-to-bottom
# Set __result__ to return a value
#
# NOTE: This top-level code is COMMENTED OUT to prevent conflicts
# when using -func parameter. To use this example, uncomment these lines
# OR create a function wrapper.
#
# simple_calculation = 42 * 2
# __result__ = simple_calculation


# Example 2: Access execution context
# The 'context' dictionary is automatically available and contains:
#   - last_output: Most recent device command output
#   - device: Current device connection
#   - devices: All device connections
#   - variables: Runtime variables
#   - config: Parsed configuration
#   - get_variable(name): Get variable value
#   - set_variable(name, val): Set variable value
#   - workspace: Workspace directory path
#   - logger: Logger instance


def access_context_example():
    """Example showing how to access execution context."""
    # Access last command output from device
    output = context.get("last_output", "")

    # Access variables
    variables = context.get("variables", {})

    # Use logger
    logger = context.get("logger")
    if logger:
        logger.info("Processing device output from context")

    return f"Output length: {len(output)}, Variables count: {len(variables)}"


# Example 3: Parse device output
def parse_output():
    """
    Parse device output from context.

    Returns:
        dict: Parsed data from device output
    """
    # Get the last output from device
    output = context.get("last_output", "")

    # Example: Parse hostname from output
    hostname_match = re.search(r"hostname\s+(\S+)", output)
    hostname = hostname_match.group(1) if hostname_match else "unknown"

    # Example: Parse IP addresses
    ip_pattern = r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"
    ip_addresses = re.findall(ip_pattern, output)

    # Example: Parse interface status
    interface_pattern = r"(\w+\d+)\s+is\s+(up|down)"
    interfaces = re.findall(interface_pattern, output)

    result = {
        "hostname": hostname,
        "ip_addresses": ip_addresses,
        "interfaces": dict(interfaces) if interfaces else {},
        "output_size": len(output),
    }

    # Log the result
    logger = context.get("logger")
    if logger:
        logger.info(f"Parsed result: {result}")

    return result


# Example 4: Function with arguments
def extract_ip(ip_string):
    """
    Extract and validate IP address.

    Args:
        ip_string: String containing IP address

    Returns:
        dict: IP address and validity status
    """
    ip_pattern = r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"
    match = re.search(ip_pattern, ip_string)

    if match:
        ip = match.group(1)
        octets = [int(x) for x in ip.split(".")]
        is_valid = all(0 <= octet <= 255 for octet in octets)

        return {"ip": ip, "valid": is_valid, "octets": octets}

    return {"ip": None, "valid": False, "octets": []}


# Example 5: Using variables from context
def calculate_with_variables():
    """
    Perform calculations using variables from execution context.

    Returns:
        int: Calculated result
    """
    # Get variable using helper function
    get_var = context.get("get_variable")
    set_var = context.get("set_variable")

    # Get values from variables (with defaults)
    count = get_var("count") or 0
    multiplier = get_var("multiplier") or 1

    result = int(count) * int(multiplier)

    # Store intermediate result back to variables
    if set_var:
        set_var("calculation_result", result)

    return result


# Example 6: Complex data processing
def process_device_data():
    """
    Complex example showing data processing from device.

    Returns:
        dict: Processed data
    """

    # Access multiple context items
    output = context.get("last_output", "")
    variables = context.get("variables", {})
    logger = context.get("logger")

    # Process data
    data = {
        "timestamp": variables.get("timestamp", "N/A"),
        "test_id": variables.get("qaid", "N/A"),
        "output_lines": len(output.split("\n")),
        "output_chars": len(output),
        "status": "processed",
    }

    if logger:
        logger.info(f"Processed device data: {json.dumps(data, indent=2)}")

    return data


# Example 7: String manipulation
def format_output(prefix="Result"):
    """
    Format device output with custom prefix.

    Args:
        prefix: Prefix to add to each line

    Returns:
        str: Formatted output
    """
    output = context.get("last_output", "")
    lines = output.split("\n")

    formatted_lines = [f"{prefix}: {line}" for line in lines if line.strip()]

    return "\n".join(formatted_lines)


# Example 8: Return different data types
def return_list_example():
    """Example returning a list."""
    return [1, 2, 3, 4, 5]


def return_dict_example():
    """Example returning a dictionary."""
    return {"key1": "value1", "key2": "value2", "nested": {"a": 1, "b": 2}}


def return_bool_example():
    """Example returning a boolean."""
    output = context.get("last_output", "")
    return "success" in output.lower()


def return_string_example():
    """Example returning a string."""
    return "Operation completed successfully"


# Example 9: Error handling
def safe_parse():
    """
    Example with error handling.

    Returns:
        dict: Result with success status
    """
    try:
        output = context.get("last_output", "")
        pattern = r"Error:\s+(.+)"
        match = re.search(pattern, output)

        if match:
            return {"success": False, "error": match.group(1), "output": output}

        return {"success": True, "error": None, "output": output}

    except Exception as e:
        logger = context.get("logger")
        if logger:
            logger.error(f"Error in safe_parse: {e}")

        return {"success": False, "error": str(e), "output": None}


# Example 10: Working with multiple variables
def batch_variable_processing():
    """
    Process multiple variables at once.

    Returns:
        dict: Processed variables
    """
    get_var = context.get("get_variable")
    set_var = context.get("set_variable")

    # Get multiple variables
    var_names = ["hostname", "ip_address", "port", "status"]
    result = {}

    for var_name in var_names:
        value = get_var(var_name)
        if value:
            result[var_name] = value

    # Set a summary variable
    if set_var:
        set_var("vars_processed", len(result))

    return result


################################################################################
# COMPREHENSIVE CONTEXT DEMONSTRATIONS
# The following examples demonstrate ALL available context keys
################################################################################


# CONTEXT KEY 1: last_output
def demo_last_output():
    """
    Comprehensive example: Access and parse last device output.

    Context key: last_output (str)
    Description: Contains the most recent command output from the device.

    Returns:
        dict: Parsed information from last output
    """
    # Get last output from device
    output = context.get("last_output", "")

    logger = context.get("logger")
    if logger:
        logger.info(f"Processing device output ({len(output)} characters)")
        logger.debug(f"Output preview: {output[:100]}...")

    # Parse various information
    result = {
        "length": len(output),
        "lines": len(output.split("\n")),
        "contains_error": "error" in output.lower() or "fail" in output.lower(),
        "ip_addresses": re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", output),
        "first_line": output.split("\n")[0] if output else "",
    }

    return result


# CONTEXT KEY 2: device
def demo_device():
    """
    Comprehensive example: Access current device object.

    Context key: device (object)
    Description: Current device connection object with methods like send(), expect(), etc.

    Returns:
        dict: Device information and capabilities
    """
    device = context.get("device")
    logger = context.get("logger")

    if not device:
        return {"error": "No device available"}

    # Access device properties
    result = {
        "has_device": True,
        "device_type": type(device).__name__,
    }

    # Access device connection if available
    if hasattr(device, "conn"):
        conn = device.conn
        result["has_connection"] = True
        result["connection_type"] = type(conn).__name__

        # Get output buffer if available
        if hasattr(conn, "output_buffer"):
            output = str(conn.output_buffer)
            result["output_buffer_size"] = len(output)
            result["output_preview"] = output[:50] if output else ""

    # Check for common device methods
    result["available_methods"] = []
    for method in ["send", "expect", "sendline", "close"]:
        if hasattr(device, method):
            result["available_methods"].append(method)

    if logger:
        logger.info(f"Device object inspection: {result}")

    return result


# CONTEXT KEY 3: devices
def demo_devices():
    """
    Comprehensive example: Access all available devices.

    Context key: devices (dict)
    Description: Dictionary of all device connections {device_name: device_obj}

    Returns:
        dict: Information about all devices
    """
    devices = context.get("devices", {})
    logger = context.get("logger")

    result = {
        "device_count": len(devices),
        "device_names": list(devices.keys()),
        "devices_info": {},
    }

    # Inspect each device
    for name, device in devices.items():
        device_info = {
            "type": type(device).__name__,
            "has_connection": hasattr(device, "conn"),
        }

        # Get connection info if available
        if hasattr(device, "conn") and hasattr(device.conn, "output_buffer"):
            output_size = len(str(device.conn.output_buffer))
            device_info["output_buffer_size"] = output_size

        result["devices_info"][name] = device_info

    if logger:
        logger.info(f"Found {len(devices)} device(s): {list(devices.keys())}")

    return result


# CONTEXT KEY 4: variables
def demo_variables():
    """
    Comprehensive example: Access runtime variables dictionary.

    Context key: variables (dict)
    Description: All runtime variables as a dictionary (defaultdict).

    Returns:
        dict: Summary of variables
    """
    variables = context.get("variables", {})
    logger = context.get("logger")

    # Count variables by type
    types_count = {}
    for key, value in variables.items():
        var_type = type(value).__name__
        types_count[var_type] = types_count.get(var_type, 0) + 1

    result = {
        "total_variables": len(variables),
        "variable_names": list(variables.keys())[:20],  # First 20
        "types_distribution": types_count,
        "sample_variables": {},
    }

    # Get a few sample variables
    for i, (key, value) in enumerate(variables.items()):
        if i >= 5:
            break
        result["sample_variables"][key] = {
            "value": str(value)[:50],  # Truncate long values
            "type": type(value).__name__,
        }

    if logger:
        logger.info(f"Variables in context: {len(variables)} total")
        logger.debug(f"Variable names: {list(variables.keys())[:10]}")

    return result


# CONTEXT KEY 5: config
def demo_config():
    """
    Comprehensive example: Access parsed configuration.

    Context key: config (FosConfigParser)
    Description: Parsed configuration file (INI-style) with sections and options.

    Returns:
        dict: Configuration information
    """
    config = context.get("config")
    logger = context.get("logger")

    if not config:
        return {"error": "No config available"}

    result = {"has_config": True, "sections": [], "config_data": {}}

    # Get all sections
    if hasattr(config, "sections"):
        result["sections"] = config.sections()

        # Get all options from each section
        for section in config.sections():
            section_data = {}

            if hasattr(config, "options"):
                for option in config.options(section):
                    try:
                        value = config.get(section, option)
                        section_data[option] = value
                    except Exception as e:
                        section_data[option] = f"Error: {e}"

            result["config_data"][section] = section_data

    if logger:
        logger.info(f"Config sections: {result['sections']}")

    return result


# CONTEXT KEY 6 & 7: get_variable and set_variable
def demo_variable_functions():
    """
    Comprehensive example: Use get_variable and set_variable functions.

    Context keys:
        - get_variable: function - Get variable value by name
        - set_variable: function - Set variable value by name

    Returns:
        dict: Demonstration results
    """
    get_var = context.get("get_variable")
    set_var = context.get("set_variable")
    logger = context.get("logger")

    result = {
        "has_get_variable": callable(get_var),
        "has_set_variable": callable(set_var),
        "operations": [],
    }

    if get_var:
        # Get some common variables
        test_vars = ["hostname", "device_name", "qaid", "status"]
        retrieved = {}

        for var_name in test_vars:
            value = get_var(var_name)
            if value is not None:
                retrieved[var_name] = value
                result["operations"].append(f"Retrieved {var_name}: {value}")

        result["retrieved_variables"] = retrieved

        if logger:
            logger.info(f"Retrieved {len(retrieved)} variables")

    if set_var:
        # Set some new variables
        set_var("demo_timestamp", datetime.datetime.now().isoformat())
        set_var("demo_count", 42)
        set_var("demo_status", "completed")

        result["operations"].append("Set demo_timestamp, demo_count, demo_status")

        if logger:
            logger.info("Set 3 demonstration variables")

    return result


# CONTEXT KEY 8: workspace
def demo_workspace():
    """
    Comprehensive example: Access workspace directory path.

    Context key: workspace (str)
    Description: Path to the workspace directory.

    Note: The 'os' module is not available in the sandboxed environment
    for security reasons. For file operations, use Bash scripts or
    request specific file operations through the framework.

    Returns:
        dict: Workspace information
    """
    workspace = context.get("workspace")
    logger = context.get("logger")

    if not workspace:
        return {"error": "Workspace path not available"}

    result = {
        "workspace_path": workspace,
        "available": True,
        "note": "Use workspace path with Bash scripts for file operations",
    }

    # Example: Build file paths (without os module)
    # You can construct paths manually
    example_paths = {
        "lib_path": f"{workspace}/lib",
        "examples_path": f"{workspace}/examples",
        "testcase_path": f"{workspace}/testcase",
        "config_path": f"{workspace}/config",
    }
    result["example_paths"] = example_paths

    if logger:
        logger.info(f"Workspace: {workspace}")
        logger.debug("For file operations, use Bash scripts via exec_code")

    return result


# CONTEXT KEY 9: logger
def demo_logger():
    """
    Comprehensive example: Use logger for different log levels.

    Context key: logger (object)
    Description: Logger instance with methods: debug(), info(), warning(), error()

    Returns:
        dict: Logger demonstration results
    """
    logger = context.get("logger")

    result = {"has_logger": logger is not None, "logged_messages": []}

    if logger:
        # Check for log methods
        log_methods = ["debug", "info", "warning", "error", "critical"]
        result["available_methods"] = [m for m in log_methods if hasattr(logger, m)]

        # Demonstrate different log levels
        if hasattr(logger, "debug"):
            logger.debug("This is a DEBUG message from demo_logger()")
            result["logged_messages"].append("DEBUG: detailed diagnostic info")

        if hasattr(logger, "info"):
            logger.info("This is an INFO message from demo_logger()")
            result["logged_messages"].append("INFO: general information")

        if hasattr(logger, "warning"):
            logger.warning("This is a WARNING message from demo_logger()")
            result["logged_messages"].append("WARNING: warning about potential issue")

        if hasattr(logger, "error"):
            logger.error("This is an ERROR message from demo_logger()")
            result["logged_messages"].append("ERROR: error condition")

        # Log with formatting
        if hasattr(logger, "info"):
            test_value = 42
            logger.info(f"Formatted log: test_value = {test_value}")
            result["logged_messages"].append("INFO: formatted message with variables")

    return result


# COMPREHENSIVE DEMO: Use ALL context keys
def demo_all_context_keys():
    """
    Comprehensive example: Demonstrate access to ALL context keys in one function.

    This function shows how to safely access and use every available context key.

    Returns:
        dict: Complete context summary
    """
    logger = context.get("logger")

    if logger:
        logger.info("=" * 60)
        logger.info("COMPREHENSIVE CONTEXT DEMONSTRATION")
        logger.info("=" * 60)

    result = {"context_keys_available": list(context.keys()), "demonstrations": {}}

    # 1. last_output
    last_output = context.get("last_output", "")
    result["demonstrations"]["last_output"] = {
        "available": last_output is not None,
        "type": type(last_output).__name__,
        "length": len(last_output) if last_output else 0,
    }
    if logger:
        logger.info(f"1. last_output: {len(last_output)} characters")

    # 2. device
    device = context.get("device")
    result["demonstrations"]["device"] = {
        "available": device is not None,
        "type": type(device).__name__ if device else None,
    }
    if logger:
        logger.info(f"2. device: {'Available' if device else 'Not available'}")

    # 3. devices
    devices = context.get("devices", {})
    result["demonstrations"]["devices"] = {
        "available": True,
        "count": len(devices),
        "names": list(devices.keys()),
    }
    if logger:
        logger.info(f"3. devices: {len(devices)} device(s)")

    # 4. variables
    variables = context.get("variables", {})
    result["demonstrations"]["variables"] = {
        "available": True,
        "count": len(variables),
        "sample_keys": list(variables.keys())[:5],
    }
    if logger:
        logger.info(f"4. variables: {len(variables)} variable(s)")

    # 5. config
    config = context.get("config")
    config_sections = []
    if config and hasattr(config, "sections"):
        config_sections = config.sections()
    result["demonstrations"]["config"] = {
        "available": config is not None,
        "sections": config_sections,
    }
    if logger:
        logger.info(f"5. config: {len(config_sections)} section(s)")

    # 6. get_variable
    get_var = context.get("get_variable")
    result["demonstrations"]["get_variable"] = {
        "available": callable(get_var),
        "is_callable": callable(get_var),
    }
    if logger:
        logger.info(
            f"6. get_variable: {'Callable' if callable(get_var) else 'Not available'}"
        )

    # 7. set_variable
    set_var = context.get("set_variable")
    result["demonstrations"]["set_variable"] = {
        "available": callable(set_var),
        "is_callable": callable(set_var),
    }
    if logger:
        logger.info(
            f"7. set_variable: {'Callable' if callable(set_var) else 'Not available'}"
        )

    # 8. workspace
    workspace = context.get("workspace")
    result["demonstrations"]["workspace"] = {
        "available": workspace is not None,
        "path": workspace,
    }
    if logger:
        logger.info(f"8. workspace: {workspace if workspace else 'Not available'}")

    # 9. logger
    result["demonstrations"]["logger"] = {
        "available": logger is not None,
        "has_info": hasattr(logger, "info") if logger else False,
        "has_debug": hasattr(logger, "debug") if logger else False,
        "has_error": hasattr(logger, "error") if logger else False,
    }
    if logger:
        logging_methods = len(
            [m for m in ["debug", "info", "warning", "error"] if hasattr(logger, m)]
        )
        logger.info(f"9. logger: Available with {logging_methods} methods")
        logger.info("=" * 60)

    return result
