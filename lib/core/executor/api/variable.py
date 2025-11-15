"""
Variable API module.

Variable manipulation and comparison APIs.
Module name 'variable' becomes the category name.
"""

# pylint: disable=unused-argument,protected-access

import re

from lib.services import env, logger

from .expect import _normalize_regexp


def setenv(executor, params):
    """
    Set environment variable for a specific device.

    Parameters (accessed via params object):
        params.var_name (str): Variable name
        params.var_val (str): Variable value
        params.device_name (str): Device name
    """
    var_name = params.var_name
    var_val = env.get_var(params.var_val)
    device_name = params.device_name

    env.set_section_var(device_name, var_name, var_val)
    logger.info(
        "Set env variable: device_name:'%s', var_name:'%s', var_val:'%s'",
        device_name,
        var_name,
        var_val,
    )


def setvar(executor, params):
    """
    Set variable from pattern match in device output.

    Parameters (accessed via params object):
        params.rule (str): Regex pattern with capture group
        params.name (str): Variable name to set
    """
    rule = _normalize_regexp(params.rule)
    name = params.name

    logger.info("rule in set_var is %s", rule)
    match, _ = executor.cur_device.expect(rule)
    if match:
        value = match.group(1)
        env.add_var(name, value)
        logger.info("Succeeded to set variable %s to '%s'", name, value)
    else:
        logger.error("Failed to execute setvar.")


def intset(executor, params):
    """
    Set integer variable (keyword implementation).

    This function is called when the <intset> keyword is used in scripts.

    Syntax:
        <intset variable_name number>

    Examples:
        <intset RETRY_COUNT 5>
        <intset MAX_WAIT 300>
        <intset PORT 8080>

    Parameters (accessed via params object):
        params.var_name (str): Variable name (without $ prefix)
        params.var_value (int): Integer value

    Notes:
        - Variable is stored globally and can be accessed with $variable_name
        - Value must be numeric
        - Variable name should not include the $ prefix
    """
    var_name = params.var_name
    var_value = params.var_value
    env.add_var(var_name, var_value)


def strset(executor, params):
    """
    Set string variable (keyword implementation).

    This function is called when the <strset> keyword is used in scripts.

    Syntax:
        <strset variable_name value>

    Examples:
        <strset PLATFORM_TYPE FortiGate-100E>
        <strset BUILD_NUMBER 12345>
        <strset STATUS none>

    Parameters (accessed via params object):
        params.var_name (str): Variable name (without $ prefix)
        params.var_value (str): String value

    Notes:
        - Variable is stored globally and can be accessed with $variable_name
        - Value can be string, number, or identifier
        - Variable name should not include the $ prefix
    """
    var_name = params.var_name
    var_value = params.var_value
    env.add_var(var_name, var_value)


def listset(executor, params):
    """
    Set list variable (keyword implementation).

    This function is called when the <listset> keyword is used in scripts.

    Syntax:
        <listset variable_name value>

    Examples:
        <listset PORTS 80,443,8080>
        <listset DEVICES FGT1,FGT2,FGT3>
        <listset IPS 192.168.1.1,192.168.1.2>

    Parameters (accessed via params object):
        params.var_name (str): Variable name (without $ prefix)
        params.var_value (str): List value (comma-separated or single value)

    Notes:
        - Variable is stored globally and can be accessed with $variable_name
        - Value can be comma-separated items or single value
        - Variable name should not include the $ prefix
    """
    var_name = params.var_name
    var_value = params.var_value
    env.add_var(var_name, var_value)


