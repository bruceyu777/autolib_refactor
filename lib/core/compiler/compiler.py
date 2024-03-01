import os

from lib.services import env, logger
from lib.utilities.exceptions import FileNotExist

from .lexer import Lexer
from .parser import Parser


class Compiler:
    def __init__(self):
        self.files = dict()
        self.devices = set()

    def _compile_file(self, file_name):
        if not os.path.exists(file_name):
            raise FileNotExist(file_name)
        if file_name in self.files:
            return
        lexer = Lexer(file_name)
        tokens, lines = lexer.parse()
        # print(tokens)
        parser = Parser(file_name, tokens, lines)
        vm_codes, devices, called_files = parser.run()

        self.files[file_name] = vm_codes
        self.devices = self.devices | devices

        for f in called_files:
            f = env.variable_interpolation(f)
            self._compile_file(f)

    def run(self, file_name):
        self._compile_file(file_name)
        logger.notice("Compiled %s", file_name)

    def retrieve_vm_codes(self, file_name):
        return self.files[file_name]

    def retrieve_devices(self):
        return self.devices


compiler = Compiler()
