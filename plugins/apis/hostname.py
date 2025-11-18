"""
Hostname extraction utilities.

This is an example user-defined API plugin that demonstrates
how to create reusable APIs for the test automation framework.
"""

import re

from lib.services import env, logger


def extract_hostname(executor, params):
    """
    Extract hostname from device output.

    Parameters (accessed via params object):
        params.var (str): Variable name to store hostname [-var]

    Example:
        [FGT_A]
        get system status
        extract_hostname -var hostname
        send "# Hostname is {$hostname}"

    Context access:
        Device output is available via executor.context['last_output']
    """
    var = params.var
    output = executor.context["last_output"]

    # Extract hostname using regex
    match = re.search(r"Hostname:\s+(\w+)", output)
    hostname = match.group(1) if match else "unknown"

    # IMPORTANT: Use env.add_var(), NOT executor.variables!
    env.add_var(var, hostname)

    logger.info(
        "extract_hostname: Extracted '%s', stored in variable '%s'", hostname, var
    )
    return hostname
