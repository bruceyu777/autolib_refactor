"""
Variable API module.

Variable manipulation and comparison APIs.
Module name 'variable' becomes the category name.
"""

# pylint: disable=unused-argument


from lib.services import env, logger

from .expect import _normalize_regexp


def setenv(executor, parameters):
    """
    Set environment variable for a specific device.

    Parameters:
        0: var_name (str) - Variable name
        1: var_val (str) - Variable value
        2: device_name (str) - Device name
    """
    var_name, var_val, device_name = parameters
    var_val = env.get_var(var_val)
    env.set_section_var(device_name, var_name, var_val)
    logger.info(
        "Set env variable: device_name:'%s', var_name:'%s', var_val:'%s'",
        device_name,
        var_name,
        var_val,
    )


def setvar(executor, parameters):
    """
    Set variable from pattern match in device output.

    Parameters:
        0: rule (str) - Pattern with capture group
        1: name (str) - Variable name to set
    """
    rule, name = parameters
    rule = _normalize_regexp(rule)
    logger.info("rule in set_var is %s", rule)
    match, _ = executor.cur_device.expect(rule)
    if match:
        value = match.group(1)
        env.add_var(name, value)
        logger.info("Succeeded to set variable %s to '%s'", name, value)
    else:
        logger.error("Failed to execute setvar.")


def intset(executor, parameters):
    """
    Set integer variable.

    Parameters:
        0: var_name (str) - Variable name
        1: var_value (int/str) - Variable value
    """
    var_name = parameters[0]
    var_value = parameters[1]
    env.add_var(var_name, var_value)


def strset(executor, parameters):
    """
    Set string variable.

    Parameters:
        0: var_name (str) - Variable name
        1: var_value (str) - Variable value
    """
    var_name = parameters[0]
    var_value = parameters[1]
    env.add_var(var_name, var_value)


def intchange(executor, parameters):
    """
    Modify integer variable using expression.

    Parameters:
        Variable tokens that form an expression
    """
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


def compare(executor, parameters):
    """
    Compare two variables and record result.

    Parameters:
        0: var1 (str) - First variable
        1: var2 (str) - Second variable
        2: qaid (str) - Test case ID
        3: fail_match (str) - "eq" or "ne"
    """
    var1, var2, qaid, fail_match = parameters
    var1 = env.get_var(var1)
    var2 = env.get_var(var2)
    is_succeeded = (str(var1) == str(var2)) ^ (fail_match == "eq")
    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        f"v1:{var1} v2:{var2}",
    )

    result_str = "Succeeded" if is_succeeded else "Failed"
    logger.info(
        "%s to to compare for testcase: %s, fail_match: %s.",
        result_str,
        qaid,
        fail_match,
    )
