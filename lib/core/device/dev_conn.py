import re
import sys
import time
import pdb

import pexpect
from lib.services import env, logger

from .log_file import LogFile
from .output_buffer import OutputBuffer

READ_WAIT_TIME = 120
WAIT_TIME = 60
MAX_SEARCH_CNT = 3

CODE_FORMAT = "ascii"
ERROR_INFO = (
    "command parse error",
    "Unknown action",
    "Command fail",
    "command parse error",
    "failed command",
)
ONE_SECOND = 1


class DevConn:
    def __init__(self, dev_name, connection, user_name, password):
        self.dev_name = dev_name
        self.conn = connection
        self._client = None
        self.user_name = user_name
        self.password = password
        self.output_buffer = OutputBuffer()
        self.log_file = None
        self.cur_pos = 0

    def __del__(self):
        if self.log_file is not None:
            del self.log_file
            self.log_file = None

    @property
    def client(self):
        if self._client is None:
            self._client = pexpect.spawn(
                self.conn,
                encoding="utf-8",
                echo=True,
                logfile=sys.stdout,
                codec_errors="ignore",
            )
            self.log_file = LogFile(self.client, self.dev_name)
            script = env.get_var("testing_script")
            if script is not None:
                self.start_record(script)
            else:
                self.start_record("setup")
            self.login()
        return self._client

    def close(self):
        self.client.sendline("exit")
        self._client = None

    def login(self):
        raise NotImplementedError

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
        logger.info("current command is %s", command)
        logger.info("current pos in send_command is %s", cur_pos)
        logger.info(
            "current output in send_command is %s", self.output_buffer[cur_pos:]
        )
        logger.info("Current pattern is %s", pattern)

        # if command == "nan_enter":
        #     self.client.send('\x0d')
        if command.endswith("?"):
            self.client.send(command)
        elif command == "nan_enter":
            self.client.send('\x0d')
        elif command.startswith("backspace"):
            cnt = int(command.split(" ")[1])
            # print("send backspace")
            for i in range(cnt):
                self.client.send("\x08")
            self.client.send("\x0d")
        else:
            self.client.sendline(command)

        #make sure to match the output after command is send
        try:
            m, output = self.search(re.escape(command), ONE_SECOND, cur_pos)
        except pexpect.TIMEOUT:
            logger.warning("Failed to match %s in %s s.", command, ONE_SECOND)
        match_pos = cur_pos
        if m:
            match_pos = match_pos + m.start()
        else:
            logger.info("current output in send_command is %s", self.output_buffer[match_pos:])
        try:
            m, output = self.search(pattern, timeout, match_pos)
            #command failure

            return m, output
        except pexpect.TIMEOUT:
            logger.warning("Failed to match %s in %s s.", pattern, timeout)
            return m, output

    def expect(self, pattern, timeout=1, need_clear=True):
        m, output = self.search(pattern, timeout)

        #logger.info("The ouput for expect is %s", output)
        #logger.info("*" * 80)
        if m is not None:
            logger.info(
                "The buffer size is %s, the matched index is %s",
                len(self.output_buffer),
                m.end(),
            )
            logger.info(
                "The buffer content that has been cleared is %s",
                self.output_buffer[: m.end()],
            )
            if need_clear:
                self.clear_buffer(m.end())

        return m, output

    def search(self, pattern, timeout, pos=0):
        if pos == -1:
            pos = len(self.output_buffer)

        count, matched = 0, False
        start_time = time.time()
        end_time = start_time + timeout
        while True:
            if timeout > 600:
                if time.time() >= start_time + (timeout/MAX_SEARCH_CNT)*count:
                    matched = self.output_buffer.search(pattern, pos)
                    count += 1
            else:
                matched = self.output_buffer.search(pattern, pos)
            if matched:
                break
            if time.time() > end_time:
                matched = self.output_buffer.search(pattern, pos)
                break

            self._read_output(ONE_SECOND)

        self._log_output(self.output_buffer)
        return matched, self.output_buffer[pos:]

    def clear_buffer(self, pos=None):
        self.output_buffer.clear(pos)

    def send(self, s):
        return self.client.send(s)

    def send_line(self, s):
        self.client.sendline(s)

    @staticmethod
    def _log_output(output):
        separator = "\n" + "-" * 80 + "\n"
        content = f"{separator} {output} {separator}"
        logger.info("Buffer content is :%s", content)

    def _dump_to_buffer(self):
        output = self.client.before + self.client.after
        # output = output.replace("\r\n", "\n")

        self.output_buffer.append(output)

        self._log_output(output)
        return output

    def _read_output(self, timeout=ONE_SECOND):
        try:
            self.client.expect(".+", timeout=timeout)
            self._dump_to_buffer()
            return True
        except pexpect.TIMEOUT:
            logger.info("No more characters captured.")
            return False

    def start_record(self, folder_name):
        self.log_file.start_record(folder_name)

    def stop_record(self):
        self.log_file.stop_record()


if __name__ == "__main__":
    pass
