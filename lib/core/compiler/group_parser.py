from ..executor.executor import Executor
from .compiler import compiler


class GroupParser:
    def __init__(self):
        self.test_scripts = {}

    def parse(self, group_file):
        compiler.run(group_file)
        vm_codes = compiler.retrieve_vm_codes(group_file)
        with Executor(group_file, vm_codes, [], False, "GROUP") as executor:
            executor.execute()
            self.test_scripts = executor.get_all_scripts().copy()

    @property
    def scripts(self):
        return self.test_scripts
