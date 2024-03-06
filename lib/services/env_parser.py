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
                    f.write(line)

    def _dereference(self):
        pattern = r"[a-zA-Z_]\w*"
        prog = re.compile(rf"(?P<section_name>{pattern}):\s*(?P<key_name>{pattern})")

        for section in self.config.sections():
            for key, value in self.config.items(section):
                # print(key, value)
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
            print(section)
            for key, value in self.config.items(section):
                print(f"key: {key}, value:{value}.")

if __name__ == "__main__":
    envParser = EnvParser("./lib/testcases/env/fgt.env")
    # print(envParser.env["FGT_A"])
    # envParser.run()
    envParser.show()
    # print("connection" in envParser.env["FGT_A"])
