"""
Network API module.

FTP and Telnet APIs for network testing.
Module name 'network' becomes the category name.
"""

from lib.services import TestStatus, logger
from lib.utilities import OperationFailure, TestFailed

from .expect import _normalize_regexp


def myftp(executor, parameters):
    """
    Execute FTP API with pattern matching.

    Parameters:
        0: rule (str) - Pattern to match
        1: ip (str) - FTP server IP
        2: qaid (str) - Test case ID
        3: fail_match (str) - "match" or "unmatch"
        4: wait_seconds (int) - Timeout in seconds
        5: user_name (str) - FTP username
        6: password (str) - FTP password
        7: command (str, optional) - FTP command to execute
        8: action (str) - Action on failure: "stop" or "nextgroup"
    """
    (
        rule,
        ip,
        qaid,
        fail_match,
        wait_seconds,
        user_name,
        password,
        command,
        action,
    ) = parameters
    wait_seconds = int(wait_seconds)
    fail_match = fail_match == "match"
    rule = _normalize_regexp(rule)
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
        "%s to to expect for testcase: %s, with rule:%s and fail_match: %s in %ss.",
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


def mytelnet(executor, parameters):
    """
    Execute Telnet API with pattern matching.

    Parameters:
        0: (unused)
        1: rule (str) - Pattern to match
        2: ip (str) - Telnet server IP
        3: qaid (str) - Test case ID
        4: fail_match (str) - "match" or "unmatch"
        5: wait_seconds (int) - Timeout in seconds
        6: user_name (str) - Username
        7: password (str) - Password
    """
    (
        _,
        rule,
        ip,
        qaid,
        fail_match,
        wait_seconds,
        user_name,
        password,
    ) = parameters
    wait_seconds = int(wait_seconds)
    fail_match = fail_match == "match"
    rule = _normalize_regexp(rule)
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
        "%s to to expect for testcase: %s, with rule:%s and fail_match: %s in %ss.",
        result_str,
        qaid,
        rule,
        fail_match,
        wait_seconds,
    )
    executor.cur_device.send_line("^]")
    executor.cur_device.search(".+")
