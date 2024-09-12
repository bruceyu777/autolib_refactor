import pexpect
import sys
from lib.services.log import logger

from .dev_conn import DevConn
from .log_file import LogFile
from .output_buffer import OutputBuffer
from lib.services import env, logger
import pdb

class ComputerConn(DevConn):
    def login(self):
        index = self._client.expect(
            [
                r"\(yes/no/\[fingerprint\]\)\? $",
                "password: $",
                pexpect.TIMEOUT,
                pexpect.EOF,
            ]
        )

        logger.info("enter into connect: the index is %s", index)
        if index == 0:
            self._client.sendline("yes")
            self.login()
        elif index == 1:
            self._client.sendline(self.password)
            self._client.expect(r"[$#\>]\s*")
        elif index == 2:
            logger.error("Timeout to login.")
        elif index == 3:
            logger.error(
                "Failed to login %s as connection is closed.", self.dev_name
            )
    def send_command(self, command, pattern, timeout):
        #make sure to match the output after command is send

        # self._read_output()

        #For diag commands, there are 3 types of output that could
        #be expected:
        #1 output will be continue untill user input another command
        #2 #
        #3 need confirmStart configuring output mode to be standard.

        # pdb.set_trace()
        cur_pos = len(self.output_buffer)
        logger.info("current command is %s", command)
        logger.info("current pos in send_command is %s", cur_pos)
        logger.info(
            "current output in send_command is %s", self.output_buffer[cur_pos:]
        )
        logger.info("Current pattern is %s", pattern)
        self.client.sendline(command)

        # For commands like this:
        # fosqa@ztna-client:~$ forticlient vpn edit sslvpn
        # =====================
        # Create new VPN profile: sslvpn
        # =====================
        # Remote Gateway: 10.1.100.4:10443
        # Authentication (1.prompt / 2.save / 3.disable) [default=1]: 1
        # Certificate Type (1.local (pkcs12) / 2.smartcard (pkcs11) / 3.disable) [current=disable]:
        # DONE.

        pattern = pattern + "|[\w\]]+:\s$" + "|Password:$" + "password:$"
        try:
            m, output = self.search(pattern, timeout, cur_pos)
            return m, output
        except pexpect.TIMEOUT:
            logger.warning("Failed to match %s in %s s.", pattern, timeout)
            return m, output

    @property
    def client(self):
        if self._client is None:
            self._client = pexpect.spawn(
                self.conn,
                encoding="utf-8",
                echo=False,
                logfile=sys.stdout,
                codec_errors='ignore',
            )
            self.log_file = LogFile(self._client, self.dev_name)
            script = env.get_var("testing_script")
            if script is not None:
                self.start_record(script)
            else:
                self.start_record("setup")
            self.pause_stdout()
            self.login()
            self.resume_stdout()
        return self._client