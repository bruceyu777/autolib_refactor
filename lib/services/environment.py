import csv
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from lib.utilities import OperationFailure, sleep_with_progress

from .env_parser import EnvParser, FosConfigParser
from .image_server import ImageServer
from .log import logger

BUFFER_CLEAN_PATTERN_SOURCE = (
    Path(__file__).resolve().parent / "static" / "buffer_clean_patterns.json"
)


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
        lowercase_key = key.lower()
        matched_keys = [k for k in self.keys() if k.lower() == lowercase_key]
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
        self._buffer_clean_pattern = None

    def _buffer_clean_pattern_source_filepath(self):
        filepath = self.user_env.get("GLOBAL", "EXEMPT_ERROR_PATTERN_SOURCE")
        if not (filepath and Path(filepath).exists()):
            logger.debug("Fall back to use default clean buffer pattern source.")
            filepath = BUFFER_CLEAN_PATTERN_SOURCE
        return filepath

    def get_performance_scale(self, dev_name):
        platform_name = self.user_env.get(dev_name, "PLATFORM", fallback="")
        try:
            platform_number_str = re.search(r"(\d+)[^\d]", platform_name).group(1)
            platform_number = int(platform_number_str)
        except (AttributeError, ValueError):
            platform_number = 100
            logger.error(
                "Cannot get platform number from platform name %s", platform_name
            )
        if platform_number <= 100:
            return 1.2
        if platform_number > 100:
            return 0.8
        return 1

    def get_actual_timer(self, dev_name, time_units):
        if self.is_cfg_option_enabled("GLOBAL", "DYNAMIC_SCALE_TIMER"):
            device = dev_name if self.is_fos_device(dev_name) else self.get_dut()
            return round(time_units * self.get_performance_scale(device), 2)
        return time_units

    @property
    def buffer_clean_pattern(self):
        if self._buffer_clean_pattern is None:
            pattern_source_filepath = self._buffer_clean_pattern_source_filepath()
            with open(pattern_source_filepath, "r", encoding="utf-8") as f:
                clean_patterns = json.load(f)
                self._buffer_clean_pattern = clean_patterns
        return self._buffer_clean_pattern

    def get_buffer_clean_pattern_by_dev_type(self, device_type):
        if device_type in self.fos_device_types:
            device_type = "FOS"
        patterns = self.buffer_clean_pattern.get(device_type, {})
        return {k: re.compile(v) for k, v in patterns.items()}

    def get_device_list(self):
        return self.user_env.get_device_list()

    def is_vm_device(self, device_name):
        return (
            device_name.startswith("FVM")
            or device_name.startswith("FFW")
            and "HOSTED_ON" in self.get_dev_cfg(device_name)
        )

    def is_fos_device(self, device_name):
        return any(map(device_name.startswith, Environment.fos_device_types))

    def is_running_on_vm(self):
        return self.is_cfg_option_enabled("GLOBAL", "RUNNING_AS_VM")

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
        host_file = self.user_env.get("GLOBAL", "VM_HOST_DEF")
        if host_file:
            self.host_servers = EnvParser(
                host_file, dump_parsed_env=self.args.debug
            ).env

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
        file_name = self.user_env.get("GLOBAL", "LICENSE_INFORMATION")
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

    def get_restore_image_args(self):
        return self.args.release, self.args.build, self.args.reset, self.args.burn

    def need_burn_fos_image(self):
        return self.args.burn

    def need_deploy_vm(self):
        return self.is_cfg_option_enabled("GLOBAL", "DEPLOY_NEW_VM")

    def init_env(self, args):
        self.args = args
        self.set_user_defined_env(
            EnvParser(self.args.env, dump_parsed_env=self.args.debug).env
        )
        self.env_file = self.args.env
        self.test_file = self.args.script or self.args.group
        if self.args.wait_image_ready_timer:
            self.wait_for_image_ready()

    def wait_for_image_ready(self):
        start_time = time.time()
        timeout_timer = self.args.wait_image_ready_timer * 60 * 60
        while time.time() - start_time <= timeout_timer:
            try:
                ImageServer().get_build_files(
                    self.args.project, self.args.release, self.args.build
                )
                return True
            except OperationFailure:
                logger.warning(
                    "Will retry to check the availability of the requested image later!"
                )
                sleep_with_progress(10 * 60)
        raise OperationFailure(
            f"No Image available for {self.args.project}(v{self.args.release}build{self.args.build})"
        )

    def get_vm_host(self, vm_name):
        return self.user_env.get(vm_name, "HOSTED_ON")

    def get_section_var(self, section, variable, fallback=None):
        logger.debug(
            "self.user_env.get(%s, %s, fallback=None): %s",
            section,
            variable,
            self.user_env.get(section, variable, fallback=fallback),
        )
        return self.user_env.get(section, variable, fallback=fallback)

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

    def variable_interpolation(self, content, current_device=None):

        def _replace(original, section, include_section=True):
            section_variable_dict = self.get_dev_cfg(section)
            for k in sorted(section_variable_dict, key=len, reverse=True):
                variable_to_replace = f"{section}:{k}" if include_section else k
                if variable_to_replace in original:
                    original = original.replace(
                        variable_to_replace, section_variable_dict[k]
                    )
            return original

        existed_sections = (s for s in self.user_env.sections() if f"{s}:" in content)
        for section in existed_sections:
            content = _replace(content, section)
        if current_device:
            content = _replace(content, current_device, include_section=False)

        logger.debug("replaced content: '%s'", content)
        return content

    def get_device_hardware_generation(self, device_name, fallback="1"):
        return self.user_env.get(device_name, "PLATFORM_GENERATION", fallback=fallback)

    def get_dut(self):
        return self.user_env.get("GLOBAL", "DUT")

    def is_fap_dut(self):
        dut = self.get_dut()
        return dut and dut.startswith("FAP")

    def get_fap_controller(self, fap):
        return self.user_env.get(fap, "CONTROLLER")

    def get_dut_info_on_fly(self):
        return self.user_env.get("GLOBAL", "DUT_INFO_ON_FLY")

    def get_local_http_server_conf(self):
        ip = self.user_env.get("GLOBAL", "LOCAL_HTTP_SERVER_IP")
        port = self.user_env.get("GLOBAL", "LOCAL_HTTP_SERVER_PORT")
        return ip, port

    def get_vm_nic(self):
        return self.user_env.get("GLOBAL", "VM_NIC")

    def get_vm_os(self):
        return self.user_env.get("GLOBAL", "VM_OS")

    def get_license_info(self):
        return self.user_env.get("GLOBAL", "LICENSE_INFORMATION")

    def need_retry_expect(self):
        return self.is_cfg_option_enabled("GLOBAL", "RETRY_EXPECT")

    def need_keep_alive(self):
        return self.is_cfg_option_enabled("GLOBAL", "KEEP_ALIVE")

    def filter_section_items(self, section_name, prefix):
        for section in self.user_env.sections():
            if section == section_name:
                return {
                    k[len(prefix) :]: v
                    for k, v in self.user_env.items(section)
                    if k.startswith(prefix)
                }
        return {}


env = Environment()


if __name__ == "__main__":
    env_parser = EnvParser("./lib/testcases/env/fgt.env")
    env.set_user_defined_env(env_parser.env)
    value_for_test = "aHR0cHM6Ly8xNzIuMTguNjIuODY6NDQ0My8%%%3D"
    env.set_section_var("GLOBAL", "LOCAL_HTTP_SERVER_PORT", value_for_test)
    result = env.get_section_var("GLOBAL", "LOCAL_HTTP_SERVER_PORT")
    assert result == value_for_test
    decoded_script = env.variable_interpolation(
        "This is a test GLOBAL:MGMT_IP-FGT_A:MGMT-FGT_A:MGMT_GW"
    )
    assert (
        decoded_script == "This is a test 172.18.57.22 255.255.255.0-mgmt-172.18.57.1"
    )
