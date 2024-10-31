from lib.core.compiler.compiler import compiler
from lib.services import summary

from .task import Task


class ScriptTask(Task):
    def compile(self):
        compiler.run(self.script)
        summary.add_testscript(self.script)

    def execute(self):
        vm_codes = compiler.retrieve_vm_codes(self.script)
        self.execute_script(self.script, vm_codes, self.devices)
