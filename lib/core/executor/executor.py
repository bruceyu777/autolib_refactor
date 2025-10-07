import logging
import re
from typing import Union

from lib.core.compiler import Group, Script
from lib.services import (
    ScriptResultManager,
    add_logger_handler,
    env,
    logger,
    output,
    summary,
)
from lib.utilities import sleep_with_progress

from .api_manager import ApiHandler


class Executor:
    def __init__(self, script: Union[Script, Group], devices, need_report=True):
        self.script = script
        self.devices = devices
        self.cur_device = None
        self.result_manager = ScriptResultManager(self.script)
        self.last_line_number = None
        self.program_counter = 0  # to read vm_codes
        self.need_report = need_report
        self.scripts = {}
        self.log_file_handler = None
        self.need_stop = False
        self.log_file = None
        self.auto_login = True
        self.api_handler = ApiHandler(self)

    # ========== Internal APIs (used by autolib framework) ==========

    def _switch_device(self, parameters):
        """Internal: Switch to a different device for subsequent commands."""
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]
        self.cur_device.switch()

    def _switch_device_for_collect_info(self, parameters):
        """Internal: Switch to a device for info collection (pauses stdout)."""
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]
        self.cur_device.pause_stdout()
        self.cur_device.switch_for_collect_info()

    def _with_device(self, parameters):
        """Internal: Set the current device context without switching."""
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]

    def _command(self, parameters):
        """Internal: Send a command to the current device."""
        if isinstance(self.script, Group):
            _, script_file, *_ = parameters[0].split()
            self.scripts[self.last_line_number] = script_file
            return

        cmd = parameters[0]

        # Check if it's a reset command and auto_login is enabled
        if self._is_reset_command(cmd) and self.auto_login:
            self._resetFirewall((cmd,))
            return

        cli_output = ""
        if len(parameters) == 1:
            *_, cli_output = self.cur_device.send_command(cmd)
        elif len(parameters) == 2:
            pattern = parameters[1]
            *_, cli_output = self.cur_device.send_command(cmd, pattern)
        elif len(parameters) > 2:
            pattern = parameters[1]
            timeout = int(parameters[2])
            *_, cli_output = self.cur_device.send_command(cmd, pattern, timeout)
        self.result_manager.check_cli_error(self.last_line_number, cmd, cli_output)

    def _send_line(self, parameters):
        """Internal: Send a line with newline character."""
        s = parameters[0] if parameters else ""
        self.cur_device.send_line(s)

    def _send(self, parameters):
        """Internal: Send text without newline."""
        s = parameters[0] if parameters else ""
        self.cur_device.send(s)

    def _search(self, parameters):
        """Internal: Search for pattern in device output."""
        if len(parameters) == 2:
            rule, timeout = parameters
            timeout = int(timeout)
            self.cur_device.search(rule, timeout)
        elif len(parameters) == 3:
            rule, timeout, pos = parameters
            pos = int(pos)
            timeout = int(timeout)
            self.cur_device.search(rule, timeout, pos)

    def _resetFirewall(self, cmd):
        """Internal: Reset firewall configuration."""
        if not cmd:
            cmd = ("execute factoryreset",)
        self.cur_device.reset_config(cmd[0] if cmd else "execute factoryreset")
        sleep_with_progress(1)

    @staticmethod
    def _is_reset_command(cmd):
        """Internal: Helper to detect reset commands."""
        pattern = re.compile(
            r"(exe.*factoryreset.*|exe.*(?:forticarrier|factory|crypto)-license|resetFirewall)"
        )
        return re.match(pattern, cmd)

    # ========== End Internal APIs ==========

    def _add_file_handler(self):
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        log_file = output.compose_log_file(self.script.id, "autotest.log")
        handler = logging.FileHandler(log_file)
        add_logger_handler(handler, logging.DEBUG, formatter)
        self.log_file_handler = handler

    def __enter__(self):
        logger.notice("\n** Start executing script ==> %s", self.script)
        summary.dump_script_start_time_to_brief_summary()
        if getattr(logger, "in_debug_mode", False):
            self._add_file_handler()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.need_report:
            self.report_script_result()
            self.clear_devices_buffer()
        logger.removeHandler(self.log_file_handler)
        logger.notice("\n** Finished executing script ==> %s", self.script)

    def clear_devices_buffer(self):
        for device in self.devices.values():
            device.clear_buffer()

    def report_script_result(self):
        device_require_collect = (
            self.result_manager.get_require_info_collection_devices()
        )
        devices_info = {
            dev: self.__collect_dut_info(dev) for dev in device_require_collect
        }
        self.result_manager.report_script_result(devices_info)

    def collect_dev_info_for_oriole(self, device):
        collect_on_the_fly = env.get_dut_info_on_fly()
        hardware_generation = env.get_device_hardware_generation(device, fallback="")
        return {
            "hardware_generation": hardware_generation,
            **self.cur_device.get_device_info(collect_on_the_fly),
        }

    def __collect_dut_info(self, device):
        logger.info(
            "Start reporting with information collected from device:%s",
            device,
        )
        self._switch_device_for_collect_info([device])
        dut_info_for_oriole = self.collect_dev_info_for_oriole(device)
        self.cur_device.resume_stdout()
        return dut_info_for_oriole

    def normalize_exp(self, exp):
        if exp == "eq":
            return "=="
        if exp == "lt":
            return "<"
        if isinstance(exp, str):
            eval_exp = env.get_var(exp)
            exp = eval_exp if eval_exp else exp
        if isinstance(exp, str) and exp.isdigit():
            return exp
        if isinstance(exp, (int, float)):
            return str(exp)
        if exp in ["+", "-", "*", "/", ">", "<", "(", ")"]:
            return exp

        return f"'{exp}'"

    def eval_expression(self, expression):
        new_expression = " ".join([self.normalize_exp(e) for e in expression])
        logger.debug("Normalized expression is %s", new_expression)
        try:
            return eval(new_expression)  # pylint:disable=eval-used
        except Exception:  # pylint:disable=broad-except
            logger.exception("Evaluation Failed!!")
            logger.info(
                "%s <=== %s",
                expression,
                "Evaluation Failed, review and file a ticket for Automation team if necessary!",
            )
        return None

    def __jump(self, target_line_number, forward=True):
        # jump to a script line
        step = 1 if forward else -1
        while True:
            code = self.script.get_compiled_code_line(self.program_counter)
            if code.line_number == target_line_number:
                break
            # code.line_number is the real line number in original script
            self.program_counter += step

    def jump_forward(self, line_number):
        self.__jump(line_number, forward=True)

    def jump_backward(self, line_number):
        self.__jump(line_number, forward=False)

    def execute(self):
        total_code_lines = self.script.get_program_counter_limit()
        while self.program_counter < total_code_lines:
            self.program_counter, code = self.script.update_code_to_execute(
                self.program_counter
            )
            if code.operation not in ["comment", "with_device"]:
                line_number = code.line_number
                if (
                    self.last_line_number is None
                    or self.last_line_number != line_number
                ):
                    logger.debug(
                        "%d  %s",
                        line_number,
                        self.script.get_script_line(line_number),
                    )
                    self.last_line_number = line_number

            parameters = code.parameters
            if code.operation not in ["switch_device", "setenv"]:
                parameters = self.variable_replacement(parameters)

            # Delegate operation execution to the operation handler
            self.api_handler.execute_api(code.operation, parameters)

            if code.operation not in [
                "if_not_goto",
                "else",
                "elseif",
                "until",
            ]:
                self.program_counter += 1
            if self.need_stop:
                break

    @staticmethod
    def _user_defined_variable_interpolation(_string):
        matched = re.findall(r"{\$.*?}", _string)
        for m in matched:
            var_name = m[2:-1]
            value = env.get_var(var_name)
            if value is not None:
                _string = _string.replace(m, str(value))
            else:
                logger.error("Failed to find the value for %s", var_name)
        return _string

    def _variable_interpolation(self, original_parameter):
        # for group file parsing, it also used this function, but it doesn't
        # have a self.cur_device, so add this guard check here
        current_device = self.cur_device.dev_name if self.cur_device else None
        parameter = env.variable_interpolation(
            original_parameter, current_device=current_device
        )
        parameter = self._user_defined_variable_interpolation(parameter)
        if original_parameter != parameter:
            logger.debug(
                "Variable interpolation: '%s' -> '%s'", original_parameter, parameter
            )
        return parameter

    def variable_replacement(self, parameters):
        replaced = []
        for parameter in parameters:
            if isinstance(parameter, str):
                parameter = self._variable_interpolation(parameter)
            replaced.append(parameter)
        return tuple(replaced)

    def get_all_scripts(self):
        return self.scripts
