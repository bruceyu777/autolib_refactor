import re
import telnetlib
import time

from lib.services import logger
from lib.utilities.exceptions import LoginDeviceFailed


class TerminalServer(telnetlib.Telnet):

    expect_list = [
        r": $",  # input password
        r">$",  # enable mode
        r"#$",  # after enable
        r"\[confirm\]$",  # [confirm]
        r"Bad passwords$",  # bad password, then connection will be reset
        r"255\)$",  # wrong command with FQDN resolve
    ]
    expect_pattern = [re.compile(exp.encode("utf-8")) for exp in expect_list]
    wrong_cmd_timeout = 11  # wrong command need to wait 11 seconds

    def __init__(self, host, port=23, user="cisco", pwd="cisco"):
        super().__init__()
        self.user = user
        self.password = pwd
        self.port = port
        self.host = host

    def __str__(self):
        return f"TerminalServer({self.host}:{self.port})"

    def send(self, cmd):
        cmd = cmd.encode("utf-8", errors="ignore")
        self.write(cmd)
        time.sleep(0.2)
        index, _, text = self.expect(TerminalServer.expect_pattern, 1)
        decoded_output = text.decode("utf-8", errors="ignore")
        logger.info(decoded_output)
        if index == 0:
            decoded_output += self.send(f"{self.password}\n")
        elif index == 1:
            decoded_output += self.send("enable\n")
        elif index == 3:
            decoded_output += self.send("y\n")
        elif index == 4:
            raise LoginDeviceFailed(
                f"Wrong password({self.user}/{self.password}) for {self}"
            )
        elif index == 5:
            time.sleep(TerminalServer.wrong_cmd_timeout)
            decoded_output += self.send("\n")
        return decoded_output

    def clear_line(self, line):
        cmd_list = ["\x03", "clear line %s" % line, ""]
        for cmd in cmd_list:
            self.send(cmd)

    def login(self, timeout=None):
        self.timeout = timeout if timeout else self.timeout
        title = " Terminal Server( %s:%s ) " % (self.host, str(self.port))
        logger.info("\n%s\n", title)
        if self.sock is None:
            self.open(self.host, self.port, self.timeout)
        while True:
            data = self.send("\x03")
            if data and not data.endswith(")#"):
                break
        return True
