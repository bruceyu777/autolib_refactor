"""
Script API module.

APIs for including and executing other scripts.
Module name 'script' becomes the category name.
"""

# pylint: disable=import-outside-toplevel

from lib.core.compiler import IncludeScript
from lib.core.executor import Executor


def include(executor, params):
    """
    Include and execute another script.

    Parameters (accessed via params object):
        params.script_path (str): Path to script file to include
    """
    script_path = params.script_path

    if executor.cur_device is None:
        include_script = IncludeScript(script_path)
    else:
        include_script = IncludeScript(script_path, executor.cur_device.dev_name)

    # Execute included script with same devices
    with Executor(include_script, executor.devices, False) as sub_executor:
        sub_executor.cur_device = executor.cur_device
        sub_executor.execute()
