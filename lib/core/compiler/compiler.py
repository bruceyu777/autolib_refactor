from lib.services import env, logger

from .lexer import Lexer
from .parser import Parser


class Compiler:
    def __init__(self):
        self.files = {}
        self.devices = set()

    def _compile_file(self, file_name):
        if file_name in self.files:
            return
        in_debug_mode = getattr(logger, "in_debug_mode", False)
        lexer = Lexer(file_name, dump_token=in_debug_mode)
        tokens, lines = lexer.parse()
        parser = Parser(file_name, tokens, lines)
        vm_codes, devices, called_files = parser.run(deump_vm_codes=in_debug_mode)

        self.files[file_name] = vm_codes
        self.devices |= devices

        for f, current_device in called_files:
            f = env.variable_interpolation(f, current_device=current_device)
            self._compile_file(f)

    def run(self, file_name):
        self._compile_file(file_name)
        logger.debug("Compiled %s", file_name)

    def retrieve_vm_codes(self, file_name):
        return self.files[file_name]

    def retrieve_devices(self):
        return self.devices


compiler = Compiler()
