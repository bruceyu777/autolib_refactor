"""
Comprehensive test suite for code execution APIs.

Tests the exec_code API and CodeExecutor infrastructure for executing
Python, Bash, and other languages from file-based code.
"""

# pylint: disable=import-outside-toplevel,unused-import,unused-variable,unused-argument

from unittest.mock import MagicMock, call

import pytest

from lib.core.executor.api.code_execution import (
    _build_context,
    _load_code_file,
    _wrap_function_call,
    exec_code,
)
from lib.core.executor.code_executor import BashExecutor, CodeExecutor, PythonExecutor

# ==================== TestCodeExecutor ====================


class TestCodeExecutor:
    """Test CodeExecutor base functionality and language executors."""

    def test_python_executor_registration(self):
        """Test that Python executor is registered."""
        executor = CodeExecutor.get("python")
        assert executor is not None
        assert executor == PythonExecutor

    def test_bash_executor_registration(self):
        """Test that Bash executor is registered."""
        executor = CodeExecutor.get("bash")
        assert executor is not None
        assert executor == BashExecutor

    def test_get_executor_unsupported_language(self):
        """Test error for unsupported language."""
        executor = CodeExecutor.get("nonexistent_language")
        assert executor is None

    def test_python_executor_basic_execution(self):
        """Test basic Python code execution."""
        code = "result = 2 + 2\n__result__ = result"
        executor = PythonExecutor(code, {}, timeout=5)
        result = executor.run()
        assert result == 4

    def test_bash_executor_basic_execution(self):
        """Test basic Bash code execution."""
        code = "echo 'Hello World'"
        executor = BashExecutor(code, {}, timeout=5)
        result = executor.run()
        assert "Hello World" in result

    def test_python_context_injection(self):
        """Test that context is available in Python code."""
        code = "__result__ = context['test_value']"
        context = {"test_value": 42}
        executor = PythonExecutor(code, context, timeout=5)
        result = executor.run()
        assert result == 42

    def test_python_sandboxing(self):
        """Test that Python executor has restricted builtins."""
        # __import__ should be restricted
        code = "__import__('os').system('echo test')"
        executor = PythonExecutor(code, {}, timeout=5)

        with pytest.raises((NameError, KeyError)):
            executor.run()

    def test_python_multiple_statements(self):
        """Test executing multiple Python statements."""
        code = """
x = 10
y = 20
z = x + y
__result__ = z
"""
        executor = PythonExecutor(code, {}, timeout=5)
        result = executor.run()
        assert result == 30

    def test_python_string_return(self):
        """Test Python execution returning a string."""
        code = "__result__ = 'Hello from Python'"
        executor = PythonExecutor(code, {}, timeout=5)
        result = executor.run()
        assert result == "Hello from Python"

    def test_bash_environment_injection(self):
        """Test that environment variables are available in Bash."""
        code = "echo $TEST_VAR"
        context = {"variables": {"TEST_VAR": "test_value"}}
        executor = BashExecutor(code, context, timeout=5)
        result = executor.run()
        assert "test_value" in result


# ==================== TestExecCodeAPI ====================


