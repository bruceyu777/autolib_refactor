import os
import sys
import webbrowser

from lib.services import env, launch_webserver_on, logger, oriole, output, summary

from .group_task import GroupTask
from .task import Task as ScriptTask


class Job:
    def __init__(self, args):
        self.args = args
        self.log_job_start_info()

    def log_job_start_info(self):
        if self.args.script:
            logger.info("Test Script: %s", self.args.script)
            test_file = self.args.script
        else:
            logger.info("Test Group: %s", self.args.group)
            test_file = self.args.group

        summary.dump_str_to_brief_summary(
            f"# Environment File: {self.args.env}\n# Test File: {test_file}\n"
        )

    def init_task(self):
        return (
            ScriptTask(self.args.script, non_strict_mode=self.args.non_strict)
            if self.args.script
            else GroupTask(self.args.group, non_strict_mode=self.args.non_strict)
        )

    def execute_script(self):
        task = self.init_task()
        task.run(self.args)
        if not self.args.debug:
            output.zip_autotest_log()

    def start_http_server(self):
        ip, port = env.get_local_http_server_conf()
        if ip and port:
            launch_webserver_on(ip, port)
        else:
            sys.exit(0)

    def init_env(self):
        env.init_env(self.args)
        oriole.set_user_cfg(self.args)

    def _launch_summary_webpage(self):
        host, port = env.get_local_http_server_conf()
        if not host or not port:
            logger.warning("Unable to get IP and PORT for LOCAL_HTTP_SERVER from env.")
            host, port = "127.0.0.1", 8080
            logger.warning("Use default IP and PORT: %s:%s", host, port)
        summary_url = f"http://{host}:{port}/{output.get_current_output_dir()}/summary"
        logger.info("Summary: %s/summary.html", summary_url)
        if self.args.portal:
            webbrowser.open_new(summary_url)

    def create_child_process(self):
        pid = os.fork()
        if pid == 0:
            self.start_http_server()
        else:
            self._launch_summary_webpage()
            self.execute_script()

    def run(self):
        self.init_env()
        self.create_child_process()
