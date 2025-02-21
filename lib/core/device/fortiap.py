import re
import time

from lib.services import logger
from lib.utilities import sleep_with_progress

from .fortigate import FortiGate


class FortiAP(FortiGate):
    asking_for_password = r"[P|p]assword: *"

    def __init__(self, dev_name):
        super().__init__(dev_name)
        self.controller = None

    def set_controller(self, controller):
        self.controller = controller

    def reboot(self):
        time.sleep(0.5)
        self.send("\n")
        self.send_line("reboot")

    def reboot_device(self):
        self.send_line("reboot")
        self.search("(y/n)", 5, -1)
        self.send("y")

    def get_device_info(self, on_fly=False):
        super().get_device_info(on_fly=on_fly)
        if self.controller is not None:
            system_status = self.controller.get_parsed_system_status()
            self._device_info["FortiOS"] = (
                f"{system_status['version']}.{system_status['build']}"
            )
        return self._device_info

    def _get_system_status(self):
        """
        Version: FortiAP-U431F v7.0.5,build0138,241011 (Interim)
        Serial-Number: PU431F5E19002478
        BIOS version: 00000003
        System Part-Number: P20143-03
        Regcode: A
        Base MAC: 00:0c:e6:87:94:a0
        Hostname: FortiAP-U431F
        Branch point: 0138
        Release Version Information: Interim
        Power-type: Eth1 PoE 802.3at
        FIPS-CC mode: Disabled
        """
        *_, system_info_raw = self.send_command(
            "get system status", pattern="Release Version.*?# $", timeout=10
        )
        return system_info_raw

    def retr_crash_log(self, cmd="diag_debug_crashlog read"):
        super().retr_crash_log(cmd)

    def get_autoupdate_versions(self, is_vdom_enabled=None):
        """
        send "utm_diag update now\r"
        sleep 30
        send "utm_diag update db-version\r"
        av engine version:      5.239 (20170413-05:40:17)
        av db version:          16.560 (20150105-20:14:16)
        ips engine version:     3.410 (20180105-06:05:39)
        ips db version:         5.590 (20150105-20:14:14)
        ips botnet db version:  1.0 (20150105-20:14:14)
        """
        self.send_command("utm_diag update now", pattern="# $", timeout=3)
        sleep_with_progress(30)
        *_, info_raw = self.send_command(
            "utm_diag update db-version", pattern="# $", timeout=20
        )
        pattern = re.compile(r"\s(?P<db>[a-z ]+) version:\s+(?P<version>[0-9.]+) ")
        return dict(re.findall(pattern, info_raw))

    def reset_config(self, cmd="factoryreset"):
        self.send_line(cmd)
        self.search("y/n", 30)
        self.send_line("y")
        self.login_firewall_after_reset()

    def login_firewall_after_reset(self):
        _, cli_output = self.search(self.asking_for_username, 600, -1)
        self.check_kernel_panic(cli_output)
        sleep_with_progress(5)
        self.clear_buffer()
        self.send("\n\n")
        self.search(self.asking_for_username, 5, -1)
        self.send_line(self.dev_cfg["USERNAME"])
        self.search(self.asking_for_password, 30, -1)
        self.send_line(self.dev_cfg["PASSWORD"])
        self.search(self.asking_for_password, 30, -1)
        self.send_line(self.dev_cfg["PASSWORD"])
        self.search(" # $", 30, -1)
