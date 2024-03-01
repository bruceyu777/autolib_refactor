from lib.services import env

from .computer import Computer
from .computer_conn import ComputerConn


class Pc(Computer):
    def __init__(self, dev_name):
        self.dev_cfg = env.get_dev_cfg(dev_name)
        super().__init__(dev_name)

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
        return super().send_command(command, timeout=60)
