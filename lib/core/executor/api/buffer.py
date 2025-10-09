"""
Buffer API module.

This module contains APIs for buffer operations.
Module name 'buffer' becomes the category name.
"""

# pylint: disable=unused-argument


def clearbuff(executor, params):
    """
    Clear device buffer.

    No parameters required.
    """
    executor.cur_device.clear_buffer()


def clean_buffer(executor, params):
    """
    Clear device buffer (alias). Deprecated API, please use clearbuff.

    No parameters required.
    """
    executor.cur_device.clear_buffer()


def clear_buffer(executor, params):
    """
    Clear device buffer (alias). Deprecated API, please use clearbuff.

    No parameters required.
    """
    executor.cur_device.clear_buffer()
