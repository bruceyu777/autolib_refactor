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

    def _login(self):
        index = self._client.expect_exact(
            ["Password:", "#", pexpect.TIMEOUT, pexpect.EOF]
        )
        if index == 1:
            return True
        if index == 0:
            self.client.sendline(self.password)
            index = self.client.expect_exact([">", "#", pexpect.TIMEOUT, pexpect.EOF])
            if index == 0:
                self.client.sendline("enable")
                match_index = self.client.expect_exact(
                    ["Password:", "#", pexpect.TIMEOUT, pexpect.EOF]
                )
                if match_index == 0:
                    self.client.sendline(self.password)
                    self.client.expect("#")
                    return True
            elif index == 1:
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
    def __init__(self, conn, password, username):
        super().__init__(conn, password)
        self.username = username

    def _login(self):
        index = self._client.expect_exact(
            ["login: ", "#> ", pexpect.TIMEOUT, pexpect.EOF]
        )
        if index == 1:
            return self._client
        if index == 0:
            self.client.sendline(self.username)
            self._client.expect("password:")
            self.client.expect("#> ")
            return self._client
        raise OperationFailure(
            "login failed. Unexpected response from terminal server."
        )

    def _retr_session_id(self, line_no):
        pattern = rf"(\d+)\s+\[\d:A-F.]+\s+serial {line_no}\s+"
        self.client.sendline("who")
        index = self.client.expect_exact([pattern, pexpect.TIMEOUT, pexpect.EOF])
        if index == 0:
            return self.client.match.group(1)
        logger.error("Unexpected response from terminal server.")
        return None

    def clear(self, line_no):
        session_id = self._retr_session_id(line_no)
        if session_id is not None:
            self.client.sendline(f"kill {session_id}")
            self.client.expect_exact(["#> ", pexpect.TIMEOUT, pexpect.EOF])
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
