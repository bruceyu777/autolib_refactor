import time

from .computer import Computer
from .computer_conn import ComputerConn
from .device import DEFAULT_PROMPTS


class Pc(Computer):
    def __init__(self, dev_name):
        self.need_carriage = False
        super().__init__(dev_name)

    def _compose_conn(self):
        return self.dev_cfg["Connection"]

    def connect(self):
        self.conn = ComputerConn(
            self.dev_name,
            self._compose_conn(),
            user_name=self.dev_cfg["Username"],
            password=self.dev_cfg["Password"],
        )
        matched, _ = self.send_command("\r")
        if matched and matched.group("windows_prompt"):
            self.need_carriage = True

        self.clear_buffer()

    def force_login(self):
        self.conn.close()
        self.connect()

    def send_command(self, command, pattern=DEFAULT_PROMPTS, timeout=5):
        if self.need_carriage:
            command = command + "\r"
        return super().send_command(command, pattern=pattern, timeout=timeout)

    def show_command_may_have_more(self, command, rule):
        self.send_line(command)
        time.sleep(1)
        self.send_line(" ")
        matched, _ = self.search(rule, 10)
        return matched.groupdict() if matched else {}
