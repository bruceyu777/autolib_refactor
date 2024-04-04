import pexpect
import sys
from .fos_dev import FosDev
from lib.services.log import logger


class FortiGate(FosDev):
    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        return self.model.replace("-", "_").replace("FortiGate", "FGT")


    @property
    def system_status(self):
        rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*?"
            r"Serial-Number: (?P<serial>[^\r\n]*).*?"
            r"BIOS version: (?P<bios_version>[^\r\n]*).*?"
            r"Virtual domain configuration: (?P<vdom_mode>[^\r\n]*).*?"
            r"Branch point: (?P<branch_point>[^\r\n]*).*?"
        )
        matched = self.show_command_may_have_more("get system status", rule)
        if not matched:
            rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
            r"Serial-Number: (?P<serial>[^\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
            r"Branch point: (?P<branch_point>[^\n]*).*"
        )
            matched = self.show_command_may_have_more("get system status", rule)
        return matched

    def clear_terminal(self):
        dev_conn = (
            self.dev_cfg["connection"]
            if "telnet" in self.dev_cfg["connection"]
            else f"telnet {self.dev_cfg['connection']}"
        )
        conn = " ".join(dev_conn.split(" ")[:2])
        line_no = int(dev_conn.split(" ")[-1]) - 2000
        print(self.dev_cfg)
        password = self.dev_cfg["ciscopassword"]

        client = pexpect.spawn(conn,
                encoding="utf-8",
                echo=True,
                logfile=sys.stdout,
                codec_errors="ignore")
        client.expect("Password:")
        client.sendline(password)
        index = client.expect_exact([">", "#", pexpect.TIMEOUT, pexpect.EOF])
        if index == 0:
            client.sendline("enable")
            client.expect("Password:")
            client.sendline(password)
            client.expect("#")
            self.clear(client, line_no)
        elif index == 1:
            self.clear(client, line_no)
        elif index in [2, 3]:
            logger.info("Failed to clear terminal server.")

    def clear(self, client, line_no):
        client.sendline(f"clear line {line_no}")
        client.expect("\[confirm\]")
        client.sendline("")
        client.expect("#")
        client.sendline("exit")

    def connect(self):
        #make sure console port in therterminal server is not occupied
        self.clear_terminal()
        super().connect()