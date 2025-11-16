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


class PythonExecutor(CodeExecutor):
    """Execute Python code with context injection and sandboxing."""

    def run(self):
        """Execute Python code."""
        start_time = time.time()

        try:
            # Create sandboxed global namespace
            safe_globals = {
                "__builtins__": {
                    # Safe built-ins
                    "abs": abs,
                    "all": all,
                    "any": any,
                    "bool": bool,
                    "dict": dict,
                    "enumerate": enumerate,
                    "filter": filter,
                    "float": float,
                    "int": int,
                    "len": len,
                    "list": list,
                    "map": map,
                    "max": max,
                    "min": min,
                    "range": range,
                    "str": str,
                    "sum": sum,
                    "tuple": tuple,
                    "zip": zip,
                    # Safe modules
                    "re": __import__("re"),
                    "json": __import__("json"),
                    "datetime": __import__("datetime"),
                    "math": __import__("math"),
                }
            }

            # Inject context
            safe_globals["context"] = self.context
            safe_globals["__return__"] = None

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
