"""
Utility API module.

Miscellaneous helper APIs for debugging, logging, and timing.
Module name 'utility' becomes the category name.
"""

# pylint: disable=unused-argument

import pdb

from lib.services import env, logger, summary
from lib.utilities import sleep_with_progress


def comment(executor, params):
    """
    Add comment to logs and summary.

    Parameters (accessed via params object):
        params.comment_text (str): Comment text to log
    """
    comment_text = params.comment_text
    logger.info(comment_text)
    summary.dump_str_to_brief_summary(comment_text)


def sleep(executor, params):
    """
    Sleep for specified duration.

    Parameters (accessed via params object):
        params.seconds (int): Number of seconds to sleep
    """
    seconds = params.seconds  # Already int from schema
    seconds = env.get_actual_timer(executor.cur_device.dev_name, seconds)
    sleep_with_progress(seconds, logger_func=logger.info)


# Note: Named 'breakpoint_' because 'breakpoint' is a Python keyword
# The trailing underscore will be stripped by the auto-discovery mechanism
# to register this as 'breakpoint' API
def breakpoint_(executor, params):
    """
    Pause execution at breakpoint.

    No parameters required.
    """
    executor.script.breakpoint()


def enter_dev_debugmode(executor, params):
    """
    Enter Python debugger (pdb).

    No parameters required.
    """
    # pylint: disable=forgotten-debug-statement
    pdb.set_trace()