def intchange(executor, params):
    """
    Modify integer variable using arithmetic expression (keyword implementation).

    This function is called when the <intchange> keyword is used in scripts.

    Syntax:
        <intchange $variable_name operator value>

    Examples:
        <intchange $count + 1>
        <intchange $index - 10>
        <intchange $total * 2>
        <intchange $result / 5>

    Supported operators:
        + (addition)
        - (subtraction)
        * (multiplication)
        / (division)

    Parameters (accessed via params object):
        params.expression_tokens: Variable number of expression tokens
                                  (variable, operator, value)

    Notes:
        - First token must be a variable (with $ prefix)
        - Result is stored back to the variable
        - This API receives variable-length parameters as a tuple
    """
    # For variable-length expressions, we get the raw data
    # This API needs special handling since it doesn't have fixed params
    # pylint: disable=protected-access
    parameters = params._raw if hasattr(params, "_raw") else params.to_dict().values()

    new_expression = []
    var_name = None
    for token in parameters:
        new_token = env.get_var(token)
        if new_token is None:
            new_expression.append(token)
        else:
            new_expression.append(new_token)
            var_name = token
    var_val = executor.eval_expression(new_expression)
    env.add_var(var_name, var_val)


def compare(executor, params):
    """
    Compare two variables and record result.

    Parameters (accessed via params object):
        params.var1 (str): First variable name
        params.var2 (str): Second variable name
        params.qaid (str): Test case ID
        params.fail_match (str): "eq" or "uneq" (default: "uneq")
    """
    var1 = env.get_var(params.var1)
    var2 = env.get_var(params.var2)
    qaid = params.qaid
    fail_match = params.fail_match

    is_succeeded = (str(var1) == str(var2)) ^ (fail_match == "eq")

    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        f"v1:{var1} v2:{var2}",
    )

    result_str = "Succeeded" if is_succeeded else "Failed"
    logger.info(
        "%s to compare for testcase: %s, fail_match: %s.",
        result_str,
        qaid,
        fail_match,
    )


def check_var(executor, params):
    """
    Check if variable matches expected value and report result.

    Parameters (accessed via params object):
        params.name (str): Variable name to check [-name]
        params.value (str, optional): Expected exact value [-value]
        params.pattern (str, optional): Regex pattern to match [-pattern]
        params.contains (str, optional): Substring to check [-contains]
        params.qaid (str): Test case ID [-for]
        params.fail_match (str): "match" or "unmatch" (default: "unmatch") [-fail]

    Example:
        check_var -name hostname -value "FGT-Branch" -for 801830
        check_var -name hostname -pattern "FGT-.*" -for 801831
        check_var -name status -contains "success" -for 801832
    """
    # Extract parameters
    name = params.name
    value = params.get("value")
    pattern = params.get("pattern")
    contains = params.get("contains")
    qaid = params.qaid
    fail_match = params.get("fail_match", "unmatch") == "match"

    # Get variable value using env service (CORRECTED!)
    var_value = env.get_var(name)

    if var_value is None:
        raise ValueError(f"Variable '{name}' not found")

    # Determine match based on check type
    if value is not None:
        matched = str(var_value) == str(value)
        check_desc = f"exact match: '{value}'"
    elif pattern is not None:
        # Normalize pattern to remove surrounding quotes (like setvar does)
        normalized_pattern = _normalize_regexp(pattern)
        matched = bool(re.search(normalized_pattern, str(var_value)))
        check_desc = f"pattern: '{normalized_pattern}'"
    elif contains is not None:
        matched = str(contains) in str(var_value)
        check_desc = f"contains: '{contains}'"
    else:
        raise ValueError("Must specify one of: value, pattern, or contains")

    # XOR logic like expect API
    is_succeeded = bool(matched) ^ fail_match

    # Record result
    line_number = getattr(executor, "last_line_number", 0)
    result_status = "PASS" if is_succeeded else "FAIL"
    cli_output = (
        f"Variable '{name}' = '{var_value}' | "
        f"Check: {check_desc} | Result: {result_status}"
    )
    executor.result_manager.add_qaid_expect_result(
        qaid=qaid,
        is_succeeded=is_succeeded,
        line_number=line_number,
        cli_output=cli_output,
    )

    logger.info(
        "check_var: %s=%s | %s | %s",
        name,
        var_value,
        check_desc,
        "PASS" if is_succeeded else "FAIL",
    )
