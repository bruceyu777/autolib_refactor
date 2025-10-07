"""
Buffer API module.

This module contains APIs for buffer operations.
Module name 'buffer' becomes the category name.
"""

# pylint: disable=unused-argument


def clearbuff(executor, parameters):
    """Clear device buffer."""
    executor.cur_device.clear_buffer()


def clean_buffer(executor, parameters):
    """Clear device buffer (alias)."""
    executor.cur_device.clear_buffer()


def clear_buffer(executor, parameters):
    """Clear device buffer (alias)."""
    executor.cur_device.clear_buffer()
