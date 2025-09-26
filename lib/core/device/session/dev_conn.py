import re
import sys
import time
from itertools import takewhile

import pexpect
import ptyprocess

from lib.services import env, logger
from lib.services import output as OUTPUT
from lib.settings import (
    BASE_TIME_UNIT,
    MAX_BUFFER_GROWTH,
    REPETITIVE_CHECK_INTERVAL,
    REPETITIVE_PATTERN_THRESHOLD,
)

from .pexpect_wrapper import LogFile, OutputBuffer, Spawn

ERROR_INFO = (
    "command parse error",
    "Unknown action",
    "Command fail",
    "command parse error",
    "failed command",
)


def get_read_buffer_timer(timeout_timer):
    rate = timeout_timer // 100

    if rate <= 2:
        return BASE_TIME_UNIT
    if rate <= 10:
        return BASE_TIME_UNIT * rate * 10
    return BASE_TIME_UNIT * 100


class DevConn:
    def __init__(self, dev_name, connection):
        # def __init__(self, dev_name, connection, user_name, password):
        self.dev_name = dev_name
        self.conn = connection
        self.client = None
        clean_patterns = env.get_buffer_clean_pattern_by_dev_type(
            self.dev_name.split("_")[0]
        )
        self.output_buffer = OutputBuffer(clean_patterns=clean_patterns)
        self.log_file = None
        self.cur_pos = 0

    def __del__(self):
        if self.log_file is not None:
            del self.log_file
            self.log_file = None

    def _normalize_conn_parameters(self):
        # disable SSH strict host key checking
        if "ssh" in self.conn:
            self.conn = self.conn.replace(
                "ssh ",
                "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ",
            )
            logger.info("Disable SSH strict host key checking.")

    def create_session_log_file(self):
        if self.log_file is None:
            self.log_file = LogFile(
                self.client,
                self.dev_name,
                filepath_generator=OUTPUT.compose_terminal_file,
            )
        return self.log_file

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
            echo=True,
            logfile=sys.stdout,
            codec_errors="ignore",
        )
        self.create_session_log_file()
        script = env.get_var("testing_script")
        record = "setup" if script is None else script
        self.start_record(record)
        return self

    def isalive(self):
        return self.client and self.client.isalive()

    def close(self):
        try:
            self.client.close()
        except (
            AttributeError,
            OSError,
            pexpect.ExceptionPexpect,
            ptyprocess.PtyProcessError,
        ) as e:
            logger.debug("Failed to close the client(%s).", e)

    def send_command(self, command, pattern, timeout):
        # make sure to match the output after command is send

        # self._read_output()

        # For diag commands, there are 3 types of output that could
        # be expected:
        # 1 output will be continue untill user input another command
        # 2 #
        # 3 need confirmStart configuring output mode to be standard.
        cur_pos = len(self.output_buffer)
        logger.debug("current command is '%s'", command)
        logger.debug("current pos in send_command is %s", cur_pos)
        logger.debug(
            "current output in send_command is\n'%s'", self.output_buffer[cur_pos:]
        )
        logger.debug("Current pattern is '%s'", pattern)

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
            m, output = self.search(re.escape(command), BASE_TIME_UNIT, cur_pos)
            match_pos = cur_pos + m.start()
        except (pexpect.TIMEOUT, Exception):
            logger.debug("Failed to match %s in %s s.", command, BASE_TIME_UNIT)
            match_pos = cur_pos
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
            logger.debug(
                "The buffer size is %s, the matched index is %s",
                len(self.output_buffer),
                m.end(),
            )
            logger.debug(
                "The buffer content that has been cleared is %s",
                self.output_buffer[: m.end()],
            )
            if need_clear:
                self.clear_buffer(pos=m.end())

        return m, output

    def search(self, pattern, timeout, pos=0):
        logger.debug(
            "The pattern for search is '%s', timeout is %d s.", pattern, timeout
        )
        if pos == -1:
            pos = len(self.output_buffer)

        read_buffer_timeout = get_read_buffer_timer(timeout)
        matched = None
        start_time = time.time()
        end_time = start_time + timeout

        # Initialize guard state for detecting potentially infinite output
        guard = self._init_infinite_output_guard()

        while time.time() <= end_time:
            matched = self.output_buffer.search(pattern, pos)
            if matched:
                break

            should_break, reason = self._should_break_for_infinite_output(guard)
            if should_break:
                logger.warning("%s", reason)
                break

            self._read_output(read_buffer_timeout)

        time_used = time.time() - start_time
        self._log_output(self.output_buffer)
        logger.debug(
            "Pattern - <%s> was matched?  %s, time used: %.1f s",
            matched,
            pattern,
            time_used,
        )
        return matched, self.output_buffer[pos:]

    def clear_buffer(self, pos=None, read_before_clean=True):
        if read_before_clean:
            self._read_output(timeout=0.1)
        self.output_buffer.clear(pos)

    def send(self, s):
        return self.client.send(s)

    def send_line(self, s):
        self.client.sendline(s)

    @staticmethod
    def _log_output(output):
        separator = "\n" + "-" * 80 + "\n"
        content = f"{separator} {output} {separator}"
        logger.debug("Buffer content is :%s", content)

    def _dump_to_buffer(self):
        output = self.client.before + self.client.after
        self.output_buffer.append(output)
        self._log_output(output)
        return output

    def _read_output(self, timeout=BASE_TIME_UNIT):
        try:
            self.client.expect(".+", timeout=timeout)
            self._dump_to_buffer()
            return True
        except pexpect.TIMEOUT:
            logger.debug("No more characters captured.")
            return False

    def _init_infinite_output_guard(self):
        return {
            "initial_buffer_size": len(self.output_buffer),
            "last_check_size": len(self.output_buffer),
            "max_buffer_growth": MAX_BUFFER_GROWTH,
            "repetitive_check_interval": REPETITIVE_CHECK_INTERVAL,
            "repetitive_pattern_threshold": REPETITIVE_PATTERN_THRESHOLD,
        }

    def _handle_infinite_output(self, recent_output, guard):
        if self._detect_repetitive_pattern(
            recent_output, guard["repetitive_pattern_threshold"]
        ):
            self.client.send("\x03")
            return True, (
                "Repetitive pattern detected in output. Possible infinite output. "
                "Breaking search loop by Ctrl-C."
            )
        return False, ""

    def _should_break_for_infinite_output(self, guard):
        current_size = len(self.output_buffer)
        growth = current_size - guard["initial_buffer_size"]
        should_break = False
        reason = ""

        # Excessive growth guard
        if growth > guard["max_buffer_growth"]:
            should_break = True
            reason = (
                f"Buffer growth exceeded limit ({growth} chars). "
                "Possible infinite output detected. Breaking search loop to prevent memory exhaustion."
            )

        # Repetitive pattern guard (checked periodically)
        elif (
            current_size - guard["last_check_size"] > guard["repetitive_check_interval"]
        ):
            recent_output = self.output_buffer[guard["last_check_size"] :]
            should_break, reason = self._handle_infinite_output(recent_output, guard)
            guard["last_check_size"] = current_size

        return should_break, reason

    def _detect_repetitive_pattern(self, text, threshold):
        """Fast check for repetitive output at the buffer tail.

        Strategy (O(window)):
        - Inspect only a small tail window.
        - Detect a long trailing run of one character (e.g., yyyyy...).
        - Detect consecutive repeats of a short unit at the tail.
        """
        if not text or len(text) < threshold:
            return False

        max_unit = min(16, max(1, len(text) // max(1, threshold)))
        # Tail window size:
        # - Must be large enough to hold `threshold` repeats of the largest unit (`max_unit * threshold`).
        # - Add a small constant slack (+8) to avoid missing partial matches at the boundary.
        tail_window_len = max_unit * threshold + 8
        tail = text[-tail_window_len:]
        return self._has_repetitive_char_run(
            tail, threshold
        ) or self._has_repetitive_unit_run(tail, threshold, max_unit)

    def _has_repetitive_char_run(self, text, threshold):
        last_char = text[-1]
        run = sum(1 for _ in takewhile(lambda ch: ch == last_char, reversed(text)))
        return run >= threshold

    def _has_repetitive_unit_run(self, text, threshold, max_unit):
        """Check if the tail consists of consecutive repeats of a short unit.
        Compares unit-length slices walking backwards from the end.
        """
        n = len(text)
        if n == 0:
            return False
        for unit_len in range(max_unit, 0, -1):
            if unit_len * threshold > n:
                # Not enough room for the required repeats
                continue
            unit = text[-unit_len:]
            repeats = 1
            idx = n - 2 * unit_len
            while idx >= 0 and text[idx : idx + unit_len] == unit:
                repeats += 1
                if repeats >= threshold:
                    return True
                idx -= unit_len
        return False

    def start_record(self, folder_name):
        self.log_file.start_record(folder_name)

    def stop_record(self):
        self.log_file.stop_record()

    def pause_stdout(self):
        self.log_file.pause_stdout()

    def resume_stdout(self):
        self.log_file.resume_stdout()
