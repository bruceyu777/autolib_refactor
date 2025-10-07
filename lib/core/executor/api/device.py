"""
Device API module.

This module contains APIs for device switching, login, and configuration.
Module name 'device' becomes the category name.
"""

# pylint: disable=unused-argument

from lib.utilities import sleep_with_progress


def forcelogin(executor, parameters):
    """Force login to the current device."""
    executor.cur_device.force_login()


def auto_login(executor, parameters):
    """
    Enable or disable automatic login on reset commands.

    Parameters:
        0: enabled (int) - 1 to enable, 0 to disable
    """
    value = bool(int(parameters[0]))
    executor.auto_login = value


def keep_running(executor, parameters):
    """
    Set keep_running flag for the device.

    Parameters:
        0: enabled (int) - 1 to enable, 0 to disable
    """
    value = bool(int(parameters[0]))
    executor.cur_device.set_keep_running(value)


def confirm_with_newline(executor, parameters):
    """
    Set confirm_with_newline flag for the device.

    Parameters:
        0: enabled (int) - 1 to enable, 0 to disable
    """
    value = bool(int(parameters[0]))
    executor.cur_device.set_confirm_with_newline(value)


def wait_for_confirm(executor, parameters):
    """
    Set wait_for_confirm flag for the device.

    Parameters:
        0: enabled (int) - 1 to enable, 0 to disable
    """
    value = bool(int(parameters[0]))
    executor.cur_device.set_wait_for_confirm(value)


def restore_image(executor, parameters):
    """
    Restore a device image to a specific release and build.

    Parameters:
        0: release (str) - Release version to restore
        1: build (str) - Build number to restore
    """
    release, build = parameters
    executor.cur_device.restore_image(release, build, False)


def resetFirewall(executor, cmd):
    """
    Reset firewall configuration.

    Parameters:
        0: cmd (str) - Reset command (optional, defaults to "execute factoryreset")
    """
    if not cmd:
        cmd = "execute factoryreset"
    executor.cur_device.reset_config(cmd)
    sleep_with_progress(1)


def resetFAP(executor, cmd):
    """
    Reset FAP device.

    Parameters:
        0: cmd (str) - Reset command (optional, defaults to "factoryreset")
    """
    if not cmd:
        cmd = "factoryreset"
    executor.cur_device.reset_config(cmd)
