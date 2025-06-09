import re
import time

from lib.services import env, logger
from lib.utilities import LicenseLoadErr, sleep_with_progress

from .fos_dev import FosDev
from .session import get_session_init_class

MAX_WAIT_TIME_FOR_LIC_UPDATE = 5 * 60


class FortiVM(FosDev):
    FORTISTACK_CLOUD_INIT_PASSWORD = "admin"

    def __init__(self, dev_name):
        super().__init__(dev_name)
        self.license = None
        self.license_server = None

    @property
    def DEFAULT_PASSWORD(self):
        if env.is_running_on_vm():
            return self.FORTISTACK_CLOUD_INIT_PASSWORD
        return super().DEFAULT_PASSWORD

    def get_session_init_class(self):
        return get_session_init_class(self.is_serial_connection_used(), True)

    def is_serial_connection_used(self):
        # for FVM we support telnet is serial connection
        # but currently, telnet was not in CONNECTION
        return (
            "telnet" in self.dev_cfg["CONNECTION"]
            or len(self.dev_cfg["CONNECTION"].split()) == 2
        )

    def reset_config(self, cmd):
        if self.is_vdom_enabled:
            self._goto_global_view()
        if re.match("^exe.*?factoryreset$", cmd):
            logger.info("Override '%s' command to keep vm license!", cmd)
            cmd = "execute factoryreset keepvmlicense"
        self.send_line(cmd)
        self.search("y/n", 30)
        self.send_line("y")
        self.login_firewall_after_reset()

    def login_firewall_after_reset(self):
        if env.is_running_on_vm():
            # for case when we need to wait for cloud-init script finish
            sleep_time = float(
                env.get_section_var(
                    "GLOBAL", "CLOUD_INIT_DELAY_SECONDS", fallback=3 * 60
                )
            )
            sleep_with_progress(sleep_time)
        _, cli_output = self.search(self.asking_for_username, 10 * 60, -1)
        self.check_kernel_panic(cli_output)
        cli_output += self._login(self.DEFAULT_ADMIN, self.DEFAULT_PASSWORD)
        if "forced to change your" in cli_output:
            self._handle_password_enforcement()

    def _send_reset_command(self):
        self.send_line("exe factoryreset keepvmlicense")

    def get_license_by_type(self):
        license_type = self.dev_cfg.get("LICENSE_TYPE", None)
        license_dir = self.dev_cfg.get("LICENSE_DIR", None)
        if license_dir:
            return license_dir + self.license_info[license_type]["SN"]
        return self.license_info[license_type]["SN"]

    def request_license(self):
        mylicense = self.get_license_by_type()
        self.license = mylicense
        self.license_server = self.dev_cfg.get("LICENSE_SERVER", None)
        logger.debug(
            "license: '%s',license_server: '%s'", self.license, self.license_server
        )
        return self.license, self.license_server

    def load_license(self):
        command = "execute restore vmlicense tftp {} {}".format(
            self.license, self.license_server
        )
        self.send_line(f"{command}")
        self.search("y/n", 30)
        self.send_line("y")
        self.search("login:", 5 * 60, -1)
        # NOTE:
        # After license was uploaded, admin will be kicked out to login view
        # and a few seconds later, device will reboot and then go back to
        # login view again, add a delay wait device reboot
        time.sleep(100)
        _, output = self.search("login:", 5 * 60, -1)
        failure = "license install failed."
        if output.find(failure) != -1:
            logger.error("\n%s\n", failure.title())
            raise LicenseLoadErr("License Load ERROR!")
        self._login(self.DEFAULT_ADMIN, self.TEMP_PASSWORD)
        self.send_line("execute update-now")
        self.search("#", 30, -1)

    def activate_license(self):
        if self.use_evaluation_license():
            logger.warning("Use evaluation license!")
            return
        # need all the hosted entity have those attribute
        self.setup_management_access()
        self.request_license()
        self.load_license()
        self.wait_until_valid()

    def validate_license(self):
        """
        Method 1:  <== NOT REAL STATUS
        Root-F-1 # diagnose debug vm-print-license
        VM License Info
        Serial number: FGVM020000132628
        License Allowance: 2 CPUs and 4096 MB RAM.
        License created: Mon Jan 15 18:23:06 2018
        License expires: Wed Jan 16 00:00:00 2019
        Method 2:  <== NOT REAL STATUS
        get sys status
        License Status: Valid
        License Expires: 2019-11-08
        VM Resources: 4 CPU/4 allowed, 5988 MB RAM/6144 MB allowed
        Method3:    <=== RELIABLE
        FGVM020000175440 # diagnose hardware sysinfo vm full
        UUID:     564dfc21b8c9e40a6dc8d37a2d2a005f
        valid:    1
        status:   1
        code:     200    <--- 2xx or 3xx means Valid
        warn:     0
        copy:     0
        received: 4294940602
        warning:  0
        recv:     201901222347
        dup:
        """
        command = "diagnose hardware sysinfo vm full"
        self.send_line(f"{command}")
        _, ret = self.search(f"{self.general_view}|{self.asking_for_username}", 30, -1)
        required = {"valid": [1], "status": [1], "code": range(200, 400)}
        selected = (
            line.split(":") for line in ret.splitlines() if line.find(": ") != -1
        )
        stripped = (map(str.strip, values) for values in selected)
        status = {key: int(value) for key, value in stripped if key in required}
        valid = all(
            status.get(key, 0) in allow_values for key, allow_values in required.items()
        )
        if re.search(self.asking_for_username, ret):
            self._login(self.DEFAULT_ADMIN, self.TEMP_PASSWORD)
        return valid

    def wait_until_valid(self, timeout=MAX_WAIT_TIME_FOR_LIC_UPDATE):
        wait_time = 0
        interval = 10
        while wait_time < timeout:
            self.send_line("")
            _, ret = self.search(
                f"{self.general_view}|{self.asking_for_username}", interval, -1
            )
            if ret and re.search(self.asking_for_username, ret):
                self._login(self.DEFAULT_ADMIN, self.TEMP_PASSWORD)
            if self.validate_license():
                break
            msg = f"\nSleep {interval} seconds to wait license activate!\n"
            logger.info(msg)
            time.sleep(interval)
            wait_time += interval
        else:
            msg = "Unable to activate license in {} seconds".format(timeout)
            logger.critical(msg)
            raise LicenseLoadErr(msg)
        return True

    def use_evaluation_license(self):
        return env.is_cfg_option_enabled("GLOBAL", "EVALUATION_LICENSE")
