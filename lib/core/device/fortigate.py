import pexpect
import sys
from .fos_dev import FosDev
from .bios import BIOS
from lib.services.log import logger
from lib.services.image_server import Image, UPGRADE, image_server
import pdb
import telnetlib
import time
import requests
from synlinkpy import SynLinkPy
from .common import BURN_IMAGE_STAGE, LOGIN_STAGE


class FortiGate(FosDev):
    def __init__(self, dev_name, need_burn=False):
        self.cur_stage = BURN_IMAGE_STAGE if need_burn else LOGIN_STAGE
        super().__init__(dev_name)


    def image_prefix(self):
        if not self.model:
            self.model = self.system_status["platform"]
        return self.model.replace("-", "_").replace("FortiGate", "FGT")

    @property
    def system_status(self):
        rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*?"
            r"Serial-Number: (?P<serial>[^\r\n]*).*?"
            r"BIOS version: (?P<bios_version>[^\r\n]*).*?"
            r"Virtual domain configuration: (?P<vdom_mode>[^\r\n]*).*?"
            r"Branch point: (?P<branch_point>[^\r\n]*).*?"
        )
        matched = self.show_command_may_have_more("get system status", rule)
        if not matched:
            rule = (
            r"Version:\s+(?P<platform>[\w-]+)\s+v(?P<version>\d+\.\d+\.\d+),"
            r"(build(?P<build>\d+)),\d+\s+\((?P<release_type>[\.\s\w]+)\).*"
            r"Serial-Number: (?P<serial>[^\n]*).*"
            r"Virtual domain configuration: (?P<vdom_mode>[^\n]*).*"
            r"Branch point: (?P<branch_point>[^\n]*).*"
        )
            matched = self.show_command_may_have_more("get system status", rule)
        return matched

    def clear_terminal(self):
        dev_conn = (
            self.dev_cfg["connection"]
            if "telnet" in self.dev_cfg["connection"]
            else f"telnet {self.dev_cfg['connection']}"
        )
        conn = " ".join(dev_conn.split(" ")[:2])
        line_no = int(dev_conn.split(" ")[-1]) - 2000
        # print(self.dev_cfg)

        if "ciscopassword"  not in self.dev_cfg:
            logger.info("Skip clear line as no terminal server password configured.")
            return

        password = self.dev_cfg["ciscopassword"]


        client = pexpect.spawn(conn,
                encoding="utf-8",
                echo=True,
                logfile=sys.stdout,
                codec_errors="ignore")
        matched_index = client.expect_exact(["Password:", "#", pexpect.TIMEOUT, pexpect.EOF])
        if matched_index == 1:
            self.clear(client, line_no)
        elif matched_index == 0:
            client.sendline(password)
            index = client.expect_exact([">", "#", pexpect.TIMEOUT, pexpect.EOF])
            if index == 0:
                client.sendline("enable")
                match_index = client.expect_exact(["Password:", ">", pexpect.TIMEOUT, pexpect.EOF])
                if match_index == 0:
                    client.sendline(password)
                    client.expect("#")
                    self.clear(client, line_no)
                elif match_index == 1:
                    # some QAs do not know how to configure terminal server password or terminal server password not set.
                    pass
            elif index == 1:
                self.clear(client, line_no)
            elif index in [2, 3]:
                logger.info("Failed to clear terminal server.")
        else:
            logger.info("Skip clear line.")

    def clear(self, client, line_no):
        client.sendline(f"clear line {line_no}")
        client.expect("\[confirm\]")
        client.sendline("")
        client.expect("#")
        client.sendline("exit")

    def connect(self):
        #make sure console port in therterminal server is not occupied
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
        pdu_server = self.dev_cfg.get("pdu", None)
        pdu_port = self.dev_cfg.get("pdu_port", None)
        pdu_type = self.dev_cfg.get("pdu_type", None)

        if pdu_server and pdu_port and pdu_type:

            self.set_stage(BURN_IMAGE_STAGE)
            logger.info("Reboot %s by pdu.", self.dev_name)
            if pdu_type == "SYNACCESS":
                with telnetlib.Telnet(pdu_server, 23) as tn:
                    time.sleep(3)
                    cmd = f"pset {pdu_port} 0"
                    tn.write((cmd + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b">").decode('utf-8')
                    print(output)
                    time.sleep(3)
                    cmd = "logout"
                    tn.write((cmd + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b">", 10)
                    print(output)

                with telnetlib.Telnet(pdu_server, 23) as tn:
                    time.sleep(3)
                    cmd = f"pset {pdu_port} 1"
                    tn.write((cmd + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b">").decode('utf-8')
                    print(output)
                    time.sleep(3)
                    cmd = "logout"
                    tn.write((cmd + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b">", 10).decode('utf-8')
                    print(output)
            elif pdu_type == "SCHNEIDER":
                with telnetlib.Telnet(pdu_server, 23) as tn:
                    pdu_user = self.dev_cfg.get("pdu_user", "")
                    pdu_password = self.dev_cfg.get("pdu_password", "")
                    if not pdu_user:
                        print("Please configure pdu credential")
                        sys.exit(0)
                    output = tn.read_until(b"User Name :", 10).decode("utf-8")
                    print(output)
                    tn.write((pdu_user + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b"Password  :", 10).decode("utf-8")
                    print(f"user input: {output} ")
                    tn.write((pdu_password + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b">", 10).decode("utf-8")
                    print("password input", output)
                    tn.write((f"olreboot {pdu_port}" + "\r").encode("utf-8"))
                    time.sleep(1)
                    output = tn.read_until(b">", 10).decode("utf-8")
                    print(output)
                    tn.write(("quit\n").encode("utf-8"))
            print("Triggered reboot with PDU.")
            logger.info("Triggered %s reboot with PDU.", self.dev_name)
        else:
            self.set_stage(LOGIN_STAGE)
            logger.info("Reboot %s by command.", self.dev_name)
            self.send_line("config global")
            self.search('#', 5, -1)
            self.send_line("execute reboot")
            self.search("(y/n)", 5, -1)
            self.send('y')

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
        self.reboot_device()
        self.send("\n")
        matched, output = self.search("Press any key to display configuration menu.", 120, -1)

        if not matched:
            print("Failed to reboot.")
            sys.exit(0)
        self.send("\n")
        self.search(BIOS.pattern["main_menu"], 30, -1)
        self.send(BIOS.command['goto_tftp_menu'])
        self.search(BIOS.pattern['wildcard_menu'], 10, -1)
        self.send(BIOS.command["set_dhcp_status"])
        self.search(BIOS.pattern["dhcp_option"], 10, -1)
        self.send(BIOS.command["disable_dhcp"])
        self.search(BIOS.pattern["wildcard_menu"], 10, -1)

        self._set_option_from_config("set_download_port", "burn_interface")
        self._set_option_from_config("set_local_ip", "burn_ip")
        self._set_option_from_config("set_local_gateway", "burn_gw")
        self._set_option_from_config("set_net_mask", "burn_netmask",fallback="255.255.255.0")
        self._set_option_from_config("set_vlan_id", "bios_vlan_id", fallback="-1")
        self._set_option_value("set_tftp_server_ip", "172.18.52.254")

        self.extract_model_from_boot_info(output)
        image = Image(self.image_prefix(), release, build, UPGRADE)
        image_file = image_server.lookup_image(image)
        image_loc = f"{image_file['parent_dir']}/{image_file['name']}"
        logger.info("The image location is %s", image_loc)
        self._set_option_value("set_firmware_filename", f"{image_loc}")

        self.send(BIOS.command["review_tftp_settings"])
        self.search(BIOS.pattern["wildcard_menu"], 10, -1)

        self.send("Q")
        self.search(BIOS.pattern["main_menu"],10, -1)

        self.send("T")
        self.search(BIOS.pattern["firmware_choice"],200, -1)

        self.send(BIOS.command["set_default_firmware"])
