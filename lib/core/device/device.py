import csv
import re
import time

from lib.services.environment import DeviceConfig, env
from lib.services.log import logger

DEFAULT_TIMEOUT_FOR_PROMPT = 10
MAX_TIMEOUT_FOR_REBOOT = 10 * 60


UNIVERSAL_PROMPTS = (r"(?<!--)[$#>]\s?$", r"(?P<windows_prompt>\:.*?\>)")

FOS_LOGIN_PROMPTS = r"[\w\-]{1,35} login:\s*$"

FOS_UNIVERSAL_PROMPTS = (
    FOS_LOGIN_PROMPTS,
    r"[P|p]assword:\s*$",
)

AUTO_PROCEED_RULE_MAP = {
    r"\(y/n\)$": "y",
    r"\(yes/no.*\)\?*$": "yes",
    r"\[Y/N\]\?": "Y",
    r"to accept\): $": "a",
    r"\[confirm\]$": "y",
    r"--More--\s*$": " ",
}

AUTO_PROCEED_PATTERNS = "|".join(AUTO_PROCEED_RULE_MAP.keys())
MAX_AUTO_PROCEED_TIMES = 6

SYSCTRL_COMAND = (r"Admin:\s*$",)
FTP_NAME_PROMPT = (r"Name\s*\(.+\):\s*$",)
DEFAULT_PROMPTS = "|".join(
    UNIVERSAL_PROMPTS
    + FOS_UNIVERSAL_PROMPTS
    + tuple(AUTO_PROCEED_RULE_MAP.keys())
    + SYSCTRL_COMAND
    + FTP_NAME_PROMPT
)
DISABLE = "disable"


def _parse_fos_version(version):
    pattern = re.compile(
        r"^(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
        r"build((?P<build>\d+)),\d+\s+\((?P<release_type>.*?)\)"
    )
    matched = pattern.search(version)
    return matched.groupdict() if matched else {}


