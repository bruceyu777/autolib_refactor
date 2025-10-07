"""
Command API module.

This module contains APIs for sending commands and text to devices.
Module name 'command' becomes the category name.
"""

from lib.services import logger


def send_literal(executor, parameters):
    """
    Send a literal string with escape sequences.

    Parameters:
        0: literal (str) - Double-quoted string with escape sequences
    """
    if (
        parameters
        and len(parameters[0]) >= 2
        and parameters[0].startswith('"')
        and parameters[0].endswith('"')
    ):
        cmd = parameters[0][1:-1]
        cmd = cmd.encode().decode("unicode_escape").replace("CRLF", "\r\n")
        executor.cur_device.send(cmd)
    else:
        logger.error("raw command must be DOUBLE-QUOTED!!!")
