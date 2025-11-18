"""
Device API module.

This module contains APIs for device switching, login, and configuration.
Module name 'device' becomes the category name.
"""

# pylint: disable=unused-argument

from lib.utilities import sleep_with_progress


def forcelogin(executor, params):
    """
    Force login to the current device.

    No parameters required.
    """
    executor.cur_device.force_login()


def auto_login(executor, params):
    """
    Enable or disable automatic login on reset commands.

    Parameters (accessed via params object):
        params.enabled (int): 1 to enable, 0 to disable
    """
    value = bool(params.enabled)  # Already int from schema
    executor.auto_login = value


def keep_running(executor, params):
    """
    Set keep_running flag for the device.

    Parameters (accessed via params object):
        params.enabled (int): 1 to enable, 0 to disable
    """
    value = bool(params.enabled)  # Already int from schema
    executor.cur_device.set_keep_running(value)


def confirm_with_newline(executor, params):
    """
    Set confirm_with_newline flag for the device.

    Parameters (accessed via params object):
        params.enabled (int): 1 to enable, 0 to disable
    """
    value = bool(params.enabled)  # Already int from schema
    executor.cur_device.set_confirm_with_newline(value)


def wait_for_confirm(executor, params):
    """
    Set wait_for_confirm flag for the device.

    Parameters (accessed via params object):
        params.enabled (int): 1 to enable, 0 to disable
    """
    value = bool(params.enabled)  # Already int from schema
    executor.cur_device.set_wait_for_confirm(value)


def restore_image(executor, params):
    """
    Restore a device image to a specific release and build.

    Parameters (accessed via params object):
        params.release (str): Release version to restore [-v]
        params.build (str): Build number to restore [-b]
    """
    release = params.release
    build = params.build
    executor.cur_device.restore_image(release, build, False)


def resetFirewall(executor, params):
    """
    Reset firewall configuration.

    Parameters (accessed via params object):
        params.cmd (str, optional): Reset command (default: "execute factoryreset")
    """
    cmd = params.get("cmd") or "execute factoryreset"
    executor.cur_device.reset_config(cmd)
    sleep_with_progress(1)


def resetFAP(executor, params):
    """
    Reset FAP device.

    Parameters (accessed via params object):
        params.cmd (str, optional): Reset command (default: "factoryreset")
    """
    cmd = params.get("cmd") or "factoryreset"
    executor.cur_device.reset_config(cmd)
