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
        self.preprocess()

    def preprocess(self):
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
    @property
    def env(self):
        config_parser = ConfigParser()
        config_parser.read(self.converted_file)
        return config_parser



if __name__ == "__main__":
    envParser = EnvParser("./testcases/fgt.env")
    print(envParser.env["FGT_A"])
    print("connection" in envParser.env["FGT_A"])
