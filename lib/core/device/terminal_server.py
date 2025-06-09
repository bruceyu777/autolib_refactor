import re
import sys
import time

import pexpect

from lib.services import logger
from lib.utilities import NotSupportedDevice, OperationFailure


class CiscoTerminalServer:
    def __init__(self, conn, password):
        self.conn = conn
        self.password = password
        self._client = None

    def _new_session(self):
        return pexpect.spawn(
            self.conn,
            encoding="utf-8",
            echo=True,
            logfile=sys.stdout,
            codec_errors="ignore",
        )

    def _enable(self):
        self.client.sendline("enable")
        index = self.client.expect_exact(
            ["#", "Password:", pexpect.TIMEOUT, pexpect.EOF]
        )
        if index == 1:
            self.client.sendline(self.password)
            index = self.client.expect(["#", pexpect.TIMEOUT, pexpect.EOF])
        return index == 0

    def _login(self):
        index = self._client.expect_exact(
            [">", "#", "Password:", pexpect.TIMEOUT, pexpect.EOF]
        )
        if index == 2:
            self.client.sendline(self.password)
            index = self.client.expect_exact([">", "#", pexpect.TIMEOUT, pexpect.EOF])
        if index == 0:
            return self._enable()
        if index == 1:
            return True
        raise OperationFailure(
            "login failed. Unexpected response from terminal server."
        )

    @property
    def client(self):
        if self._client is None or not self._client.isalive():
            self._client = self._new_session()
            self._login()
        return self._client

    def clear(self, line_no):
        self.client.sendline(f"clear line {line_no}")
        self.client.expect(r"\[confirm\]")
        self.client.sendline("y")
        self.client.expect("#")

    def __del__(self):
        self.client.close()


class DigiTerminalServer(CiscoTerminalServer):
    prompts = r"#> "

    def __init__(self, conn, password, username):
        super().__init__(conn, password)
        self.username = username

    def _login(self):
        index = self._client.expect_exact(
            ["login: ", DigiTerminalServer.prompts, pexpect.TIMEOUT, pexpect.EOF]
        )
        if index == 1:
            return self._client
        if index == 0:
            self.client.sendline(self.username)
            self._client.expect("password:")
            self.client.sendline(self.password or "")
            self.client.expect(DigiTerminalServer.prompts)
            return self._client
        raise OperationFailure(
            "login failed. Unexpected response from terminal server."
        )

    def _retr_session_id(self, line_no):
        self.client.sendline("who")
        index = self.client.expect(DigiTerminalServer.prompts)
        if index == 0:
            output = self.client.before
            pattern = rf"(\d+)\s+[\d:A-F.]+\s+serial {line_no}\s"
            session_match = re.search(pattern, output)
            return session_match.group(1) if session_match else None
        logger.error("Unexpected response from terminal server.")
        return None

    def clear(self, line_no):
        session_id = self._retr_session_id(line_no)
        if session_id is not None:
            self.client.sendline(f"kill {session_id}")
            self.client.expect_exact(
                [DigiTerminalServer.prompts, pexpect.TIMEOUT, pexpect.EOF]
            )
            time.sleep(1)
            session_id = self._retr_session_id(line_no)
            if session_id is not None:
                logger.error("\n*** Failed to kill the session. ***\n")


def new_terminal_server(conn, password, username=None, vendor="CISCO"):
    if vendor == "CISCO":
        return CiscoTerminalServer(conn, password)
    if vendor == "DIGI":
        return DigiTerminalServer(conn, password, username)
    raise NotSupportedDevice("Unsupported terminal server vendor: %s" % vendor)
