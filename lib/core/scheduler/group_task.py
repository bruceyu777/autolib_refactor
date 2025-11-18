from time import perf_counter

from lib.core.compiler import Group
from lib.core.executor import Executor
from lib.services import logger, summary
from lib.utilities import BlockingException

from .task import Task


class GroupTask(Task):

    script_init_class = Group

    def compile(self):
        self.script.parse(Executor)
        for script in self.script.included_scripts.values():
            summary.add_testscript(script)

    def execute(self):
        for script in self.script.included_scripts.values():
            self.keepalive_devices()
            try:
                self.execute_script(script, self.devices)
            except BlockingException:
                raise
            except Exception as e:
                logger.exception("Skip script(%s) run", script.source_file)
                if self.non_strict_mode:
                    continue
                raise e

    def run(self, args):
        t1 = perf_counter()
        self.compile()
        t2 = perf_counter()
        logger.info("Compile scripts used %.1f s", t2 - t1)
        super().run(args)
