import re
import telnetlib
import time

from lib.services.environment import env
from lib.services.log import logger
from lib.utilities.exceptions import ResourceNotAvailable
from lib.utilities.util import wrap_as_title


class PowerController(telnetlib.Telnet):
    TYPE = "PDU"
    MAXIMUM_WAIT_TIME = 25
    SESSION_RETRY = 3

    CLI_SYNTAX = {
        "NETBOOTER": {
            "WELCOME_VIEW": r"Telnet .*?V\d+\..*?\r\n",
            "INPUT_VIEW": r"> *$",
            "USERNAME_VIEW": r"User ID: $|>Enter user name: $|>Login: $",
            "PASSWORD_VIEW": r"Password: *$|>Enter password: $",
            "CMD_REBOOT_OUTLET": "rb {}",
            "CMD_OFF_OUTLET": "pset {} 0",
            "CMD_ON_OUTLET": "pset {} 1",
            "CMD_LOGOUT": "logout",
        },
        "SCHNEIDER": {
            "WELCOME_VIEW": r"apc> ",
            "INPUT_VIEW": r"> *$",
            "USERNAME_VIEW": r"User Name : $",
            "PASSWORD_VIEW": r"Password  : $",
            "CMD_REBOOT_OUTLET": "olReboot {}\r",
            "CMD_OFF_OUTLET": "olOff {}\r",
            "CMD_ON_OUTLET": "olOn {}\r",
            "CMD_LOGOUT": "bye\r",
        },
    }

    def __init__(self, name):
        self.dev_name = name
        self.managed_devices = {}
        config = env.get_dev_cfg(self.dev_name)
        self.vendor = config["VENDOR"]
        self.host, *others = config["CONNECTION"].split()
        self.port = others[0] if others else 23
        self.expect_pattern = self._generate_expect_pattern()
        self.extract_dev_outlet_mapping(config)
        super().__init__(self, timeout=PowerController.MAXIMUM_WAIT_TIME)

    def _generate_expect_pattern(self):
        patterns = [v for k, v in self.CLI_SYNTAX[self.vendor] if k.endswith("_VIEW")]
        return sorted(patterns, key=len, reverse=True)

    def extract_dev_outlet_mapping(self, config):
        device_list = env.get_device_list()
        self.managed_devices = {
            k: v.split() for k, v in config.items() if k in device_list
        }

    def __str__(self):
        return "{}-{}('{}:{}')".format(self.vendor, self.dev_name, self.host, self.port)

    def check_connection(self):
        if not self.sock:
            for _ in range(self.SESSION_RETRY):
                if self.login():
                    break
                logger.error(wrap_as_title("Login failed! Trying again..."))
                self.close()
                time.sleep(5)
            else:
                raise ResourceNotAvailable("'{}:{}'".format(self.host, self.port))

    def _open_connection(self, timeout):
        if self.sock is None:
            logger.debug("Open a new connection!")
            self.open(self.host, self.port, timeout)
        return self.sock

    def _pattern(self, view):
        return self.CLI_SYNTAX[self.vendor][view]

    # pylint: disable=arguments-renamed
    def expect(self, patterns, timeout=None):
        compiled_rules = [
            re.compile(p.encode("utf-8"), flags=re.M | re.S) for p in patterns
        ]
        return super().expect(compiled_rules, timeout)

    def login(self, timeout=None):
        timeout = timeout or self.MAXIMUM_WAIT_TIME
        # this power controller can't work with read_until
        logger.info(
            wrap_as_title(" Power Controller( %s:%s ) " % (self.host, self.port))
        )
        for _ in range(self.SESSION_RETRY):
            self._open_connection(timeout)
            time.sleep(2)
            index, *_ = self.read([self._pattern("USERNAME_VIEW")])
            if index == 0:
                username = env.get_section_var(self.dev_name, "USERNAME")
                self.send(f"{username}\r", withcrlf=False)
                time.sleep(2)
                index, *_ = self.read([self._pattern("PASSWORD_VIEW")])
                if index == 0:
                    password = env.get_section_var(self.dev_name, "PASSWORD")
                    self.send(f"{password}\r", withcrlf=False)
                    time.sleep(2)
                    index, *_ = self.read([self._pattern("INPUT_VIEW")])
                    if index == 0:
                        logger.debug("Login Successfully!")
                        time.sleep(2)
                        return True
        return False

    def send(self, cmd, withcrlf=True):
        if withcrlf:
            cmd = cmd.strip() + "\r\n"
        self.write(cmd.encode("utf-8", errors="ignore"))

    def read(self, pattern=None, timeout=5):
        pattern = pattern or self.expect_pattern
        index, matched, text = self.expect(pattern, timeout)
        cli_output = text.decode("utf-8", errors="ignore")
        logger.info(cli_output)
        return index, matched, text

    def rebootoutlet(self, outlet):
        cmd = self._pattern("CMD_REBOOT_OUTLET").format(outlet.strip())
        self.send(cmd)
        time.sleep(2)
        return self.read()

    def power_on_off(self, outlet, poweron=True):
        view = "CMD_ON_OUTLET" if poweron else "CMD_OFF_OUTLET"
        cmd = self._pattern(view).format(outlet)
        self.send(cmd)
        time.sleep(2)
        return self.read()

    def rebootdev(self, dev, interval=2):
        try:
            outlets = self.managed_devices[dev]
        except KeyError as e:
            raise ResourceNotAvailable(dev) from e

        for outlet in outlets:
            self.power_on_off(outlet, poweron=False)
        time.sleep(interval)
        for outlet in outlets:
            self.power_on_off(outlet, poweron=True)
        time.sleep(interval)

    def logout(self):
        try:
            self.send(self._pattern("CMD_LOGOUT"))
            time.sleep(2)
            self.read()
        except ConnectionResetError:
            self.close()
            logger.error("logout")
        logger.info("\n%s\n", (wrap_as_title()))
