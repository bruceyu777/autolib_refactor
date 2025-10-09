"""
Command API module.

This module contains APIs for sending commands and text to devices.
Module name 'command' becomes the category name.
"""

from lib.services import logger


def send_literal(executor, params):
    """
    Send a literal string with escape sequences.

    Parameters (accessed via params object):
        params.literal (str): Double-quoted string with escape sequences
    """
    literal = params.literal

    if (
        literal
        and len(literal) >= 2
        and literal.startswith('"')
        and literal.endswith('"')
    ):
        cmd = literal[1:-1]
        cmd = cmd.encode().decode("unicode_escape").replace("CRLF", "\r\n")
        executor.cur_device.send(cmd)
    else:
        logger.error("raw command must be DOUBLE-QUOTED!!!")
