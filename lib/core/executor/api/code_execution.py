"""
Code execution APIs for running Python, Bash, and other languages.
"""

import os

from lib.core.executor.code_executor import CodeExecutor
from lib.services import env, logger


def exec_code(executor, params):
    """
    Execute code in specified language from file and store result in variable.

    Note: Code runs on your control PC, not on the device.

    Parameters (accessed via params object):
        params.lang (str): Language (python|bash|javascript|ruby) [-lang]
        params.var (str): Variable name to store result [-var]
        params.file (str): Path to code file to execute [-file]
        params.func (str, optional): Function name to call [-func]
        params.args (str, optional): Comma-separated args for function [-args]
        params.timeout (int): Timeout in seconds (default: 30) [-timeout]

    Example:
        exec_code -lang python -var result -file "scripts/parser.py"
        exec_code -lang python -var result -file "lib/parser.py" -func "parse"
        exec_code -lang bash -var ip -file "scripts/get_ip.sh"
    """
    # Extract parameters
    lang = params.lang
    var = params.var
    file = params.file  # Required parameter
    func = params.get("func")
    args = params.get("args")
    timeout = params.get("timeout", 30)

    # Log execution start
    logger.info(
        (
            "exec_code: Starting execution with \n-> Language: %s\n-> "
            "File: '%s'\n-> Variable: '%s'\n-> Timeout: %ds"
        ),
        lang,
        file,
        var,
        timeout,
    )
    if func:
        logger.info("-> Function: %s", func)
    if args:
        logger.info("-> Arguments: %s", args)

    try:
        # Load code from file
        logger.debug("exec_code: Loading code from file: %s", file)
        code = _load_code_file(executor, file)
        logger.debug("exec_code: Code loaded successfully (%d bytes)", len(code))

        # Wrap function call if specified
        if func:
            logger.debug("exec_code: Wrapping function call: %s", func)
            code = _wrap_function_call(code, func, args)

        # Build execution context
        logger.debug("exec_code: Building execution context")
        context = build_context(executor)
        logger.debug("exec_code: Built execution context with %d keys", len(context))

        # Get code executor for language
        logger.debug("exec_code: Getting code executor for language: %s", lang)
        code_executor_class = CodeExecutor.get(lang)
        if not code_executor_class:
            logger.error("exec_code: Unsupported language: %s", lang)
            raise ValueError(f"Unsupported language: {lang}")

        # Execute code
        logger.info("exec_code: Executing %s code from %s", lang, file)
        code_executor = code_executor_class(code, context, timeout)
        result = code_executor.run()

        logger.info("exec_code: Execution completed successfully")
        logger.debug("exec_code: Result type: %s", type(result).__name__)
        logger.debug("exec_code: Result value: '%s'", str(result))

        # Store result using env service (NOT executor.variables!)
        env.add_var(var, result)
        logger.info("exec_code: Stored result in variable: $%s", var)

        return result

    except Exception:
        logger.exception("*** exec_code: Execution failed!!! ***")
        raise


def _load_code_file(executor, filepath):
    """Load code from file with logging."""
    workspace = getattr(executor, "workspace", "")
    if filepath.startswith(("'", '"')):
        filepath = filepath[1:-1]
    full_path = os.path.join(workspace, filepath)

    logger.debug("exec_code: Resolved file path: %s", full_path)
    with open(full_path, "r", encoding="utf-8") as f:
        code = f.read()
    logger.debug("exec_code: File read successfully")
    return code


def _wrap_function_call(code, func_name, args):
    """Wrap code to call specific function."""
    args_str = args if args else ""
    return f"{code}\n\n__result__ = {func_name}({args_str})"


def build_context(executor):
    """
    Build execution context for API and code execution.

    This context is available to both plugin APIs and code files executed
    via exec_code. Access via executor.context['key_name'].

    Available context keys:
        last_output: Most recent device command output (string)
        device: Current device connection object
        devices: All device connections
        variables: Runtime variables dict
        config: Parsed config (FosConfigParser)
        get_variable: Function to get variable value
        set_variable: Function to set variable value
        workspace: Workspace directory path
        logger: Logger instance

    Args:
        executor: Executor instance

    Returns:
        Dictionary with execution context
    """
    # pylint: disable=unnecessary-lambda
    return {
        # Device access
        "last_output": str(executor.cur_device.conn.output_buffer),
        "device": executor.cur_device,
        "devices": executor.devices,
        "variables": env.variables,  # Runtime variables (defaultdict)
        "config": env.user_env,  # Parsed config (FosConfigParser)
        "get_variable": lambda name: env.get_var(name),
        "set_variable": lambda name, val: env.add_var(name, val),
        # Utilities
        "workspace": getattr(executor, "workspace", None),
        "logger": logger,
    }
