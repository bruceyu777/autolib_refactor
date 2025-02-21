import sys

import pexpect

from lib.services import env, logger

from .dev_conn import DevConn
from .pexpect_wrapper import Spawn


class ComputerConn(DevConn):

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

    def connect(self):
        clean_patterns = env.get_buffer_clean_pattern_by_dev_type(
            self.dev_name.split("_")[0]
        )
        self._normalize_conn_parameters()
        self.client = Spawn(
            self.conn,
            clean_patterns,
            logger.job_log_handler,
            encoding="utf-8",
            echo=False,
            logfile=sys.stdout,
            codec_errors="ignore",
        )
        self.create_session_log_file()
        script = env.get_var("testing_script")
        record = "setup" if script is None else script
        self.start_record(record)
        return self
