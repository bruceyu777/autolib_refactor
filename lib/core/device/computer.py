from lib.services.log import logger

from .device import Device

FIVE_MINUTES = 5 * 60
DEFAULT_TIMEOUT = FIVE_MINUTES
DEFAULT_EXPECTED_OUTPUT = r"[#$:]\s?$"


class Computer(Device):
    def __init__(self, device_name):
        super().__init__(device_name)
        self.prompts = DEFAULT_EXPECTED_OUTPUT
        self.timeout = DEFAULT_TIMEOUT

    def connect(self):
        raise NotImplementedError
