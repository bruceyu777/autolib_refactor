import re
import time

from lib.services import Image, image_server, logger, platform_manager
from lib.settings import BASE_TIME_UNIT, SEND_COMMAND_TIMEOUT
from lib.utilities import (
    KernelPanicErr,
    ResourceNotAvailable,
    RestoreFailure,
    sleep_with_progress,
)

from ._helper.crashlog import CrashLog
from .device import DEFAULT_PROMPTS, DISABLE, Device
from .session import get_session_init_class

DEFAULT_MGMT = "port1"
ERROR_INFO = (
    "command parse error",
    "Unknown action",
    "Command fail",
    "command parse error",
    "failed command",
)


class FosDev(Device):

    DEFAULT_ADMIN = "admin"
    TEMP_PASSWORD = "Fortinet@552103"
    DEFAULT_PASSWORD = ""
    asking_for_username = "login: $"
    asking_for_password = "assword: $"
    image_file_ext = ".out"
    general_view = r"[ )~][#$] $"

    def __init__(self, dev_name):
        self.model = ""
        logger.info("Start calling the device initialization.")
        super().__init__(dev_name)

    def get_parsed_system_status(self):
        system_status = super().get_parsed_system_status()
        self.model = platform_manager.normalize_platform(system_status["platform"])
        self.is_vdom_enabled = (
            system_status.get("Virtual domain configuration", DISABLE) != DISABLE
        )
        return system_status

    def is_serial_connection_used(self):
        if "telnet" not in self.dev_cfg["CONNECTION"]:
            return False
        return any(
            k in self.dev_cfg for k in ("CISCOPASSWORD", "TERMINAL_SERVER_PASSWORD")
        )

    def initialize(self):
        self.connect()
        if "ssh" in self.dev_cfg["CONNECTION"]:
            self.login_for_ssh()
        else:
            self.login()
        self.get_parsed_system_status()

    def get_session_init_class(self):
        return get_session_init_class(self.is_serial_connection_used(), False)

    def connect(self):
        logger.info("Start connecting to device %s.", self.dev_name)
        connection_init_class = self.get_session_init_class()
        max_attempts, backoff_time = 3, 5
        for attempt in range(max_attempts):
            try:
                self.conn = connection_init_class(
                    self.dev_name,
                    self.dev_cfg["CONNECTION"],
                ).connect()
                logger.info("Succeeded to connect to device %s.", self.dev_name)
                return
            except Exception as e:
                logger.error(
                    "Connection attempt %d failed for device %s: %s",
                    attempt + 1,
                    self.dev_name,
                    str(e),
                )
                sleep_with_progress(backoff_time)
                backoff_time *= 3
        raise ResourceNotAvailable(
            f"Cannot connect to device {self.dev_name} after {max_attempts} attempts"
        )

    def set_output_mode(self, mode="standard"):
        with self.global_view():
            commands = ["config system console", "set output %s" % mode, "end"]
            for cmd in commands:
                self.send_command(cmd)
                time.sleep(0.5)

    def switch(self, retry=0):
        # for diag command without any output when switched in, send whitespace will not show
        # anything, send ctrl+c could make it output prompt.
        if self.keep_running:
            return
        ctrl_c = "\x03"
        self.conn.send(ctrl_c)
        super().switch(retry=retry)

    def update_settings_after_reset(self):
        self.is_vdom_enabled = False
        self.login()
        self.set_output_mode()

    def switch_for_collect_info(self):
        keep_running = self.keep_running
        self.keep_running = 0
        self.switch()
        self.keep_running = keep_running

    def _send_ctrl_c_and_d(self):
        # NOTE: if the interval is too short, for FVM simulated console, it may hang
        ctrl_c = "\x03"
        ctrl_d = "\x04"
        logger.debug("Start sending ctrl_c and ctrl_d.")
        self.send(ctrl_c)
        time.sleep(1)
        self.send(ctrl_d)
        time.sleep(1)

    def _force_login_non_serial(self):
        self.conn.close()
        self.connect()

    def force_login(self):
        # for non-serial connection, this will cause connection killed
        logger.debug("Start force logout and then login.")
        if self.is_serial_connection_used():
            self.login()
        else:
            self._force_login_non_serial()

    def set_admin_password(self, admin, password, old_password):
        self.send_line("config system admin")
        self.search(self.general_view, 30, -1)
        self.send_line(f"edit {admin}")
        self.search(self.general_view, 30, -1)
        self.send_line(f"set password {password}")
        matched, _ = self.search(self.asking_for_password, 30, -1)
        if matched:
            self.send_line(old_password)
        self.search(self.general_view, 30, -1)
        self.send_line("end")

    def _get_login_error(self, output):
        output = output.lower()
        get_error = any(e in output for e in ("incorrect", "error"))
        return get_error

    def login_for_ssh(self):
        password = self.dev_cfg["PASSWORD"]
        self.search(self.asking_for_password, 30, -1)
        self.send_line(password)
        _, cli_output = self.search(self.general_view, 30, -1)
        user = self.dev_cfg["CONNECTION"].split("@")[0].split()[-1]
        self._post_login_handling(cli_output, user, password)

    def login(self, user=None, password=None):
        user = user or self.dev_cfg["USERNAME"]
        password = self.dev_cfg["PASSWORD"] if password is None else password
        output = self._login(user, password)
        self._post_login_handling(output, user, password)

    def _post_login_handling(self, output, user, password):
        login_error = self._get_login_error(output)
        if login_error and password != self.DEFAULT_PASSWORD:
            logger.debug("Login failure, fallback to try default password!!")
            login_error, output = self._login_fallback_with_default_password(user)
        if login_error:
            err = "*** Unable to login Device!!! ***"
            logger.error(err)
            raise RuntimeError(err)
        self._handle_password_enforcement(output, password, self.dev_cfg["PASSWORD"])

    def _login_fallback_with_default_password(self, user):
        logger.warning("\nTry default password to login FortiGate!\n")
        output = self._login(user, self.DEFAULT_PASSWORD)
        get_error = self._get_login_error(output)
        return get_error, output

    def _login_without_check_prompt(self, username, password):
        self.send_line(username)
        self.search(self.asking_for_password, 30, -1)
        self.send_line(password)

    def _is_in_rebooting_status(self, data):
        if not data:
            return True
        lowercase_data = data.lower()
        rebooting_patterns = {
            "starting",
            "scanning",
            "reboot",
            "formatting",
            "unmounting",
            "system is going down",
            "serial number is",
        }
        return any(keyword in lowercase_data for keyword in rebooting_patterns)

    def _pre_login_handling(self):
        self.clear_buffer()
        self.send_line("\n")
        # some VM are very slow, may don't have any output in 5 seconds
        pattern = f"{self.asking_for_username}|{self.general_view}"
        matched, cli_output = self.search(pattern, 60, -1)
        if matched and re.search(self.asking_for_username, cli_output):
            return
        if not re.search(
            self.general_view, cli_output
        ) and self._is_in_rebooting_status(cli_output):
            matched, cli_output = self.search(self.asking_for_username, 10 * 60, -1)
            return
        logger.debug("Sending ctrl + c and d to force logout...")
        self._send_ctrl_c_and_d()
        matched, cli_output = self.search(self.asking_for_username, 60, -1)
        self.clear_buffer()
        return

    def _login(self, username, password):
        self._pre_login_handling()
        self._login_without_check_prompt(username, password)
        _, cli_output = self.search(
            f"({self.general_view}|forced to change your.*?Password: $|{self.asking_for_username})",
            10,
            -1,
        )
        return cli_output

    def unset_admin_password(self, admin, password):
        self.clear_buffer()
        self.send_line("config system admin")
        self.search(self.general_view, 30, -1)
        self.send_line(f"edit {admin}")
        self.search(self.general_view, 30, -1)
        self.send("unset password ?")
        require_old_password, _ = self.search(r"\<old passwd\>", 2, -1)
        self.clear_buffer()
        if require_old_password:
            self.send_line(password)
            self.search(self.general_view, 30, -1)
        else:
            self.send("\n")
            matched, _ = self.search(self.asking_for_password, 2, -1)
            if matched:
                self.send_line(password)
                logger.debug("###### password send:  '%s'", password)
                self.search(self.general_view, 10, -1)
        self.send_line("end")
        matched, _ = self.search(self.asking_for_password, 2, -1)
        if matched:
            self.send_line(password)
            logger.debug("###### password send:  '%s'", password)

    def login_firewall_after_reset(self):
        _, cli_output = self.search(self.asking_for_username, 600, -1)
        self.check_kernel_panic(cli_output)
        retry = 3
        while retry > 0:
            cli_output += self._login(self.DEFAULT_ADMIN, self.DEFAULT_PASSWORD)
            if not re.search(self.asking_for_username, cli_output):
                break
            retry -= 1
            logger.debug("Try to login again...")
        else:
            raise ResourceNotAvailable("Failed to login device")
        self._handle_password_enforcement(
            cli_output, self.DEFAULT_PASSWORD, self.dev_cfg["PASSWORD"]
        )

    def disable_password_policy(self):
        # mantis 1208336, password-policy enabled by default
        self.send_line("get system password-policy")
        is_enabled, _ = self.search(r"status\s+:\s+enable", 2, -1)
        if is_enabled:
            commands = ["config system password-policy", "set status disable", "end"]
            for cmd in commands:
                self.send_line(cmd)
                self.search(self.general_view, 30, -1)

    def _set_temp_password(self):
        self.send_line(FosDev.TEMP_PASSWORD)
        self.search(self.asking_for_password, 30, -1)
        self.send_line(FosDev.TEMP_PASSWORD)
        self.search(self.general_view, 30, -1)

    def _restore_to_required_password(self, password_to_set):
        if not password_to_set:
            self.unset_admin_password("admin", FosDev.TEMP_PASSWORD)
        else:
            self.set_admin_password(
                self.DEFAULT_ADMIN, password_to_set, FosDev.TEMP_PASSWORD
            )
        self.search(self.asking_for_username, 5, -1)
        self._login_without_check_prompt(self.DEFAULT_ADMIN, password_to_set)

    def _handle_password_enforcement(self, output, old_password, password_to_set):
        if "are forced to change your password." in output:
            # for upgrade user case, it requires to have extra Old password input
            # for image burn case, it won't require this
            if "Old password:" in output:
                self.send_line(old_password)
            self._set_temp_password()
            self.update_vdom_status()
            if self.is_vdom_enabled:
                self._goto_global_view()
            self.disable_password_policy()
            if password_to_set != FosDev.TEMP_PASSWORD:
                self._restore_to_required_password(password_to_set)
                _, cli_output = self.search(self.general_view, 5, -1)
                if "Welcome!" not in cli_output:
                    raise RuntimeError("Unable to login Device!!!")

    def reset_config(self, cmd):
        with self.global_view():
            self.send_line(cmd)
            self.search("y/n", 30)
            self.send_line("y")
            self.is_vdom_enabled = False
            self.login_firewall_after_reset()

    def check_kernel_panic(self, cli_output):
        keywords = ["NULL", "BUG: ", "Call Trace", " KERNEL ", "Kernel panic"]
        rule = "|".join(keywords)

        panic_patterns = re.compile(rf"({rule})").search(cli_output)
        if panic_patterns:
            logger.error("Kernel panic pattern was detected(%s)!!", panic_patterns)
            raise KernelPanicErr(self.dev_name)

    def _handle_yes_no_util_pattern_matched(
        self, command, pattern_to_break, wait_for_y_timer=5
    ):
        self.send_line(command)
        remaining_attempts, output = 10, ""
        confirmation_patterns = [
            r"\(y/n\)",
            r"\(yes/no\)",
            r"\[Y/N\]",
        ]
        patterns = "|".join(confirmation_patterns)
        while remaining_attempts > 0:
            matched, data = self.expect(patterns, wait_for_y_timer)
            output += data
            if "Command fail" in output:
                logger.error("Command failure!!!")
                break
            break_flag, _ = self.search(pattern_to_break, timeout=BASE_TIME_UNIT)
            if break_flag or not matched:
                break
            self.send("y")
            remaining_attempts -= 1
            time.sleep(1)
        return output

    def _restore_image_via_url(self, image):
        image_url = image_server.get_image_http_url(image)
        command = f"exe restore image url {image_url}"
        output = self._handle_yes_no_util_pattern_matched(
            command, "system is going down NOW", wait_for_y_timer=60
        )
        is_login_view = False
        if "Command fail" not in output:
            is_login_view, _ = self.search(self.asking_for_username, timeout=60)
            if not is_login_view:
                self.clear_buffer(read_before_clean=False)
                _is_login_view, data = self.expect(self.asking_for_username, 6 * 60)
                is_login_view = is_login_view or _is_login_view
                output += data
        self.check_kernel_panic(output)
        return (
            is_login_view
            or self.search(self.asking_for_username, timeout=BASE_TIME_UNIT)[0]
        )

    def restore_image(self, release, build, need_reset=True, need_burn=False):
        if not need_burn and need_reset:
            logger.debug("Start reset firewall.")
            self.reset_config("exe factoryreset")
        logger.debug("Succeeded configuring output mode to be standard.")
        logger.debug("Start configuring mgmt settings.")
        self.setup_management_access()
        logger.debug("Finished configuring mgmt settings.")
        if self.is_vdom_enabled:
            self._goto_global_view()
        image = Image(self.model, release, build, self.image_file_ext)
        upgrade_done_properly = self._restore_image_via_url(image)
        if not upgrade_done_properly:
            raise RestoreFailure(self.dev_name, release, build)
        self.login()
        return self.is_image_installed(release, build)

    def is_image_installed(self, release, build):
        system_status = self.get_parsed_system_status()

        return release in system_status["version"] and build in system_status["build"]

    def set_interface_ip(self, port, ipaddr, mask="255.255.255.0", allowaccess=None):
        allowaccess = allowaccess or ["https", "ssh", "telnet", "http", "ping"]
        cmdlst = [
            "config system interface",
            f"edit {port}",
            "set mode static",
            "unset dedicated-to",
            f"set ip {ipaddr} {mask}",
            "set allowaccess " + " ".join(allowaccess),
            "end",
        ]
        for cmd in cmdlst:
            self.send_command(cmd)

    # pylint: disable=too-many-positional-arguments
    def add_static_route(self, gtw, subnet="0.0.0.0", mask="0.0.0.0", dev="", eid="0"):
        cmdlst = [
            "config router static",
            f"edit {eid}",
            f"set dst {subnet} {mask}",
            f"set gateway {gtw}",
        ]
        if dev:
            cmdlst.append(f"set device {dev}")
        cmdlst.append("end")
        for cmd in cmdlst:
            self.send_command(cmd)

    def setup_management_access(self):
        mgmt_port = self.dev_cfg.get("MGMT_PORT", DEFAULT_MGMT)
        if all(k in self.dev_cfg for k in ("MGMT_IP", "MGMT_GW")):
            self.set_interface_ip(
                mgmt_port,
                self.dev_cfg["MGMT_IP"],
                self.dev_cfg.get("MGMT_MASK", "255.255.255.0"),
            )
            self.add_static_route(
                gtw=self.dev_cfg["MGMT_GW"],
                dev=mgmt_port,
                eid="1",
            )
            time.sleep(10)
        else:
            logger.error(
                "*** MGMT_IP/MGMT_MASK/MGMT_GW *** in device config file is not configured."
            )

    def send_command(
        self, command, pattern=DEFAULT_PROMPTS, timeout=SEND_COMMAND_TIMEOUT
    ):
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

    def retr_crash_log(self, cmd="diag debug crashlog read"):
        self.send_command(cmd)
        _, crashlog_output = self.expect(self.general_view, timeout=20 * 60)
        return CrashLog(crashlog_output).dump_parsed_log(self.dev_name)
