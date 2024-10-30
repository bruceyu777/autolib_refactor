import sys

import pexpect

from lib.services import env, logger

from .dev_conn import DevConn
from .pexpect_wrapper import LogFile, Spawn


class ComputerConn(DevConn):
    def login(self):
        index = self._client.expect(
            [
                r"\(yes/no/\[fingerprint\]\)\? $",
                r"[Pp]assword: $",  # Some linux flavor popup is `Password:`
                pexpect.TIMEOUT,
                pexpect.EOF,
            ]
        )

        logger.debug("enter into connect: the index is %s", index)
        if index == 0:
            self._client.sendline("yes")
            self.login()
        elif index == 1:
            self._client.sendline(self.password)
            self._client.expect(r"[$#\>]\s*")
        elif index == 2:
            logger.error("\nTimeout to login.")
        elif index == 3:
            logger.error("\nFailed to login %s as connection is closed.", self.dev_name)

    def send_command(self, command, pattern, timeout):
        # make sure to match the output after command is send
        # self._read_output()
        # For diag commands, there are 3 types of output that could
        # be expected:
        # 1 output will be continue untill user input another command
        # 2 #
        # 3 need confirmStart configuring output mode to be standard.

        # pdb.set_trace()
        cur_pos = len(self.output_buffer)
        logger.debug("current command is '%s'", command)
        logger.debug("current pos in send_command is %s", cur_pos)
        logger.debug(
            "current output in send_command is '%s'", self.output_buffer[cur_pos:]
        )
        logger.debug("Current pattern is '%s'", pattern)
        self.send_line(command)

        # For commands like this:
        # fosqa@ztna-client:~$ forticlient vpn edit sslvpn
        # =====================
        # Create new VPN profile: sslvpn
        # =====================
        # Remote Gateway: 10.1.100.4:10443
        # Authentication (1.prompt / 2.save / 3.disable) [default=1]: 1
        # Certificate Type (1.local (pkcs12) / 2.smartcard (pkcs11) / 3.disable) [current=disable]:
        # DONE.

        pattern += r"|[\w\]]+:\s$" + "|[Pp]assword:$"
        try:
            m, output = self.search(pattern, timeout, cur_pos)
            return m, output
        except pexpect.TIMEOUT:
            logger.warning("Failed to match %s in %s s.", pattern, timeout)
            return m, output

    def _new_client(self):
        if self._client:
            self.close()
        buffer_for_pexpect = self.get_clean_buffer_init_class()
        self._client = Spawn(
            self.conn,
            buffer_for_pexpect,
            logger.job_log_handler,
            encoding="utf-8",
            echo=False,
            logfile=sys.stdout,
            codec_errors="ignore",
        )
        self.log_file = LogFile(self._client, self.dev_name)
        script = env.get_var("testing_script")
        record = "setup" if script is None else script
        self.start_record(record)

    @property
    def client(self):
        if not self._client or not self._client.isalive():
            self._new_client()
            self.login()
            self.resume_stdout()
        return self._client
