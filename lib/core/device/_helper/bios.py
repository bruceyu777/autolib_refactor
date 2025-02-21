import logging
import re
import time

logger = logging.getLogger(__name__)
BIOS_WAIT_TIMER = 10 * 60
ctrl_b = "\x02"


class BIOS:
    switch_menu_delay_in_sec = 5

    pattern = {
        "entry_point": r"to display configuration menu",
        "main_menu": r"Enter [CG].*?[HQ]:$",
        "wildcard_menu": r"Enter .*?[HQ]:$",
        "set_option": r"(?:Enter|Input).*?\[.*?\]:",
        "dhcp_option": r"Enter DHCP setting.*?:",
        "general_choice": r"\]\?",
        "firmware_choice": (r"Save as Default firmware.*?saving:\[D/B/R\]\?"),
        "format_boot_device": r"It will erase.*?Continue\? \[yes/no\]",
        "yes_or_no": r"\[Y/N\]\?$",
    }
    command = {
        "dummy": "",
        "Y": "Y",
        "yes": "yes",
        "quit": "Q",
        "help": "H",
        "start_tftp": "T",
        "set_vlan_id": "V",
        "set_dhcp_status": "D",
        "disable_dhcp": "2",
        "set_default_firmware": "D",
        "set_backup_firmware": "B",
        "set_local_gateway": "G",
        "goto_tftp_menu": "C",
        "diagnose_network": "N",
        "set_net_mask": "S",
        "set_security_level": "U",
        "reset_tftp_parameters": "E",
        "system_info": "I",
        "set_download_port": "P",
        "set_restrict_mode": "R",
        "set_firmware_filename": "F",
        "set_timeout": "T",
        "set_local_ip": "I",
        "review_tftp_settings": "R",
        "format_boot_device": "F",
        "set_tftp_server_ip": "T",
    }

    @staticmethod
    def extract_enter_bios_key(bootup_print_out):
        return "dummy" if "press any key" in bootup_print_out else ctrl_b

    @staticmethod
    def in_bios_menu(bios_print_out):
        return bool(re.findall(BIOS.pattern["wildcard_menu"], bios_print_out))


class BiosImageLoader:
    def __init__(self, connection):
        self.console = connection

    def _exec_cmd_until(
        self,
        command,
        pattern="wildcard_menu",
        timeout=BIOS.switch_menu_delay_in_sec,
        addenter=False,
    ):
        command = BIOS.command.get(command, command)
        if addenter:
            self.console.send_line(command)
        else:
            self.console.send(command)
        time.sleep(0.5)
        pattern_to_search = BIOS.pattern.get(pattern, pattern)
        _, output = self.console.search(pattern_to_search, timeout, -1)
        return output

    def _set_option_value(self, option, value):
        output = self._exec_cmd_until(option, pattern="set_option")
        if option == "set_download_port":
            value = self._handle_download_ports(output, value)
        output += self._exec_cmd_until(value, addenter=True)
        return output

    def _handle_download_ports(self, options, download_port):
        """Enter P,D,I,S,G,V,T,F,E,R,N,Q,or H:
        [0]:  port 1
        [1]:  port 2
        [2]:  port 3
        [3]:  port 4
        [4]:  port 5
        [5]:  A
        [6]:  B
        [7]:  DMZ
        [8]:  WAN1
        [9]:  WAN2"""
        pattern = re.compile(r"\s*\[*(?P<index>\d+)\]*:\s*(?P<port_name>\w+)")
        mapping = {v.lower(): k for k, v in pattern.findall(options.replace(" ", ""))}
        return mapping[download_port.lower()] if mapping else download_port

    def goto_bios_main_menu(self, max_menu_depth=5):
        output = self._exec_cmd_until("dummy", addenter=True)
        while not re.findall(BIOS.pattern["main_menu"], output):
            output += self._exec_cmd_until("quit")
            max_menu_depth -= 1
            if not max_menu_depth:
                raise RuntimeError("Failed to switch back to BIOS main menu")
        return output

    def enter_into_bios_menu(self):
        _, output = self.console.search(BIOS.pattern["entry_point"], BIOS_WAIT_TIMER)
        enter_bios_key = BIOS.extract_enter_bios_key(output)
        output += self._exec_cmd_until(
            enter_bios_key, pattern="main_menu", addenter=True
        )
        if not BIOS.in_bios_menu(output):
            raise RuntimeError("Unable to enter in BIOS menu!!!")
        return output

    def format_boot_device(self):
        output = self._exec_cmd_until(
            "format_boot_device", pattern="format_boot_device"
        )
        output += self._exec_cmd_until("yes", addenter=True)
        return output

    def set_local_ip(self, burn_ip):
        return self._set_option_value("set_local_ip", burn_ip)

    def set_local_gateway(self, burn_ip_gw):
        return self._set_option_value("set_local_gateway", burn_ip_gw)

    def set_local_subnet_mask(self, burn_ip_mask="255.255.255.0"):
        return self._set_option_value("set_net_mask", burn_ip_mask)

    def set_vlan_id(self, burn_vlan_id="-1"):
        return self._set_option_value("set_vlan_id", burn_vlan_id)

    def set_tftp_server_ip(self, tftp_server="172.18.70.52.254"):
        return self._set_option_value("set_tftp_server_ip", tftp_server)

    def set_download_port(self, burn_port):
        return self._set_option_value("set_download_port", burn_port)

    def set_firmware_filename(self, firmware_filename):
        return self._set_option_value("set_firmware_filename", firmware_filename)

    def review_tftp_settings(self):
        return self._exec_cmd_until("review_tftp_settings")

    def goto_tftp_configure_menu(self):
        return self._exec_cmd_until("goto_tftp_menu")

    def load_firmware(self):
        output = self._exec_cmd_until(
            "start_tftp",
            pattern="firmware_choice",
            timeout=BIOS_WAIT_TIMER,
        )
        output += self._exec_cmd_until("set_default_firmware", pattern="general_choice")
        while re.findall(BIOS.pattern["yes_or_no"], output):
            output += self._exec_cmd_until("Y", pattern="general_choice", addenter=True)
        return output

    def load_firmware_from_bios(
        self,
        tftp_server,
        image_filename,
        burn_port,
        burn_ip,
        burn_ip_gw,
        burn_ip_mask="255.255.255.0",
        burn_vlan_id="-1",
        format_boot_device=False,
    ):
        if format_boot_device:
            self.format_boot_device()
        self.goto_tftp_configure_menu()
        self.set_download_port(burn_port)
        self.set_local_ip(burn_ip)
        self.set_local_gateway(burn_ip_gw)
        self.set_local_subnet_mask(burn_ip_mask)
        self.set_tftp_server_ip(tftp_server)
        self.set_firmware_filename(image_filename)
        self.set_vlan_id(burn_vlan_id)
        self.review_tftp_settings()
        self.goto_bios_main_menu()
        return self.load_firmware()