class TestExecCodeAPI:
    """Test exec_code API implementation."""

    def test_exec_code_python_from_file(self, mocker, temp_dir):
        """Test executing Python code from file."""
        # Create test file
        test_file = temp_dir / "test_script.py"
        test_file.write_text("__result__ = 42")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = "test output"
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "test_script.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        result = exec_code(mock_executor, mock_params)

        # Verify
        assert result == 42
        mock_env.add_var.assert_called_once_with("result", 42)

    def test_exec_code_bash_from_file(self, mocker, temp_dir):
        """Test executing Bash code from file."""
        # Create test file
        test_file = temp_dir / "test_script.sh"
        test_file.write_text("echo 'Success'")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "bash"
        mock_params.var = "output"
        mock_params.file = "test_script.sh"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        result = exec_code(mock_executor, mock_params)

        # Verify
        assert "Success" in result
        assert mock_env.add_var.called

    def test_exec_code_with_function_call(self, mocker, temp_dir):
        """Test executing specific function from file."""
        # Create test file with function
        test_file = temp_dir / "lib.py"
        test_file.write_text(
            """
def calculate(x, y):
    return x * y
"""
        )

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "lib.py"
        mock_params.get.side_effect = lambda x, default=None: {
            "func": "calculate",
            "args": "5, 10",
        }.get(x, default)

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        result = exec_code(mock_executor, mock_params)

        # Verify
        assert result == 50
        mock_env.add_var.assert_called_once_with("result", 50)

    def test_exec_code_with_function_no_args(self, mocker, temp_dir):
        """Test executing function without arguments."""
        # Create test file with function
        test_file = temp_dir / "lib.py"
        test_file.write_text(
            """
def get_value():
    return 'test_value'
"""
        )

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "lib.py"
        mock_params.get.side_effect = lambda x, default=None: {"func": "get_value"}.get(
            x, default
        )

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        result = exec_code(mock_executor, mock_params)

        # Verify
        assert result == "test_value"

    def test_exec_code_context_access(self, mocker, temp_dir):
        """Test that code can access execution context."""
        # Create test file that accesses context
        test_file = temp_dir / "context_test.py"
        test_file.write_text("__result__ = context['last_output'].upper()")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.cur_device.conn.output_buffer = "hello world"
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "context_test.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        result = exec_code(mock_executor, mock_params)

        # Verify
        assert result == "HELLO WORLD"

    def test_exec_code_variable_storage(self, mocker, temp_dir):
        """Test that result is stored in env.variables."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("__result__ = 123")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "my_var"
        mock_params.file = "test.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        exec_code(mock_executor, mock_params)

        # Verify variable was stored with correct name
        mock_env.add_var.assert_called_once_with("my_var", 123)

    def test_exec_code_file_not_found(self, mocker):
        """Test error when file doesn't exist."""
        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = "/nonexistent"

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "missing.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")

        # Execute and verify error
        with pytest.raises(FileNotFoundError):
            exec_code(mock_executor, mock_params)

    def test_exec_code_unsupported_language(self, mocker, temp_dir):
        """Test error for invalid language."""
        # Create test file
        test_file = temp_dir / "test.xyz"
        test_file.write_text("code")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "unsupported_language"
        mock_params.var = "result"
        mock_params.file = "test.xyz"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute and verify error
        with pytest.raises(ValueError, match="Unsupported language"):
            exec_code(mock_executor, mock_params)

    def test_exec_code_execution_error(self, mocker, temp_dir):
        """Test error handling when code execution fails."""
        # Create test file with invalid Python code
        test_file = temp_dir / "bad_code.py"
        test_file.write_text("undefined_variable")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "bad_code.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute and verify error
        with pytest.raises(NameError):
            exec_code(mock_executor, mock_params)

    def test_exec_code_return_value_types(self, mocker, temp_dir):
        """Test various return value types."""
        test_cases = [
            ("__result__ = 42", 42),
            ("__result__ = 'string'", "string"),
            ("__result__ = [1, 2, 3]", [1, 2, 3]),
            ("__result__ = {'key': 'value'}", {"key": "value"}),
            ("__result__ = True", True),
            ("__result__ = None", None),
        ]

        for code, expected in test_cases:
            # Create test file
            test_file = temp_dir / f"test_{expected}.py"
            test_file.write_text(code)

            # Mock dependencies
            mock_executor = MagicMock()
            mock_executor.workspace = str(temp_dir)
            mock_executor.last_output = ""
            mock_executor.cur_device = MagicMock()
            mock_executor.devices = {}

            mock_params = MagicMock()
            mock_params.lang = "python"
            mock_params.var = "result"
            mock_params.file = f"test_{expected}.py"
            mock_params.get.side_effect = lambda x, default=None: default

            mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
            mock_env.variables = {}
            mock_env.user_env = {}

            # Execute
            result = exec_code(mock_executor, mock_params)

            # Verify
            assert result == expected


# ==================== TestExecCodeLogging ====================


class TestExecCodeLogging:
    """Test logging functionality in exec_code."""

    def test_logging_info_messages(self, mocker, temp_dir, caplog):
        """Test that INFO level logs are generated."""
        import logging

        caplog.set_level(logging.INFO)

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("42")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "test.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        exec_code(mock_executor, mock_params)

        # Verify logs
        assert "exec_code: Starting execution" in caplog.text
        assert "Language: python" in caplog.text
        assert "File: 'test.py'" in caplog.text  # Note: log includes quotes
        assert "Variable: 'result'" in caplog.text  # Note: log includes quotes
        assert "Executing python code from test.py" in caplog.text
        assert "Execution completed successfully" in caplog.text
        assert "Stored result in variable: $result" in caplog.text

    def test_logging_debug_messages(self, mocker, temp_dir, caplog):
        """Test that DEBUG level logs are generated."""
        import logging

        caplog.set_level(logging.DEBUG)

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("42")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "test.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        exec_code(mock_executor, mock_params)

        # Verify DEBUG logs
        assert "exec_code: Loading code from file" in caplog.text
        assert "exec_code: Code loaded successfully" in caplog.text
        assert "exec_code: Building execution context" in caplog.text
        assert "exec_code: Getting code executor for language" in caplog.text
        assert "exec_code: Result type:" in caplog.text
        assert "exec_code: Result value:" in caplog.text

    def test_logging_on_file_not_found(self, mocker, caplog):
        """Test error logs when file is not found."""
        import logging

        caplog.set_level(logging.ERROR)

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = "/nonexistent"

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "missing.py"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")

        # Execute and expect error
        with pytest.raises(FileNotFoundError):
            exec_code(mock_executor, mock_params)

        # Verify error logs (traceback includes FileNotFoundError and filename)
        assert "exec_code: Execution failed" in caplog.text
        assert "FileNotFoundError" in caplog.text
        assert "missing.py" in caplog.text

    def test_logging_on_unsupported_language(self, mocker, temp_dir, caplog):
        """Test error logs for unsupported language."""
        import logging

        caplog.set_level(logging.ERROR)

        # Create test file
        test_file = temp_dir / "test.xyz"
        test_file.write_text("code")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "invalid_lang"
        mock_params.var = "result"
        mock_params.file = "test.xyz"
        mock_params.get.side_effect = lambda x, default=None: default

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute and expect error
        with pytest.raises(ValueError):
            exec_code(mock_executor, mock_params)

        # Verify error logs
        assert "exec_code: Unsupported language" in caplog.text
        assert "invalid_lang" in caplog.text

    def test_logging_with_function_call(self, mocker, temp_dir, caplog):
        """Test logging when function is specified."""
        import logging

        caplog.set_level(logging.INFO)

        # Create test file
        test_file = temp_dir / "lib.py"
        test_file.write_text("def foo(): return 1")

        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)
        mock_executor.last_output = ""
        mock_executor.cur_device = MagicMock()
        mock_executor.devices = {}

        mock_params = MagicMock()
        mock_params.lang = "python"
        mock_params.var = "result"
        mock_params.file = "lib.py"
        mock_params.get.side_effect = lambda x, default=None: {"func": "foo"}.get(
            x, default
        )

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}

        # Execute
        exec_code(mock_executor, mock_params)

        # Verify function is logged
        assert "Function: foo" in caplog.text


