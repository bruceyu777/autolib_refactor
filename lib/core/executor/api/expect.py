"""
Expect API module.

Pattern matching APIs with validation and retry logic.
Module name 'expect' becomes the category name.
"""

import re

from lib.services import env, logger

# Helper functions (not APIs - start with _)


def _normalize_regexp(reg_exp):
    """
    *** Used by autolib ***
    Normalize regular expression patterns.
    """
    if re.search(r"(?<!\\)\\\\\\\(", reg_exp):
        reg_exp = re.sub(r"(?<!\\)\\\\\\\(", r"\(", reg_exp)
        logger.debug(reg_exp)
        reg_exp = re.sub(r"(?<!\\)\\\\\\\)", r"\)", reg_exp)
        logger.debug(reg_exp)
    reg_exp = reg_exp.replace(r"\\\\", "\\")
    logger.debug(reg_exp)
    if reg_exp.startswith('"') and reg_exp.endswith('"'):
        reg_exp = reg_exp[1:-1]
    if reg_exp.startswith("'") and reg_exp.endswith("'"):
        reg_exp = reg_exp[1:-1]
    return reg_exp


def _handle_need_retry_expect(executor, retry_command):
    """*** Used by autolib ***
    Handle retry logic for expect APIs."""
    if env.need_retry_expect():
        if retry_command is None:
            previous_vm_code = executor.script.get_compiled_code_line(
                executor.program_counter - 1
            )
            if previous_vm_code.operation == "command":
                previous_command = previous_vm_code.parameters[0]
                if previous_command.startswith(
                    ("curl", "wget", "exe log display", "execute log display")
                ):
                    return f'"{previous_command}"', 3
    return retry_command, -1


def _log_expect_result(is_succeeded, qaid, rule, fail_match, timeout_timer):
    """*** Used by autolib ***
    Log expect API results."""
    if is_succeeded:
        logger.debug(
            "\n* Expect Succeeded(%s) *\nRule: '%s'\n'fail_match' Flag: %s\nTimeout Timer: %ss\n\n",
            qaid,
            rule,
            fail_match,
            timeout_timer,
        )
    else:
        logger.warning(
            "\n* Expect Failure(%s) *\nRule: '%s'\n'fail_match' Flag: %s\nTimeout Timer: %ss\n\n",
            qaid,
            rule,
            fail_match,
            timeout_timer,
        )


# Public APIs


def expect_ctrl_c(executor, params):
    """
    Send Ctrl+C then expect pattern.

    Uses same parameters as expect API.
    Parameters accessed via params.rule, params.qaid, etc.
    """
    executor.cur_device.send_command("ctrl_c")
    expect(executor, params)


def expect(executor, params):
    """
    Expect pattern in output with optional retry logic.

    Parameters (accessed via params object):
        params.rule (str): Regular expression pattern to match [-e]
        params.qaid (str): Test case ID for reporting [-for]
        params.wait_seconds (int): Timeout in seconds (default: 5) [-t]
        params.fail_match (str): "match" or "unmatch" (default: "unmatch") [-fail]
        params.clear (str): "yes" or "no" to clear buffer (default: "yes") [-clear]
        params.retry_command (str, optional): Command to retry on failure [-retry_command]
        params.retry_cnt (int): Number of retries (default: 3) [-retry_cnt]

    Example:
        expect -e "login:" -for 803001 -t 10 -fail unmatch

    Schema-driven parameters enable:
    - Type safety (ints are auto-cast)
    - Default values (from schema)
    - Named access (self-documenting)
    - CLI option reference in help
    """
    # Access validated parameters - types already cast by schema
    rule = params.rule
    qaid = params.qaid
    wait_seconds = params.wait_seconds  # Already int from schema
    fail_match = params.fail_match == "match"
    clear = params.clear == "yes"
    retry_command = params.get("retry_command")
    retry_cnt = params.retry_cnt  # Already int from schema

    rule = _normalize_regexp(rule)
    matched, cli_output = executor.cur_device.expect(rule, wait_seconds, clear)
    is_succeeded = bool(matched) ^ fail_match

    retry_command, _retry_cnt = _handle_need_retry_expect(executor, retry_command)
    if _retry_cnt != -1:
        retry_cnt = _retry_cnt

    cnt = 1
    while not is_succeeded and retry_command is not None and cnt < retry_cnt:
        logger.info("Begin to retry for expect, cur cnt: %s", cnt)
        executor.cur_device.send_command(retry_command[1:-1])
        matched, cli_output = executor.cur_device.expect(rule, wait_seconds, clear)
        is_succeeded = bool(matched) ^ fail_match
        cnt += 1

    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        cli_output,
    )
    _log_expect_result(is_succeeded, qaid, rule, fail_match, wait_seconds)


def expect_OR(executor, params):
    """
    Expect one of two patterns (logical OR).

    Parameters (accessed via params object):
        params.rule1 (str): First pattern to match
        params.rule2 (str): Second pattern to match
        params.fail1_match (str): "match" or "unmatch" for rule1
        params.fail2_match (str): "match" or "unmatch" for rule2
        params.qaid (str): Test case ID
        params.wait_seconds (int): Timeout in seconds (default: 5)
    """
    # Access validated parameters
    rule1 = _normalize_regexp(params.rule1)
    rule2 = _normalize_regexp(params.rule2)
    fail1_match = params.fail1_match == "match"
    fail2_match = params.fail2_match == "match"
    qaid = params.qaid
    wait_seconds = params.wait_seconds  # Already int from schema

    result1, cli_output1 = executor.cur_device.expect(rule1, wait_seconds)
    result2, cli_output2 = executor.cur_device.expect(rule2, wait_seconds)

    is_succeeded = bool(result1) ^ fail1_match | bool(result2) ^ fail2_match
    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        f"output of {rule1}:\n{cli_output1}\noutput of {rule2}:\n{cli_output2}\n",
    )

    _log_expect_result(
        is_succeeded,
        qaid,
        (rule1, rule2),
        (fail1_match, fail2_match),
        wait_seconds,
    )


def varexpect(executor, params):
    """
    Expect variable value in output.

    Parameters (accessed via params object):
        params.variable (str): Variable name whose value to expect
        params.qaid (str): Test case ID
        params.wait_seconds (int): Timeout in seconds (default: 5)
        params.fail_match (str): "match" or "unmatch"
    """
    # Access validated parameters
    variable = params.variable
    qaid = params.qaid
    wait_seconds = params.wait_seconds  # Already int from schema
    fail_match = params.fail_match == "match"

    value = env.get_var(variable)
    value = variable if value is None else value

    # For this scenario: varexpect -v "{$SerialNum}" -for 803092 -t 20
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    result, cli_output = executor.cur_device.expect(value, wait_seconds)
    is_succeeded = bool(result) ^ fail_match

    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        cli_output,
    )

    result_str = "Succeeded" if is_succeeded else "Failed"
    logger.info(
        "%s to expect for testcase: %s, with variable:%s value: (%s) and fail_match: %s in %ss.",
        result_str,
        qaid,
        variable,
        value,
        fail_match,
        wait_seconds,
    )
