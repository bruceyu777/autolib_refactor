import csv
import re
from collections import defaultdict
import pdb
from .env_parser import EnvParser
from .log import logger

OPTION_ENABLED_VALUE = ("y", "yes", "true", "enable", "on", "enabled")


class Environment:
    def __init__(self):
        self.user_env = None
        self.variables = defaultdict()
        self.license_info = dict()
        self.host_servers = None
        self.args = None
        self.env_file = None
        self.test_file = None

    def _get_global_section_var_val(self, var_name):
        return self.user_env.get("GLOBAL", var_name, fallback="") or self.user_env.get(
            "Global", var_name, fallback=""
        )

    def get_dev_cfg(self, device_name):
        cfg = None
        if self.user_env.has_section(device_name):
            cfg = self.user_env.items(device_name)
        elif self.host_servers and self.host_servers.has_section(device_name):
            cfg = self.host_servers.items(device_name)

        return dict(cfg) if cfg else {}

    def set_user_defined_env(self, user_env):
        self.user_env = user_env
        self.extract_license_info()
        self.extract_host_servers()

    def extract_host_servers(self):
        host_file = self._get_global_section_var_val("VM_HOST_DEF")
        if host_file:
            self.host_servers = EnvParser(host_file).env

    def retrieve_dev_cfg(self, device_name):
        return self.user_env[device_name]

    def add_var(self, name, value):
        self.variables[name] = value

    def clear_var(self, name):
        self.variables.pop(name, None)

    def get_var(self, name):
        return self.variables.get(name, None)

    def set_license_var(self, lic_type, sub_type, var_name):
        if lic_type not in self.license_info:
            logger.error("Failed to find the license type: %s", lic_type)
            return
        val = self.license_info[lic_type][sub_type.lower()]
        self.add_var(var_name, val)

    def extract_license_info(self):
        file_name = self._get_global_section_var_val("LICENSE_INFORMATION")
        if not file_name:
            return
        with open(file_name, "r", encoding="utf-8") as f:
            rows = csv.DictReader(f)
            self.license_info = {
                r["Type"]: {
                    "sn": r["SN"],
                    "vdom": r["Vdom Lic"],
                    "expire_date": r["Expired Date"],
                }
                for r in rows
            }

    def is_cfg_option_enabled(self, section, option):
        status = self.user_env.get(section, option, fallback="n").lower()
        return status in OPTION_ENABLED_VALUE

    def need_deploy_vm(self):
        return self.is_cfg_option_enabled(
            "GLOBAL", "DEPLOY_NEW_VM"
        ) or self.is_cfg_option_enabled("Global", "DEPLOY_NEW_VM")

    def init_env(self, args):
        self.args = args
        self.set_user_defined_env(EnvParser(self.args.env).env)
        self.env_file = self.args.env
        self.test_file = self.args.script or self.args.group

    def get_vm_host(self, vm_name):
        return self.user_env.get(vm_name, "HOSTED_ON")

    def get_section_var(self, section, variable):
        return self.user_env.get(section, variable, fallback=None)

    def set_section_var(self, section, var_name, var_val):
        if var_val is None:
            logger.error("section:%s var_name:%s var_val %s", section, var_name, var_val)
            return
        self.user_env[section][var_name] = var_val
        return

    def get_env_file_name(self):
        return self.env_file

    def get_test_file_name(self):
        return self.test_file

    def variable_interpolation(self, string):
        #"Gateway Route(.*)\r(.*)- IP:PC_01:ETH1_IPV4, MAC: PC_01:MAC_ETH1\(.*)\r(.*)- Interface:FGT_A:PORT2, VFID:PC_01:REF1, SN: FGT_A:SN"
        pattern = r"[a-zA-Z_]\w*"
        matched = re.findall(rf"{pattern}(?::{pattern})+", string)
        for m in sorted(matched, key=len, reverse=True):
            tokens = m.split(":")
            if len(tokens) == 2:
                section, var_name = m.split(":")

                if section == "GLOBAL":
                    value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                else:
                    value = self.get_section_var(section, var_name)
                if value is not None:
                    string = string.replace(m, value)
            else:
                if len(tokens) == 3:
                    section, var_name = tokens[1], tokens[2]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                elif len(tokens) ==4:
                    section, var_name = tokens[0], tokens[1]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                    section, var_name = tokens[2], tokens[3]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                elif len(tokens) ==5:
                    section, var_name = tokens[1], tokens[2]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                    section, var_name = tokens[3], tokens[4]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                elif len(tokens) == 6:
                    section, var_name = tokens[0], tokens[1]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                    section, var_name = tokens[2], tokens[3]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
                    section, var_name = tokens[4], tokens[5]
                    if section == "GLOBAL":
                        value = self.get_section_var(section, var_name) or self.get_section_var(
                        "Global", var_name
                    )
                    else:
                        value = self.get_section_var(section, var_name)
                    if value is not None:
                        string = string.replace(f"{section}:{var_name}", value)
        return string

    def get_dut(self):
        return self._get_global_section_var_val("DUT")

    def get_dut_info_on_fly(self):
        return self._get_global_section_var_val("DUT_INFO_ON_FLY")

    def get_local_http_server_conf(self):
        ip = self._get_global_section_var_val("LOCAL_HTTP_SERVER_IP")
        port = self._get_global_section_var_val("LOCAL_HTTP_SERVER_PORT")
        return ip, port

    def get_vm_nic(self):
        return self._get_global_section_var_val("VM_NIC")

    def get_vm_os(self):
        return self._get_global_section_var_val("VM_OS")

env = Environment()
# env.get_env_file_name()
