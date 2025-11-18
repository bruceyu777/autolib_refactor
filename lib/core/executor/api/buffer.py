"""
Buffer API module.

This module contains APIs for buffer operations.
Module name 'buffer' becomes the category name.
"""

# pylint: disable=unused-argument


def clear_buffer(executor, params):
    """
    Clear device buffer, replace the legacy clear_buffer and clean_buffer.

    No parameters required.
    """
    executor.cur_device.clear_buffer()
