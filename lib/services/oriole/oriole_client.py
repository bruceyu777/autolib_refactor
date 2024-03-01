import copy
import csv
import datetime
import json
import os

import requests
import time
from ..environment import env
from ..log import logger
from ..output import output
from ..summary import summary

from .settings import (
    CFG_FILE_DIR,
    HOST,
    ORIOLE_REPORT_FIXED_FIELDS,
    PLATREV_CSV_FILE,
    PORT,
    PRODUCT_SHORTEN,
)

REPORT_FILE = "report.json"


def get_short_product_name(name):
    for key in sorted(PRODUCT_SHORTEN, reverse=True):
        if name.startswith(key):
            return name.replace(key, PRODUCT_SHORTEN[key]).replace("-", "_")

    return name


class OrioleClient:
    def __init__(
        self,
        platrev_csv_file=os.path.join(CFG_FILE_DIR, PLATREV_CSV_FILE),
    ):
        self.user = None
        self.password = None

        self.platrev_csv_file = platrev_csv_file
        self.platform_revision = {}
        self.api = f"http://{HOST}:{PORT}/api/"
        self.file_name = output.compose_summary_file(REPORT_FILE)
        self.submit_flag = "None"
        self.reports = []
        self.get_platform_generation()
        self.release_tag = None


    def set_credential(self, user, password):
        self.user = user
        self.password = password

    def set_user_cfg(self, args):
        self.user = env.get_section_var("ORIOLE", "USER")
        self.password = env.get_section_var("ORIOLE", "ENCODE_PASSWORD")
        self.submit_flag = (
            args.submit_flag if hasattr(args, "submit_flag") else self.submit_flag
        )

    def send_oriole(self, user, password, report, release_tag):
        try:
            url = self.api + "oriole"
            payload = dict(
                zip(
                    ["user", "password", "report", "release_tag"],
                    [user, password, report, release_tag],
                )
            )
            response = requests.request("POST", url, data=payload, timeout=60)
            return (
                response.status_code == requests.codes.ok  # pylint: disable=no-member
            )
        except Exception as e:
            logger.error("Failed to report to oriole: %s", e)
            return False

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
                logger.error("Faliled to report to oriole.")
        t2 = time.perf_counter()
        logger.notify("It takes %s s to submit.", t2 - t1)
        return succeeded

    def get_platform_generation(self):
        with open(self.platrev_csv_file) as f:
            f_csv = csv.DictReader(f)
            for row in f_csv:
                platform = row["plt_name"]
                self.platform_revision[platform] = row["rev"]

    @staticmethod
    def get_testcases(csv_file, testcases_product_id_map):
        with open(csv_file) as f:
            f_csv = csv.DictReader(f)
            for row in f_csv:
                product = row["Objective"].split(":")[0].replace("-", "_")
                testcases_product_id_map[product] = row["QAID"]

    @staticmethod
    def gen_plt_info_for_oriole(device_info, report):
        report["platform"] = device_info["platform"]
        report["build"] = device_info["build"][-4:]
        report["aveng"] = device_info.get("AV Engine", "")
        avdef = device_info.get("Virus Definitions", "")
        eavdf = device_info.get("Extended set", "")
        favdf = device_info.get("Flow-based Virus Definitions", "")
        report["avdef"] = " ".join([avdef, eavdf, favdf])
        report["ipseng"] = device_info.get("IPS Attack Engine", "")
        atkver = device_info.get("Attack Definitions", "")
        etkver = device_info.get("Attack Extended Definitions", "")
        report["ipsdef"] = " ".join([atkver, etkver])
        report["bios"] = device_info.get("bios_version", "")
        report["SN"] = device_info.get("serial", "")
        if env.get_vm_nic():
            report["vm_nic"] = env.get_vm_nic()
        if env.get_vm_os():
            report["vm_os"] = env.get_vm_os()

    def generate_product_report(self, testcase_id, is_passed, device_info):
        short_product = get_short_product_name(device_info["platform"])
        report = copy.deepcopy(ORIOLE_REPORT_FIXED_FIELDS)

        report["time"] = datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
        report["platform_id"] = short_product
        report["pltgen"] = self.platform_revision.get(short_product, "1")

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
                # result = self.submit(product_report, device_info["version"])
                self.release_tag = device_info["version"]
                self.reports.append(product_report)
                self.dump()
        return result

    def dump(self):
        with open(self.file_name, "w") as f:
            f.write(json.dumps(self.reports, indent=4))


    @staticmethod
    def _compose_filename():
        return "oriole_report.json"


oriole = OrioleClient()
