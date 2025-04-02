import re

from lib.services import IMAGE_SERVER_IP, Image, image_server, logger
from lib.utilities import ImageInstallErr, sleep_with_progress

from ._helper.bios import BiosImageLoader
from .device import MAX_TIMEOUT_FOR_REBOOT
from .fos_dev import FosDev
from .pdu import PowerController
from .terminal_server import new_terminal_server


class FortiGate(FosDev):

    def restore_image(self, release, build, need_reset=True, need_burn=False):
        if need_burn:
            logger.debug("Start burn image.")
            self.burn_image(release, build)
            return self.is_image_installed(release, build)
        is_upgrade_success = super().restore_image(
            release, build, need_reset=need_reset, need_burn=False
        )
        return is_upgrade_success

    def clear_terminal(self):
        dev_conn = (
            self.dev_cfg["CONNECTION"]
            if "telnet" in self.dev_cfg["CONNECTION"]
            else f"telnet {self.dev_cfg['CONNECTION']}"
        )
        conn = " ".join(dev_conn.split(" ")[:2])
        line_no = int(dev_conn.split(" ")[-1]) - 2000
        password = self.dev_cfg.get(
            "TERMINAL_SERVER_PASSWORD", self.dev_cfg.get("CISCOPASSWORD", None)
        )
        username = self.dev_cfg.get("TERMINAL_SERVER_USERNAME")
        vendor = self.dev_cfg.get("TERMINAL_SERVER_VENDOR", "CISCO")
        terminal_server = new_terminal_server(
            conn, password, username=username, vendor=vendor
        )
        terminal_server.clear(line_no)

    def connect(self):
        if self.is_serial_connection_used():
            self.clear_terminal()
        super().connect()

    def reboot_device(self):
        logger.info("Reboot %s by command.", self.dev_name)
        if self.is_vdom_enabled:
            self._goto_global_view()
        self.send_line("execute reboot")
        self.search("(y/n)", 5, -1)
        self.send("y")

    def powercycle_device(self):
        pdu_name = self.dev_cfg.get("PDU", None)
        power_controller = PowerController(pdu_name)
        power_controller.login()
        power_controller.rebootdev(self.dev_name)
        logger.info("Triggered %s reboot with PDU.", self.dev_name)
        power_controller.logout()

    def extract_model_from_boot_info(self, bootinfo):
        """
        Please stand by while rebooting the system.
        Restarting system.
        FortiGate-1200D (15:58-06.23.2016)
        or sometimes return like:
        .........FortiGate-1200D (15:58-06.23.2016)
        """
        model_pattern = re.compile(r"(Forti|FGR)\w+-\S+", flags=re.M | re.S)
        matched = model_pattern.search(bootinfo)
        return matched.group(0) if matched else ""

    def _try_all_ways_to_reboot(self):

        def _reboot(reboot_func):
            try:
                reboot_func()
                self.send("\n")
                matched, _ = self.search(
                    "Please stand by while rebooting the system.", 60, -1
                )
            except Exception:
                return False
            return matched

        return any(map(_reboot, (self.reboot_device, self.powercycle_device)))

    def burn_image(self, release, build):

        try:
            if not self.model:
                self.get_parsed_system_status()
        except Exception:
            model_info_ready = False
        else:
            model_info_ready = True

        if not self._try_all_ways_to_reboot():
            raise ImageInstallErr(f"Unable to reboot the {self.dev_name}")

        image_loader = BiosImageLoader(self.conn)
        output = image_loader.enter_into_bios_menu()
        if not model_info_ready:
            self.extract_model_from_boot_info(output)
        logger.debug("Model information: %s", self.model)
        image = Image(self.model, release, build, self.image_file_ext)
        self._load_firmware_from_bios(image_loader, image)
        if not self.is_image_installed(image.release, image.build):
            error = "Image wasn't upgraded successfully(build mismatched)!!!"
            raise ImageInstallErr(error)

    def _load_firmware_from_bios(self, image_loader, image):
        image_path = image_server.locate_image(image)
        output = image_loader.load_firmware_from_bios(
            IMAGE_SERVER_IP,
            image_path,
            self.dev_cfg["BURN_INTERFACE"],
            self.dev_cfg["BURN_IP"],
            self.dev_cfg["BURN_GW"],
            burn_ip_mask=self.dev_cfg.get("BURN_NETMASK", "255.255.255.0"),
            burn_vlan_id=self.dev_cfg.get("BURN_VLANID", "-1"),
            format_boot_device=self.dev_cfg.get("FORMAT_BOOT_DEVICE", False),
        )
        matched, output = self.search(
            self.asking_for_username, timeout=MAX_TIMEOUT_FOR_REBOOT
        )
        self.check_kernel_panic(output)
        if not matched:
            self.send("\n")
            self.search(self.asking_for_username, timeout=5)
        logger.info("Sleep for 5 seconds to make FGT to be ready for CLI")
        sleep_with_progress(10)
        self.login(password=self.DEFAULT_PASSWORD)
