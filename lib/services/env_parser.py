import os
import re
from configparser import _UNSET, ConfigParser

from lib.services.output import output
from lib.utilities.exceptions import FileNotExist, ScriptSyntaxError


class FosConfigParser(ConfigParser):

    BOOLEAN_STATES = {
        "1": True,
        "yes": True,
        "true": True,
        "on": True,
        "y": True,
        "0": False,
        "no": False,
        "false": False,
        "off": False,
        "n": False,
        "N": False,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._global_section = None

    def _section(self, section):
        return self.global_section if section.lower() == "global" else section

    @property
    def global_section(self):
        if self._global_section is None:
            for section in self.sections():
                if section.lower() == "global":
                    self._global_section = section
                    break
            else:
                raise ScriptSyntaxError("GLOBAL section not found")
        return self._global_section

    def is_option_enabled(self, section, option, fallback=False):
        section = self._section(section)
        value = self.get(section, option, fallback=_UNSET)
        if value is _UNSET:
            return fallback
        value = value.lower()
        if value not in FosConfigParser.BOOLEAN_STATES:
            print("Invalid value for bool option %s in section %s" % (option, section))
            print("Valid values are: %s" % ", ".join(FosConfigParser.BOOLEAN_STATES))
        return self.BOOLEAN_STATES.get(value, fallback)

    def get_device_list(self):
        return [
            d
            for d in self.sections()
            if self.has_option(d, "CONNECTION") or self.has_option(d, "Connection")
        ]

    def optionxform(self, optionstr):
        # by default the option keys are case insensitive
        # override this func to make it case sensitive
        return optionstr

    def _lookup_real_option(self, section, option):
        if not self.has_section(section):
            return None
        existed_options = self.options(section)
        if option in existed_options:
            return option
        lower_case_option = option.lower()
        matched_options = [o for o in existed_options if o.lower() == lower_case_option]
        return matched_options[0] if len(matched_options) == 1 else None

    # pylint: disable=redefined-builtin
    def get(self, section, option, *, raw=False, vars=None, fallback=None):
        section = self._section(section)
        option = self._lookup_real_option(section, option)
        return (
            fallback
            if option is None
            else super().get(section, option, raw=raw, vars=vars)
        )

    def has_option(self, section, option):
        section = self._section(section)
        option = self._lookup_real_option(section, option)
        return False if option is None else super().has_option(section, option)

    def set(self, section, option, value=None):
        section = self._section(section)
        matched_option = self._lookup_real_option(section, option)
        return super().set(section, matched_option or option, value)


class EnvParser:
    def __init__(self, env_file, dump_parsed_env=False):
        if not os.path.exists(env_file):
            raise FileNotExist(env_file)
        self.env_file = env_file
        self.section_commented = False
        self.config = FosConfigParser()
        self.run()
        if dump_parsed_env:
            self._dump_procecssed_config()

    def _dump_procecssed_config(self):
        filename = f"Converted_{os.path.basename(self.env_file)}"
        file_path = output.compose_summary_file(filename)
        with open(file_path, "w") as processed_config:
            self.config.write(processed_config)

    def finalize_value(self, value):
        read_from_prefix = "readfile->>"
        if not value.startswith(read_from_prefix):
            return value

        file_path = value[len(read_from_prefix) :].strip()
        with open(file_path, encoding="utf-8") as f:
            value = f.read()
        return value

    def _preprocess(self):
        with open(self.env_file, "r") as f:
            lines = f.readlines()
        content = ""
        for line in lines:
            if re.match(r"#\s*\[.*\]", line):
                self.section_commented = True
            elif re.match(r"\[.+\]", line):
                self.section_commented = False
            if not self.section_commented:
                content += f"{line.strip()}\n"
        return content

    def _parse_value(self, value, parse_pattern, visited):
        # support nested reference and multiple reference for a value
        result = parse_pattern.findall(value)
        if result:
            for section, key in set(result):
                if (section, key) in visited:
                    raise SyntaxError(
                        f"Error: circular reference detected for {section}:{key}"
                    )
                visited.add((section, key))
                value = value.replace(f"{section}:{key}", self.config.get(section, key))
            return self._parse_value(value, parse_pattern, visited)
        return value

    def _dereference(self):
        # TODO: to support variable name not end with space
        sections = "|".join(self.config.sections())
        parse_pattern = re.compile(
            rf"(?P<section_name>{sections}):\s*(?P<key_name>[^\s]+)"
        )
        for section in self.config.sections():
            for key, value in self.config.items(section):
                visited = {
                    (section, key),
                }
                parsed_value = self._parse_value(value, parse_pattern, visited)
                parsed_value = self.finalize_value(parsed_value)
                self.config.set(section, key, parsed_value)

    @property
    def env(self):
        return self.config

    def run(self):
        process_config = self._preprocess()
        self.config.read_string(process_config)
        self._dereference()

    def show(self):
        for section in self.config.sections():
            for key, value in self.config.items(section):
                print(section, key, value)
            if section == "ORIOLE":
                for key, value in self.config.items(section):
                    print(key)
                    if key.startswith("field"):
                        print(f"key: {key}, value:{value}.")

    def filter_section_items(self, section_name, start_string):
        res = {}
        for section in self.config.sections():
            if section == section_name:
                for key, value in self.config.items(section):
                    token, real_key, *_ = key.split("_")
                    if token == start_string:
                        res[real_key] = value
        return res


if __name__ == "__main__":
    envParser = EnvParser("./lib/testcases/env/fgt.env")
    envParser.show()
    envParser.env.set(
        "GLOBAL", "local_http_server_ip", r"aHR0cHM6Ly8xNzIuMTguNjIuODY6NDQ0My8%%3D"
    )
    envParser.show()
    try:
        EnvParser("./lib/testcases/env/fgt_wrong.env")
        assert False
    except ScriptSyntaxError as e:
        print(e.message)
        assert True
