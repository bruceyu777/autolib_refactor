import re
import time
from lib.services.environment import env, logger

DEFAULT_TIMEOUT_FOR_PROMPT = 10


UNIVERSAL_PROMPTS = (r"(?<!--)[$#>] $",)

FOS_UNIVERSAL_PROMPTS = (
    r"login: $",
    r"[P|p]assword: $",
)

AUTO_PROCEED_RULE_MAP = {
    r"\(y/n\)$": "y",
    r"\(yes/no.*\)\??": "yes",
    r"\[Y/N\]\?": "Y",
    r"to accept\): ": "a",
    r"\[confirm\]": "y",
}

SYSCTRL_COMAND = ("Admin:\s*$",)
DEFAULT_PROMPTS = "|".join(
    UNIVERSAL_PROMPTS
    + FOS_UNIVERSAL_PROMPTS
    + tuple(AUTO_PROCEED_RULE_MAP.keys())
    + SYSCTRL_COMAND
)


class Device:
    def __init__(self, dev_name):
        self.dev_name = dev_name
        self.conn = None
        self.dev_cfg = env.get_dev_cfg(dev_name)
        self.keep_running = False
        self.connect()
        self.embeded_conn = False
        self.fnsysctl = False

    def _reconnect_if_exited(self):
        # self.conn._read_output()
        expected_switch_prompts = (
            r"((?P<prompt>[#$]\s*$)|(?P<login>login:)|(?P<Password>Password:))"
        )
        try:
            matched, output = self.conn.send_command(
                "", expected_switch_prompts, DEFAULT_TIMEOUT_FOR_PROMPT
            )
            if matched is None:
                logger.notify(
                    "Failed to switch to device:%s, start reconnecting.",
                    self.dev_name,
                )
                self.connect()
                logger.notify("Device:%s is reconnected.", self.dev_name)
            logger.info("The output is %s.", output)
            logger.info("The matched is %s.", matched)
        except Exception:
            logger.notify(
                "Exception happened when switching to device:%s, start reconnecting.",
                self.dev_name,
            )
            self.connect()
            logger.notify("Device:%s is reconnected.", self.dev_name)

    def switch(self, retry=0):
        # self.clear_buffer()
        if retry > 3:
            logger.info("Failed to switch device: %s", self.dev_name)
        try:
            # self.conn.send_command("\x03", "#", DEFAULT_TIMEOUT_FOR_PROMPT)
            # self._reconnect_if_exited()
            if self.keep_running:
                # expected_switch_prompts = (
                #     r"((?P<prompt>[#$]\s*$)|(?P<login>login:)|(?P<Password>Password:))"
                # )
                # matched, _ = self.conn.send_command(
                #     "", expected_switch_prompts, DEFAULT_TIMEOUT_FOR_PROMPT
                # )
                # if matched.group("login") is not None:
                #     self.conn.login()

                # logger.notify("Succeeded to login device:%s.", self.dev_name)

                return
            else:
                self._reconnect_if_exited()
                logger.info("Start login device %s", self.dev_name)
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

    def send_command(
        self,
        command,
        pattern=DEFAULT_PROMPTS,
        timeout=DEFAULT_TIMEOUT_FOR_PROMPT,
    ):
        if command == "ctrl_c":
            command = "\x03"
        if command == 'nan_enter':
            command = "\x0d"

        if command.startswith("telnet"):
            self.embeded_conn = True
        if command == "exit":
            self.embeded_conn = False

        matched, output = self.conn.send_command(command, pattern, timeout)
        if matched:
            logger.info("Matched group is %s", matched.group())
        while matched is not None:
            confirm_str = self.require_confirm(matched.group())
            if confirm_str:
                logger.info("Matched group is %s", confirm_str)
                # command_pattern = f"{confirm_str}.*{pattern}"
                matched, output = self.conn.send_command(confirm_str, pattern, timeout)
            elif self.require_login(matched.group()) and not self.embeded_conn:
                logger.info("Start login:")
                if not self.fnsysctl:
                    self.conn.login()
                else:
                    self.fnsysctl = False
                break
            elif self.sysctl_login(matched.group()):
                logger.info("Fnsysctl login:")
                self.fnsysctl = True
                break
            else:
                break
        return matched, output

    def start_record_terminal(self, folder_name):
        self.conn.start_record(folder_name)

    def stop_record_terminal(self):
        self.conn.stop_record()

    def set_keep_running(self, keep_running):
        self.keep_running = keep_running
