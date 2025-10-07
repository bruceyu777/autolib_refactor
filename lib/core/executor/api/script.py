"""
Script API module.

APIs for including and executing other scripts.
Module name 'script' becomes the category name.
"""

# pylint: disable=import-outside-toplevel

from lib.core.compiler import IncludeScript
from lib.core.executor import Executor


def include(executor, parameters):
    """
    Include and execute another script.

    Parameters:
        0: script_path (str) - Path to script to include
    """
    if executor.cur_device is None:
        include_script = IncludeScript(parameters[0])
    else:
        include_script = IncludeScript(parameters[0], executor.cur_device.dev_name)

    # # Import Executor here to avoid circular import
    # from ...executor import Executor

    with Executor(include_script, executor.devices, False) as sub_executor:
        sub_executor.cur_device = executor.cur_device
        sub_executor.execute()
