import time

from lib.services.environment import env
from lib.services.log import logger
from lib.utilities.exceptions import LicenseLoadErr

from .fos_dev import FosDev

MAX_WAIT_TIME_FOR_LIC_UPDATE = 5 * 60

class FortiVM(FosDev):
    def __init__(self, dev_name):
        super().__init__(dev_name)
        self.license = None
        self.license_server = None

    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        image_prefix = (
            self.model.replace("-", "_")
            .replace("FortiGate", "FGT")
            .replace("FortiCarrier", "FGT")
        )
        return image_prefix.replace("-", "_").replace("FortiFirewall", "FFW")

    @property
    def system_status(self):
        rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
            r"Serial-Number: (?P<serial>[^\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
            r"Branch point: (?P<branch_point>[^\n]*).*"
        )
        result, m, _ = self.send_command("get system status", rule, timeout=10)
        return m.groupdict() if m and result else {}

    def get_license_by_type(self):
        # breakpoint()
        license_type = self.dev_cfg.get("license_type", None)
        license_dir = self.dev_cfg.get("license_dir", None)
        if license_dir:
            return license_dir + self.license_info[license_type]["SN"]
        return self.license_info[license_type]["SN"]

    def request_license(self):
        mylicense = self.get_license_by_type()
        mgmt_ip = self.dev_cfg.get("mgmt_ip", None)
        self.license = mylicense
        self.license_server = self.dev_cfg.get(
            "license_server", None
        )
        logger.debug(
            "license: '%s',license_server: '%s'", self.license, self.license_server
        )
        return self.license, self.license_server

    def load_license(self):
        logger.debug("server: '%s',license_file: '%s'", self.license_server, self.license)
        command = "execute restore vmlicense tftp {} {}".format(self.license, self.license_server)
        self.send_line(f"{command}")
        self.search("y/n", 30)
        self.send_line("y")
        self.search("login:", 300, -1)
        # NOTE:
        # After license was uploaded, admin will be kicked out to login view
        # and a few seconds later, device will reboot and then go back to
        # login view again, add a delay wait device reboot
        time.sleep(100)
        matched, output = self.search("login:", 300, -1)
        failure = "license install failed."
        if output.find(failure) != -1:
            logger.error("\n%s\n", failure.title())
            raise LicenseLoadErr("License Load ERROR!")
        self.send_line("admin")
        self.search("Password:", 30, -1)
        self.send_line("admin")
        self.search("#", 30, -1)
        self.send_line("execute update-now")
        self.search("#", 30, -1)

    def activate_license(self):
        if self.use_evaluation_license():
            return
        # need all the hosted entity have those atttribute
        self.pre_mgmt_settings()
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
        matched, ret = self.search("#|login:", 30, -1)
        required = {"valid": [1], "status": [1], "code": range(200, 400)}
        selected = (
            line.split(":") for line in ret.splitlines() if line.find(": ") != -1
        )
        stripped = (map(str.strip, values) for values in selected)
        status = {key: int(value) for key, value in stripped if key in required}
        valid = all(
            status.get(key, 0) in allow_values for key, allow_values in required.items()
        )
        if ret.endswith("login: "):
            self.send_line("admin")
            self.search("Password:", 30, -1)
            self.send_line("admin")
            self.search("#", 30, -1)
        logger.debug("<<< 'valid': '%s'", valid)
        return valid

    def wait_until_valid(self, timeout=MAX_WAIT_TIME_FOR_LIC_UPDATE):
        logger.debug(">>> timeout:'%d'", timeout)
        wait_time = 0
        while wait_time < timeout:
            self.send_line("")
            matched, ret = self.search("#|login:", 10, -1)
            if ret and ret.find("login: ") != -1:
                self.send_line("admin")
                self.search("Password:", 30, -1)
                self.send_line("admin")
                self.search("#", 30, -1)
            if self.validate_license():
                break
            msg = "\nSleep 20 seconds to wait license activate!\n"
            logger.info(msg)
            time.sleep(20)
            wait_time += 20
        else:
            msg = "Unable to activate license in {} seconds".format(timeout)
            logger.critical(msg)
            raise LicenseLoadErr(msg)
        logger.debug("<<< activated_flag: '%s'", True)
        return True

    def use_evaluation_license(self):
        return env.is_cfg_option_enabled("GLOBAL", "EVALUATION_LICENSE")

