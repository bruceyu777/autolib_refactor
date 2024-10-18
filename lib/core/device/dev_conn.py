import re
import sys
import time

import pexpect
import ptyprocess

from lib.services import env, logger

from .log_file import LogFile
from .output_buffer import OutputBuffer
from .pexpect_wrapper import Spawn, new_buffer_init_class

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

    def get_clean_buffer_init_class(self):
        device_type = self.dev_name.split("_")[0]
        buffer_clean_pattern = env.get_buffer_clean_pattern_by_dev_type(device_type)
        return new_buffer_init_class(device_type, buffer_clean_pattern)

    def _new_client(self):
        if self._client:
            self.close()
        buffer_for_pexpect = self.get_clean_buffer_init_class()
        self._client = Spawn(
            self.conn,
            buffer_for_pexpect,
            encoding="utf-8",
            echo=True,
            logfile=sys.stdout,
            codec_errors="ignore",
        )
        self.log_file = LogFile(self._client, self.dev_name)
        script = env.get_var("testing_script")
        if script is None:
            self.start_record("setup")
        else:
            self.start_record(script)

    @property
    def client(self):
        if not self._client or not self._client.isalive():
            self._new_client()
            self.login()
        return self._client

    def close(self):
        try:
            self._client.close()
        except (
            AttributeError,
            OSError,
            pexpect.ExceptionPexpect,
            ptyprocess.PtyProcessError,
        ):
            pass

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
        cur_pos = len(self.output_buffer)
        logger.debug("current command is %s", command)
        logger.debug("current pos in send_command is %s", cur_pos)
        logger.debug(
            "current output in send_command is %s", self.output_buffer[cur_pos:]
        )
        logger.debug("Current pattern is %s", pattern)

        if command.endswith("?"):
            self.send(command)
        elif command == "nan_enter":
            self.send("\x0d")
        elif command.startswith("backspace"):
            cnt = int(command.split(" ")[1])
            for _ in range(cnt):
                self.send("\x08")
            self.send("\x0d")
        else:
            self.send_line(command)
        # make sure to match the output after command is send
        try:
            m, output = self.search(re.escape(command), ONE_SECOND, cur_pos)
        except pexpect.TIMEOUT:
            logger.warning("Failed to match %s in %s s.", command, ONE_SECOND)
        match_pos = cur_pos
        if m:
            match_pos = match_pos + m.start()
        else:
            logger.debug(
                "current output in send_command is %s", self.output_buffer[match_pos:]
            )
        try:
            m, output = self.search(pattern, timeout, match_pos)
            return m, output
        except pexpect.TIMEOUT:
            logger.warning("Failed to match %s in %s s.", pattern, timeout)
            return m, output

    def expect(self, pattern, timeout=1, need_clear=True):
        m, output = self.search(pattern, timeout)

        logger.debug("The ouput for expect is: \n'%s'", output)
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
                if time.time() >= start_time + (timeout / MAX_SEARCH_CNT) * count:
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

    def pause_stdout(self):
        self.log_file.pause_stdout()

    def resume_stdout(self):
        self.log_file.resume_stdout()


if __name__ == "__main__":
    pass
