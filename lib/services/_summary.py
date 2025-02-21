import collections
import html
import os
import shutil
from datetime import datetime
from enum import Enum, IntEnum

# pylint: disable=wrong-import-order, import-error
from rich.console import Console
from rich.table import Table

from .environment import env
from .output import output
from .template_env import web_server_env

TEMPLATE_FILENAME = "summary.template"
LOADED_SUMMARY_TEMPLATE = web_server_env.get_template(TEMPLATE_FILENAME)


class OutputFileType(IntEnum):

    SUMMARY = 1
    BRIEF_SUMMARY = 2
    FAILED_TESTSCRIPT = 3
    FAILED_COMMAND = 4


class TestStatus(Enum):

    TESTING = "TESTING"
    TESTED = "TESTED"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PENDING = "PENDING"
    NOT_TESTED = "AWAITING TESTING"

    def __str__(self):
        return self.value


NOT_APPLICABLE = "N/A"


def get_output_filename(output_type):
    mapping = {
        OutputFileType.SUMMARY: "summary.html",
        OutputFileType.BRIEF_SUMMARY: "brief_summary.txt",
        OutputFileType.FAILED_TESTSCRIPT: "failed_testscripts.txt",
        OutputFileType.FAILED_COMMAND: "failed_commands.txt",
    }
    return output.compose_summary_file(mapping[output_type])