class Device:
    def __init__(self, dev_name):
        self.dev_name = dev_name
        self.conn = None
        self._device_info = None
        self.dev_cfg: DeviceConfig = env.get_dev_cfg(dev_name)
        self.keep_running = False
        self.confirm_with_newline = False
        self.wait_for_confirm = False
        self.embeded_conn = False
        self.connect()
        self.license_info = {}
        self._extract_license_info()

    def __str__(self):
        return f"{type(self).__name__}({self.dev_name})"

    def _reconnect_if_exited(self):
        expected_switch_prompts = (
            r"((?P<prompt>[#$]\s*$)|(?P<login>login:)|(?P<Password>Password:))"
        )
        try:
            matched, output = self.conn.send_command(
                "", expected_switch_prompts, DEFAULT_TIMEOUT_FOR_PROMPT
            )
            if matched is None:
                logger.error(
                    "Failed to switch to device:%s, start reconnecting.",
                    self.dev_name,
                )
                self.connect()
                logger.debug("Device:%s is reconnected.", self.dev_name)
            logger.debug("The output is %s.", output)
            logger.debug("The matched is %s.", matched)
        except Exception:
            logger.debug(
                "Exception happened when switching to device:%s, start reconnecting.",
                self.dev_name,
            )
            self.connect()
            logger.debug("Device:%s is reconnected.", self.dev_name)

    def switch(self, retry=0):
        if retry > 3:
            logger.debug("Failed to switch device: %s", self.dev_name)
        try:
            if self.keep_running:
                return
            self._reconnect_if_exited()
            logger.debug("Start login device %s", self.dev_name)
            self.force_login()
            self.clear_buffer()

        except Exception as e:
            print(e)
            self.switch(retry + 1)

    def connect(self):
        raise NotImplementedError

    def force_login(self):
        raise NotImplementedError

    def expect(self, pattern, timeout=DEFAULT_TIMEOUT_FOR_PROMPT, need_clear=True):
        return self.conn.expect(pattern, timeout, need_clear)

    def search(self, pattern, timeout=DEFAULT_TIMEOUT_FOR_PROMPT, pos=0):
        return self.conn.search(pattern, timeout, pos)

    def send_line(self, s):
        return self.conn.send_line(s)

    def send(self, s):
        return self.conn.send(s)

    def clear_buffer(self):
        self.conn.clear_buffer()

    def require_confirm(self, s):
        for key, val in AUTO_PROCEED_RULE_MAP.items():
            if re.match(key, s):
                if self.confirm_with_newline:
                    return val + "\n"
                return val
        return None

    def require_login(self, s):
        for key in FOS_UNIVERSAL_PROMPTS:
            if re.match(key, s):
                return True
        return False

    def sysctl_login(self, s):
        for key in SYSCTRL_COMAND:
            if re.match(key, s):
                return True
        return False

    @property
    def system_status(self):
        *_, system_info_raw = self.send_command("get system status", timeout=10)
        logger.debug("System info captured: %s", system_info_raw)
        selected_lines = [
            l.split(": ", maxsplit=1) for l in system_info_raw.splitlines() if ": " in l
        ]
        if not selected_lines:
            return {}
        system_status = dict(selected_lines)
        if "Version" in system_status:
            system_status.update(_parse_fos_version(system_status["Version"]))
        if "Virtual domain configuration" not in system_status:
            system_status["Virtual domain configuration"] = DISABLE
        if "BIOS version" not in system_status:
            system_status["BIOS version"] = "0"
        return system_status

    def get_device_info(self, on_fly=False):
        if self._device_info is None or on_fly:
            t1 = time.perf_counter()
            system_status = self.system_status
            t2 = time.perf_counter()
            logger.debug("It takes %.1f s to collect system status.", t2 - t1)
            t1 = time.perf_counter()
            autoupdate_versions = self.get_autoupdate_versions()
            t2 = time.perf_counter()
            logger.debug("It takes %.1f s to collect autoupdate versions.", t2 - t1)
            system_status_selected = {
                k: v for k, v in system_status.items() if k not in autoupdate_versions
            }
            self._device_info = {**system_status_selected, **autoupdate_versions}
        return self._device_info

    @property
    def is_vdom_enabled(self):
        # for some platform if vdom not enabled, won't have Virtual information in
        # get system statuss
        return (
            self.system_status.get("Virtual domain configuration", DISABLE) != DISABLE
        )

    def get_autoupdate_versions(self, is_vdom_enabled=None):
        if is_vdom_enabled or self.is_vdom_enabled:
            self._goto_global_view()
        self.clear_buffer()
        *_, versions_raw = self.send_command("diag autoupdate versions", timeout=10)
        logger.debug("The autoupdate version is\n%s", versions_raw)
        pattern = re.compile(
            r"\r\n([^\r\n]+)\r\n--+\r\nVersion: ([0-9.]+)[ \r\n]", flags=re.M | re.S
        )
        matched = pattern.findall(versions_raw)
        update_versions = {}
        if matched:
            update_versions = dict(matched)
        else:
            logger.error("Failed to parse update versions")
        if is_vdom_enabled:
            self._return_to_user_view()
        logger.debug("The extracted autoupdate version is\n%s", update_versions)
        return update_versions

    def _goto_global_view(self):
        self.send_command("config global")

    def _return_to_user_view(self):
        self.send_command("end")

    def _handle_embeded_session(self, command):
        new_session_commands = ("telnet ", "ssh ", "sshpass ", "ftp ")
        if command.startswith(new_session_commands):
            self.embeded_conn = True
        if command == "exit":
            self.embeded_conn = False
        return self.embeded_conn

    def _translate_signal_command(self, command):
        mapping = {
            "ctrl_b": "\x02",
            "ctrl_c": "\x03",
            "ctrl_d": "\x04",
            "backspace": "\x08",
        }
        return mapping.get(command.strip(), command)

    def _process_command(self, command):
        command = self._translate_signal_command(command)
        self._handle_embeded_session(command)
        return command

    def is_reboot_command(self, command):
        reboot_command_patterns = (
            r"^exe[^\s]*\s+reboot",
            r"^exe[^\s]*\s+vm-license",
            r"^exe[^\s]*\s+restore",
            r"^diag[^\s]*\s+sys[^\s]*\s+flash[^\s]*\s+format",
            r"^diag[^\s]*\s+deb[^\s]*\s+kernel\s+sysrq\s+command\s+crash",
        )
        return any(re.match(pattern, command) for pattern in reboot_command_patterns)

    def send_command(
        self,
        command,
        pattern=DEFAULT_PROMPTS,
        timeout=MAX_TIMEOUT_FOR_REBOOT,
    ):
        self.clear_buffer()
        command = self._process_command(command)
        if self.is_reboot_command(command) and pattern == DEFAULT_PROMPTS:
            pattern = FOS_LOGIN_PROMPTS
        pattern = f"{pattern}|{AUTO_PROCEED_PATTERNS}"
        start_time = time.time()
        auto_proceed_times = 0
        matched, handled_output = self.conn.send_command(command, pattern, timeout)
        logger.info(handled_output)
        while time.time() - start_time < timeout:
            logger.debug("Matched group is '%s'", matched.group())
            command = self.require_confirm(matched.group())
            if command is None:
                break
            if auto_proceed_times > MAX_AUTO_PROCEED_TIMES:
                logger.warning("Stopping AUTOPROCEED by sending CTRL_C")
                matched, output = self.conn.send_command("\x03", pattern, 3)
                logger.info(output)
                handled_output += output
                break
            matched, output = self.conn.send_command(command, pattern, timeout)
            logger.info(output)
            handled_output += output
            auto_proceed_times += 1
        else:
            logger.debug("* TIMEOUT * Unable to match pattern...")
        return matched, handled_output

    def start_record_terminal(self, folder_name):
        self.conn.start_record(folder_name)

    def stop_record_terminal(self):
        self.conn.stop_record()

    def set_keep_running(self, keep_running):
        self.keep_running = keep_running

    def set_confirm_with_newline(self, confirm_with_newline):
        self.confirm_with_newline = confirm_with_newline

    def set_wait_for_confirm(self, wait_for_confirm):
        self.wait_for_confirm = wait_for_confirm

    def _extract_license_info(self):
        license_info_file = env.get_license_info()
        if not license_info_file:
            return
        with open(license_info_file, "r", encoding="utf-8") as f:
            input_file = csv.DictReader(f)
            for row in input_file:
                type_ = row["Type"]
                sn = row["SN"]
                vdom_lic = row["Vdom Lic"]
                expire_date = row["Expired Date"]
                self.license_info[type_] = {
                    "SN": sn,
                    "VDOM": vdom_lic,
                    "expire_date": expire_date,
                }

    def pause_stdout(self):
        self.conn.pause_stdout()

    def resume_stdout(self):
        self.conn.resume_stdout()
