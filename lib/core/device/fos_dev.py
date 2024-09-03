import re
import time

import pexpect
from lib.services.image_server import (TFTP_SERVER_IP, UPGRADE, Image,
                                       image_server)
from lib.services.log import logger
from lib.services.environment import env
from lib.utilities.exceptions import KernelPanicErr, RestoreFailure

from .common import BURN_IMAGE_STAGE, LOGIN_STAGE
from .device import Device
from .fosdev_conn import FosDevConn


DEFAULT_MGMT = "port1"
ERROR_INFO = (
    "command parse error",
    "Unknown action",
    "Command fail",
    "command parse error",
    "failed command",
)
TEN_SECONDS = 10
DEFAULT_PATTERN = r"# $"


class FosDev(Device):
    def __init__(self, dev_name):
        self.model = ""
        logger.info("Start calling the device intialization.")
        super().__init__(dev_name)
        self._device_info = None


    def set_stage(self, stage):
        self.cur_stage = stage
        self.conn.set_stage(stage)


    def connect(self):
        connection = (
            self.dev_cfg["connection"]
            if "telnet" in self.dev_cfg["connection"]
            else f"telnet {self.dev_cfg['connection']}"
        )
        logger.info("Start connecting to device %s.", self.dev_name)
        self.conn = FosDevConn(
            self.dev_name,
            connection,
            self.dev_cfg["username"],
            self.dev_cfg["password"],
            self.cur_stage
        )
        logger.info("Succeeded to connect to device %s.", self.dev_name)
        if self.cur_stage == BURN_IMAGE_STAGE:
            return
        self.send_command("")
        # logger.notify("Start configuring output mode to be standard.")
        # self.set_output_mode()
        # logger.notify("Succeeded configuring output mode to be standard.")
        # self.model = self.system_status["platform"]
        # logger.notify("Start configuring mgmt settings.")
        # self.pre_mgmt_settings()
        # logger.notify("Finished configuring mgmt settings.")

        self.clear_buffer()

    def show_command_may_have_more(self, command, rule):
        logger.notify(f"begin to send {command}")
        self.send_line(command)
        time.sleep(1)
        logger.notify(f"begin to send whitespace")
        self.send_line(" ")

        matched, _ = self.search(rule, 10)
        return matched.groupdict() if matched else {}

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
            r"Serial-Number: (?P<serial>[^\r\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\r\n]*).*"
            r"Branch point: (?P<branch_point>[^\r\n]*).*"
        )
            matched = self.show_command_may_have_more("get system status", rule)
            if not matched:
                logger.error("Failed to get system status.")
        # print(f"The matched is {matched}")
        return matched


    @property
    def is_vdom_enabled(self):
        return self.system_status["vdom_mode"] != 'disable'

    @property
    def autoupdate_versions(self):
        return self.get_autoupdate_versions()

    def get_autoupdate_versions(self, is_vdom_enabled=None):
        # raise Exception()
        if is_vdom_enabled is None:
            is_vdom_enabled = self.is_vdom_enabled
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
        # rule = "".join(
        #     rf"{fd}\n---------\nVersion: ([\d.]+).*" for fd in VERSION_FIELDS[:1]
        # )
        rule = "".join(
             rf"{fd}(?:\r\n?|\n)---------\r\nVersion: ([\d.]+).*" for fd in VERSION_FIELDS
        )

        self.clear_buffer()
        logger.debug("The rule for diag autoupdate version is: %s", rule)
        is_succeeded, match, _ = self.send_command(
            "diag autoupdate versions", rule, timeout=10
        )
        logger.debug("The reulst for diag autoupdate versions: %s %s", is_succeeded, match)
        if is_vdom_enabled:
            self._return_to_user_view()
        result =  {fd: match.group(i + 1) for i, fd in enumerate(VERSION_FIELDS)} if is_succeeded and match else {}

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



    def _goto_global_view(self):
        self.send_command("config global")

    def _return_to_user_view(self):
        self.send_command("end")

    def set_output_mode(self, mode="standard", is_vdom_enabled=None):
        logger.debug(">>> mode: '%s'", mode)
        is_vdom_enabled = (
            self.is_vdom_enabled if is_vdom_enabled is None else is_vdom_enabled
        )
        if is_vdom_enabled:
            self._goto_global_view()
        commands = ["config system console", "set output %s" % mode, "end"]
        for cmd in commands:
            self.send_command(cmd)
            time.sleep(0.5)
        if is_vdom_enabled:
            self._return_to_user_view()

    def is_reset_command(self, command):
        pattern = re.compile(
            r"(exe.*factoryreset.*|exe.*forticarrier-license|exe.*restore)"
        )
        return re.match(pattern, command)

    def update_settings_after_reset(self):

        self.conn.login("")
        self.set_output_mode()

    def switch(self, retry=0):
        #for diag command without any output when switched in, send whitespace will not show
        #anything, send ctrl+c could make it output prompt.
        if self.keep_running:
            return
        ctrl_c = "\x03"
        self.conn.send(ctrl_c)
        super().switch()

    def switch_for_collect_info(self):
        keep_running = self.keep_running
        self.keep_running = 0
        self.switch()
        self.keep_running = keep_running

    # def goback(self):

    def force_login(self):
        logger.info("Start force logout and then login.")
        cnt = 0
        while cnt < 3:
            ctrl_c = "\x03"
            ctrl_d = "\x04"
            logger.info("Start sending ctrl_c and ctrl_d.")
            self.conn.send(ctrl_c)
            self.conn.send(ctrl_d)
            m, _ = self.conn.expect("login:", 10)
            if m is None:
                logger.warning("Failed to execute ctrl-d in the device.")
                cnt += 1
            else:
                self.conn.login()
                return
        logger.error("Failed to force login, please check the device.")

    def image_prefix(self):
        raise NotImplementedError

    # def _send_reset_command(self):
    #     self.send_line("exe factoryreset")
    def login_firewall_after_reset(self):
        self.search("login:", 1800, -1)
        self.send_line("admin")
        self.search("Password:", 30, -1)
        self.send_line("")
        self.search("Password:", 30, -1)
        self.send_line("admin")
        self.search("Password:", 30, -1)
        self.send_line("admin")
        self.search("#", 30, -1)
        self.send_line("config global")
        self.search("#", 30)
        self.send_line("config system admin")
        self.search("#", 30, -1)
        self.send_line("edit admin")
        self.search("#", 30, -1)

        self.send_line("unset password ?")
        req_old_passwd, _ = self.search("\<old passwd\>", 30, -1)
        if req_old_passwd:
            self.send_line("unset password admin")
            self.search("#", 30, -1)
        else:
            self.send_line("unset password")
            matched, _ = self.search("password:", 30, -1)
            if matched:
                self.send_line("admin")
            self.search("#", 30, -1)
        self.send_line("end")
        self.search("login:", 30, -1)
        self.send_line("admin")
        self.search("Password:", 30, -1)
        self.send_line("")
        self.search("#", 30, -1)
        password = env.get_section_var(self.dev_name, "PASSWORD")
        if password:
            self.send_line("config global")
            self.search("#", 30)
            self.send_line("config system admin")
            self.search("#", 30, -1)
            self.send_line("edit admin")
            self.search("#", 30, -1)
            self.send_line(f"set password {password}")
            matched, _ = self.search("password:", 30, -1)
            if matched:
                self.send_line("admin")
            self.search("#", 30, -1)
            self.send_line("end")
            self.search("login:", 30, -1)
            self.send_line("admin")
            self.search("Password:", 30, -1)
            self.send_line(password)
            self.search("#", 30, -1)

    def reset_firewall(self, cmd):
        self.send_line("config global")
        self.search("#", 30)
        # self.send_line("exe factoryreset")
        self.send_line(cmd)
        self.search("y/n", 30)
        self.send_line("y")
        self.login_firewall_after_reset()


    def restore_image(self, release, build, need_reset=True, need_burn=False):
        if need_reset:
            logger.notify("Start reset firewall.")
            self.reset_firewall("exe factoryreset")

        if need_burn:
            logger.notify("Start burn image.")
            self.burn_image(release, build)
            self.set_stage("start_from_login")
            self.login_firewall_after_reset()
            return self.validate_build(release, build)

        image = Image(self.image_prefix(), release, build, UPGRADE)
        image_file = image_server.lookup_image(image)
        image_loc = f"{image_file['parent_dir']}/{image_file['name']}"

        logger.notify("Start configuring output mode to be standard.")
        is_vdom_enabled = self.is_vdom_enabled
        self.set_output_mode(is_vdom_enabled=is_vdom_enabled)
        logger.notify("Succeeded configuring output mode to be standard.")
        self.model = self.system_status["platform"]
        logger.notify("Start configuring mgmt settings.")
        self.pre_mgmt_settings()
        logger.notify("Finished configuring mgmt settings.")
        command = f"exe restore image url http://{TFTP_SERVER_IP}/{image_loc}"
        if self.is_vdom_enabled:
            self._goto_global_view()
        self.send_line(command)
        matched, output = self.expect(r"(\(y/n\)|\(yes/no\)|\[Y/N\])", 10)
        if matched:
            self.send("y")
        matched = True
        wait_time = 300
        cnt = 0
        while cnt < wait_time:
            matched, output = self.expect(r"(\(y/n\)|\(yes/no\)|\[Y/N\])", 10)
            if matched:
                self.send("y")
            matched, output = self.search("login:", 10)
            if matched:
                break
            cnt += 1
            time.sleep(1)
        if cnt >= wait_time and not matched:
            raise RestoreFailure(self.dev_name, release, build)

        self.conn.login()

        keywords = ["NULL", "BUG:", r"\[\<", "PID:", "STACK:", " KERNEL "]
        rule = "|".join(keywords)

        match, output = self.search(rf"({rule})", timeout=5)
        if match:
            logger.error("Kernel panic detected: %s", output)
            raise KernelPanicErr(self.dev_name)

        return self.validate_build(release, build)

    def validate_build(self, release, build):
        system_status = self.system_status

        return (
            release in system_status["version"]
            and build in system_status["build"]
        )

    def set_interface_ip(self, port, ipaddr, mask, allowaccess=None):
        allowaccess = allowaccess or ["https", "ssh", "telnet", "http", "ping"]
        template = ">>> port:%s', ipaddr: '%s', mask:'%s', allowaccess:'%s'"
        logger.debug(template, port, ipaddr, mask, str(allowaccess))
        cmdlst = [
            "config system interface",
            "edit %s" % port,
            "set mode static",
            "set ip %s %s" % (ipaddr, mask),
            "set allowaccess " + " ".join(allowaccess),
            "end",
        ]
        for cmd in cmdlst:
            self.send_command(cmd)

    def add_staic_route(
        self, gtw, subnet="0.0.0.0", mask="0.0.0.0", dev="", eid="0"
    ):
        template = (
            ">>> subnet: '%s', mask: '%s', gtw: '%s', dev: '%s', eid: '%s'"
        )
        logger.debug(template, gtw, subnet, mask, dev, eid)
        cmdlst = [
            "config router static",
            "edit %s" % eid,
            "set dst %s %s" % (subnet, mask),
            "set gateway %s" % gtw,
        ]
        if dev:
            cmdlst.extend(["set device " + dev, "end"])
        else:
            cmdlst.extend(["end"])
        for cmd in cmdlst:
            self.send_command(cmd)

    def pre_mgmt_settings(self):
        if "mgmt_ip" in self.dev_cfg and "mgmt_mask" in self.dev_cfg and "mgmt_gw" in self.dev_cfg:
            self.set_interface_ip(
                self.dev_cfg.get("mgmt_port", DEFAULT_MGMT), self.dev_cfg["mgmt_ip"], self.dev_cfg["mgmt_mask"]
            )
            self.add_staic_route(
                gtw=self.dev_cfg["mgmt_gw"], dev=self.dev_cfg.get("mgmt_port", DEFAULT_MGMT), eid="1"
            )
            time.sleep(10)

    def send_command(
        self, command, pattern=DEFAULT_PATTERN, timeout=TEN_SECONDS
    ):
        # if command.startswith("diag") and pattern == DEFAULT_PATTERN:
        #     pattern = ".+"

        if pattern != DEFAULT_PATTERN:
            match, output = super().send_command(command, pattern, timeout)
        else:
            match, output = super().send_command(command, timeout=timeout)
        is_succeeded = self._if_succeeded_to_execute_command(output, command)
        return is_succeeded, match, output

    def _if_succeeded_to_execute_command(self, result, command):
        if any(err in result for err in ERROR_INFO):
            error_report = result.splitlines()
            logger.error("Failed to execute command: %s.", command)
            error_info = " ".join(error_report[2:-2])
            logger.error("Error information: %s", error_info)
            return False
        logger.info("Succeeded to execute command %s.", command)
        return True
