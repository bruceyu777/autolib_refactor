"""
Multi-language code execution engine.

Provides a pluggable architecture for executing code in different languages
(Python, Bash, JavaScript, etc.) with context injection and sandboxing.
"""

import os
import subprocess
import time
from abc import ABC, abstractmethod


class CodeExecutor(ABC):
    """Base class for language-specific code executors."""

    _EXECUTORS = {}

    def __init__(self, code, context, timeout=30):
        """
        Initialize code executor.

        Args:
            code: Code string to execute
            context: Execution context dict with devices, variables, config, etc.
            timeout: Maximum execution time in seconds
        """
        self.code = code
        self.context = context
        self.timeout = timeout
        self.status = None
        self.duration = None

    @abstractmethod
    def run(self):
        """
        Execute code and return result.

        Returns:
            Execution result (type depends on language)

        Raises:
            TimeoutError: If execution exceeds timeout
            Exception: If execution fails
        """
        raise NotImplementedError()

    @classmethod
    def register(cls, lang, executor_class):
        """
        Register executor for a language.

        Args:
            lang: Language name (e.g., 'python', 'bash')
            executor_class: Executor class for this language
        """
        cls._EXECUTORS[lang] = executor_class

    @classmethod
    def get(cls, lang):
        """
        Get executor class for language.

        Args:
            lang: Language name

        Returns:
            Executor class or None if not registered
        """
        return cls._EXECUTORS.get(lang)


def _safe_import(name, globals_dict=None, locals_dict=None, fromlist=(), level=0):
    """
    Restricted import that only allows whitelisted modules.

    This enables users to write standard import statements while
    maintaining security by blocking dangerous modules.
    """
    ALLOWED_MODULES = ["re", "json", "datetime", "math"]

    if name in ALLOWED_MODULES:
        # Use the real __import__ from builtins
        return __import__(name, globals_dict, locals_dict, fromlist, level)

    raise ImportError(
        f"Import of module '{name}' is not allowed in sandbox. "
        f"Allowed modules: {', '.join(ALLOWED_MODULES)}"
    )


def _new_safe_global_sandbox():
    # Use blocklist approach: include all builtins except dangerous ones
    import builtins

    all_builtins = {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if not name.startswith("_")
    }

    # Block dangerous builtins for security
    BLOCKED_BUILTINS = {
        "open",  # File I/O operations
        "eval",  # Arbitrary code execution
        "exec",  # Arbitrary code execution
        "compile",  # Code compilation
        "input",  # User input (could hang execution)
        "__import__",  # We provide our own safe version
        "globals",  # Direct namespace access
        "locals",  # Direct namespace access
        "vars",  # Direct namespace access
        "breakpoint",  # Debugging hooks
        "help",  # Interactive help system
        "exit",  # Exit interpreter
        "quit",  # Exit interpreter
    }

    # Create safe builtins by filtering out blocked ones
    safe_builtins = {k: v for k, v in all_builtins.items() if k not in BLOCKED_BUILTINS}

    # Add our custom safe import function
    safe_builtins["__import__"] = _safe_import

    return {
        "__builtins__": safe_builtins,
        # Pre-loaded modules (in global namespace, not builtins)
        "re": __import__("re"),
        "json": __import__("json"),
        "datetime": __import__("datetime"),
        "math": __import__("math"),
    }


class PythonExecutor(CodeExecutor):
    """Execute Python code with context injection and sandboxing."""

    def run(self):
        """Execute Python code."""
        start_time = time.time()

        try:
            # Create sandboxed global namespace
            # IMPORTANT: Modules must be in global namespace, NOT in __builtins__
            safe_globals = {**_new_safe_global_sandbox(), "context": self.context}

            # Execute code
            exec(self.code, safe_globals)  # pylint: disable=exec-used

            # Get result - check multiple possible result variables
            result = (
                safe_globals.get("__result__")
                or safe_globals.get("__return__")
                or safe_globals.get("return")
            )
            self.status = "success"
            return result

        except Exception:
            self.status = "error"
            raise
        finally:
            self.duration = time.time() - start_time


class BashExecutor(CodeExecutor):
    """
    Execute Bash commands with environment variable injection.

    IMPORTANT: Environment variables are injected into the subprocess ONLY.
    Changes to bash_env do NOT affect:
        - Parent Python process
        - System-wide environment variables
        - Other subprocesses or exec_code calls
        - User's shell environment

    The bash_env is a COPY of os.environ that only exists during script execution.

    Context items exposed as environment variables:
        - Runtime variables: $VAR_NAME (uppercase)
        - Config values: $SECTION__OPTION (uppercase, double underscore)
        - Last output: $LAST_OUTPUT (device command output)
        - Workspace: $WORKSPACE (workspace directory path)
        - Current device: $CURRENT_DEVICE_NAME (if available)
        - Device list: $DEVICE_NAMES (comma-separated)
    """

    def run(self):
        """Execute Bash code with context injection."""
        start_time = time.time()

        try:
            # SAFETY: Create a COPY of environment (does NOT modify parent process)
            # This copy only affects the subprocess being created
            bash_env = os.environ.copy()

            # 1. Inject config variables from env.user_env (FosConfigParser)
            config = self.context.get("config")
            if config:
                # Iterate through all sections and options
                for section in config.sections():
                    for option in config.options(section):
                        # Export as SECTION__OPTION (double underscore separator)
                        key = f"{section}__{option}".upper()
                        value = config.get(section, option)
                        bash_env[key] = str(value)

            # 2. Inject runtime variables
            for key, value in self.context.get("variables", {}).items():
                bash_env[key.upper()] = str(value)

            # 3. Inject last device output
            last_output = self.context.get("last_output", "")
            if last_output:
                bash_env["LAST_OUTPUT"] = str(last_output)

            # 4. Inject workspace path
            workspace = self.context.get("workspace")
            if workspace:
                bash_env["WORKSPACE"] = str(workspace)

            # 5. Inject current device name (if available)
            device = self.context.get("device")
            if device and hasattr(device, "name"):
                bash_env["CURRENT_DEVICE_NAME"] = str(device.name)

            # 6. Inject all device names as comma-separated list
            devices = self.context.get("devices", {})
            if devices:
                device_names = ",".join(devices.keys())
                bash_env["DEVICE_NAMES"] = device_names

            # Execute with timeout
            result = subprocess.run(
                self.code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=bash_env,
                check=False,
            )

            self.status = "success" if result.returncode == 0 else "error"
            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            self.status = "timeout"
            raise
        except Exception:
            self.status = "error"
            raise
        finally:
            self.duration = time.time() - start_time


# Register executors
CodeExecutor.register("python", PythonExecutor)
CodeExecutor.register("bash", BashExecutor)
