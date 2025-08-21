import copy
import datetime
import json
import os
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
    ORIOLE_SUBMIT_TIMEOUT,
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

    def report_to_submit(self):
        if self.submit_flag == "None":
            return ""
        filename, ext = os.path.splitext(REPORT_FILE)
        filename = f"{filename}_{self.submit_flag.lower()}"
        report_filename = output.compose_summary_file(f"{filename}{ext}")
        return report_filename

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

    def send_oriole(self):
        report_file = self.report_to_submit()
        if report_file and os.path.exists(report_file):
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    report = f.read()

                payload = {
                    "user": self.user,
                    "password": self.password,
                    "report": report,
                    "release_tag": self.release_tag,
                    "project": "FAP" if env.is_fap_dut() else "FOS",
                }

                task_path_template = env.get_section_var("ORIOLE", "TASK_PATH")
                if task_path_template:
                    payload["task_path"] = task_path_template.format(
                        RELEASE=self.release_tag
                    )

                response = requests.request(
                    "POST",
                    ORIOLE_SUBMIT_API_URL,
                    data=payload,
                    timeout=ORIOLE_SUBMIT_TIMEOUT,
                    verify=False,
                )
                if response.status_code == 200:
                    return True
                logger.error(
                    "Failed to report to oriole for %s! Response: %s",
                    report_file,
                    response.text,
                )
            except Exception:
                logger.exception("Failed to report to oriole for %s!", report_file)
                return False
        logger.warning("No report to report to oriole for %s!", report_file)
        return False

    def submit(self):
        t1 = time.perf_counter()
        succeeded = False
        if self.reports:
            succeeded = self.send_oriole()
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
        if product_report and testcase_id.isdigit():
            self.release_tag = (
                env.get_section_var("ORIOLE", "RELEASE") or device_info["version"]
            )
            self.reports.append(product_report)
            self.dump()

    @staticmethod
    def _dump(reports, only_succeeded=False):
        json_str = json.dumps(reports, indent=4)
        filename, ext = os.path.splitext(REPORT_FILE)
        filename = f"{filename}_succeeded" if only_succeeded else f"{filename}_all"
        report_filename = output.compose_summary_file(f"{filename}{ext}")
        with open(report_filename, "w") as f:
            f.write(json_str)

    def dump(self):
        succeeded_reports = [
            r for r in self.reports if r["results"] and r["results"][0]["result"] == "1"
        ]
        if succeeded_reports:
            self._dump(succeeded_reports, only_succeeded=True)
        self._dump(self.reports)


oriole = OrioleClient()