# ==================== TestCodeFileHelpers ====================


class TestCodeFileHelpers:
    """Test helper functions for code file operations."""

    def test_load_code_file_success(self, temp_dir):
        """Test loading valid code file."""
        # Create test file
        test_file = temp_dir / "script.py"
        test_content = "print('Hello World')"
        test_file.write_text(test_content)

        # Mock executor
        mock_executor = MagicMock()
        mock_executor.workspace = str(temp_dir)

        # Load file
        result = _load_code_file(mock_executor, "script.py")

        # Verify
        assert result == test_content

    def test_load_code_file_not_found(self):
        """Test error when file is missing."""
        # Mock executor
        mock_executor = MagicMock()
        mock_executor.workspace = "/nonexistent"

        # Load file and expect error
        with pytest.raises(FileNotFoundError):
            _load_code_file(mock_executor, "missing.py")

    def test_wrap_function_call_no_args(self):
        """Test wrapping function without arguments."""
        code = "def foo():\n    return 42"
        result = _wrap_function_call(code, "foo", None)

        # Verify
        assert "__result__ = foo()" in result
        assert code in result

    def test_wrap_function_call_with_args(self):
        """Test wrapping function with arguments."""
        code = "def add(x, y):\n    return x + y"
        result = _wrap_function_call(code, "add", "5, 10")

        # Verify
        assert "__result__ = add(5, 10)" in result
        assert code in result

    def test_wrap_function_call_empty_args(self):
        """Test wrapping function with empty args string."""
        code = "def bar():\n    return 'test'"
        result = _wrap_function_call(code, "bar", "")

        # Verify
        assert "__result__ = bar()" in result

    def test__build_context(self, mocker):
        """Test building execution context."""
        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.cur_device.conn.output_buffer = "output"
        mock_executor.devices = {"device1": "dev"}
        mock_executor.workspace = "/workspace"

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {"var1": "value1"}
        mock_env.user_env = {"config_key": "config_value"}

        # Build context
        context = _build_context(mock_executor)

        # Verify context structure
        assert context["last_output"] == "output"
        assert context["device"] == mock_executor.cur_device
        assert context["devices"] == {"device1": "dev"}
        assert context["variables"] == {"var1": "value1"}
        assert context["config"] == {"config_key": "config_value"}
        assert "get_variable" in context
        assert "set_variable" in context
        assert callable(context["get_variable"])
        assert callable(context["set_variable"])

    def test__build_context_helper_functions(self, mocker):
        """Test that context helper functions work correctly."""
        # Mock dependencies
        mock_executor = MagicMock()
        mock_executor.cur_device.conn.output_buffer = ""
        mock_executor.devices = {}

        mock_env = mocker.patch("lib.core.executor.api.code_execution.env")
        mock_env.variables = {}
        mock_env.user_env = {}
        mock_env.get_var = MagicMock(return_value="test_value")
        mock_env.add_var = MagicMock()

        # Build context
        context = _build_context(mock_executor)

        # Test get_variable
        result = context["get_variable"]("test_var")
        mock_env.get_var.assert_called_once_with("test_var")
        assert result == "test_value"

        # Test set_variable
        context["set_variable"]("new_var", "new_value")
        mock_env.add_var.assert_called_once_with("new_var", "new_value")
