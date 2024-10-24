import time

import pexpect

from lib.services import logger
from lib.utilities.exceptions import LoginDeviceFailed

from .common import BURN_IMAGE_STAGE
from .dev_conn import DevConn

READ_WAIT_TIME = 120
WAIT_TIME = 60

CODE_FORMAT = "ascii"
MAX_VIEW_LAYER = 5


class FosDevConn(DevConn):
    RETRY_MAX_TIME = 15
    FOS_DEFAULT_PASSWORD = ""

    def __init__(self, dev_name, connection, user_name, password, cur_stage):
        super().__init__(dev_name, connection, user_name, password)
        self.conn_state = "init"
        self.retry_cnt = 0
        self.use_default_password = False
        self.init_view = True
        self.cur_stage = cur_stage

    def _connected(self):
        self._client.sendline("")
        logger.debug("enter into connect")
        index = self._client.expect_exact(
            ["login:", "#", "Password:", pexpect.TIMEOUT, pexpect.EOF]
        )
        logger.debug("enter into connect: the index is %s", index)
        if index in [0, 1, 2]:
            logger.debug(
                "In connected, current buffer output is %s",
                self._client.before + self._client.after,
            )
        if index == 0:
            self.conn_state = "_require_credential"
        elif index == 1:
            self.conn_state = "_cache_logged"
        elif index == 2:
            logger.debug("Password appears before login, ignored it.")
            self.conn_state = "_retry"
        elif index == 3:
            logger.debug("\nFailed to login %s, will retry it again.", self.dev_name)
            self.conn_state = "_retry"
        else:
            logger.error("\nFailed to login %s as connection is closed.", self.dev_name)
            self.conn_state = "_retry"

    def _cache_logged(self):
        view_layer = 0
        logger.debug("Enter into cache logged.")
        if not self.init_view:
            self.conn_state = "_logged_in"
            return
        while view_layer < MAX_VIEW_LAYER:
            self._client.sendline("")
            logger.debug("Start expecting prompts.")
            index = self._client.expect_exact(
                ["#", ") #", pexpect.TIMEOUT, pexpect.EOF]
            )
            logger.debug(
                "In connected, current buffer output is %s",
                self._client.before + self._client.after,
            )
            logger.debug("Finished expecting prompts.")
            if index == 0:
                self.conn_state = "_logged_in"
                return
            self._client.sendline("end")
            view_layer += 1

        self.conn_state = "_retry"

    def set_stage(self, stage):
        self.cur_stage = stage

    def _require_credential(self):
        self._client.sendline(self.user_name)
        self._client.expect("Password:")
        password = (
            self.FOS_DEFAULT_PASSWORD if self.use_default_password else self.password
        )
        self._client.sendline(password)
        index = self._client.expect_exact(
            [
                "#",
                "Login incorrect",
                "You are forced to change your password. Please input a new password.",
            ]
        )
        if index == 0:
            self.conn_state = "_logged_in"
        elif index == 1:
            self.use_default_password = True
            self.conn_state = "_retry"
        elif index == 2:
            logger.debug("Required to reset password.")
            self.conn_state = "_reset_password"

    def _reset_password(self):
        self._client.expect("New Password:")
        self._client.sendline(self.password)
        self._client.expect("Confirm Password:")
        self._client.sendline(self.password)
        self._client.expect("#")
        self.conn_state = "_logged_in"

    def _retry(self):
        self._client.sendline("\n")
        time.sleep(0.1)
        self._client.sendcontrol("c")
        if self.retry_cnt > self.RETRY_MAX_TIME:
            logger.error("\nFailed to login after retry for %s times", self.retry_cnt)
            self.conn_state = "_failed"
            return
        time.sleep(60)
        self.retry_cnt += 1
        self.conn_state = "_connected"

    def login(self, reset=False, init_view=True):
        if self.cur_stage == BURN_IMAGE_STAGE:
            logger.debug("Do not need to login the device for burning image.")
            return

        self.init_view = init_view
        logger.debug("enter into login")
        try:
            logger.debug("Start sending line.")
            self._client.sendline("")
            logger.debug("Start reading.")
            self._client.expect(".+")
        except pexpect.TIMEOUT:
            logger.debug("No more characters cleared for login.")

        logger.debug(
            "current buffer output for login is %s",
            self._client.before + self._client.after,
        )
        self.retry_cnt = 0
        self.conn_state = "_connected"
        self.use_default_password = reset
        while hasattr(self, self.conn_state):
            func = getattr(self, self.conn_state)
            func()
        if self.conn_state == "_failed":
            raise LoginDeviceFailed(self.conn)
        if self.conn_state == "_logged_in":
            logger.debug("Succeeded to login the device: %s. ", self.dev_name)


if __name__ == "__main__":
    dev_conn = DevConn("FGT_A", "172.18.57.99 2004", "admin", "admin")
    dev_conn.send_command("get system status", "# ", 5)
