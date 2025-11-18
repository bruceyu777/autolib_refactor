"""
Network API module.

FTP and Telnet APIs for network testing.
Module name 'network' becomes the category name.
"""

from lib.services import TestStatus, logger
from lib.utilities import OperationFailure, TestFailed

from .expect import _normalize_regexp


def myftp(executor, params):
    """
    Execute FTP API with pattern matching.

    Parameters (accessed via params object):
        params.rule (str): Pattern to match [-e]
        params.ip (str): FTP server IP address [-ip]
        params.qaid (str): Test case ID [-for]
        params.fail_match (str): "match" or "unmatch" [-fail]
        params.wait_seconds (int): Timeout in seconds (default: 5) [-t]
        params.user_name (str, optional): FTP username [-u]
        params.password (str, optional): FTP password [-p]
        params.command (str, optional): FTP command to execute [-c]
        params.action (str): Action on failure: "stop", "continue", or "nextgroup" (default: "continue") [-a]
    """
    # Access validated parameters
    rule = _normalize_regexp(params.rule)
    ip = params.ip
    qaid = params.qaid
    fail_match = params.fail_match == "match"
    wait_seconds = params.wait_seconds  # Already int
    user_name = params.get("user_name")
    password = params.get("password")
    command = params.get("command")
    action = params.action

    executor.cur_device.send_line(f"ftp {ip}")
    executor.cur_device.search("Name", pos=-1)
    executor.cur_device.send_line(user_name)
    executor.cur_device.search("Password:", pos=-1)
    executor.cur_device.send_line(password)

    if command is not None:
        executor.cur_device.search("[#>]", pos=-1)
        executor.cur_device.send_line(command)

    result, cli_output = executor.cur_device.expect(rule, wait_seconds)
    is_succeeded = bool(result) ^ fail_match

    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        cli_output,
    )

    result_str = TestStatus.PASSED if is_succeeded else TestStatus.FAILED
    logger.info(
        "%s to expect for testcase: %s, with rule:%s and fail_match: %s in %ss.",
        result_str,
        qaid,
        rule,
        fail_match,
        wait_seconds,
    )

    executor.cur_device.send_line("quit")
    executor.cur_device.search(".+")

    if result_str is not TestStatus.PASSED:
        if action == "stop":
            raise OperationFailure("FTP Failed and user requested to STOP!!!")
        if action == "nextgroup":
            raise TestFailed("FTP failed and user requested to go to next!!!")


def mytelnet(executor, params):
    """
    Execute Telnet API with pattern matching.

    Parameters (accessed via params object):
        params.rule (str): Pattern to match [-e]
        params.ip (str): Telnet server IP [-ip]
        params.qaid (str): Test case ID [-for]
        params.fail_match (str): "match" or "unmatch" [-fail]
        params.wait_seconds (int): Timeout in seconds (default: 5) [-t]
        params.user_name (str, optional): Username [-u]
        params.password (str, optional): Password [-p]
    """
    # Access validated parameters
    rule = _normalize_regexp(params.rule)
    ip = params.ip
    qaid = params.qaid
    fail_match = params.fail_match == "match"
    wait_seconds = params.wait_seconds  # Already int
    user_name = params.get("user_name")
    password = params.get("password")

    executor.cur_device.send_line(f"telnet {ip}")
    executor.cur_device.search("login:")
    executor.cur_device.send_line(user_name)
    executor.cur_device.search("Password:")
    executor.cur_device.send_line(password)

    result, cli_output = executor.cur_device.expect(rule, wait_seconds)
    is_succeeded = bool(result) ^ fail_match

    executor.result_manager.add_qaid_expect_result(
        qaid,
        is_succeeded,
        executor.last_line_number,
        cli_output,
    )

    result_str = "Succeeded" if is_succeeded else "Failed"
    logger.info(
        "%s to expect for testcase: %s, with rule:%s and fail_match: %s in %ss.",
        result_str,
        qaid,
        rule,
        fail_match,
        wait_seconds,
    )

    executor.cur_device.send_line("^]")
    executor.cur_device.search(".+")
