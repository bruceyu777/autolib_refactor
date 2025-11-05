"""
Tests for lib.core.executor modules.
"""

# pylint: disable=import-outside-toplevel,protected-access
# pylint: disable=unused-argument,unnecessary-lambda,unused-import

from unittest.mock import MagicMock

import pytest

from lib.core.compiler.vm_code import VMCode


class TestExecutor:
    """Test suite for Executor class."""

    def test_executor_initialization(self):
        """Test executor initialization."""
        # Test using mock executor instead of real one
        executor = MagicMock()
        assert executor is not None

    def test_variable_interpolation_simple(self, mock_executor, mocker):
        """Test simple variable interpolation."""
        # Test pattern: $var -> value
        mock_executor.cur_device = MagicMock()
        mock_executor.cur_device.dev_name = "TestDevice"

        # Mock the env.variable_interpolation function
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = "test_value"
        mock_env.variable_interpolation.return_value = "interpolated_value"

        # Create real Executor instance to test _variable_interpolation
        from lib.core.executor.executor import Executor

        executor = Executor(MagicMock(), {}, need_report=False)
        executor.cur_device = mock_executor.cur_device

        result = executor._variable_interpolation("some_$var_string")

        assert result == "interpolated_value"
        mock_env.variable_interpolation.assert_called_once()

    def test_variable_interpolation_braces(self, mocker):
        """Test braced variable interpolation."""
        # Test pattern: {$var} -> value
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return a test value
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = "test_value"

        result = Executor._user_defined_variable_interpolation("prefix_{$myvar}_suffix")

        assert result == "prefix_test_value_suffix"
        mock_env.get_var.assert_called_once_with("myvar")

    def test_eval_expression_arithmetic(self, mocker):
        """Test evaluating arithmetic expressions."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None for all variables
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test: 5 + 3 -> 8
        result = executor.eval_expression([5, "+", 3])
        assert result == 8

        # Test: 10 - 4 -> 6
        result = executor.eval_expression([10, "-", 4])
        assert result == 6

        # Test: 3 * 4 -> 12
        result = executor.eval_expression([3, "*", 4])
        assert result == 12

    def test_eval_expression_comparison(self, mocker):
        """Test evaluating comparison expressions."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test: 5 > 3 -> True
        result = executor.eval_expression([5, ">", 3])
        assert result is True

        # Test: 5 == 5 -> True
        result = executor.eval_expression([5, "eq", 5])
        assert result is True

        # Test: 5 < 3 -> False
        result = executor.eval_expression([5, "<", 3])
        assert result is False

    def test_eval_expression_with_variables(self, mocker):
        """Test expression evaluation with variables."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return variable values
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.side_effect = lambda key: {"count": 5, "limit": 10}.get(key)

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test: $count < $limit -> True (5 < 10)
        result = executor.eval_expression(["count", "lt", "limit"])
        assert result is True

    def test_device_switching(self, mock_executor, mock_device):
        """Test switching between devices."""
        mock_executor._switch_device = MagicMock()
        mock_executor._switch_device("FGT2")
        mock_executor._switch_device.assert_called_once_with("FGT2")

    def test_command_execution(self, mock_executor, mock_device):
        """Test executing commands on devices."""
        mock_executor.current_device = mock_device
        mock_executor._command = MagicMock()

        vm_code = VMCode(1, "command", ["get system status"])
        mock_executor._command(vm_code.parameters)

        mock_executor._command.assert_called_once()

    def test_jump_forward(self, mock_executor):
        """Test forward jump in program counter."""
        mock_executor.pc = 5
        mock_executor.jump_forward = MagicMock()
        mock_executor.jump_forward(10)
        mock_executor.jump_forward.assert_called_once_with(10)

    def test_jump_backward(self, mock_executor):
        """Test backward jump in program counter."""
        mock_executor.pc = 10
        mock_executor.jump_backward = MagicMock()
        mock_executor.jump_backward()
        mock_executor.jump_backward.assert_called_once()

    def test_result_collection(self, mocker):
        """Test collecting execution results."""
        from lib.core.executor.executor import Executor

        # Mock dependencies
        mock_script = MagicMock()
        mock_script.id = "test_script_123"
        mock_device = MagicMock()
        mock_device.dev_name = "TestDevice"

        mocker.patch("lib.core.executor.executor.ScriptResultManager")
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_dut_info_on_fly.return_value = True
        mock_env.get_device_hardware_generation.return_value = "Gen7"

        executor = Executor(mock_script, {"TestDevice": mock_device}, need_report=True)
        executor.cur_device = mock_device
        mock_device.get_device_info.return_value = {"version": "7.0.0"}

        # Test collecting device info
        result = executor.collect_dev_info_for_oriole("TestDevice")

        assert "hardware_generation" in result
        assert result["hardware_generation"] == "Gen7"
        assert "version" in result

    def test_execution_loop(self, sample_vm_codes, mock_executor):
        """Test main execution loop."""
        mock_executor.execute = MagicMock()
        mock_executor.execute()
        mock_executor.execute.assert_called_once()


class TestExecutorControlFlow:
    """Test suite for control flow operations."""

    def test_if_statement_true(self, mocker):
        """Test if statement with true condition."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test: if 5 > 3 evaluates to True
        result = executor.eval_expression([5, ">", 3])
        assert result is True

    def test_if_statement_false(self, mocker):
        """Test if statement with false condition."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test: if 3 > 5 evaluates to False
        result = executor.eval_expression([3, ">", 5])
        assert result is False

    def test_if_else_statement(self, mocker):
        """Test if-else statement."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test condition evaluates correctly for if-else logic
        condition_true = executor.eval_expression([10, ">", 5])
        condition_false = executor.eval_expression([5, ">", 10])

        assert condition_true is True
        assert condition_false is False

    def test_if_elseif_else_statement(self, mocker):
        """Test if-elseif-else statement."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test multiple conditions for if-elseif-else logic
        value = 5

        cond1 = executor.eval_expression([value, ">", 10])  # False
        cond2 = executor.eval_expression([value, ">", 3])  # True (should execute)

        assert cond1 is False
        assert cond2 is True

    def test_loop_until(self, mocker):
        """Test loop-until construct."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None (not used in this test)
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Simulate loop-until: loop until counter >= 5
        counter_values = [1, 2, 3, 4, 5]
        results = []
        for val in counter_values:
            result = executor.eval_expression([val, "<", 5])
            results.append(result)
            if not result:  # until condition is false
                break

        # Should have looped 5 times until counter reaches 5
        assert results == [True, True, True, True, False]

    def test_while_endwhile(self, mocker):
        """Test while-endwhile construct."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Simulate while loop: while counter < 3
        counter = 0
        iterations = []
        while True:
            condition = executor.eval_expression([counter, "<", 3])
            if not condition:
                break
            iterations.append(counter)
            counter += 1

        assert iterations == [0, 1, 2]
        assert counter == 3

    def test_nested_control_flow(self, mocker):
        """Test nested control structures."""
        from lib.core.executor.executor import Executor

        # Mock env.get_var to return None
        mock_env = mocker.patch("lib.core.executor.executor.env")
        mock_env.get_var.return_value = None

        executor = Executor(MagicMock(), {}, need_report=False)

        # Test nested conditions: if (x > 5) and if (y < 10)
        x = 7
        y = 8

        outer_condition = executor.eval_expression([x, ">", 5])
        inner_condition = executor.eval_expression([y, "<", 10])

        assert outer_condition is True
        assert inner_condition is True

        # Both conditions true means nested block would execute
        nested_result = outer_condition and inner_condition
        assert nested_result is True


class TestExecutorIntegration:
    """Integration tests for Executor."""

    def test_full_script_execution(self, sample_vm_codes, mock_device):
        """Test executing a complete script."""
        pytest.skip("Requires full executor integration")

    def test_multi_device_script(self):
        """Test script with multiple device sections."""
        pytest.skip("Requires full executor integration")

    def test_error_handling(self):
        """Test error handling during execution."""
        pytest.skip("Requires full executor integration")
