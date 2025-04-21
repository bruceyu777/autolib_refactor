import os
from pathlib import Path

from lib.utilities import FileNotExist

from .compiler import compiler
from .debugger import Debugger
from .vm_code import VMCode


class Script:
    def __init__(self, source_file):
        if not os.path.exists(source_file):
            raise FileNotExist(source_file)
        self.source_file = source_file
        compiler.run(self.source_file)
        self.vm_codes = compiler.retrieve_vm_codes(self.source_file)
        with open(self.source_file, "r", encoding="utf-8") as f:
            self.lines = [line.strip() for line in f]
        self._debugger = Debugger(self.lines, self.vm_codes)

    def get_script_line(self, line_number):
        return self.lines[line_number - 1]

    def update_code_to_execute(self, program_counter):
        code = self.vm_codes[program_counter]
        if code.line_number is not None:
            program_counter = self.debug_run(code.line_number - 1, program_counter)
            code = self.vm_codes[program_counter]
        return program_counter, code

    def get_program_counter_limit(self):
        return len(self.vm_codes)

    def get_compiled_code_line(self, line_number):
        return self.vm_codes[line_number]

    def get_all_involved_devices(self):
        return compiler.devices

    @property
    def id(self):
        return Path(self.source_file).stem

    def __str__(self):
        return self.source_file

    def breakpoint(self):
        self._debugger.breakpoint()

    def debug_run(self, line_number, program_counter):
        return self._debugger.run(line_number, program_counter)


class Group(Script):

    def __init__(self, source_file):
        super().__init__(source_file)
        self.included_scripts = {}

    def parse(self, executor_cls):
        with executor_cls(self, [], False) as executor:
            executor.execute()
            self.included_scripts = {
                line_number: Script(source_file)
                for line_number, source_file in executor.get_all_scripts().items()
            }


class IncludeScript(Script):
    def __init__(self, source_file, current_device=None):
        super().__init__(source_file)
        self.device = current_device
        if current_device is not None:
            self.vm_codes.insert(
                0,
                VMCode(
                    None,
                    "with_device",
                    (current_device,),
                ),
            )
