import copy
import datetime
import json
import re
import time

import requests
import urllib3

from lib.services._summary import summary
from lib.services.environment import env
from lib.services.fos import platform_manager
from lib.services.log import logger
from lib.services.output import output

from .meta import (
    ORIOLE_FIELD_SOURCE,
    ORIOLE_REPORT_FIXED_FIELDS,
    ORIOLE_SUBMIT_API_URL,
    REPORT_FILE,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OrioleClient:

    def __init__(self):
        self.user = None
        self.password = None
        self.specified_fields = None
        self.submit_flag = "None"
        self.reports = []
        self.release_tag = None

    def set_user_cfg(self, args):
        self.submit_flag = (
            args.submit_flag if hasattr(args, "submit_flag") else self.submit_flag
        )
        if self.submit_flag:
            self.user = env.get_section_var("ORIOLE", "USER")
            self.password = env.get_section_var("ORIOLE", "ENCODE_PASSWORD")
        selected_fields = env.filter_section_items("ORIOLE", "RES_FIELD_")
        self.specified_fields = {k.lower(): v for k, v in selected_fields.items()}
        self.specified_fields.setdefault("mark", "AutoLib_v3")

    def send_oriole(self, user, password, report, release_tag):
        response = None
        try:
            payload = {
                "user": user,
                "password": password,
                "report": report,
                "release_tag": release_tag,
                "project": "FAP" if env.is_fap_dut() else "FOS",
            }
            taskpath_template = env.get_section_var("ORIOLE", "TASK_PATH")
            if taskpath_template:
                payload["task_path"] = taskpath_template.format(RELEASE=release_tag)
            response = requests.request(
                "POST", ORIOLE_SUBMIT_API_URL, data=payload, timeout=60, verify=False
            )
            succeeded = response.status_code == 200
        except Exception:
            logger.exception("Failed to report to oriole!")
            succeeded = False

        if not succeeded:
            if response is not None:
                logger.error("Error details from Oriole: %s", response.text)
            else:
                logger.error("Unable to access to %s", ORIOLE_SUBMIT_API_URL)
        return succeeded

    def submit(self):
        t1 = time.perf_counter()
        succeeded = False
        if self.reports:
            succeeded = self.send_oriole(
                self.user, self.password, json.dumps(self.reports), self.release_tag
            )
            if succeeded:
                logger.info("Succeeded to report to oriole.")
                for report in self.reports:
                    summary.update_reported(report["results"][0]["testcase_id"])
            else:
                logger.error("Failed to report to oriole.")
        t2 = time.perf_counter()
        logger.info("It takes %.1f s to submit.", t2 - t1)
        return succeeded

    @staticmethod
    def get_field_source():
        return ORIOLE_FIELD_SOURCE["FAP" if env.is_fap_dut() else "FOS"]

    def gen_plt_info_for_oriole(self, device_info, report):
        for k, fos_sources in OrioleClient.get_field_source().items():
            value = " ".join([device_info.get(f, "") for f in fos_sources])
            report[k] = value
        if env.get_vm_nic():
            report["vm_nic"] = env.get_vm_nic()
        if env.get_vm_os():
            report["vm_os"] = env.get_vm_os()
        report["platform_id"] = platform_manager.normalize_platform(report["platform"])
        report["pltgen"] = report.get(
            "hardware_generation", ""
        ) or platform_manager.get_platform_generation(report["platform_id"])

    def generate_product_report(self, testcase_id, is_passed, device_info):
        report = copy.deepcopy(ORIOLE_REPORT_FIXED_FIELDS)
        report["time"] = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
        self.gen_plt_info_for_oriole(device_info, report)
        result = (
            {
                "testcase_id": testcase_id,
                "result": "1",
            }
            if is_passed
            else {
                "testcase_id": testcase_id,
                "result": "2",
                "bug_id": "1",
            }
        )

        result.update(self.specified_fields)

        report["results"] = [result]
        return report

    def report(self, testcase_id, is_passed, device_info):
        product_report = self.generate_product_report(
            testcase_id, is_passed, device_info
        )
        result = False
        if product_report and testcase_id.isdigit():
            if self.submit_flag == "all" or (
                self.submit_flag == "succeeded" and is_passed
            ):
                self.release_tag = (
                    env.get_section_var("ORIOLE", "RELEASE") or device_info["version"]
                )
                self.reports.append(product_report)
                self.dump()
        return result

    def dump(self):
        json_str = json.dumps(self.reports, indent=4)
        new_lines = []
        results_begin = False
        results_lines = []
        for line in json_str.splitlines():
            if re.match(r'\s+"results": \[', line):
                results_begin = True
                results_lines.append(line)
            else:
                if results_begin:
                    results_lines.append(line.strip())
                    if re.match(r"\s+\]", line):
                        results_begin = False
                        new_lines.append("".join(results_lines))
                        results_lines = []
                else:
                    new_lines.append(line)
        report_str = "\n".join(new_lines)
        report_filename = output.compose_summary_file(REPORT_FILE)
        with open(report_filename, "w") as f:
            f.write(report_str)


oriole = OrioleClient()


if __name__ == "__main__":
    oriole.send_oriole(
        "rainxiao",
        "UW14SlI****",
        {
            "time": "2024-05-06 11:55:58",
            "project": "FOS",
            "task_path": "/FOS/7.6.0/Regression",
            "platform_id": "FGT_60F",
            "release": "7.6.0",
            "build": "3361",
            "SN": "FG4H1FT922900514",
            "bios": "06000006",
            "aveng": "7.00025",
            "avdef": "92.04027",
            "ipseng": "7.01002",
            "ipsdef": "6.00741",
            "pltgen": "Gen1",
            "snmp_mib": "3359",
            "total": 39,
            "results": [
                {"testcase_id": "964292", "result": "1"},
            ],
        },
        "7.6.0",
    )
