import re

from lib.services.log import logger
from lib.utilities import ResourceNotAvailable, sleep_with_progress

from .device import Device
from .session import ComputerConn

FIVE_MINUTES = 5 * 60
DEFAULT_TIMEOUT = FIVE_MINUTES
DEFAULT_EXPECTED_OUTPUT = r"[#$:\>]\s?$"


class Computer(Device):
    password_pattern = r"[Pp]assword:\s*$"

    def __init__(self, device_name):
        self.prompts = DEFAULT_EXPECTED_OUTPUT
        self.timeout = DEFAULT_TIMEOUT
        self.need_carriage = False
        super().__init__(device_name)

    def initialize(self):
        super().initialize()
        self.login()
        self.conn.resume_stdout()

    def reconnect(self, max_retries=3):
        logger.info("Start to reconnect...")
        backoff_timer = 5
        for attempt in range(max_retries):
            try:
                self.connect()
                self.initialize()
                return
            except Exception:
                logger.exception("Reconnect attempt %d failed!", attempt + 1)
                sleep_with_progress(backoff_timer)
                backoff_timer *= 3
        raise ResourceNotAvailable("Max reconnect attempts reached")

    def _compose_conn(self):
        if "CONNECTION" in self.dev_cfg:
            return self.dev_cfg["CONNECTION"]
        ip = self.dev_cfg["MANAGEMENT"]
        proto = self.dev_cfg.get("ACCESS_PROTOCOL", "SSH")
        port = self.dev_cfg.get("ACCESS_PORT", "22")
        if proto.upper() != "SSH":
            raise NotImplementedError
        username = self.dev_cfg["USERNAME"]
        return f"ssh -p {port} {username}@{ip}"

    def connect(self):
        retry_times, backoff_timer = 3, 5
        for _ in range(retry_times):
            try:
                self.conn = ComputerConn(
                    self.dev_name,
                    self._compose_conn(),
                ).connect()
                matched, _ = self.send_command("\r")
                if matched and matched.group("windows_prompt"):
                    self.need_carriage = True
                return
            except Exception:
                logger.exception("Failed to connect to device %s.", self.dev_name)
                sleep_with_progress(backoff_timer)
                backoff_timer *= 3
        raise ResourceNotAvailable("Max reconnect attempts reached")

    def login(self):
        patterns = "|".join([self.password_pattern, self.prompts])
        matched, output = self.conn.expect(patterns, timeout=20)
        if re.search(self.prompts, output):
            logger.info("Already logged in %s.", self.dev_name)
        else:
            if not matched:
                logger.error("\nFailed to get password prompt for %s!", self.dev_name)
                raise ResourceNotAvailable(f"Unable to login {self.dev_name}")
            self.conn.send_line(self.dev_cfg["PASSWORD"])
            self.conn.expect(self.prompts, timeout=30)
            logger.info("Successfully logged in %s.", self.dev_name)

    def force_login(self):
        self.conn.close()
        self.reconnect()
