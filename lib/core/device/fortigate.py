import sys
import time

import pexpect

from lib.services.image_server import IMAGE_SERVER_IP, UPGRADE, Image, image_server
from lib.services.log import logger

from .bios import BIOS
from .common import BURN_IMAGE_STAGE, LOGIN_STAGE
from .fos_dev import FosDev
from .pdu import PowerController


class FortiGate(FosDev):
    def __init__(self, dev_name, need_burn=False):
        self.cur_stage = BURN_IMAGE_STAGE if need_burn else LOGIN_STAGE
        super().__init__(dev_name)

    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        return self.model.replace("-", "_").replace("FortiGate", "FGT")

    def restore_image(self, release, build, need_reset=True, need_burn=False):
        if need_burn:
            logger.notify("Start burn image.")
            self.burn_image(release, build)
            self.set_stage("start_from_login")
            self.login_firewall_after_reset()
            return self.validate_build(release, build)
        is_upgrade_success = super().restore_image(
            release, build, need_reset=need_reset, need_burn=False
        )
        return is_upgrade_success

    def clear_terminal(self):
        dev_conn = (
            self.dev_cfg["connection"]
            if "telnet" in self.dev_cfg["connection"]
            else f"telnet {self.dev_cfg['connection']}"
        )
        conn = " ".join(dev_conn.split(" ")[:2])
        line_no = int(dev_conn.split(" ")[-1]) - 2000

        if "ciscopassword" not in self.dev_cfg:
            logger.info("Skip clear line as no terminal server password configured.")
            return

        password = self.dev_cfg["ciscopassword"]

        client = pexpect.spawn(
            conn, encoding="utf-8", echo=True, logfile=sys.stdout, codec_errors="ignore"
        )
        matched_index = client.expect_exact(
            ["Password:", "#", pexpect.TIMEOUT, pexpect.EOF]
        )
        if matched_index == 1:
            self.clear(client, line_no)
        elif matched_index == 0:
            client.sendline(password)
            index = client.expect_exact([">", "#", pexpect.TIMEOUT, pexpect.EOF])
            if index == 0:
                client.sendline("enable")
                match_index = client.expect_exact(
                    ["Password:", ">", pexpect.TIMEOUT, pexpect.EOF]
                )
                if match_index == 0:
                    client.sendline(password)
                    client.expect("#")
                    self.clear(client, line_no)
                elif match_index == 1:
                    # some QAs do not know how to configure terminal server password
                    # or terminal server password not set.
                    pass
            elif index == 1:
                self.clear(client, line_no)
            elif index in [2, 3]:
                logger.info("Failed to clear terminal server.")
        else:
            logger.info("Skip clear line.")

    def clear(self, client, line_no):
        client.sendline(f"clear line {line_no}")
        client.expect(r"\[confirm\]")
        client.sendline("")
        client.expect("#")
        client.sendline("exit")

    def connect(self):
        # make sure console port in therterminal server is not occupied
        self.clear_terminal()
        super().connect()

    def _set_option_value(self, option, value):
        self.send(BIOS.command[option])
        self.search(BIOS.pattern["set_option"], 10, -1)
        self.send_line(value)
        self.search(BIOS.pattern["wildcard_menu"], 30, -1)
        time.sleep(1)

    def _set_option_from_config(self, option, config_key, fallback=""):
        value = self.dev_cfg.get(config_key, fallback)
        return self._set_option_value(option, value)

    def reboot_device(self):
        self.set_stage(LOGIN_STAGE)
        logger.info("Reboot %s by command.", self.dev_name)
        if self.is_vdom_enabled:
            self._goto_global_view()
        self.send_line("execute reboot")
        self.search("(y/n)", 5, -1)
        self.send("y")

    def powercycle_device(self):
        pdu_name = self.dev_cfg.get("pdu", None)
        power_contoller = PowerController(pdu_name)
        power_contoller.login()
        power_contoller.rebootdev(self.dev_name)
        logger.info("Triggered %s reboot with PDU.", self.dev_name)
        power_contoller.logout()

    def extract_model_from_boot_info(self, bootinfo):
        """
        Please stand by while rebooting the system.
        Restarting system.
        FortiGate-1200D (15:58-06.23.2016)
        or sometimes return like:
        .........FortiGate-1200D (15:58-06.23.2016)
        """
        candidates = (l for l in bootinfo.splitlines() if " (" in l and "F" in l)
        for line in candidates:
            for i in ("Forti", "FGR"):
                start_index = line.find(i)
                if start_index != -1:
                    self.model = line[start_index:].strip().split(" (")[0]
                    logger.info("The model is %s", self.model)
                    return
        return

    def burn_image(self, release, build):

        def _reboot(reboot_func):
            reboot_func()
            self.send("\n")
            matched, _ = self.search(
                "Please stand by while rebooting the system.", 60, -1
            )
            return matched

        if not any(map(_reboot, (self.reboot_device, self.powercycle_device))):
            print("Failed to reboot.")
            sys.exit(1)
        _, bootup_output = self.search(
            "Press any key to display configuration menu.", 120, -1
        )
        self.check_kernel_panic(bootup_output)
        self.send("\n")
        self.search(BIOS.pattern["main_menu"], 30, -1)
        self.send(BIOS.command["goto_tftp_menu"])
        self.search(BIOS.pattern["wildcard_menu"], 10, -1)
        self.send(BIOS.command["set_dhcp_status"])
        self.search(BIOS.pattern["dhcp_option"], 10, -1)
        self.send(BIOS.command["disable_dhcp"])
        self.search(BIOS.pattern["wildcard_menu"], 10, -1)
        self._set_option_from_config("set_download_port", "burn_interface")
        self._set_option_from_config("set_local_ip", "burn_ip")
        self._set_option_from_config("set_local_gateway", "burn_gw")
        self._set_option_from_config(
            "set_net_mask", "burn_netmask", fallback="255.255.255.0"
        )
        self._set_option_from_config("set_vlan_id", "bios_vlan_id", fallback="-1")
        self._set_option_value("set_tftp_server_ip", IMAGE_SERVER_IP)
        self.extract_model_from_boot_info(bootup_output)
        image = Image(self.image_prefix(), release, build, UPGRADE)
        image_loc = image_server.locate_image(image)
        logger.info("The image location is %s", image_loc)
        self._set_option_value("set_firmware_filename", f"{image_loc}")
        self.send(BIOS.command["review_tftp_settings"])
        self.search(BIOS.pattern["wildcard_menu"], 10, -1)
        self.send("Q")
        self.search(BIOS.pattern["main_menu"], 10, -1)
        self.send("T")
        self.search(BIOS.pattern["firmware_choice"], 200, -1)
        self.send(BIOS.command["set_default_firmware"])
