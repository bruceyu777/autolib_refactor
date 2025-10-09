"""
Variable API module.

Variable manipulation and comparison APIs.
Module name 'variable' becomes the category name.
"""

# pylint: disable=unused-argument


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
    Set integer variable.

    Parameters (accessed via params object):
        params.var_name (str): Variable name
        params.var_value (int): Integer value
    """
    var_name = params.var_name
    var_value = params.var_value
    env.add_var(var_name, var_value)


def strset(executor, params):
    """
    Set string variable.

    Parameters (accessed via params object):
        params.var_name (str): Variable name
        params.var_value (str): String value
    """
    var_name = params.var_name
    var_value = params.var_value
    env.add_var(var_name, var_value)


def listset(executor, params):
    """
    Set list variable.

    Parameters (accessed via params object):
        params.var_name (str): Variable name
        params.var_value (str): List value
    """
    var_name = params.var_name
    var_value = params.var_value
    env.add_var(var_name, var_value)


def intchange(executor, params):
    """
    Modify integer variable using expression.

    Parameters (accessed via params object):
        params.expression_tokens: Variable number of expression tokens

    Note: This API receives variable-length parameters as a tuple,
    so we handle it specially.
    """
    # For variable-length expressions, we get the raw data
    # This API needs special handling since it doesn't have fixed params
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