class Summary:

    SCRIPT_LINE_MSG_TEMPLATE = "{script_id:15}{script:64}{comment}"

    def __init__(self):
        self.testscripts = collections.defaultdict(tuple)
        self.testcases = collections.defaultdict(tuple)
        self.start_time = datetime.now().replace(microsecond=0)
        self.end_time = NOT_APPLICABLE
        self.qaid_script_mapping = {}

    def add_qaid_script_mapping(self, qaid, source_filepath):
        self.qaid_script_mapping[qaid] = os.path.relpath(source_filepath, os.getcwd())

    def add_testcase(self, id_, source_filepath):
        self.add_qaid_script_mapping(id_, source_filepath)
        self.testcases[id_] = (TestStatus.NOT_TESTED, (), False)
        self._generate()

    def update_testcase(self, id_, res, reported):
        self.testcases[id_] = (TestStatus.TESTED, res, reported)
        self._generate()

    def update_reported(self, id_):
        status, res, _ = self.testcases[id_]
        self.testcases[id_] = (status, res, True)
        self._generate()

    def add_testscript(self, script):
        self.add_qaid_script_mapping(script.id, script.source_file)
        self.testscripts[script.id] = (TestStatus.NOT_TESTED, NOT_APPLICABLE)
        self._generate()

    def update_testscript(self, id_, status, duration=NOT_APPLICABLE):
        self.testscripts[id_] = (status, duration)
        self._generate()

    def update_testscript_duration(self, id_, duration):
        status, _ = self.testscripts[id_]
        self.testscripts[id_] = (status, duration)
        self._generate()
        return status

    def show_summary(self):
        self.end_time = datetime.now().replace(microsecond=0)
        self._generate()
        self._print()

    def _statistic_testcases(self):
        statistics = {}
        statistics["total_number"] = len(self.testcases)
        statistics["passed_number"] = sum(
            status is TestStatus.TESTED and all(r for r, *_ in res)
            for status, res, *_ in self.testcases.values()
        )
        statistics["failed_number"] = sum(
            status is TestStatus.TESTED and any(not r for r, *_ in res)
            for status, res, *_ in self.testcases.values()
        )
        statistics["passed_percentage"] = 100 * round(
            (
                statistics["passed_number"] / statistics["total_number"]
                if statistics["total_number"]
                else 0
            ),
            2,
        )
        statistics["not_tested_number"] = sum(
            status == TestStatus.NOT_TESTED for status, *_ in self.testcases.values()
        )

        return statistics

    @staticmethod
    def _split_long_lines(text):
        # Split the text into lines
        lines = text.split("\n")

        # Iterate through each line
        for i, line in enumerate(lines):
            # Check if the line length exceeds 100 characters
            if len(line) > 100:
                # Split the line into chunks of maximum 100 characters
                chunks = [line[j : j + 100] for j in range(0, len(line), 100)]
                # Replace the original line with the split chunks
                lines[i : i + 1] = chunks

        # Join the lines back into a single string
        return "\n".join(lines)

    def _normalize_output_for_html(self, raw_output: str) -> str:
        """Normalize output for HTML by escaping special characters,
        splitting long lines, and replacing newlines with HTML line breaks."""
        escaped_output = html.escape(raw_output)
        normalized_output = self._split_long_lines(escaped_output)
        return normalized_output.replace("\n", "<br>")

    def _classify_testcases(self):
        results = []
        for testcase_id, (
            status,
            res,
            reported,
        ) in self.testcases.items():
            if status is not TestStatus.TESTED:
                continue

            details = [
                dict(
                    zip(
                        ["line_num", "expect", "output"],
                        [line_number, expect, self._normalize_output_for_html(output)],
                    )
                )
                for succeeded, line_number, expect, output in res
                if not succeeded
            ]
            final_res = all(succeeded for succeeded, *_ in res)
            result = {
                "id": testcase_id,
                "res": final_res,
                "details": details,
                "reported": reported,
            }
            results.append(result)
        return results

    def _render(self):
        not_tested_cases = [
            _id
            for _id, (status, *_) in self.testcases.items()
            if status is TestStatus.NOT_TESTED
        ]
        statistics = self._statistic_testcases()
        duration = NOT_APPLICABLE
        if self.end_time != NOT_APPLICABLE:
            duration = int((self.end_time - self.start_time).total_seconds())

        rendered_content = LOADED_SUMMARY_TEMPLATE.render(
            env_file=env.get_env_file_name(),
            test_file=env.get_test_file_name(),
            start_time=self.start_time,
            end_time=self.end_time,
            duration=duration,
            testscripts=self.testscripts,
            not_tested_cases=not_tested_cases,
            testcase_results=self._classify_testcases(),
            qaid_script_mapping=self.qaid_script_mapping,
            **statistics,
        )

        return rendered_content

    def _generate(self):
        rendered_content = self._render()
        summary_filepath = get_output_filename(OutputFileType.SUMMARY)
        with open(summary_filepath, "w+", encoding="utf-8") as f:
            f.write(rendered_content)
        return rendered_content

    def _print(self):
        table = Table(title="Testcase Results")
        table.add_column("Oriole QAID", justify="center", style="cyan", no_wrap=True)
        table.add_column("Result", justify="center", style="magenta")
        table.add_column("Oriole Reported", justify="center", style="magenta")

        for testcase in self._classify_testcases():
            test_result = str(
                TestStatus.PASSED if testcase["res"] else TestStatus.FAILED
            )
            table.add_row(
                testcase["id"],
                str(test_result),
                "Yes" if testcase["reported"] else "No",
            )

        console = Console()
        console.print(table)

    def write_notes_to_file(
        self, script_id, script, comment, note_type: OutputFileType
    ):
        failed_commands_file_name = get_output_filename(note_type)
        if note_type in (
            OutputFileType.FAILED_TESTSCRIPT,
            OutputFileType.FAILED_COMMAND,
        ):
            comment = f"\n{comment}"
        failed_info = self.SCRIPT_LINE_MSG_TEMPLATE.format(
            script_id=script_id, script=script, comment=f"{comment}\n\n"
        )
        with open(failed_commands_file_name, "a", encoding="utf-8") as f:
            f.write(failed_info)
        # add failure or error to to brief summary
        if note_type is OutputFileType.FAILED_TESTSCRIPT:
            self.dump_str_to_brief_summary(f"##### Expect Failures:{comment}")
        if note_type is OutputFileType.FAILED_COMMAND:
            self.dump_str_to_brief_summary(f"##### Command Errors:{comment}")

    def dump_str_to_brief_summary(self, comment):
        brief_summary_file_name = get_output_filename(OutputFileType.BRIEF_SUMMARY)
        with open(brief_summary_file_name, "a", encoding="utf-8") as f:
            f.write(f"{comment}\n")

    def dump_script_start_time_to_brief_summary(self):
        brief_summary_file_name = get_output_filename(OutputFileType.BRIEF_SUMMARY)
        with open(brief_summary_file_name, "a", encoding="utf-8") as f:
            current_time = datetime.now().replace(microsecond=0)
            f.write(f"# Current Time: {current_time}\n")


summary = Summary()


if __name__ == "__main__":
    print("begin to copy.")
    shutil.copyfile(
        (
            "/home/fosqa/sambashare/autolib/myversion/bmrk_autolib/"
            "summary/AutoTesting_Summary_VM04_Version_7.2.1_Build_1198_Testgroup_group.txt_20220505175911.html"
        ),
        "/var/www/autolib/index.html",
    )
