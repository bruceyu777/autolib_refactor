from pathlib import Path

from lib.services import summary

from ..compiler.compiler import compiler
from .task import Task


class ScriptTask(Task):
    def compile(self):
        compiler.run(self.script)
        summary.add_testscript(Path(self.script).stem)

    def execute(self):
        vm_codes = compiler.retrieve_vm_codes(self.script)
        self.execute_script(self.script, vm_codes, self.devices)
