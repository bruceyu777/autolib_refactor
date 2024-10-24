from lib.services import summary

from ..compiler.compiler import compiler
from ..compiler.group_parser import GroupParser
from .task import Task


class GroupTask(Task):
    def __init__(self, script):
        super().__init__(script)
        self.group_parser = GroupParser()

    def compile(self):
        self.group_parser.parse(self.script)

        for script in self.group_parser.scripts.values():
            compiler.run(script)
            summary.add_testscript(script)

    def execute(self):
        for script in self.group_parser.scripts.values():
            self.keepalive_devices()
            vm_codes = compiler.retrieve_vm_codes(script)
            self.execute_script(script, vm_codes, self.devices)
