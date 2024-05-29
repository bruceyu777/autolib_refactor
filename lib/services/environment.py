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
        logger.info("user_env: %s", self.user_env)
        logger.info("section:%s, variable: %s", section, variable)
        logger.info("self.user_env.get(section, variable, fallback=None): %s", self.user_env.get(section, variable, fallback=None))
        return self.user_env.get(section, variable, fallback=None)

    @staticmethod
    def escape_single_percent(var_val):
        return re.sub("%", "%%", var_val)

    def set_section_var(self, section, var_name, var_val):
        if var_val is None:
            logger.error("section:%s var_name:%s var_val %s", section, var_name, var_val)
            return
        var_val = self.escape_single_percent(var_val)
        self.user_env[section][var_name] = var_val
        return

    def get_env_file_name(self):
        return self.env_file

    def get_test_file_name(self):
        return self.test_file

    def _update_var_value(self, var_val_dict, section, var_name):
        if section == "GLOBAL":
            value = self.get_section_var(section, var_name) or self.get_section_var(
                "Global", var_name
            )
        else:
            value = self.get_section_var(section, var_name)
        var_val_dict.update({f"{section}:{var_name}": value})

    def _interpolate_var_value(self, string, var_value_dict):
        var_val_dict_items = sorted(var_value_dict.items(), key=lambda item: item[0], reverse=True)
        for var, value in var_val_dict_items:
            if value is not None:
                string = string.replace(var, value)
        return string

    def variable_interpolation(self, string):
        #"Gateway Route(.*)\r(.*)- IP:PC_01:ETH1_IPV4, MAC: PC_01:MAC_ETH1\(.*)\r(.*)- Interface:FGT_A:PORT2, VFID:PC_01:REF1, SN: FGT_A:SN"
        pattern = r"[a-zA-Z_]\w*"
        matched = re.findall(rf"{pattern}(?::{pattern})+", string)
        var_value_dict = dict()
        for m in sorted(matched, key=len, reverse=True):
            tokens = m.split(":")
            tokens_number = len(tokens)
            if tokens_number % 2 == 0:
                for i in range(0, tokens_number, 2):
                    self._update_var_value(var_value_dict, tokens[i], tokens[i+1])
            else:
                for i in range(1, tokens_number, 2):
                    self._update_var_value(var_value_dict, tokens[i], tokens[i+1])
        logger.info("var_value_dict is %s", var_value_dict)
        return self._interpolate_var_value(string, var_value_dict)

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

    def get_license_info(self):
        return self._get_global_section_var_val("LICENSE_INFORMATION")

    def need_retry_expect(self):
        return self.is_cfg_option_enabled(
            "GLOBAL", "RETRY_EXPECT"
        ) or self.is_cfg_option_enabled("Global", "RETRY_EXPECT")

    def need_keep_alive(self):
        return self._get_global_section_var_val("KEEP_ALIVE")

    def filter_env_section_items(self, section_name, start_string):
        res = {}

        for section in self.user_env.sections():
            if section == section_name:
                for key, value in self.user_env.items(section):
                    tokens = key.split("_")
                    if tokens[0] == start_string:
                        res[tokens[1]] = value
        return res

env = Environment()
# env.get_env_file_name()

if __name__ == "__main__":
    # env.get_dut()
    env_parser = EnvParser("./lib/testcases/env/fgt.env")
    env.set_user_defined_env(env_parser.env)
    env.set_section_var("GLOBAL", "local_http_server_port", "aHR0cHM6Ly8xNzIuMTguNjIuODY6NDQ0My8%%%3D")
    res  = env_parser.show()
    res = env.get_section_var("GLOBAL", "local_http_server_port")
    print(res)

