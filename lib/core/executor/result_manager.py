import re
from collections import defaultdict
from pathlib import Path

from lib.services import env, logger, oriole, summary
from lib.utilities.exceptions import ReportUnderPCWithoutDut


class ScriptResultManager:
    # TODO: simplify this pattern in future
    CLI_ERROR_PATTERNS = (
        "Unknown action",
        "command parse error",
        "Command fail",
        "incomplete command",
        "no tablename",
        "no object",
        "value parse error",
        "ambiguous command",
        "internal error",
        "discard the setting",
        "not found in table",
        "unset oper error ret",
        "Attribute(.*?)Must be set",
        "not found in datasource",
        "object set operator error",
        "node_check_object fail",
        "object check operator error",
        "value invalid",
        "invalid netmask",
        "invalid integer value",
        "invalid unsigned integer value",
        "invalid input",
        "duplicated with another vip",
    )

    def __init__(self):
        self.cli_errors = defaultdict(list)
        self.expect_result = defaultdict(list)
        self.report_qaid_and_dev_map = {}  # qaid: dev_name
        self.dev_info_requested_by_user = {}  # qaid: dev_info dict

    def add_dev_info_requested_by_user(self, testcase_id, dev_info):
        self.dev_info_requested_by_user[testcase_id] = dev_info

    def add_report_qaid_and_dev_map(self, testcase_id, dev_name):
        if not self.is_a_valid_testcase(testcase_id):
            logger.error("Results for %s could not be found", testcase_id)
        self.report_qaid_and_dev_map[testcase_id] = dev_name
        if (
            dev_name.startswith("PC")
            and testcase_id not in self.dev_info_requested_by_user
        ):
            dut = env.get_dut()
            if dut is None:
                raise ReportUnderPCWithoutDut(
                    "Please specify DUT or collect device info ahead when reporting under PC section."
                )
            self.report_qaid_and_dev_map[testcase_id] = dut

    def check_cli_error(self, script, line_number, command, result):
        failed_pattern = "|".join(ScriptResultManager.CLI_ERROR_PATTERNS)
        m = re.search(failed_pattern, result)
        if m:
            error = m.group()
            self.cli_errors[script].append((line_number, command, error))

    def get_formatted_command_errors(self):
        def _to_str(details):
            return "\n".join(
                f"# Line {line_number: 4}: {command}  <== {error}"
                for line_number, command, error in details
            )

        return "\n".join(
            f"{script}\n{_to_str(details)}\n"
            for script, details in self.cli_errors.items()
            if details
        )

    def add_qaid_expect_result(
        self, qaid, is_succeeded, line_number, expect_statement, cli_output
    ):
        self.expect_result[qaid].append(
            (
                is_succeeded,
                line_number,
                expect_statement,
                cli_output,
            )
        )

    def _get_failure_details(self):
        return "\n".join(
            f"# Line {line_number: 4}: {line}"
            for _, details in self.expect_result.items()
            for result, line_number, line, _ in details
            if not result
        )

    def get_brief_result(self):
        failure_lines = " ".join(
            f"{line_number}"
            for _, details in self.expect_result.items()
            for result, line_number, *_ in details
            if not result
        )
        return f"Failed {failure_lines}" if failure_lines else "Passed"

    def is_a_valid_testcase(self, testcase_id):
        return testcase_id in self.expect_result

    def is_qaid_succeeded(self, qaid):
        if qaid not in self.expect_result:
            return False
        return all(result for result, *_ in self.expect_result[qaid])

    def report_to_oriole(self, qaid, device_info):
        is_succeeded = self.is_qaid_succeeded(qaid)
        res_str = "passed" if is_succeeded else "failed"
        logger.info("Testcase %s %s", qaid, res_str)
        result = oriole.report(qaid, is_succeeded, device_info)
        summary.update_testcase(qaid, self.expect_result[qaid], result)
        return is_succeeded

    def report_all(self, report_qaid_and_dev_map, script_path):
        is_script_succeeded = True
        devices_info = {**report_qaid_and_dev_map, **self.dev_info_requested_by_user}
        for qaid in self.expect_result:
            if qaid not in self.report_qaid_and_dev_map:
                summary.dump_err_command_to_brief_summary(
                    f"QAID in Expect without 'report': {qaid}\n"
                )
                logger.warning("\n** QAID - %s in Expect without 'report' ***\n", qaid)
                continue
            dev = self.report_qaid_and_dev_map[qaid]
            if not self.report_to_oriole(qaid, devices_info[dev]):
                is_script_succeeded = False
        script_name = Path(script_path).stem
        result = self.get_brief_result()
        # 1. update summary results
        summary.dump_result_to_brief_summary(script_name, script_path, result)
        summary.update_testscript(
            script_name, "passed" if is_script_succeeded else "failed"
        )
        # 2. update failed expect results
        if not is_script_succeeded:
            summary.add_failed_testscript(
                script_name, script_path, self._get_failure_details()
            )
        # 3. update failed commands
        command_errors = self.get_formatted_command_errors()
        if command_errors:
            summary.add_failed_command(self.get_formatted_command_errors())

    def get_require_info_collection_devices(self):
        device_set = set()
        for qaid in self.expect_result:
            if qaid in self.dev_info_requested_by_user:
                continue
            if qaid in self.report_qaid_and_dev_map:
                dev = self.report_qaid_and_dev_map[qaid]
                device_set.add(dev)
        return device_set
