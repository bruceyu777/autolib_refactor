import collections
import shutil
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

# pylint: disable=wrong-import-order, import-error
from rich.console import Console
from rich.table import Table

from .environment import env
from .output import output
import os
import html

# from lib.services.oriole.oriole_client import oriole

SUMMARY_FILE_NAME = "summary.html"
TEMPLATE_FILE_NAME = "summary.template"
BRIEF_SUMMARY_FILE_NAME = "brief_summary.txt"
FAILED_TESTSCRIPTS_FILE_NAME = "failed_testscripts.txt"
TEMPLATE_FILE_DIR = os.path.dirname(os.path.realpath(__file__))


class Summary:
    def __init__(self):
        self.testscripts = collections.defaultdict(tuple)
        self.testcases = collections.defaultdict(tuple)
        self.file_name = output.compose_summary_file(SUMMARY_FILE_NAME)
        self.failed_testscripts_file_name = output.compose_summary_file(
            FAILED_TESTSCRIPTS_FILE_NAME
        )
        self.brief_summary_file_name = output.compose_summary_file(
            BRIEF_SUMMARY_FILE_NAME
        )
        self.start_time = datetime.now().replace(microsecond=0)
        self.end_time = "NA"

    def add_testcase(self, id_):
        self.testcases[id_] = ("Not Tested", (), False)
        self._generate()

    def update_testcase(self, id_, res, reported):
        self.testcases[id_] = ("Tested", res, reported)
        self._generate()

    def update_reported(self, id_):
        status, res, reported = self.testcases[id_]
        self.testcases[id_] = status, res, True
        self._generate()

    def add_testscript(self, id_):
        self.testscripts[id_] = ("Not Tested", "NA")
        self._generate()

    def update_testscript(self, id_, status, duration="NA"):
        self.testscripts[id_] = (status, duration)
        self._generate()
        # oriole.dump()

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
            status == "Tested" and all(r for r, *_ in res)
            for status, res, _ in self.testcases.values()
        )
        statistics["failed_number"] = sum(
            status == "Tested" and any(not r for r, *_ in res)
            for status, res, _ in self.testcases.values()
        )
        statistics["passed_percentage"] = 100 * round(
            statistics["passed_number"] / statistics["total_number"]
            if statistics["total_number"]
            else 0,
            2,
        )
        statistics["not_tested_number"] = sum(
            status == "Not Tested" for status, *_ in self.testcases.values()
        )

        return statistics

    @staticmethod
    def _split_long_lines(text):
        # Split the text into lines
        lines = text.split('\n')

        # Iterate through each line
        for i, line in enumerate(lines):
            # Check if the line length exceeds 100 characters
            if len(line) > 100:
                # Split the line into chunks of maximum 100 characters
                chunks = [line[j:j+100] for j in range(0, len(line), 100)]
                # print(chunks)
                # Replace the original line with the split chunks
                lines[i:i+1] = chunks

        # Join the lines back into a single string
        # print(lines)
        return '\n'.join(lines)


    def _normalize_output_for_html(self, output):
        output = html.escape(output)
        output = self._split_long_lines(output)
        return output.replace('\n', '<br>')


    def _classify_testcases(self):
        results = []
        for testcase_id, (status, res, reported) in self.testcases.items():
            if status != "Tested":
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

        file_loader = FileSystemLoader(TEMPLATE_FILE_DIR)
        render_env = Environment(loader=file_loader)
        template = render_env.get_template(TEMPLATE_FILE_NAME)
        not_tested_cases = [
            _id
            for _id, (status, *_) in self.testcases.items()
            if status == "Not Tested"
        ]
        statistics = self._statistic_testcases()
        duration = "NA"
        if self.end_time != "NA":
            duration = int((self.end_time - self.start_time).total_seconds())

        rendered_content = template.render(
            env_file=env.get_env_file_name(),
            test_file=env.get_test_file_name(),
            start_time=self.start_time,
            end_time=self.end_time,
            duration=duration,
            testscripts=self.testscripts,
            not_tested_cases=not_tested_cases,
            testcase_results=self._classify_testcases(),
            **statistics,
        )

        return rendered_content

    def _generate(self):
        rendered_content = self._render()
        with open(self.file_name, "w+", encoding="utf-8") as f:
            f.write(rendered_content)
        return rendered_content

    def _print(self):
        table = Table(title="Testcase Results")
        table.add_column(
            "Testcase Id", justify="right", style="cyan", no_wrap=True
        )
        table.add_column("Result", style="magenta")
        table.add_column("Reported", style="magenta")

        for testcase in self._classify_testcases():
            table.add_row(
                testcase["id"],
                "Passed" if testcase["res"] else "Failed",
                "Yes" if testcase["reported"] else "No",
            )

        console = Console()
        console.print(table)

    def add_failed_testscript(
        self, script_id, script, comment="Failed testscript"
    ):
        with open(
            self.failed_testscripts_file_name, "a", encoding="utf-8"
        ) as f:
            f.write(f"{script_id}  {script} {comment}\n")

    def dump_result_to_brief_summary(self, script_id, script, result):
        with open(self.brief_summary_file_name, "a", encoding="utf-8") as f:
            f.write(f"{script_id} {script} {result}\n")

    def dump_comments_to_brief_summary(self, comment):
        with open(self.brief_summary_file_name, "a", encoding="utf-8") as f:
            f.write(f"{comment}\n")

    def dump_script_start_time_to_brief_summary(self):
        with open(self.brief_summary_file_name, "a", encoding="utf-8") as f:
            current_time = datetime.now().replace(microsecond=0)
            f.write(f"Current Time: {current_time}\n")


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
