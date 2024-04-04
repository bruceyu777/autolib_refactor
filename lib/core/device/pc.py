from lib.services import env
import time
from .computer import Computer
from .computer_conn import ComputerConn
from lib.services import logger

class Pc(Computer):
    def __init__(self, dev_name):
        self.dev_cfg = env.get_dev_cfg(dev_name)
        super().__init__(dev_name)
        self._device_info = None

    def _compose_conn(self):
        return self.dev_cfg["connection"]

    def connect(self):
        self.conn = ComputerConn(
            self.dev_name,
            self._compose_conn(),
            user_name=self.dev_cfg["username"],
            password=self.dev_cfg["password"],
        )
        self.send_command("")
        self.clear_buffer()

    def force_login(self):
        self.conn.close()
        self.connect()

    def send_command(self, command):
        # return super().send_command(command+"\r", timeout=60)
        return super().send_command(command, timeout=60)

    def show_command_may_have_more(self, command, rule):
        self.send_line(command)
        time.sleep(1)
        self.send_line(" ")
        matched, _ = self.search(rule, 10)
        return matched.groupdict() if matched else {}

    def _return_to_user_view(self):
        self.send_command("end")

    def _goto_global_view(self):
        self.send_command("config global")

    @property
    def system_status(self):
        rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*?"
            r"Serial-Number: (?P<serial>[^\r\n]*).*?"
            r"BIOS version: (?P<bios_version>[^\r\n]*).*?"
            r"Virtual domain configuration: (?P<vdom_mode>[^\r\n]*).*?"
            r"Branch point: (?P<branch_point>[^\r\n]*).*?"
        )
        matched = self.show_command_may_have_more("get system status", rule)
        if not matched:
            rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
            r"Serial-Number: (?P<serial>[^\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
            r"Branch point: (?P<branch_point>[^\n]*).*"
        )
            matched = self.show_command_may_have_more("get system status", rule)
        return matched



    def get_autoupdate_versions(self, is_vdom_enabled=None):
        # raise Exception()
        # if is_vdom_enabled is None:
        #     is_vdom_enabled = self.is_vdom_enabled
        if is_vdom_enabled:
            self._goto_global_view()
        VERSION_FIELDS = [
            "AV Engine",
            "Virus Definitions",
            "Extended set",
            "IPS Attack Engine",
            "Attack Definitions",
            "Attack Extended Definitions",
            "Application Definitions",
            "IPS Malicious URL Database",
            "Flow-based Virus Definitions",
            "Botnet Domain Database",
            "URL Allow list",
        ]
        rule = "".join(
            rf"{fd}\n---------\nVersion: ([\d.]+).*" for fd in VERSION_FIELDS
        )

        self.clear_buffer()
        logger.debug("The rule for diag autoupdate version is: %s", rule)
        match, output = super().send_command(
            "diag autoupdate versions", rule, timeout=10
        )
        logger.debug("The reulst for diag autoupdate versions: %s", match)
        if is_vdom_enabled:
            self._return_to_user_view()
        result =  {fd: match.group(i + 1) for i, fd in enumerate(VERSION_FIELDS)} if match  else {}

        logger.debug("The extracted autoupdate version is %s", result)
        return result


    def get_device_info(self, on_fly=False):
        if self._device_info is None or on_fly:
            t1 = time.perf_counter()
            system_status = self.system_status
            # logger.info("system status is %s", system_status)
            t2 = time.perf_counter()
            logger.info("It takes %s s to collect system status.", t2 - t1)
            t1 = time.perf_counter()
            # print(system_status)
            autoupdate_versions = self.get_autoupdate_versions(system_status['vdom_mode'] != "disable")
            t2 = time.perf_counter()
            logger.info("It takes %s s to collect autoupdate versions.", t2 - t1)

            self._device_info = {**system_status, **autoupdate_versions}
        return self._device_info

