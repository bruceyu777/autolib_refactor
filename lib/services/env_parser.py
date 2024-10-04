import os
import re
from configparser import ConfigParser, NoOptionError

from lib.services.output import output
from lib.utilities.exceptions import FileNotExist, ScriptSyntaxError

CONVERTED_ENV = "converted.env"


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

    @property
    def global_section(self):
        if self._global_section is None:
            for section in self.sections():
                if section.lower() == "global":
                    self._global_section = section
                    break
            else:
                raise ScriptSyntaxError("Global section not found")
        return self._global_section

    def is_option_enabled(self, section, option, fallback=False):
        if section.lower() == "global":
            section = self.global_section
        try:
            value = self.get(section, option)
            value = value.lower()
            if value not in FosConfigParser.BOOLEAN_STATES:
                print(
                    "Invalid value for bool option %s in section %s" % (option, section)
                )
                print(
                    "Valid values are: %s" % ", ".join(FosConfigParser.BOOLEAN_STATES)
                )
                return fallback
            return self.BOOLEAN_STATES[value]
        except NoOptionError:
            return fallback

    def get_global_option_value(self, option, fallback=""):
        return self.get(self.global_section, option, fallback=fallback)

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


class EnvParser:
    def __init__(self, env_file):
        if not os.path.exists(env_file):
            raise FileNotExist(env_file)
        self.env_file = env_file
        self.converted_file = output.compose_summary_file(CONVERTED_ENV)
        self.section_commented = False
        self.config = FosConfigParser()
        self.run()

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

        with open(self.converted_file, "w") as f:
            for line in lines:
                if re.match(r"#\s*\[.*\]", line):
                    self.section_commented = True
                elif re.match(r"\[.+\]", line):
                    self.section_commented = False
                if not self.section_commented:
                    f.write(line.strip() + "\n")

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
        self._preprocess()
        self.config.read(self.converted_file)
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
