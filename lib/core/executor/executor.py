import logging
import pdb
import re
from typing import Union

from lib.core.compiler import Group, IncludeScript, Script
from lib.services import (
    ScriptResultManager,
    TestStatus,
    add_logger_handler,
    env,
    logger,
    output,
    summary,
)
from lib.utilities import OperationFailure, TestFailed, sleep_with_progress

from .if_stack import if_stack


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

    def _switch_device(self, parameters):
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]
        self.cur_device.switch()

    def _switch_device_for_collect_info(self, parameters):
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]
        self.cur_device.pause_stdout()
        self.cur_device.switch_for_collect_info()

    def _is_reset_command(self, cmd):
        pattern = re.compile(
            r"(exe.*factoryreset.*|exe.*(?:forticarrier|factory|crypto)-license|resetFirewall)"
        )
        return re.match(pattern, cmd)

    def _command(self, parameters):
        if isinstance(self.script, Group):
            _, script_file, *_ = parameters[0].split()
            self.scripts[self.last_line_number] = script_file
            return

        cmd = parameters[0]

        if self._is_reset_command(cmd) and self.auto_login:
            self._resetFirewall(cmd)
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

    def _clearbuff(self, _):
        self.cur_device.clear_buffer()

    def _breakpoint(self, _):
        self.script.breakpoint()

    def _enter_dev_debugmode(self, _):
        # pylint: disable=forgotten-debug-statement
        pdb.set_trace()

    def _resetFirewall(self, cmd):
        if not cmd:
            cmd = "execute factoryreset"
        self.cur_device.reset_config(cmd)
        sleep_with_progress(1)
        # to avoid some error message message other commands

    def _resetFAP(self, cmd):
        if not cmd:
            cmd = "factoryreset"
        self.cur_device.reset_config(cmd)

    def _send_literal(self, parameters):
        if (
            parameters
            and len(parameters[0]) >= 2
            and parameters[0].startswith('"')
            and parameters[0].endswith('"')
        ):
            cmd = parameters[0][1:-1]
            cmd = cmd.encode().decode("unicode_escape").replace("CRLF", "\r\n")
            self.cur_device.send(cmd)
        else:
            logger.error("raw command must be DOUBLE-QUOTED!!!")

    def _restore_image(self, parameters):
        release, build = parameters
        self.cur_device.restore_image(release, build, False)

    def _clean_buffer(self, _):
        self.cur_device.clear_buffer()

    def _clear_buffer(self, _):
        self.cur_device.clear_buffer()

    def _send_line(self, parameters):
        s = parameters[0] if parameters else ""

        self.cur_device.send_line(s)

    def _send(self, parameters):
        s = parameters[0] if parameters else ""
        self.cur_device.send(s)

    def _search(self, parameters):
        if len(parameters) == 2:
            rule, timeout = parameters
            timeout = int(timeout)
            self.cur_device.search(rule, timeout)
        elif len(parameters) == 3:
            rule, timeout, pos = parameters
            pos = int(pos)
            timeout = int(timeout)
            self.cur_device.search(rule, timeout, pos)

    def _normalize_regexp(self, reg_exp):
        if re.search(r"(?<!\\)\\\\\\\(", reg_exp):
            reg_exp = re.sub(r"(?<!\\)\\\\\\\(", r"\(", reg_exp)
            logger.debug(reg_exp)
            reg_exp = re.sub(r"(?<!\\)\\\\\\\)", r"\)", reg_exp)
            logger.debug(reg_exp)
        reg_exp = reg_exp.replace(r"\\\\", "\\")
        logger.debug(reg_exp)
        if reg_exp.startswith('"') and reg_exp.endswith('"'):
            reg_exp = reg_exp[1:-1]
        if reg_exp.startswith("'") and reg_exp.endswith("'"):
            reg_exp = reg_exp[1:-1]
        return reg_exp

    def _expect_ctrl_c(self, parameters):
        self.cur_device.send_command("ctrl_c")
        self._expect(parameters)

    def _handle_need_retry_expect(self, retry_command):
        if env.need_retry_expect():
            if retry_command is None:
                previous_vm_code = self.script.get_compiled_code_line(
                    self.program_counter - 1
                )
                if previous_vm_code.operation == "command":
                    previous_command = previous_vm_code.parameters[0]
                    if previous_command.startswith(
                        ("curl", "wget", "exe log display", "execute log display")
                    ):
                        return f'"{previous_command}"', 3
        return retry_command, -1

    # pylint: disable=too-many-positional-arguments
    def _log_expect_result(self, is_succeeded, qaid, rule, fail_match, timeout_timer):
        if is_succeeded:
            logger.debug(
                "\n* Expect Succeeded(%s) *\nRule: '%s'\n'fail_match' Flag: %s\nTimeout Timer: %ss\n\n",
                qaid,
                rule,
                fail_match,
                timeout_timer,
            )
        else:
            logger.notice(
                "\n* Expect Failure(%s) *\nRule: '%s'\n'fail_match' Flag: %s\nTimeout Timer: %ss\n\n",
                qaid,
                rule,
                fail_match,
                timeout_timer,
            )

    def _expect(self, parameters):
        (
            rule,
            qaid,
            wait_seconds,
            fail_match,
            _,
            _,
            clear,
            retry_command,
            retry_cnt,
        ) = parameters
        wait_seconds = int(wait_seconds)
        retry_cnt = int(retry_cnt)
        fail_match = fail_match == "match"
        rule = self._normalize_regexp(rule)
        matched, cli_output = self.cur_device.expect(rule, wait_seconds, clear == "yes")
        is_succeeded = bool(matched) ^ fail_match
        retry_command, _retry_cnt = self._handle_need_retry_expect(retry_command)
        if _retry_cnt != -1:
            retry_cnt = _retry_cnt
        cnt = 1
        while not is_succeeded and retry_command is not None and cnt < retry_cnt:
            logger.info("Begin to retry for expect, cur cnt: %s", cnt)
            self.cur_device.send_command(retry_command[1:-1])
            matched, cli_output = self.cur_device.expect(
                rule, wait_seconds, clear == "yes"
            )
            is_succeeded = bool(matched) ^ fail_match
            cnt += 1

        self.result_manager.add_qaid_expect_result(
            qaid,
            is_succeeded,
            self.last_line_number,
            cli_output,
        )
        self._log_expect_result(is_succeeded, qaid, rule, fail_match, wait_seconds)

    def _expect_OR(self, parameters):
        (rule1, rule2, fail1_match, fail2_match, qaid, wait_seconds) = parameters
        wait_seconds = int(wait_seconds)
        fail1_match = fail1_match == "match"
        fail2_match = fail2_match == "match"

        rule1 = self._normalize_regexp(rule1)
        result1, cli_output1 = self.cur_device.expect(rule1, wait_seconds)

        rule2 = self._normalize_regexp(rule2)
        result2, cli_output2 = self.cur_device.expect(rule2, wait_seconds)

        is_succeeded = bool(result1) ^ fail1_match | bool(result2) ^ fail2_match
        self.result_manager.add_qaid_expect_result(
            qaid,
            is_succeeded,
            self.last_line_number,
            f"output of {rule1}:\n{cli_output1}\noutput of {rule2}:\n{cli_output2}\n",
        )

        self._log_expect_result(
            is_succeeded,
            qaid,
            (rule1, rule2),
            (fail1_match, fail2_match),
            wait_seconds,
        )

    def _myftp(self, parameters):
        (
            rule,
            ip,
            qaid,
            fail_match,
            wait_seconds,
            user_name,
            password,
            command,
            action,
        ) = parameters
        wait_seconds = int(wait_seconds)
        fail_match = fail_match == "match"
        rule = self._normalize_regexp(rule)
        self.cur_device.send_line(f"ftp {ip}")
        self.cur_device.search("Name", pos=-1)
        self.cur_device.send_line(user_name)
        self.cur_device.search("Password:", pos=-1)
        self.cur_device.send_line(password)
        if command is not None:
            self.cur_device.search("[#>]", pos=-1)
            self.cur_device.send_line(command)

        result, cli_output = self.cur_device.expect(rule, wait_seconds)

        is_succeeded = bool(result) ^ fail_match
        self.result_manager.add_qaid_expect_result(
            qaid,
            is_succeeded,
            self.last_line_number,
            cli_output,
        )

        result_str = TestStatus.PASSED if is_succeeded else TestStatus.FAILED
        logger.info(
            "%s to to expect for testcase: %s, with rule:%s and fail_match: %s in %ss.",
            result_str,
            qaid,
            rule,
            fail_match,
            wait_seconds,
        )
        self.cur_device.send_line("quit")
        self.cur_device.search(".+")

        if result_str is not TestStatus.PASSED:
            if action == "stop":
                raise OperationFailure("FTP Failed and user requested to STOP!!!")
            if action == "nextgroup":
                raise TestFailed("FTP failed and user requested to go to next!!!")

    def _mytelnet(self, parameters):
        (
            _,
            rule,
            ip,
            qaid,
            fail_match,
            wait_seconds,
            user_name,
            password,
        ) = parameters
        wait_seconds = int(wait_seconds)
        fail_match = fail_match == "match"
        rule = self._normalize_regexp(rule)
        self.cur_device.send_line(f"telnet {ip}")
        self.cur_device.search("login:")
        self.cur_device.send_line(user_name)
        self.cur_device.search("Password:")
        self.cur_device.send_line(password)
        result, cli_output = self.cur_device.expect(rule, wait_seconds)
        is_succeeded = bool(result) ^ fail_match
        self.result_manager.add_qaid_expect_result(
            qaid,
            is_succeeded,
            self.last_line_number,
            cli_output,
        )
        result_str = "Succeeded" if is_succeeded else "Failed"
        logger.info(
            "%s to to expect for testcase: %s, with rule:%s and fail_match: %s in %ss.",
            result_str,
            qaid,
            rule,
            fail_match,
            wait_seconds,
        )
        self.cur_device.send_line("^]")
        self.cur_device.search(".+")

    def _setenv(self, parameters):
        var_name, var_val, device_name = parameters
        var_val = env.get_var(var_val)
        env.set_section_var(device_name, var_name, var_val)
        logger.info(
            "Set env variable: device_name:'%s', var_name:'%s', var_val:'%s'",
            device_name,
            var_name,
            var_val,
        )

    def _compare(self, parameters):
        var1, var2, qaid, fail_match = parameters
        var1 = env.get_var(var1)
        var2 = env.get_var(var2)
        is_succeeded = (str(var1) == str(var2)) ^ (fail_match == "eq")
        self.result_manager.add_qaid_expect_result(
            qaid,
            is_succeeded,
            self.last_line_number,
            f"v1:{var1} v2:{var2}",
        )

        result_str = "Succeeded" if is_succeeded else "Failed"
        logger.info(
            "%s to to compare for testcase: %s, fail_match: %s.",
            result_str,
            qaid,
            fail_match,
        )

    def _comment(self, parameters):
        comment = parameters[0]
        logger.info(comment)
        summary.dump_str_to_brief_summary(comment)

    def report_script_result(self):
        device_require_collect = (
            self.result_manager.get_require_info_collection_devices()
        )
        devices_info = {
            dev: self.__collect_dut_info(dev) for dev in device_require_collect
        }
        self.result_manager.report_script_result(devices_info)

    def _report(self, parameters):
        qaid = parameters[0]
        dut = self.cur_device.dev_name if self.cur_device else env.get_dut()
        self.result_manager.add_report_qaid_and_dev_map(qaid, dut)

    def __collect_dev_info_for_oriole(self, device):
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
        dut_info_for_oriole = self.__collect_dev_info_for_oriole(device)
        self.cur_device.resume_stdout()
        return dut_info_for_oriole

    def _collect_dev_info(self, parameters):
        qaid = parameters[0]
        device = self.cur_device.dev_name
        device_info = self.__collect_dev_info_for_oriole(device)
        self.result_manager.add_dev_info_requested_by_user(qaid, device_info)

    def _setvar(self, parameters):
        rule, name = parameters
        rule = self._normalize_regexp(rule)
        logger.info("rule in set_var is %s", rule)
        match, _ = self.cur_device.expect(rule)
        if match:
            value = match.group(1)
            env.add_var(name, value)
            logger.info("Succeeded to set variable %s to '%s'", name, value)
        else:
            logger.error("Failed to execute setvar.")

    def _varexpect(self, parameters):
        (
            _,
            variable,
            qaid,
            str_wait_seconds,
            fail_match,
            _,
        ) = parameters
        wait_seconds = int(str_wait_seconds)
        fail_match = fail_match == "match"

        value = env.get_var(variable)

        value = variable if value is None else value
        # For this scenario: varexpect -v "{$SerialNum}" -for 803092 -t 20
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        result, cli_output = self.cur_device.expect(value, wait_seconds)
        is_succeeded = bool(result) ^ fail_match
        self.result_manager.add_qaid_expect_result(
            qaid,
            is_succeeded,
            self.last_line_number,
            cli_output,
        )
        result_str = "Succeeded" if is_succeeded else "Failed"
        logger.info(
            "%s to expect for testcase: %s, with variable:%s value: (%s) and fail_match: %s in %ss.",
            result_str,
            qaid,
            variable,
            value,
            fail_match,
            wait_seconds,
        )

    def _sleep(self, parameters):
        seconds = int(parameters[0])
        seconds = env.get_actual_timer(self.cur_device.dev_name, seconds)
        sleep_with_progress(seconds, logger_func=logger.notice)

    def _forcelogin(self, _):
        self.cur_device.force_login()

    def _setlicense(self, parameters):
        lic_type, file_name, var_name = parameters
        env.set_license_var(lic_type, file_name, var_name)

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
            logger.exception("Evaludation Failed!!")
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

    def _if_not_goto(self, parameters):
        line_number = parameters[-1]
        expression = parameters[:-1]
        if self.eval_expression(expression):
            if_stack.push(True)
            self.program_counter += 1
        else:
            if_stack.push(False)
            self.jump_forward(line_number)

    def _else(self, parameters):
        line_number = parameters[-1]
        if if_stack.top():
            self.jump_forward(line_number)
        else:
            self.program_counter += 1

    def _elseif(self, parameters):
        line_number = parameters[-1]
        expression = parameters[:-1]
        if if_stack.top():
            self.jump_forward(line_number)
        else:
            if self.eval_expression(expression):
                if_stack.pop()
                if_stack.push(True)
                self.program_counter += 1
            else:
                self.jump_forward(line_number)

    def _endif(self, _):
        if_stack.pop()

    def _intset(self, parameters):
        var_name = parameters[0]
        var_value = parameters[1]
        env.add_var(var_name, var_value)

    def _strset(self, parameters):
        var_name = parameters[0]
        var_value = parameters[1]
        env.add_var(var_name, var_value)

    def _loop(self, _):
        pass

    def _intchange(self, parameters):
        new_expression = []
        var_name = None
        for token in parameters:
            new_token = env.get_var(token)
            if new_token is None:
                new_expression.append(token)
            else:
                new_expression.append(new_token)
                var_name = token
        var_val = self.eval_expression(new_expression)
        env.add_var(var_name, var_val)

    def _until(self, parameters):
        line_number = parameters[0]
        expression = parameters[1:]
        new_expression = []
        for token in expression:
            if token.startswith("$"):
                new_token = env.get_var(token[1:])
                if new_token is None:
                    new_expression.append(token)
                else:
                    new_expression.append(new_token)
            else:
                new_expression.append(token)
        if self.eval_expression(new_expression):
            self.program_counter += 1
        else:
            self.jump_backward(line_number)

    def _with_device(self, parameters):
        dev_name = parameters[0]
        self.cur_device = self.devices[dev_name]

    def _include(self, parameters):
        if self.cur_device is None:
            include_script = IncludeScript(parameters[0])
        else:
            include_script = IncludeScript(parameters[0], self.cur_device.dev_name)
        with Executor(include_script, self.devices, False) as executor:
            executor.cur_device = self.cur_device
            executor.execute()

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
            func = getattr(self, f"_{code.operation}")
            parameters = code.parameters
            if code.operation not in ["switch_device", "setenv"]:
                parameters = self.variable_replacement(parameters)

            func(parameters)
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

    def _keep_running(self, parameters):
        value = bool(int(parameters[0]))
        self.cur_device.set_keep_running(value)

    def _confirm_with_newline(self, parameters):
        value = bool(int(parameters[0]))
        self.cur_device.set_confirm_with_newline(value)

    def _wait_for_confirm(self, parameters):
        value = bool(int(parameters[0]))
        self.cur_device.set_wait_for_confirm(value)

    def _auto_login(self, parameters):
        value = bool(int(parameters[0]))
        self.auto_login = value
