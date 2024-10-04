import csv
import re
from collections import defaultdict

from .env_parser import EnvParser, FosConfigParser
from .log import logger

OPTION_ENABLED_VALUE = ("y", "yes", "true", "enable", "on", "enabled")


class DeviceConfig(dict):

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            real_key = self._get_real_key(key)
            if real_key is not None:
                return super().__getitem__(real_key)
            raise

    def _get_real_key(self, key):
        if key in self.keys():
            return key
        matched_keys = [k for k in self.keys() if k.lower() == key]
        return matched_keys[0] if len(matched_keys) == 1 else None

    def __contains__(self, key):
        real_key = self._get_real_key(key)
        return super().__contains__(real_key)

    def get(self, key, default=None):
        real_key = self._get_real_key(key)
        if real_key is not None:
            return super().get(real_key, default)
        return default


class Environment:
    fos_device_types = ("FFW", "FVM", "FGT")

    def __init__(self):
        self.user_env: FosConfigParser = None
        self.variables = defaultdict()
        self.license_info = {}
        self.host_servers = None
        self.args = None
        self.env_file = None
        self.test_file = None

    def _get_global_section_option_value(self, option, fallback=""):
        return self.user_env.get_global_option_value(option, fallback=fallback)

    def get_device_list(self):
        return self.user_env.get_device_list()

    def is_vm_device(self, device_name):
        return (
            device_name.startswith("FVM")
            or device_name.startswith("FFW")
            and "HOSTED_ON" in self.get_dev_cfg(device_name)
        )

    def is_fos_deivce(self, device_name):
        return any(map(device_name.startswith, Environment.fos_device_types))

    def get_dev_cfg(self, device_name):
        cfg = None
        if self.user_env.has_section(device_name):
            cfg = self.user_env.items(device_name)
        elif self.host_servers and self.host_servers.has_section(device_name):
            cfg = self.host_servers.items(device_name)

        return DeviceConfig(cfg if cfg else {})

    def set_user_defined_env(self, user_env):
        self.user_env: FosConfigParser = user_env
        self.extract_license_info()
        self.extract_host_servers()

    def extract_host_servers(self):
        host_file = self._get_global_section_option_value("VM_HOST_DEF")
        if host_file:
            self.host_servers = EnvParser(host_file).env

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
        file_name = self._get_global_section_option_value("LICENSE_INFORMATION")
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

    def is_cfg_option_enabled(self, section, option, fallback=False):
        return self.user_env.is_option_enabled(section, option, fallback=fallback)

    def need_deploy_vm(self):
        return self.is_cfg_option_enabled("GLOBAL", "DEPLOY_NEW_VM")

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
        logger.info(
            "self.user_env.get(section, variable, fallback=None): %s",
            self.user_env.get(section, variable, fallback=None),
        )
        return self.user_env.get(section, variable, fallback=None)

    @staticmethod
    def escape_single_percent(var_val):
        return re.sub("%", "%%", var_val)

    def set_section_var(self, section, var_name, var_val):
        if var_val is None:
            logger.error(
                "section:%s var_name:%s var_val %s", section, var_name, var_val
            )
            return
        var_val = self.escape_single_percent(var_val)
        self.user_env[section][var_name] = var_val
        return

    def get_env_file_name(self):
        return self.env_file

    def get_test_file_name(self):
        return self.test_file

    def _update_var_value(self, var_val_dict, section, var_name):
        value = self.get_section_var(section, var_name)
        var_val_dict.update({f"{section}:{var_name}": value})

    def variable_interpolation(self, content):

        def _replace(original, section):
            section_variable_dict = self.get_dev_cfg(section)
            for k in sorted(section_variable_dict, key=len, reverse=True):
                section_key = f"{section}:{k}"
                if section_key in original:
                    original = original.replace(section_key, section_variable_dict[k])
            return original

        existed_sections = (s for s in self.user_env.sections() if f"{s}:" in content)
        for section in existed_sections:
            content = _replace(content, section)

        logger.debug("replaced content: '%s'", content)
        return content

    def get_device_hardware_generation(self, device_name, fallback="1"):
        return self.user_env.get(device_name, "PLATFORMGENERATION", fallback=fallback)

    def get_dut(self):
        return self._get_global_section_option_value("DUT")

    def get_dut_info_on_fly(self):
        return self._get_global_section_option_value("DUT_INFO_ON_FLY")

    def get_local_http_server_conf(self):
        ip = self._get_global_section_option_value("LOCAL_HTTP_SERVER_IP")
        port = self._get_global_section_option_value("LOCAL_HTTP_SERVER_PORT")
        return ip, port

    def get_vm_nic(self):
        return self._get_global_section_option_value("VM_NIC")

    def get_vm_os(self):
        return self._get_global_section_option_value("VM_OS")

    def get_license_info(self):
        return self._get_global_section_option_value("LICENSE_INFORMATION")

    def need_retry_expect(self):
        return self.is_cfg_option_enabled("GLOBAL", "RETRY_EXPECT")

    def need_keep_alive(self):
        return self.is_cfg_option_enabled("GLOBAL", "KEEP_ALIVE")

    def filter_env_section_items(self, section_name, start_string):
        selected_items = {}
        for section in self.user_env.sections():
            if section == section_name:
                for key, value in self.user_env.items(section):
                    tokens = key.split("_")
                    if tokens[0] == start_string:
                        selected_items[tokens[1]] = value
        return selected_items


env = Environment()


if __name__ == "__main__":
    env_parser = EnvParser("./lib/testcases/env/fgt.env")
    env.set_user_defined_env(env_parser.env)
    value_for_test = "aHR0cHM6Ly8xNzIuMTguNjIuODY6NDQ0My8%%%3D"
    env.set_section_var("GLOBAL", "local_http_server_port", value_for_test)
    env_parser.show()
    result = env.get_section_var("GLOBAL", "local_http_server_port")
    assert result == value_for_test
    decoded_script = env.variable_interpolation(
        "This is a test GLOBAL:MGMT_IP-FGT_A:MGMT-FGT_A:MGMT_GW"
    )
    assert (
        decoded_script == "This is a test 172.18.57.22 255.255.255.0-mgmt-172.18.57.1"
    )
