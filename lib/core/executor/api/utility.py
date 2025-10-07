"""
Utility API module.

Miscellaneous helper APIs for debugging, logging, and timing.
Module name 'utility' becomes the category name.
"""

# pylint: disable=unused-argument

import pdb

from lib.services import env, logger, summary
from lib.utilities import sleep_with_progress


def comment(executor, parameters):
    """
    Add comment to logs and summary.

    Parameters:
        0: comment (str) - Comment text
    """
    comment_text = parameters[0]
    logger.info(comment_text)
    summary.dump_str_to_brief_summary(comment_text)


def sleep(executor, parameters):
    """
    Sleep for specified duration.

    Parameters:
        0: seconds (int) - Sleep duration in seconds
    """
    seconds = int(parameters[0])
    seconds = env.get_actual_timer(executor.cur_device.dev_name, seconds)
    sleep_with_progress(seconds, logger_func=logger.notice)


# Note: Named 'breakpoint_' because 'breakpoint' is a Python keyword
# The trailing underscore will be stripped by the auto-discovery mechanism
# to register this as 'breakpoint' API
def breakpoint_(executor, parameters):
    """
    Pause execution at breakpoint.

    Parameters:
        None
    """
    executor.script.breakpoint()


def enter_dev_debugmode(executor, parameters):
    """
    Enter Python debugger (pdb).

    Parameters:
        None
    """
    # pylint: disable=forgotten-debug-statement
    pdb.set_trace()
