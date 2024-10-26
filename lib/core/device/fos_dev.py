import re
import time

from lib.services import UPGRADE, Image, env, image_server, logger, platform_manager
from lib.utilities.exceptions import KernelPanicErr, RestoreFailure

from .common import BURN_IMAGE_STAGE
from .device import DEFAULT_PROMPTS, Device
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


class FosDev(Device):

    DEFAULT_ADMIN = "admin"
    TEMP_PASSWORD = "admin"
    DEFAULT_PASSWORD = ""

    def __init__(self, dev_name):
        self.model = ""
        logger.info("Start calling the device intialization.")
        super().__init__(dev_name)
        self.cur_stage = None

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
            self.cur_stage,
        )
        logger.info("Succeeded to connect to device %s.", self.dev_name)
        if self.cur_stage == BURN_IMAGE_STAGE:
            return
        self.send_command("")
        self.clear_buffer()

    def set_output_mode(self, mode="standard", is_vdom_enabled=None):
        is_vdom_enabled = is_vdom_enabled or self.is_vdom_enabled
        if is_vdom_enabled:
            self._goto_global_view()
        commands = ["config system console", "set output %s" % mode, "end"]
        for cmd in commands:
            self.send_command(cmd)
            time.sleep(0.5)
        if is_vdom_enabled:
            self._return_to_user_view()

    def update_settings_after_reset(self):
        self.conn.login("")
        self.set_output_mode()

    def switch(self, retry=0):
        # for diag command without any output when switched in, send whitespace will not show
        # anything, send ctrl+c could make it output prompt.
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

    def force_login(self):
        logger.debug("Start force logout and then login.")
        cnt = 0
        while cnt < 3:
            ctrl_c = "\x03"
            ctrl_d = "\x04"
            logger.debug("Start sending ctrl_c and ctrl_d.")
            self.conn.send(ctrl_c)
            time.sleep(1)
            self.conn.send(ctrl_d)
            time.sleep(1)
            # NOTE: if the interval is too short, for FVM simulated console, it may hang
            m, _ = self.conn.expect("login:", 10)
            if m is None:
                logger.debug("Failed to execute ctrl-d in the device.")
                cnt += 1
            else:
                self.conn.login()
                return
        logger.error("Failed to force login, please check the device.")

    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        return platform_manager.normalize_platform(self.model)

    def set_admin_password(self, admin, password, old_password):
        self.send_line("config system admin")
        self.search("#", 30, -1)
        self.send_line(f"edit {admin}")
        self.search("#", 30, -1)
        self.send_line(f"set password {password}")
        matched, _ = self.search("password:", 30, -1)
        if matched:
            self.send_line(old_password)
        self.search("#", 30, -1)
        self.send_line("end")

    def _login_without_check_prompt(self, username, password):
        self.send_line(username)
        self.search("Password:", 30, -1)
        self.send_line(password)

    def _login(self, username, password):
        self._login_without_check_prompt(username, password)
        self.search("#", 30, -1)

    def unset_admin_password(self, admin, password):
        self.send_line("config system admin")
        self.search("#", 30, -1)
        self.send_line(f"edit {admin}")
        self.search("#", 30, -1)

        self.send_line("unset password ?")
        req_old_passwd, _ = self.search(r"\<old passwd\>", 30, -1)
        if req_old_passwd:
            self.send_line(f"unset password {password}")
            self.search("#", 30, -1)
        else:
            self.send_line("unset password")
            matched, _ = self.search("password:", 30, -1)
            if matched:
                self.send_line(password)
            self.search("#", 30, -1)
        self.send_line("end")

    def login_firewall_after_reset(self, temp_password=None):
        temp_password = FosDev.TEMP_PASSWORD if temp_password is None else temp_password
        _, cli_output = self.search("login:", 600, -1)
        self.check_kernel_panic(cli_output)
        self._login_without_check_prompt(self.DEFAULT_ADMIN, self.DEFAULT_PASSWORD)
        self.search("Password:", 30, -1)
        self.send_line(temp_password)
        self.search("Password:", 30, -1)
        self.send_line(temp_password)
        self.search("#", 30, -1)
        password = env.get_section_var(self.dev_name, "PASSWORD")
        if password and password != temp_password:
            self.set_admin_password(self.DEFAULT_ADMIN, password, temp_password)
        if not password:
            self.unset_admin_password("admin", temp_password)
        if password != temp_password:
            self.search("login:", 5, -1)
            self._login(self.DEFAULT_ADMIN, password)

    def reset_firewall(self, cmd):
        if self.is_vdom_enabled:
            self._goto_global_view()
        self.send_line(cmd)
        self.search("y/n", 30)
        self.send_line("y")
        self.login_firewall_after_reset()

    def check_kernel_panic(self, cli_output):
        keywords = ["NULL", "BUG:", r"\[\<", "PID:", "STACK:", " KERNEL "]
        rule = "|".join(keywords)

        panic_patterns = re.compile(rf"({rule})").search(cli_output)
        if panic_patterns:
            logger.error("Kernel panic pattern was detected(%s)!!", panic_patterns)
            raise KernelPanicErr(self.dev_name)

    def _restore_image_via_url(self, image):
        image_url = image_server.get_image_http_url(image)
        command = f"exe restore image url {image_url}"
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
                self.check_kernel_panic(output)
                break
            cnt += 1
            time.sleep(1)
        return cnt <= wait_time and matched

    def restore_image(self, release, build, need_reset=True, need_burn=False):
        if not need_burn and need_reset:
            logger.debug("Start reset firewall.")
            self.reset_firewall("exe factoryreset")

        logger.debug("Start configuring output mode to be standard.")
        self.set_output_mode()
        logger.debug("Succeeded configuring output mode to be standard.")
        self.model = self.system_status["platform"]
        logger.debug("Start configuring mgmt settings.")
        self.pre_mgmt_settings()
        logger.debug("Finished configuring mgmt settings.")
        if self.is_vdom_enabled:
            self._goto_global_view()
        image = Image(self.image_prefix(), release, build, UPGRADE)
        upgrade_done_properly = self._restore_image_via_url(image)
        if not upgrade_done_properly:
            raise RestoreFailure(self.dev_name, release, build)
        self.conn.login()
        return self.validate_build(release, build)

    def validate_build(self, release, build):
        system_status = self.system_status

        return release in system_status["version"] and build in system_status["build"]

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

    def add_staic_route(self, gtw, subnet="0.0.0.0", mask="0.0.0.0", dev="", eid="0"):
        template = ">>> subnet: '%s', mask: '%s', gtw: '%s', dev: '%s', eid: '%s'"
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
        if (
            "mgmt_ip" in self.dev_cfg
            and "mgmt_mask" in self.dev_cfg
            and "mgmt_gw" in self.dev_cfg
        ):
            self.set_interface_ip(
                self.dev_cfg.get("mgmt_port", DEFAULT_MGMT),
                self.dev_cfg["mgmt_ip"],
                self.dev_cfg["mgmt_mask"],
            )
            self.add_staic_route(
                gtw=self.dev_cfg["mgmt_gw"],
                dev=self.dev_cfg.get("mgmt_port", DEFAULT_MGMT),
                eid="1",
            )
            time.sleep(10)
        else:
            logger.warning(
                "mgmt_ip/mgmt_mask/mgmt_gw in device config file is not configured."
            )

    def send_command(self, command, pattern=DEFAULT_PROMPTS, timeout=TEN_SECONDS):
        match, output = super().send_command(command, pattern, timeout=timeout)
        is_succeeded = self._if_succeeded_to_execute_command(output, command)
        return is_succeeded, match, output

    def _if_succeeded_to_execute_command(self, result, command):
        if any(err in result for err in ERROR_INFO):
            logger.error("Failed to execute command: '%s'.", command)
            error_report = result.splitlines()
            error_info = "\n".join(error_report[2:-2])
            logger.error("Error information: \n'%s'\n", error_info)
            return False
        logger.debug("Succeeded to execute command '%s'.", command)
        return True
