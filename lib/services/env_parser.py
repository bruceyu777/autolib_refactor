import os
import re

from configparser import ConfigParser

from lib.utilities.exceptions import FileNotExist
from lib.services.output import output


CONVERTED_ENV = "converted.env"

class EnvParser:
    def __init__(self, env_file):
        self.env_file = env_file
        self.converted_file = output.compose_summary_file(CONVERTED_ENV)
        self.section_commented = False
        self.config = ConfigParser()
        self.run()


    def _preprocess(self):
        if not os.path.exists(self.env_file):
            raise FileNotExist(self.env_file)

        with open(self.env_file, "r") as f:
            lines = f.readlines()

        with open(self.converted_file, "w") as f:
            for line in lines:
                # if line.startswith('# [FGT_B]'):
                #     breakpoint()
                if re.match(r"#\s*\[.*\]", line):
                    self.section_commented = True
                elif re.match(r"\[.+\]", line):
                    self.section_commented = False
                if not self.section_commented:
                    f.write(line.strip() + "\n")

    def _dereference(self):
        pattern = r"[a-zA-Z_]\w*"
        prog = re.compile(rf"(?P<section_name>{pattern}):\s*(?P<key_name>{pattern})")

        for section in self.config.sections():
            for key, value in self.config.items(section):
                result = prog.match(value)
                if result:
                    section_name = result.group("section_name")
                    key_name = result.group("key_name")
                    if self.config.has_section(section_name) and self.config.has_option(section_name, key_name):
                        self.config.set(section, key, self.config.get(section_name, key_name))

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
                print(section)
                for key, value in self.config.items(section):
                    print(key)
                    if key.startswith("field"):
                        print(f"key: {key}, value:{value}.")

    def filter_section_items(self, section_name, start_string):
        res = {}
        for section in self.config.sections():
            if section == section_name:
                for key, value in self.config.items(section):
                    tokens = key.split("_")
                    if tokens[0] == start_string:
                        res[tokens[1]] = value
        return res


if __name__ == "__main__":
    envParser = EnvParser("./lib/testcases/env/fgt.env")
    # print(envParser.env["FGT_A"])
    # envParser.run()
    res = envParser.show()
    envParser.env.set("GLOBAL", "local_http_server_port", "aHR0cHM6Ly8xNzIuMTguNjIuODY6NDQ0My8%3D")
    # envParser.get
    # print(res)

    res = envParser.show()
    print(res)
    # print("connection" in envParser.env["FGT_A"])
