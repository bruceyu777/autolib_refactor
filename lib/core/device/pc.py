import time

from .computer import Computer
from .device import DEFAULT_PROMPTS


class Pc(Computer):

    def force_login(self):
        self.conn.close()
        self.initialize()

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
